"""
Centralized LangSmith configuration for the worker.

Reads env vars at import time and exposes a `get_tracer()` helper
that returns a configured CallbackHandler (or None when tracing is disabled).

PHI safety: all data sent to LangSmith is redacted via `redact_for_trace()`.

Environment variables:
  LANGSMITH_API_KEY       – required to enable tracing
  LANGCHAIN_PROJECT       – LangSmith project name  (default: researchflow-demo)
  LANGCHAIN_TRACING_V2    – must be "true" to enable (default: true when key is set)
  LANGSMITH_SAMPLING_RATE – 0.0-1.0  (default: 1.0)
"""

from __future__ import annotations

import logging
import os
import re
import random
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LANGSMITH_API_KEY: str = os.environ.get("LANGSMITH_API_KEY", "").strip()
LANGCHAIN_PROJECT: str = os.environ.get(
    "LANGCHAIN_PROJECT",
    f"researchflow-{os.environ.get('GOVERNANCE_MODE', 'demo').lower()}",
)
LANGCHAIN_TRACING_V2: bool = (
    os.environ.get("LANGCHAIN_TRACING_V2", "true").strip().lower() == "true"
)
SAMPLING_RATE: float = float(os.environ.get("LANGSMITH_SAMPLING_RATE", "1.0"))

TRACING_ENABLED: bool = bool(LANGSMITH_API_KEY) and LANGCHAIN_TRACING_V2

# ---------------------------------------------------------------------------
# PHI redaction patterns (mirrors orchestrator audit-redaction.util.ts)
# ---------------------------------------------------------------------------

_PHI_PATTERNS: list[re.Pattern[str]] = [
    # SSN: xxx-xx-xxxx
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    # MRN: MRN or MR# followed by digits
    re.compile(r"\b(?:MRN|MR#?)\s*:?\s*\d{4,}\b", re.IGNORECASE),
    # Date-of-birth patterns: DOB: mm/dd/yyyy, yyyy-mm-dd etc.
    re.compile(
        r"\b(?:DOB|Date\s*of\s*Birth)\s*:?\s*\d{1,4}[/\-]\d{1,2}[/\-]\d{1,4}\b",
        re.IGNORECASE,
    ),
    # Email addresses
    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    # US phone numbers
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
]


def redact_for_trace(data: Any) -> Any:
    """
    Strip PHI patterns from data before sending to LangSmith.

    Handles strings, dicts, and lists recursively.
    Non-serializable types are converted to str first.
    """
    if data is None:
        return data
    if isinstance(data, str):
        result = data
        for pattern in _PHI_PATTERNS:
            result = pattern.sub("[REDACTED]", result)
        return result
    if isinstance(data, dict):
        return {k: redact_for_trace(v) for k, v in data.items()}
    if isinstance(data, (list, tuple)):
        return [redact_for_trace(item) for item in data]
    if isinstance(data, (int, float, bool)):
        return data
    # Fallback: convert to string and redact
    return redact_for_trace(str(data))


# ---------------------------------------------------------------------------
# Tracer factory
# ---------------------------------------------------------------------------


def get_tracer() -> Optional[Any]:
    """
    Return a configured LangSmith CallbackHandler, or None if tracing
    is disabled (missing API key, import failure, or sampling skip).

    Usage::

        tracer = get_tracer()
        callbacks = [tracer] if tracer else []
        result = await llm.ainvoke(prompt, config={"callbacks": callbacks})

    """
    if not TRACING_ENABLED:
        return None

    # Probabilistic sampling
    if SAMPLING_RATE < 1.0 and random.random() > SAMPLING_RATE:
        return None

    try:
        from langchain_core.tracers import LangChainTracer

        tracer = LangChainTracer(project_name=LANGCHAIN_PROJECT)
        return tracer
    except ImportError:
        logger.debug(
            "langchain_core not installed; LangSmith tracing unavailable. "
            "Install with: pip install langchain-core"
        )
        return None
    except Exception as exc:
        logger.warning("Failed to create LangSmith tracer: %s", exc)
        return None
