"""De-identification utilities.

Provides:
- Simple k-anonymity validation support (best-effort for free-text)
- Generalization strategies for quasi-identifiers (placeholder hooks)

NOTE: True k-anonymity is usually applied to tabular data; for free-text we
validate absence of direct identifiers and produce a report.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KAnonymityConfig(BaseModel):
    k: int = Field(default=5, ge=2)
    quasi_identifiers: List[str] = Field(default_factory=list)


class DeidentificationReport(BaseModel):
    direct_identifiers_found: bool
    direct_identifier_kinds: List[str] = Field(default_factory=list)
    k_anonymity_target: int
    quasi_identifiers: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class Deidentifier:
    def __init__(self):
        from src.phi.scanner.batch_scanner import HybridDetector

        self._detector = HybridDetector()

    async def validate(self, text: str, config: KAnonymityConfig, sensitivity: str = "high") -> DeidentificationReport:
        detections = await self._detector.detect(text, sensitivity=sensitivity)
        kinds = sorted({d.kind for d in detections})
        direct_found = len(kinds) > 0

        notes: List[str] = []
        if config.quasi_identifiers:
            notes.append(
                "Free-text quasi-identifier k-anonymity cannot be computed reliably; provide tabular data for strict k-anonymity."
            )

        return DeidentificationReport(
            direct_identifiers_found=direct_found,
            direct_identifier_kinds=kinds,
            k_anonymity_target=config.k,
            quasi_identifiers=config.quasi_identifiers,
            notes=notes,
        )
