"""
Stage2 extract agent: extract PICO, endpoints, sample size, key results from papers
using GroundingPack and/or abstracts. Outputs normalized extraction table + citations (docId/chunkId).
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import httpx
import structlog

from agent.schemas import GroundingPack

logger = structlog.get_logger()

TASK_TYPE = "STAGE_2_EXTRACT"
AI_BRIDGE_TASK_TYPE = "STAGE_2_EXTRACT"

# Max text length per unit sent to LLM
MAX_TEXT_PER_UNIT = 8000


def _ai_bridge_url() -> str:
    return (
        os.getenv("AI_BRIDGE_URL")
        or os.getenv("ORCHESTRATOR_INTERNAL_URL")
        or os.getenv("ORCHESTRATOR_URL")
        or "http://localhost:3001"
    ).rstrip("/")


def _auth_token() -> str:
    return os.getenv("AI_BRIDGE_TOKEN") or os.getenv("WORKER_SERVICE_TOKEN") or ""


async def _invoke_bridge(
    prompt: str,
    governance_mode: str = "DEMO",
    request_id: str = "extract",
    max_tokens: int = 4000,
) -> str:
    """Call AI Bridge /api/ai-bridge/invoke; returns content string."""
    base = _ai_bridge_url()
    token = _auth_token()
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "prompt": prompt,
        "options": {
            "taskType": AI_BRIDGE_TASK_TYPE,
            "modelTier": "STANDARD",
            "governanceMode": governance_mode,
            "requirePhiCompliance": False,
            "maxTokens": max_tokens,
        },
        "metadata": {
            "agentId": "agent-stage2-extract",
            "projectId": "researchflow",
            "runId": request_id,
            "threadId": "thread-extract",
            "stageRange": [1, 20],
            "currentStage": 2,
        },
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(
            f"{base}/api/ai-bridge/invoke",
            json=payload,
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
        content = (data.get("content") or data.get("text") or "").strip()
        return content or ""


def _units_from_grounding(grounding: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build list of { doc_id, chunk_id, text } from GroundingPack (chunks or sources)."""
    if not grounding:
        return []
    out: List[Dict[str, Any]] = []
    # Prefer chunks array (has doc_id, chunk_id, text)
    chunks = grounding.get("chunks") or []
    for c in chunks:
        if not isinstance(c, dict):
            continue
        doc_id = str(c.get("doc_id") or c.get("docId") or "")
        chunk_id = str(c.get("chunk_id") or c.get("chunkId") or "")
        text = str(c.get("text") or "")[:MAX_TEXT_PER_UNIT]
        if not doc_id and chunk_id:
            doc_id = chunk_id.split("-chunk-")[0] if "-chunk-" in chunk_id else chunk_id
        if not chunk_id and doc_id:
            chunk_id = f"{doc_id}-chunk-{len(out)}"
        if doc_id or text:
            out.append({"doc_id": doc_id or f"doc_{len(out)}", "chunk_id": chunk_id, "text": text})
    if out:
        return out
    # Fallback: sources (id/chunkId, doc_id, text/content)
    sources = grounding.get("sources") or []
    for s in sources:
        if not isinstance(s, dict):
            continue
        chunk_id = str(s.get("id") or s.get("chunkId") or s.get("chunk_id") or f"chunk_{len(out)}")
        doc_id = str(s.get("doc_id") or s.get("docId") or "")
        if not doc_id and "-chunk-" in chunk_id:
            doc_id = chunk_id.split("-chunk-")[0]
        if not doc_id:
            doc_id = f"doc_{len(out)}"
        text = str(s.get("text") or s.get("content") or "")[:MAX_TEXT_PER_UNIT]
        out.append({"doc_id": doc_id, "chunk_id": chunk_id, "text": text})
    return out


def _units_from_abstracts(abstracts: Any) -> List[Dict[str, Any]]:
    """Build list of { doc_id, chunk_id, text } from inputs.abstracts or inputs.papers."""
    if not abstracts or not isinstance(abstracts, list):
        return []
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(abstracts):
        if not isinstance(item, dict):
            continue
        doc_id = str(item.get("doc_id") or item.get("docId") or item.get("paper_id") or item.get("id") or f"doc_{i}")
        chunk_id = str(item.get("chunk_id") or item.get("chunkId") or f"{doc_id}-abstract")
        text = str(item.get("abstract") or item.get("text") or "")[:MAX_TEXT_PER_UNIT]
        if not text and item.get("title"):
            text = str(item.get("title"))[:MAX_TEXT_PER_UNIT]
        out.append({"doc_id": doc_id, "chunk_id": chunk_id, "text": text})
    return out


def normalize_input_units(inputs: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Combine grounding and abstracts/papers into a single list of units. Dedupe by doc_id+chunk_id."""
    seen: set = set()
    units: List[Dict[str, Any]] = []
    grounding = inputs.get("groundingPack") or inputs.get("grounding_pack")
    for u in _units_from_grounding(grounding):
        key = (u["doc_id"], u["chunk_id"])
        if key not in seen and (u["doc_id"] or u["text"]):
            seen.add(key)
            units.append(u)
    abstracts = inputs.get("abstracts") or inputs.get("papers")
    for u in _units_from_abstracts(abstracts):
        key = (u["doc_id"], u["chunk_id"])
        if key not in seen and (u["doc_id"] or u["text"]):
            seen.add(key)
            units.append(u)
    return units


def _stub_extraction_table_and_citations(
    units: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Build stub extraction_table (empty PICO/endpoints/sample_size/key_results) and citations from units."""
    table: List[Dict[str, Any]] = []
    citations: List[Dict[str, str]] = []
    for u in units:
        doc_id = u.get("doc_id") or ""
        chunk_id = u.get("chunk_id") or ""
        table.append({
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "pico": None,
            "endpoints": [],
            "sample_size": None,
            "key_results": None,
        })
        citations.append({"doc_id": doc_id, "chunk_id": chunk_id})
    return table, citations


def _parse_pico(obj: Any) -> Optional[Dict[str, Any]]:
    if not obj or not isinstance(obj, dict):
        return None
    return {
        "population": obj.get("population"),
        "intervention": obj.get("intervention"),
        "comparator": obj.get("comparator"),
        "outcomes": obj.get("outcomes") if isinstance(obj.get("outcomes"), list) else [],
        "timeframe": obj.get("timeframe"),
    }


def _parse_llm_extractions(raw: str, units: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Parse LLM JSON array into extraction_table and citations. On failure return stub rows."""
    table: List[Dict[str, Any]] = []
    citations: List[Dict[str, str]] = []
    # Try to extract JSON array from response (allow markdown code block)
    text = (raw or "").strip()
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    if not text.startswith("["):
        # Stub by units
        return _stub_extraction_table_and_citations(units)
    try:
        arr = json.loads(text)
        if not isinstance(arr, list):
            return _stub_extraction_table_and_citations(units)
        for i, item in enumerate(arr):
            if not isinstance(item, dict):
                continue
            doc_id = str(item.get("doc_id") or (units[i]["doc_id"] if i < len(units) else ""))
            chunk_id = str(item.get("chunk_id") or (units[i]["chunk_id"] if i < len(units) else ""))
            if not doc_id and i < len(units):
                doc_id = units[i].get("doc_id") or ""
            if not chunk_id and i < len(units):
                chunk_id = units[i].get("chunk_id") or ""
            pico = _parse_pico(item.get("pico"))
            endpoints = item.get("endpoints")
            if not isinstance(endpoints, list):
                endpoints = [endpoints] if endpoints else []
            endpoints = [str(x) for x in endpoints if x is not None]
            sample_size = item.get("sample_size")
            key_results = item.get("key_results")
            table.append({
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "pico": pico,
                "endpoints": endpoints,
                "sample_size": sample_size,
                "key_results": key_results,
            })
            citations.append({"doc_id": doc_id, "chunk_id": chunk_id})
        # Ensure we have one citation per unit if LLM returned fewer rows
        for i, u in enumerate(units):
            if i >= len(citations):
                citations.append({"doc_id": u.get("doc_id") or "", "chunk_id": u.get("chunk_id") or ""})
        return table, citations
    except json.JSONDecodeError:
        return _stub_extraction_table_and_citations(units)


async def _execute_extract(
    inputs: Dict[str, Any],
    mode: str,
    request_id: str,
) -> Dict[str, Any]:
    """Run extraction: normalize units, call AI Bridge or return stub, return extraction_table + citations."""
    units = normalize_input_units(inputs)
    if not units:
        return {
            "extraction_table": [],
            "citations": [],
            "error": "No grounding or abstracts provided",
        }
    governance_mode = (inputs.get("governanceMode") or inputs.get("governance_mode") or mode or "DEMO").strip()
    use_bridge = bool(_ai_bridge_url())
    if governance_mode.upper() == "DEMO" and not use_bridge:
        table, citations = _stub_extraction_table_and_citations(units)
        return {"extraction_table": table, "citations": citations}
    if use_bridge:
        # Build prompt: one block per unit
        blocks: List[str] = []
        for u in units:
            blocks.append(f"[doc_id={u['doc_id']} chunk_id={u['chunk_id']}]\n{u.get('text', '')}")
        context = "\n\n---\n\n".join(blocks)
        prompt = f"""You are a research assistant. Extract structured fields from each of the following paper chunks or abstracts.
For each block (marked with [doc_id=... chunk_id=...]), output one JSON object with:
- doc_id: exact doc_id from the block
- chunk_id: exact chunk_id from the block
- pico: object with population, intervention, comparator, outcomes (array), timeframe (strings or null)
- endpoints: array of endpoint/outcome measure names
- sample_size: number or string (e.g. "n=120" or 120)
- key_results: string or array of key findings

Blocks:
{context}

Respond with a JSON array only: one object per block, in the same order. Use only the doc_id and chunk_id values given in the blocks. No other text."""

        try:
            raw = await _invoke_bridge(prompt, governance_mode=governance_mode, request_id=request_id, max_tokens=4000)
        except Exception as e:
            logger.warning("extract_bridge_invoke_failed", error=str(type(e).__name__))
            table, citations = _stub_extraction_table_and_citations(units)
            return {"extraction_table": table, "citations": citations, "warning": str(e)}
        table, citations = _parse_llm_extractions(raw, units)
        return {"extraction_table": table, "citations": citations}
    table, citations = _stub_extraction_table_and_citations(units)
    return {"extraction_table": table, "citations": citations}


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous agent execution for stage2 extract."""
    started = time.time()
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    inputs = payload.get("inputs", {})
    mode = payload.get("mode", "DEMO")

    logger.info("agent_sync_start", request_id=request_id, task_type=task_type)

    outputs = await _execute_extract(inputs, mode, request_id)

    if outputs.get("error"):
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": outputs,
            "artifacts": [],
            "provenance": {"governance_mode": mode},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
            "error": {"code": "VALIDATION_ERROR", "message": outputs["error"]},
        }

    # Optionally echo input grounding on response
    grounding = None
    gp = inputs.get("groundingPack") or inputs.get("grounding_pack")
    if gp and isinstance(gp, dict):
        try:
            grounding = GroundingPack(**gp)
        except Exception:
            pass

    logger.info("agent_sync_complete", request_id=request_id, task_type=task_type)
    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": outputs,
        "artifacts": [],
        "provenance": {"governance_mode": mode},
        "usage": {"duration_ms": int((time.time() - started) * 1000)},
        "grounding": grounding,
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming agent execution with SSE events."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    inputs = payload.get("inputs", {})
    mode = payload.get("mode", "DEMO")

    logger.info("agent_stream_start", request_id=request_id, task_type=task_type)

    yield {"type": "started", "request_id": request_id, "task_type": task_type}
    yield {"type": "progress", "request_id": request_id, "progress": 50, "step": "extracting"}

    result = await run_sync(payload)

    yield {
        "type": "final",
        "request_id": request_id,
        "task_type": task_type,
        "status": result.get("status", "ok"),
        "success": result.get("status") == "ok",
        "outputs": result.get("outputs", {}),
        "duration_ms": result.get("usage", {}).get("duration_ms", 0),
    }
    logger.info("agent_stream_complete", request_id=request_id, task_type=task_type)
