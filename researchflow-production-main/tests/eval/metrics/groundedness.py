"""Groundedness metric — Rouge-L F1 between actual and expected output.

Uses the lightweight `rouge-score` PyPI package.
BERTScore can be swapped in later behind a --bert flag.
"""
from __future__ import annotations

from typing import Any, Dict, Union


def rouge_l_f1(actual: str, expected: str) -> float:
    """Compute Rouge-L F1 between *actual* and *expected* text.

    Returns a float in [0, 1].  Returns 0.0 on import failure or empty inputs.
    """
    if not actual or not expected:
        return 0.0

    try:
        from rouge_score import rouge_scorer  # type: ignore[import-untyped]
    except ImportError:
        # Graceful fallback — schema-only (P0) mode doesn't need this
        return 0.0

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(expected, actual)
    return round(scores["rougeL"].fmeasure, 4)


def check_groundedness(score: float, threshold: float = 0.70) -> bool:
    """Return True if the Rouge-L F1 score meets the threshold."""
    return score >= threshold


def flatten_outputs(outputs: Dict[str, Any]) -> str:
    """Best-effort flatten an outputs dict to a single string for scoring."""
    parts: list[str] = []
    for key, val in outputs.items():
        if isinstance(val, str):
            parts.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.extend(str(v) for v in item.values() if isinstance(v, str))
        elif isinstance(val, dict):
            parts.extend(str(v) for v in val.values() if isinstance(v, str))
    return " ".join(parts)
