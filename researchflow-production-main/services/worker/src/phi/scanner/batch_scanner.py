"""Batch PHI scanning.

Hybrid detection:
- Regex patterns (HIPAA + international + custom)
- Optional spaCy NER (PERSON/GPE/LOC/ORG) when available

Supports sensitivity levels and async concurrency.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field

from src.phi.patterns import CUSTOM_PATTERNS, HIPAA_IDENTIFIER_PATTERNS, INTERNATIONAL_PATTERNS
from src.phi.scanner.confidence_scorer import ConfidenceScorer, DetectionFeatures


@dataclass(frozen=True)
class Detection:
    kind: str
    start: int
    end: int
    text: str
    source: str  # regex|spacy
    confidence: float


class BatchProgress(BaseModel):
    processed: int
    total: int


class BatchScanConfig(BaseModel):
    sensitivity: str = Field(default="high")
    allowlist: List[str] = Field(default_factory=list)
    concurrency: int = Field(default=8, ge=1, le=64)
    include_redacted_preview: bool = Field(default=False)


class ItemScanResult(BaseModel):
    item_id: str
    detected: bool
    kinds: List[str]
    detections: List[Dict[str, Any]]


class BatchScanResult(BaseModel):
    total: int
    flagged: int
    results: List[ItemScanResult]


class HybridDetector:
    def __init__(self):
        self._scorer = ConfidenceScorer()
        self._spacy_nlp = None
        self._spacy_available = False

        try:
            import spacy  # type: ignore

            # prefer a small model if present; otherwise fallback to blank english
            try:
                self._spacy_nlp = spacy.load("en_core_web_sm")
            except Exception:
                self._spacy_nlp = spacy.blank("en")
            self._spacy_available = True
        except Exception:
            self._spacy_available = False

    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        pats: Dict[str, List[str]] = {}
        for d in list(HIPAA_IDENTIFIER_PATTERNS.values()) + list(INTERNATIONAL_PATTERNS.values()) + list(CUSTOM_PATTERNS.values()):
            pats.setdefault(d.key, []).extend(d.regexes)
        compiled: Dict[str, List[re.Pattern]] = {}
        for k, regs in pats.items():
            compiled[k] = [re.compile(r, re.IGNORECASE) for r in regs]
        return compiled

    async def detect(self, text: str, sensitivity: str = "high", allowlist: Optional[List[str]] = None) -> List[Detection]:
        allowlist = allowlist or []
        allow_compiled = [re.compile(a, re.IGNORECASE) for a in allowlist if a]
        compiled = self._compile_patterns()

        dets: List[Detection] = []

        def is_allowed(span_text: str) -> bool:
            return any(a.search(span_text) for a in allow_compiled)

        # Regex detections
        for kind, regs in compiled.items():
            for rgx in regs:
                for m in rgx.finditer(text):
                    s, e = m.start(), m.end()
                    t = text[s:e]
                    if not t.strip():
                        continue
                    if is_allowed(t):
                        continue
                    feats = DetectionFeatures(
                        kind=kind,
                        source="regex",
                        length=len(t),
                        has_digits=any(ch.isdigit() for ch in t),
                        has_alpha=any(ch.isalpha() for ch in t),
                    )
                    dets.append(Detection(kind=kind, start=s, end=e, text=t, source="regex", confidence=self._scorer.score(feats)))

        # spaCy NER (context-aware for names/locations)
        if self._spacy_available and self._spacy_nlp is not None:
            doc = await asyncio.to_thread(self._spacy_nlp, text)
            for ent in doc.ents:
                if ent.label_ in {"PERSON"}:
                    kind = "names"
                elif ent.label_ in {"GPE", "LOC"}:
                    kind = "geographic"
                elif ent.label_ in {"ORG"}:
                    kind = "other_unique"
                else:
                    continue

                t = ent.text
                if is_allowed(t):
                    continue
                feats = DetectionFeatures(
                    kind=kind,
                    source="spacy",
                    length=len(t),
                    has_digits=any(ch.isdigit() for ch in t),
                    has_alpha=any(ch.isalpha() for ch in t),
                )
                dets.append(
                    Detection(
                        kind=kind,
                        start=ent.start_char,
                        end=ent.end_char,
                        text=t,
                        source="spacy",
                        confidence=self._scorer.score(feats),
                    )
                )

        # sensitivity filtering
        threshold = {
            "low": 0.55,
            "medium": 0.65,
            "high": 0.75,
            "paranoid": 0.55,  # low threshold but later consumers may fail-closed
        }.get(sensitivity.lower(), 0.75)

        filtered = [d for d in dets if d.confidence >= threshold]
        # Deduplicate overlapping spans by preferring higher confidence
        filtered.sort(key=lambda d: (d.start, -(d.end - d.start), -d.confidence))
        out: List[Detection] = []
        last_end = -1
        for d in filtered:
            if d.start < last_end:
                continue
            out.append(d)
            last_end = d.end
        return out


class BatchScanner:
    def __init__(self):
        self._detector = HybridDetector()

    def list_patterns(self) -> Dict[str, Any]:
        return {
            "hipaa": [p.key for p in HIPAA_IDENTIFIER_PATTERNS.values()],
            "international": [p.key for p in INTERNATIONAL_PATTERNS.values()],
            "custom": [p.key for p in CUSTOM_PATTERNS.values()],
        }

    async def scan_items(
        self,
        items: List[Dict[str, Any]],
        config: BatchScanConfig,
        progress_cb: Optional[Any] = None,
    ) -> BatchScanResult:
        total = len(items)
        sem = asyncio.Semaphore(max(1, min(config.concurrency, 64)))
        processed = 0
        results: List[ItemScanResult] = []

        async def one(item: Dict[str, Any]) -> ItemScanResult:
            nonlocal processed
            async with sem:
                dets = await self._detector.detect(
                    item.get("content", ""),
                    sensitivity=config.sensitivity,
                    allowlist=config.allowlist,
                )
                kinds = sorted({d.kind for d in dets})
                res = ItemScanResult(
                    item_id=str(item.get("item_id")),
                    detected=len(dets) > 0,
                    kinds=kinds,
                    detections=[
                        {
                            "kind": d.kind,
                            "start": d.start,
                            "end": d.end,
                            "source": d.source,
                            "confidence": d.confidence,
                        }
                        for d in dets
                    ],
                )
                processed += 1
                if progress_cb:
                    await progress_cb(BatchProgress(processed=processed, total=total))
                return res

        tasks = [asyncio.create_task(one(i)) for i in items]
        ordered = await asyncio.gather(*tasks)
        results.extend(ordered)
        flagged = sum(1 for r in results if r.detected)
        return BatchScanResult(total=total, flagged=flagged, results=results)


class BatchScannerCompat(BatchScanner):
    """Alias for backward compatibility if needed."""

    pass
