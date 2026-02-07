"""
LLM-based reranking via AI Bridge.

Calls AI Bridge with a constrained prompt to rank candidate chunk IDs by relevance.
Deterministic (temperature=0). Never invents chunks not in the candidate set.

PHI-safe: chunk text is sent to the LLM for ranking, but only IDs are logged.
"""
from __future__ import annotations

import json
import os
import re
import structlog
from typing import Any, Dict, List, Optional

import httpx

logger = structlog.get_logger(__name__)


def _ai_bridge_url() -> str:
    return (
        os.getenv("AI_BRIDGE_URL")
        or os.getenv("ORCHESTRATOR_INTERNAL_URL")
        or os.getenv("ORCHESTRATOR_URL")
        or "http://localhost:3001"
    ).rstrip("/")


def _auth_token() -> str:
    return os.getenv("AI_BRIDGE_TOKEN") or os.getenv("WORKER_SERVICE_TOKEN") or ""


async def llm_rerank(
    query: str,
    chunks: List[Dict[str, Any]],
    *,
    top_k: int = 20,
    request_id: str = "unknown",
    governance_mode: str = "DEMO",
) -> List[Dict[str, Any]]:
    """
    Rerank chunks using an LLM via AI Bridge.

    The LLM is given the query and chunk texts, and asked to return an ordered
    list of chunk IDs from most to least relevant. Only IDs from the input set
    are accepted; any hallucinated IDs are ignored.

    Parameters
    ----------
    query : str
        The user query.
    chunks : list[dict]
        Chunks to rerank, each with at least 'id' and 'text' keys.
    top_k : int
        Maximum number of chunks to return after reranking.
    request_id : str
        Request ID for logging/tracing.
    governance_mode : str
        Governance mode for AI Bridge (DEMO, LIVE, etc.).

    Returns
    -------
    list[dict]
        Reranked chunks (up to top_k), with 'llmRank' added to metadata.
        Falls back to input order on any failure.
    """
    if not chunks:
        return chunks

    chunk_ids = {ch["id"] for ch in chunks}
    id_to_chunk = {ch["id"]: ch for ch in chunks}

    # Build the prompt
    prompt = _build_rerank_prompt(query, chunks, top_k)

    try:
        ranked_ids = await _invoke_bridge_rerank(
            prompt=prompt,
            request_id=request_id,
            governance_mode=governance_mode,
        )
    except Exception as e:
        logger.warning(
            "llm_rerank_failed",
            request_id=request_id,
            error=type(e).__name__,
            error_msg=str(e)[:200],
        )
        # Fallback: return chunks as-is with llmRank = None
        for ch in chunks:
            ch.setdefault("metadata", {})["llmRank"] = None
        return chunks[:top_k]

    # Filter to only valid IDs from the candidate set
    valid_ranked = [cid for cid in ranked_ids if cid in chunk_ids]

    if not valid_ranked:
        logger.warning(
            "llm_rerank_no_valid_ids",
            request_id=request_id,
            returned_count=len(ranked_ids),
        )
        for ch in chunks:
            ch.setdefault("metadata", {})["llmRank"] = None
        return chunks[:top_k]

    # Build reranked list
    reranked: List[Dict[str, Any]] = []
    seen = set()

    for rank, cid in enumerate(valid_ranked[:top_k], start=1):
        if cid in seen:
            continue
        seen.add(cid)
        ch = id_to_chunk[cid]
        ch.setdefault("metadata", {})["llmRank"] = rank
        reranked.append(ch)

    # Append any remaining chunks not in the LLM response (preserving original order)
    for ch in chunks:
        if ch["id"] not in seen and len(reranked) < top_k:
            ch.setdefault("metadata", {})["llmRank"] = None
            reranked.append(ch)
            seen.add(ch["id"])

    logger.info(
        "llm_rerank_complete",
        request_id=request_id,
        input_count=len(chunks),
        output_count=len(reranked),
        valid_llm_ids=len(valid_ranked),
    )

    return reranked


def _build_rerank_prompt(query: str, chunks: List[Dict[str, Any]], top_k: int) -> str:
    """Build a constrained prompt for LLM reranking."""
    chunk_list = []
    for ch in chunks:
        chunk_id = ch.get("id", "")
        text = (ch.get("text", "") or "")[:1500]  # Limit text length per chunk
        chunk_list.append(f"[{chunk_id}]\n{text}")

    chunks_text = "\n\n---\n\n".join(chunk_list)

    return f"""You are a relevance ranker. Given a QUERY and a list of text CHUNKS (each with an ID in brackets), rank the chunks by relevance to the query.

QUERY: {query}

CHUNKS:
{chunks_text}

INSTRUCTIONS:
1. Rank the chunks from MOST relevant to LEAST relevant for answering the query.
2. Return ONLY a JSON array of chunk IDs in ranked order, e.g.: ["chunk-1", "chunk-5", "chunk-2"]
3. Include up to {top_k} chunk IDs maximum.
4. Only use IDs that appear in the CHUNKS above. Do not invent new IDs.
5. Return nothing but the JSON array — no explanation, no markdown.

JSON array of ranked chunk IDs:"""


async def _invoke_bridge_rerank(
    prompt: str,
    request_id: str,
    governance_mode: str,
) -> List[str]:
    """
    Call AI Bridge with temperature=0 for deterministic ranking.
    Returns a list of chunk IDs parsed from the LLM response.
    """
    base = _ai_bridge_url()
    token = _auth_token()

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "prompt": prompt,
        "options": {
            "taskType": "RAG_RERANK",
            "modelTier": "FAST",  # Use fast model for reranking
            "governanceMode": governance_mode,
            "requirePhiCompliance": False,
            "maxTokens": 500,
            "temperature": 0,  # Deterministic
        },
        "metadata": {
            "agentId": "agent-rag-retrieve",
            "projectId": "researchflow",
            "runId": request_id,
            "threadId": f"rerank-{request_id}",
            "stageRange": [1, 20],
            "currentStage": 1,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base}/api/ai-bridge/invoke",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    content = (data.get("content") or data.get("text") or "").strip()
    return _parse_ranked_ids(content)


def _parse_ranked_ids(content: str) -> List[str]:
    """
    Parse a JSON array of chunk IDs from LLM response.
    Tolerates markdown code fences and extra whitespace.
    """
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        # Remove opening fence
        content = re.sub(r"^```(?:json)?\s*", "", content)
        # Remove closing fence
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()

    if not content:
        return []

    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [str(item) for item in parsed if isinstance(item, str)]
    except json.JSONDecodeError:
        pass

    # Fallback: try to extract array pattern
    match = re.search(r'\[([^\]]+)\]', content)
    if match:
        try:
            parsed = json.loads(f"[{match.group(1)}]")
            if isinstance(parsed, list):
                return [str(item) for item in parsed if isinstance(item, str)]
        except json.JSONDecodeError:
            pass

    return []
