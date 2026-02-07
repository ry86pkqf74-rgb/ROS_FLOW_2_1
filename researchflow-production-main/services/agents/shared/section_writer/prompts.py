"""Build system and user prompts for section writing with evidence."""
from __future__ import annotations

import json
from typing import Any, Dict, List


def get_grounding_chunk_and_doc_ids(grounding_pack: Dict[str, Any]) -> tuple[set[str], set[str]]:
    """Return (set of chunk_ids, set of doc_ids) from grounding pack for validation."""
    chunks = _chunks_from_grounding(grounding_pack)
    chunk_ids = {c.get("chunk_id") for c in chunks if c.get("chunk_id")}
    doc_ids = {c.get("doc_id") for c in chunks if c.get("doc_id")}
    return chunk_ids, doc_ids


def _chunks_from_grounding(grounding_pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract list of chunks (id, doc_id, text) from GroundingPack."""
    if not grounding_pack:
        return []
    out: List[Dict[str, Any]] = []
    # Prefer chunks (RetrievalChunk), then sources
    chunks = grounding_pack.get("chunks") or grounding_pack.get("sources") or []
    for c in chunks:
        if not isinstance(c, dict):
            continue
        chunk_id = c.get("chunk_id") or c.get("chunkId") or c.get("id") or c.get("chunk_id")
        doc_id = c.get("doc_id") or c.get("docId") or ""
        text = c.get("text") or c.get("content") or ""
        if not chunk_id:
            chunk_id = f"chunk_{len(out)}"
        out.append({"chunk_id": str(chunk_id), "doc_id": str(doc_id), "text": str(text)[:8000]})
    return out


def _format_verified_claims(verified_claims: List[Dict[str, Any]]) -> str:
    """Format verified claims for prompt context."""
    lines: List[str] = []
    for i, v in enumerate(verified_claims, 1):
        claim = v.get("claim") or ""
        verdict = v.get("verdict") or "unclear"
        evidence = v.get("evidence") or []
        refs = ", ".join(
            (e.get("chunk_id") or e.get("chunkId") or "?") for e in evidence if isinstance(e, dict)
        )
        lines.append(f"{i}. {claim} [verdict: {verdict}] refs: {refs}")
    return "\n".join(lines) if lines else "(none)"


def _format_extraction_rows(rows: List[Dict[str, Any]]) -> str:
    """Format extraction rows for prompt context."""
    lines: List[str] = []
    for i, r in enumerate(rows, 1):
        doc_id = r.get("doc_id") or r.get("docId") or "?"
        chunk_id = r.get("chunk_id") or r.get("chunkId") or "?"
        key_results = r.get("key_results")
        if isinstance(key_results, list):
            key_results = " | ".join(str(x) for x in key_results)
        lines.append(
            f"[{i}] doc_id={doc_id} chunk_id={chunk_id} "
            f"key_results={key_results!s}"
        )
    return "\n".join(lines) if lines else "(none)"


def _format_grounding_context(chunks: List[Dict[str, Any]]) -> str:
    """Format grounding chunks for prompt (chunk_id, doc_id, text)."""
    lines: List[str] = []
    for c in chunks:
        lines.append(
            f"[chunk_id={c.get('chunk_id', '')} doc_id={c.get('doc_id', '')}]\n{c.get('text', '')}"
        )
    return "\n\n".join(lines) if lines else "(no grounding chunks)"


SYSTEM_TEMPLATE = """You are writing a single manuscript section that is fully grounded in evidence. Your output must follow these rules strictly:
- Only state claims that are directly supported by the provided grounding chunks and extraction rows.
- Every claim MUST be tied to evidence using chunk_id and doc_id from the grounding pack. Do not invent chunk or doc ids.
- Output exactly two parts in your response:
  1. SECTION_MARKDOWN: (the markdown section only, no extra label in the final text)
  2. CLAIMS_WITH_EVIDENCE: a JSON array of objects, each with "claim" (string) and "evidence_refs" (array of {"chunk_id": "...", "doc_id": "..."}). Every claim must have at least one evidence_ref; use only chunk_id and doc_id values that appear in the GROUNDING CONTEXT below.
"""


def build_section_prompt(
    section_name: str,
    outline: List[str],
    verified_claims: List[Dict[str, Any]],
    extraction_rows: List[Dict[str, Any]],
    grounding_pack: Dict[str, Any],
    style_params: Dict[str, Any],
) -> tuple[str, str]:
    """
    Build system and user prompt for writing one section.

    Returns:
        (system_prompt, user_prompt) to send to the LLM. Caller may combine or send as two messages.
    """
    chunks = _chunks_from_grounding(grounding_pack)
    grounding_context = _format_grounding_context(chunks)
    verified_blob = _format_verified_claims(verified_claims)
    extraction_blob = _format_extraction_rows(extraction_rows)

    tone = style_params.get("tone") or "academic"
    citation_style = style_params.get("citation_style") or "[chunk_id]"
    length_hint = style_params.get("length_hint") or "medium"
    audience = style_params.get("audience") or "specialist"

    user = f"""Section to write: {section_name}
Outline (all sections): {json.dumps(outline)}

Style: tone={tone}, citation_style={citation_style}, length_hint={length_hint}, audience={audience}

Verified claims (use these where relevant; cite with chunk_id/doc_id):
{verified_blob}

Extraction rows (doc_id, chunk_id, key_results):
{extraction_blob}

GROUNDING CONTEXT (use only these chunk_id and doc_id values in CLAIMS_WITH_EVIDENCE):
{grounding_context}

Write the "{section_name}" section in markdown. Then output CLAIMS_WITH_EVIDENCE as a JSON array: each element must have "claim" and "evidence_refs" (array of {{"chunk_id": "...", "doc_id": "..."}}). Every claim must have at least one evidence_ref with chunk_id and doc_id from the grounding context above."""

    return SYSTEM_TEMPLATE, user
