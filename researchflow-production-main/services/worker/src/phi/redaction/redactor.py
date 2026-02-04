"""Safe PHI redaction with consistent tokens.

Replaces detected PHI spans with stable, type-specific tokens.

Example: "Call 555-123-4567" -> "Call [PHI:PHONE:1]"
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class RedactionConfig(BaseModel):
    sensitivity: str = Field(default="high")
    token_prefix: str = Field(default="PHI")


class RedactedSpan(BaseModel):
    start: int
    end: int
    kind: str
    token: str


class RedactionResult(BaseModel):
    redacted_text: str
    spans: List[RedactedSpan]
    mapping: Dict[str, List[str]] = Field(default_factory=dict, description="token -> hashed originals")


class Redactor:
    def __init__(self):
        # Lazy import to avoid heavy deps at import time
        from src.phi.scanner.batch_scanner import HybridDetector

        self._detector = HybridDetector()

    async def redact(self, text: str, config: RedactionConfig) -> RedactionResult:
        detections = await self._detector.detect(text, sensitivity=config.sensitivity)

        # build stable token per kind + ordinal in occurrence order
        spans_sorted = sorted(detections, key=lambda d: (d.start, d.end))
        kind_counts: Dict[str, int] = {}
        redacted_parts: List[str] = []
        cursor = 0
        out_spans: List[RedactedSpan] = []
        mapping: Dict[str, List[str]] = {}

        for d in spans_sorted:
            if d.start < cursor:
                continue
            redacted_parts.append(text[cursor:d.start])
            kind_counts[d.kind] = kind_counts.get(d.kind, 0) + 1
            token = f"[{config.token_prefix}:{d.kind.upper()}:{kind_counts[d.kind]}]"
            redacted_parts.append(token)
            cursor = d.end

            h = hashlib.sha256(d.text.encode("utf-8", errors="ignore")).hexdigest()[:12]
            mapping.setdefault(token, []).append(h)
            out_spans.append(RedactedSpan(start=d.start, end=d.end, kind=d.kind, token=token))

        redacted_parts.append(text[cursor:])
        return RedactionResult(redacted_text="".join(redacted_parts), spans=out_spans, mapping=mapping)
