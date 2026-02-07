"""
Pytest configuration and fixtures for agent-verify tests.
Provides GroundingPack fixtures and mock helpers for LIVE-mode testing.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List


# ============ Fixtures: GroundingPack ============

CLINICAL_GROUNDING_PACK: Dict[str, Any] = {
    "sources": [
        {
            "id": "chunk-rct-001",
            "text": (
                "This was a randomized controlled trial with 250 participants. "
                "Participants were randomly assigned in a 1:1 ratio to receive either "
                "the intervention (n=125) or placebo (n=125) using computer-generated "
                "random numbers with stratification by age and sex."
            ),
        },
        {
            "id": "chunk-outcome-002",
            "text": (
                "The primary outcome was reduction in HbA1c at 12 weeks. "
                "The intervention group showed a mean reduction of 1.2% (95% CI: 0.9-1.5%) "
                "compared to 0.3% (95% CI: 0.1-0.5%) in the placebo group (p<0.001)."
            ),
        },
        {
            "id": "chunk-safety-003",
            "text": (
                "Adverse events were reported in 15 participants (12%) in the intervention "
                "group and 18 participants (14.4%) in the placebo group. No serious adverse "
                "events were attributed to the study intervention."
            ),
        },
        {
            "id": "chunk-methods-004",
            "text": (
                "Blood samples were collected at baseline, 6 weeks, and 12 weeks. "
                "HbA1c was measured using high-performance liquid chromatography (HPLC) "
                "at a central laboratory blinded to treatment allocation."
            ),
        },
    ],
    "citations": ["chunk-rct-001", "chunk-outcome-002", "chunk-safety-003", "chunk-methods-004"],
    "span_refs": [],
}

EMPTY_GROUNDING_PACK: Dict[str, Any] = {
    "sources": [],
    "citations": [],
    "span_refs": [],
}


# ============ Mock Bridge Response Builders ============


def make_bridge_response_pass_with_evidence(
    claim: str,
    chunk_id: str,
    quote: str,
) -> str:
    """Build mock AI Bridge response: verdict=pass WITH evidence."""
    return json.dumps([
        {
            "claim": claim,
            "verdict": "pass",
            "evidence": [{"chunk_id": chunk_id, "quote": quote}],
        }
    ])


def make_bridge_response_pass_no_evidence(claim: str) -> str:
    """Build mock AI Bridge response: verdict=pass WITHOUT evidence (triggers fail-closed)."""
    return json.dumps([
        {
            "claim": claim,
            "verdict": "pass",
            "evidence": [],
        }
    ])


def make_bridge_response_pass_empty_quote(claim: str, chunk_id: str) -> str:
    """Build mock AI Bridge response: verdict=pass with empty quote (triggers fail-closed)."""
    return json.dumps([
        {
            "claim": claim,
            "verdict": "pass",
            "evidence": [{"chunk_id": chunk_id, "quote": ""}],
        }
    ])


def make_bridge_response_multi_claims(
    claims_with_evidence: List[Dict[str, Any]],
) -> str:
    """Build mock AI Bridge response for multiple claims with mixed evidence."""
    return json.dumps(claims_with_evidence)
