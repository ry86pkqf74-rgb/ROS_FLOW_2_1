"""
agent-stage2-synthesize: grounded literature review from extraction rows + citations.
Every claim in the output must reference a provided source; no claims without evidence.
"""
import json
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

SYSTEM_PROMPT = """You are writing a grounded literature review section. Your output must follow these rules strictly:
- Only state claims that are directly supported by the provided extraction rows and citations.
- Every claim MUST reference a source using in-text citation keys, e.g. [1], [2], or [Author Year].
- Do not introduce any claim, statistic, or finding without an explicit citation.
- Output exactly two parts in your response:
  1. LITERATURE_REVIEW_SECTION: (markdown section only, no extra label in the final text)
  2. STRUCTURED_CITATIONS: a JSON array of objects with keys: key, title, authors (array), year, doi (optional), url (optional). Each key must match a citation used in the section (e.g. "1" or "AuthorYear").
Use the citation keys from the provided papers (id or index) so the section can be validated against the citation list."""

USER_PROMPT_TEMPLATE = """Research question: {research_question}

Synthesis type: {synthesis_type}

Papers (extraction rows and citation info):
{papers_blob}

Write one literature review section in markdown that synthesizes the evidence above. Use only the information from these papers. Cite every claim with a key that appears in your STRUCTURED_CITATIONS list. Then provide STRUCTURED_CITATIONS as a JSON array."""


def _papers_to_blob(papers: List[Dict[str, Any]], citations: List[Dict[str, Any]]) -> str:
    """Format papers and optional citations for the prompt."""
    lines: List[str] = []
    for i, p in enumerate(papers, start=1):
        pid = p.get("id") or f"paper-{i}"
        ext = p.get("extracted_data") or {}
        title = p.get("title") or ext.get("title") or ""
        authors = p.get("authors") or ext.get("authors") or []
        year = p.get("year") or ext.get("year") or ""
        lines.append(
            f"[{i}] id={pid} | title={title} | authors={authors} | year={year}\n"
            f"extracted_data: {json.dumps(ext, default=str)[:2000]}"
        )
    if citations:
        lines.append("\nStructured citations (use these keys in the section):")
        for c in citations:
            key = c.get("key") or c.get("id") or ""
            lines.append(f"  - {json.dumps(c)}")
    return "\n\n".join(lines)


def normalize_synthesize_inputs(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize request inputs. Raises ValueError if invalid."""
    inputs = payload.get("inputs") or {}
    papers = inputs.get("papers")
    if papers is None:
        raise ValueError("inputs.papers is required")
    if not isinstance(papers, list):
        raise ValueError("inputs.papers must be a list")
    # Allow empty papers (no evidence) but normalize to list of dicts
    papers = [p if isinstance(p, dict) else {} for p in papers]
    for i, p in enumerate(papers):
        if not isinstance(p, dict):
            continue
        if "id" not in p and "extracted_data" in p:
            p["id"] = p.get("id") or f"paper-{i + 1}"
        if "extracted_data" not in p:
            p["extracted_data"] = p.get("extracted_data") or {}

    research_question = str(inputs.get("research_question") or "").strip() or "Synthesize the provided evidence."
    synthesis_type = str(inputs.get("synthesisType") or inputs.get("synthesis_type") or "narrative").strip()
    citations = inputs.get("citations")
    if citations is not None and not isinstance(citations, list):
        citations = []
    if not citations:
        citations = []

    return {
        "papers": papers,
        "research_question": research_question,
        "synthesis_type": synthesis_type,
        "citations": citations,
    }


def _extract_citation_keys_from_markdown(section_markdown: str) -> List[str]:
    """Find in-text citation markers like [1], [2], [Author 2020], [Smith et al.]."""
    # Match [digits] or [Author Year] style
    keys: List[str] = []
    # [1], [2], [12]
    for m in re.finditer(r"\[(\d+)\]", section_markdown):
        keys.append(m.group(1))
    # [Author Year] or [Author et al. Year] - alphanumeric + spaces + et al. + year
    for m in re.finditer(r"\[([^\]]+)\]", section_markdown):
        inner = m.group(1).strip()
        if inner and not inner.isdigit():
            keys.append(inner)
    return keys


def _validate_citations_in_section(
    section_markdown: str, structured_citations: List[Dict[str, Any]]
) -> List[str]:
    """Check that every citation key used in the section appears in structured_citations. Returns list of warnings."""
    used = set(_extract_citation_keys_from_markdown(section_markdown))
    known = set()
    for c in structured_citations:
        k = c.get("key") or c.get("id")
        if k is not None:
            known.add(str(k))
    warnings: List[str] = []
    for k in used:
        if k not in known:
            warnings.append(f"Citation key '{k}' used in section but not in structured_citations list")
    return warnings


async def _call_llm(
    system: str,
    user: str,
    max_tokens: int = 4096,
    temperature: float = 0.4,
) -> str:
    """Call OpenAI-compatible chat completions API. Uses INFERENCE_URL and API_KEY env."""
    base_url = (os.getenv("INFERENCE_URL") or "").rstrip("/")
    api_key = os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    if not base_url or not api_key:
        # DEMO: return a minimal grounded response without external call
        return _demo_synthesis_response(user)

    url = f"{base_url}/chat/completions"
    if not url.startswith("http"):
        url = f"https://{base_url}/chat/completions"
    payload = {
        "model": os.getenv("INFERENCE_MODEL", "gpt-4o"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        return (msg.get("content") or "").strip()


def _demo_synthesis_response(user: str) -> str:
    """Return a fixed demo response when no inference URL/API key is set."""
    return """LITERATURE_REVIEW_SECTION:
## Literature Review (Demo)

The available evidence from the provided papers supports a narrative synthesis [1]. Further work is needed to consolidate findings across studies [2].

STRUCTURED_CITATIONS:
[{"key": "1", "title": "Provided evidence", "authors": [], "year": ""}, {"key": "2", "title": "Gap analysis", "authors": [], "year": ""}]"""


def _parse_llm_response(raw: str) -> Dict[str, Any]:
    """Parse LLM output into section_markdown and structured citations. Handles demo or real format."""
    section = ""
    citations: List[Dict[str, Any]] = []
    raw = (raw or "").strip()

    # Try to find STRUCTURED_CITATIONS JSON block
    json_match = re.search(r"STRUCTURED_CITATIONS\s*:\s*(\[[\s\S]*?\])\s*$", raw, re.MULTILINE | re.IGNORECASE)
    if json_match:
        try:
            citations = json.loads(json_match.group(1))
            if not isinstance(citations, list):
                citations = []
        except json.JSONDecodeError:
            pass
    if not citations:
        # Fallback: look for any JSON array at end
        for m in re.finditer(r"(\[[\s\S]*?\])\s*$", raw):
            try:
                cand = json.loads(m.group(1))
                if isinstance(cand, list) and cand and isinstance(cand[0], dict):
                    citations = cand
                    break
            except json.JSONDecodeError:
                continue

    # Section: before STRUCTURED_CITATIONS or full content up to first JSON
    section_match = re.search(r"LITERATURE_REVIEW_SECTION\s*:\s*([\s\S]*?)(?=STRUCTURED_CITATIONS|$)", raw, re.IGNORECASE)
    if section_match:
        section = section_match.group(1).strip()
    else:
        # Use everything before the last JSON array as section
        section = raw
        if citations:
            section = re.sub(r"STRUCTURED_CITATIONS\s*:?\s*[\s\S]*$", "", section, flags=re.IGNORECASE).strip()
        section = re.sub(r"^#+\s*Literature Review\s*\(Demo\)\s*$", "", section, flags=re.MULTILINE).strip() or section

    if not section:
        section = raw.split("STRUCTURED_CITATIONS")[0].strip() or "No section generated."
    return {"section_markdown": section, "citations": citations}


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    started = time.time()
    request_id = payload.get("request_id", "unknown")

    try:
        norm = normalize_synthesize_inputs(payload)
    except ValueError as e:
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {},
            "artifacts": [],
            "provenance": {},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
            "error": {"code": "VALIDATION_ERROR", "message": str(e), "details": None},
        }

    papers_blob = _papers_to_blob(norm["papers"], norm["citations"])
    user_content = USER_PROMPT_TEMPLATE.format(
        research_question=norm["research_question"],
        synthesis_type=norm["synthesis_type"],
        papers_blob=papers_blob,
    )
    budgets = (payload.get("budgets") or {})
    if isinstance(budgets, dict):
        max_tokens = int(budgets.get("max_output_tokens", 4096))
    else:
        max_tokens = 4096

    try:
        raw_response = await _call_llm(
            system=SYSTEM_PROMPT,
            user=user_content,
            max_tokens=max_tokens,
            temperature=0.4,
        )
    except Exception as e:
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {"error_detail": str(e)[:500]},
            "artifacts": [],
            "provenance": {},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
            "error": {"code": "TASK_FAILED", "message": f"Inference failed: {e}", "details": None},
        }

    parsed = _parse_llm_response(raw_response)
    section_markdown = parsed.get("section_markdown") or ""
    citations = parsed.get("citations") or []
    warnings = _validate_citations_in_section(section_markdown, citations)

    duration_ms = int((time.time() - started) * 1000)
    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": {
            "section_markdown": section_markdown,
            "citations": citations,
            "warnings": warnings,
            "research_question": norm["research_question"],
            "paper_count": len(norm["papers"]),
        },
        "artifacts": [],
        "provenance": {"synthesis_type": norm["synthesis_type"]},
        "usage": {"duration_ms": duration_ms},
        "grounding": {"citations": [str(c.get("key") or c.get("id") or "") for c in citations]},
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    request_id = payload.get("request_id", "unknown")
    yield {"type": "status", "request_id": request_id, "step": "normalize", "progress": 15}
    try:
        normalize_synthesize_inputs(payload)
    except ValueError as e:
        yield {"type": "error", "request_id": request_id, "message": str(e)}
        return
    yield {"type": "status", "request_id": request_id, "step": "synthesize", "progress": 50}
    result = await run_sync(payload)
    yield {"type": "status", "request_id": request_id, "step": "finalize", "progress": 90}
    task_type = payload.get("task_type", "STAGE2_SYNTHESIZE")
    yield {"type": "final", "task_type": task_type, **result}
