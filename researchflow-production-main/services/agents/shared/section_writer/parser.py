"""Parse LLM response into section_markdown and claims_with_evidence."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def parse_section_response(raw: str) -> Dict[str, Any]:
    """
    Parse LLM output into section_markdown and claims_with_evidence.

    Expects raw to contain SECTION_MARKDOWN: ... and CLAIMS_WITH_EVIDENCE: [...].

    Returns:
        {"section_markdown": str, "claims_with_evidence": List[ClaimWithEvidence]}
    """
    section_markdown = ""
    claims_with_evidence: List[Dict[str, Any]] = []
    raw = (raw or "").strip()

    # Try to find CLAIMS_WITH_EVIDENCE JSON block
    json_match = re.search(
        r"CLAIMS_WITH_EVIDENCE\s*:\s*(\[[\s\S]*?\])\s*$",
        raw,
        re.MULTILINE | re.IGNORECASE,
    )
    if json_match:
        try:
            claims_with_evidence = json.loads(json_match.group(1))
            if not isinstance(claims_with_evidence, list):
                claims_with_evidence = []
        except json.JSONDecodeError:
            pass
    if not claims_with_evidence:
        # Fallback: look for any JSON array at end (all elements must be dicts for "in" check)
        for m in re.finditer(r"(\[[\s\S]*?\])\s*$", raw):
            try:
                cand = json.loads(m.group(1))
                if not isinstance(cand, list) or not cand:
                    continue
                if not all(isinstance(x, dict) for x in cand):
                    continue
                if any("evidence_refs" in x or "claim" in x for x in cand):
                    claims_with_evidence = cand
                    break
            except (json.JSONDecodeError, TypeError):
                continue

    # Section: before CLAIMS_WITH_EVIDENCE
    section_match = re.search(
        r"SECTION_MARKDOWN\s*:\s*([\s\S]*?)(?=CLAIMS_WITH_EVIDENCE|$)",
        raw,
        re.IGNORECASE,
    )
    if section_match:
        section_markdown = section_match.group(1).strip()
    else:
        section_markdown = raw
        if claims_with_evidence:
            section_markdown = re.sub(
                r"CLAIMS_WITH_EVIDENCE\s*:?\s*[\s\S]*$",
                "",
                section_markdown,
                flags=re.IGNORECASE,
            ).strip()
    if not section_markdown:
        section_markdown = "No section generated."

    # Normalize claims_with_evidence: each item must have claim and evidence_refs
    normalized: List[Dict[str, Any]] = []
    for c in claims_with_evidence:
        if not isinstance(c, dict):
            continue
        claim = c.get("claim") or ""
        refs = c.get("evidence_refs") or []
        if not isinstance(refs, list):
            refs = []
        refs = [
            {"chunk_id": str(r.get("chunk_id") or r.get("chunkId") or ""), "doc_id": str(r.get("doc_id") or r.get("docId") or "")}
            for r in refs
            if isinstance(r, dict)
        ]
        normalized.append({"claim": claim, "evidence_refs": refs})
    claims_with_evidence = normalized

    return {"section_markdown": section_markdown, "claims_with_evidence": claims_with_evidence}
