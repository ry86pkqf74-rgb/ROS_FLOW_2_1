"""RAG retrieve: run_sync / run_stream returning GroundingPack with chunks, citations, retrievalTrace."""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import structlog

from agent.schemas import (
    GroundingPack,
    RetrievalChunk,
    RetrievalTrace,
)

logger = structlog.get_logger()

# Supported task type for this agent
TASK_TYPE = "RAG_RETRIEVE"


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")

    logger.info("agent_sync_start", request_id=request_id, task_type=task_type)

    started = time.perf_counter()
    result = await _execute_retrieve(payload)
    duration_ms = int((time.perf_counter() - started) * 1000)

    logger.info(
        "agent_sync_complete",
        request_id=request_id,
        task_type=task_type,
        duration_ms=duration_ms,
    )

    result.setdefault("usage", {})["duration_ms"] = duration_ms
    return result


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")

    logger.info("agent_stream_start", request_id=request_id, task_type=task_type)

    yield {"type": "started", "request_id": request_id, "task_type": task_type}
    yield {"type": "progress", "request_id": request_id, "progress": 30, "step": "retrieving"}

    started = time.perf_counter()
    result = await _execute_retrieve(payload)
    duration_ms = int((time.perf_counter() - started) * 1000)
    result.setdefault("usage", {})["duration_ms"] = duration_ms

    yield {
        "type": "final",
        "request_id": request_id,
        "task_type": task_type,
        "status": "ok",
        "success": True,
        "outputs": result.get("outputs", {}),
        "grounding": result.get("grounding"),
        "usage": result.get("usage", {}),
        "duration_ms": duration_ms,
    }

    logger.info("agent_stream_complete", request_id=request_id, task_type=task_type)


async def _execute_retrieve(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run RAG retrieval. Inputs: query, knowledgeBase, domainId, projectId, topK, optional metadata filters.
    Returns envelope with outputs (summary) and grounding (GroundingPack: chunks, citations, retrievalTrace).
    """
    inputs = payload.get("inputs") or {}
    query_text = (inputs.get("query") or "").strip()
    knowledge_base = (inputs.get("knowledgeBase") or inputs.get("knowledge_base") or "").strip()
    domain_id = inputs.get("domainId") or inputs.get("domain_id") or payload.get("domain_id")
    project_id = inputs.get("projectId") or inputs.get("project_id")
    top_k = inputs.get("topK") or inputs.get("top_k")
    if top_k is None:
        top_k = 10
    try:
        top_k = int(top_k)
        top_k = max(1, min(100, top_k))
    except (TypeError, ValueError):
        top_k = 10

    metadata_filters = inputs.get("metadata_filters") or inputs.get("metadataFilters") or {}

    request_id = payload.get("request_id", "unknown")

    if not query_text:
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {},
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "inputs.query is required and must be non-empty",
                "details": None,
            },
        }

    collection_name = knowledge_base or "default"
    where: Dict[str, Any] = {}
    if domain_id is not None and str(domain_id).strip():
        where["domain_id"] = str(domain_id).strip()
    if project_id is not None and str(project_id).strip():
        where["project_id"] = str(project_id).strip()
    for k, v in metadata_filters.items():
        if v is not None and (not isinstance(v, str) or v.strip()):
            where[str(k)] = v

    try:
        from app.chroma_client import query as chroma_query
    except ImportError:
        logger.warning("chroma_client_unavailable", request_id=request_id)
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {},
            "error": {
                "code": "TASK_FAILED",
                "message": "Chroma client not available",
                "details": None,
            },
        }

    # Run query in thread to avoid blocking (chromadb is sync)
    import asyncio
    loop = asyncio.get_event_loop()
    hits = await loop.run_in_executor(
        None,
        lambda: chroma_query(
            collection_name=collection_name,
            query_text=query_text,
            k=top_k,
            where=where if where else None,
        ),
    )

    chunks: List[RetrievalChunk] = []
    citations: List[str] = []
    sources: List[Dict[str, Any]] = []

    for h in hits:
        doc_id = (h.metadata.get("doc_id") or h.metadata.get("document_id") or h.id)
        chunks.append(
            RetrievalChunk(
                chunk_id=h.id,
                doc_id=doc_id,
                text=h.document or "",
                score=h.score,
                metadata=dict(h.metadata),
            )
        )
        citations.append(h.id)
        sources.append({"id": h.id, "doc_id": doc_id, "text": (h.document or "")[:500]})

    retrieval_trace = RetrievalTrace(
        stages=["semantic"],
        semantic_k=top_k,
        bm25_k=None,
        rerank_k=None,
    )

    grounding = GroundingPack(
        chunks=chunks,
        citations=citations,
        retrieval_trace=retrieval_trace,
        sources=sources,
        span_refs=[],
    )

    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": {
            "groundingPack": grounding.model_dump(),
            "chunk_count": len(chunks),
            "citation_count": len(citations),
        },
        "artifacts": [],
        "provenance": {"retrieval": "chroma", "collection": collection_name},
        "usage": {},
        "grounding": grounding,
    }
