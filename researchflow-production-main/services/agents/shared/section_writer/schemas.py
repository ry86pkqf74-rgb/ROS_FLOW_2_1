"""Shared input/output types for section writer. Plain typing (no Pydantic) for minimal deps."""
from __future__ import annotations

from typing import Any, Dict, List

# Input: verified claim from agent-verify (claim, verdict, evidence with chunk_id, quote)
VerifiedClaim = Dict[str, Any]  # claim, verdict, evidence: [{ chunk_id, quote }]

# Input: extraction row (doc_id, chunk_id, pico, endpoints, sample_size, key_results)
ExtractionRow = Dict[str, Any]

# Input: grounding pack (sources/chunks with id/chunkId, doc_id/docId, text)
GroundingPack = Dict[str, Any]

# Input: style params (tone, citation_style, length_hint, audience)
StyleParams = Dict[str, Any]

# Output: one evidence reference (chunk_id + doc_id)
EvidenceRef = Dict[str, str]  # chunk_id, doc_id

# Output: claim with evidence refs
ClaimWithEvidence = Dict[str, Any]  # claim: str, evidence_refs: List[EvidenceRef]
