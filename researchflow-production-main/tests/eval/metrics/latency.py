"""Latency metric — wall-clock timing for agent calls."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Tuple


def timed_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """Call *fn* and return (result, elapsed_seconds).

    Usage::

        result, latency_s = timed_call(invoke_agent, agent_name, payload)
    """
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    return result, round(elapsed, 4)


# Threshold table from EVAL_HARNESS_ROADMAP §3.3
LATENCY_THRESHOLDS: Dict[str, float] = {
    # Tier → p95 ceiling in seconds
    "NANO": 30.0,
    "MINI": 30.0,
    "STANDARD": 60.0,
    "FRONTIER": 120.0,
}


def check_latency(latency_s: float, tier: str = "STANDARD") -> bool:
    """Return True if latency is within the threshold for the given tier."""
    ceiling = LATENCY_THRESHOLDS.get(tier.upper(), 120.0)
    return latency_s <= ceiling
