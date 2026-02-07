"""Cost metric — estimates per-call cost from token usage and tier pricing."""
from __future__ import annotations

from typing import Any, Dict, Optional


# Pricing per token (USD) — aligned with CANONICAL_AGENT_TIERING_POLICY tiers
TIER_PRICING: Dict[str, Dict[str, float]] = {
    "NANO":     {"input": 0.00000010, "output": 0.00000040},
    "MINI":     {"input": 0.00000015, "output": 0.00000060},
    "STANDARD": {"input": 0.00000300, "output": 0.00001500},
    "FRONTIER": {"input": 0.00001500, "output": 0.00007500},
}

# Agent → canonical tier (from registry.ts / tiering policy)
AGENT_TIERS: Dict[str, str] = {
    "agent-stage2-lit":        "STANDARD",
    "agent-stage2-screen":     "STANDARD",
    "agent-stage2-extract":    "STANDARD",
    "agent-stage2-synthesize": "FRONTIER",
    "agent-lit-retrieval":     "MINI",
    "agent-policy-review":     "MINI",
    "agent-rag-ingest":        "MINI",
    "agent-rag-retrieve":      "MINI",
    "agent-verify":            "FRONTIER",
    "agent-intro-writer":      "FRONTIER",
    "agent-methods-writer":    "STANDARD",
    "agent-evidence-synth":    "STANDARD",
    "agent-lit-triage":        "MINI",
}


def estimate_cost(
    usage: Dict[str, Any],
    agent_name: str,
    tier_override: Optional[str] = None,
) -> float:
    """Estimate cost in USD from usage metadata.

    ``usage`` should contain ``prompt_tokens`` and ``completion_tokens``
    (or ``input_tokens`` / ``output_tokens``).
    """
    tier = (tier_override or AGENT_TIERS.get(agent_name, "STANDARD")).upper()
    pricing = TIER_PRICING.get(tier, TIER_PRICING["STANDARD"])

    input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
    output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))

    return round(
        input_tokens * pricing["input"] + output_tokens * pricing["output"],
        8,
    )


def check_cost(
    cost_usd: float,
    baseline_usd: float,
    max_regression: float = 1.2,
) -> bool:
    """Return True if cost is within max_regression × baseline."""
    if baseline_usd <= 0:
        return True  # no baseline yet
    return cost_usd <= baseline_usd * max_regression
