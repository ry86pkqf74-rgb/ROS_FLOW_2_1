"""Enforce that every claim has at least one evidence reference (chunk_id + doc_id)."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple


def enforce_claims_evidence(
    claims_with_evidence: List[Dict[str, Any]],
    governance_mode: str,
    valid_chunk_ids: None | set[str] = None,
    valid_doc_ids: None | set[str] = None,
) -> Tuple[List[Dict[str, Any]], List[str], bool]:
    """
    Ensure every claim has at least one evidence_ref with chunk_id and doc_id.

    Args:
        claims_with_evidence: List of { claim, evidence_refs: [{ chunk_id, doc_id }] }.
        governance_mode: LIVE or DEMO.
        valid_chunk_ids: Optional set of allowed chunk_ids (if provided, refs not in set are flagged).
        valid_doc_ids: Optional set of allowed doc_ids (if provided, refs not in set are flagged).

    Returns:
        (claims_with_evidence, warnings, overall_pass).
        - LIVE: overall_pass is False if any claim has no valid evidence_refs; warnings list offending claims.
        - DEMO: warnings appended but overall_pass True (section still returned).
    """
    warnings: List[str] = []
    overall_pass = True

    for i, c in enumerate(claims_with_evidence):
        claim = c.get("claim") or ""
        refs = c.get("evidence_refs") or []
        valid_refs = []
        for r in refs:
            if not isinstance(r, dict):
                continue
            chunk_id = str(r.get("chunk_id") or r.get("chunkId") or "").strip()
            doc_id = str(r.get("doc_id") or r.get("docId") or "").strip()
            if chunk_id and doc_id:
                if valid_chunk_ids is not None and chunk_id not in valid_chunk_ids:
                    warnings.append(f"Claim {i + 1}: chunk_id '{chunk_id}' not in grounding pack")
                elif valid_doc_ids is not None and doc_id not in valid_doc_ids:
                    warnings.append(f"Claim {i + 1}: doc_id '{doc_id}' not in grounding pack")
                else:
                    valid_refs.append({"chunk_id": chunk_id, "doc_id": doc_id})
        if not valid_refs:
            msg = f"Claim has no evidence refs (chunk_id/doc_id): {claim[:80]}..."
            warnings.append(msg)
            if governance_mode.upper() == "LIVE":
                overall_pass = False
        c["evidence_refs"] = valid_refs

    return claims_with_evidence, warnings, overall_pass
