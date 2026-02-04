"""Confidence scoring for PHI detections.

This module provides a lightweight, offline-safe scoring mechanism. A true ML
model can be plugged in later; for now we implement a feature-based scorer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DetectionFeatures:
    kind: str
    source: str  # regex|spacy
    length: int
    has_digits: bool
    has_alpha: bool


class ConfidenceScorer:
    def score(self, f: DetectionFeatures) -> float:
        # Simple heuristic scoring: spaCy gets a boost; longer structured tokens higher.
        base = 0.5
        if f.source == "spacy":
            base += 0.2
        if f.length >= 8:
            base += 0.15
        if f.has_digits and not f.has_alpha:
            base += 0.1
        if f.kind in {"ssn", "mrn", "ip", "email", "phone"}:
            base += 0.1
        return max(0.0, min(0.99, base))
