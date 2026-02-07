"""
agent-rag-retrieve — core implementation.

Retrieves chunks from ChromaDB (semantic search), then applies BM25-lite
reranking to blend keyword relevance with vector similarity.

Pipeline:
    1. Parse & validate inputs (query, collection, top_k, filters)
    2. Semantic search via ChromaDB (top-N, default N=50)
    3. BM25-lite reranking over semantic results
    4. Return blended chunks with both scores in metadata

PHI-safe logging: only counts / IDs / durations — never chunk content.
"""
from __future__ import annotations

import time
import structlog
from typing import Any, AsyncGenerator, Dict, List, Optional

from agent.schemas import RetrievalChunk, RetrievalTrace
from agent.chroma_client import chroma_query
from agent.bm25_lite import bm25_rerank

logger = structlog.get_logger(__name__)

# Defaults
DEFAULT_TOP_K = 50       # Semantic window (retrieve more, rerank down)
DEFAULT_RETURN_K = 20    # Final results after reranking
DEFAULT_COLLECTION = "researchflow"
DEFAULT_SEMANTIC_WEIGHT = 0.5


def _clamp_int(x: Any, default: int, lo: int, hi: int) -> int:
    try:
        v = int(x)
        return max(lo, min(hi, v))
    except Exception:
        return default


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synchronous retrieval with BM25-lite reranking.

    Expected inputs:
        query_text (str)        — the search query  [required]
        collection (str)        — ChromaDB collection name
        top_k (int)             — final results to return (default 20)
        semantic_k (int)        — semantic search window  (default 50)
        semantic_weight (float) — blend weight [0..1]     (default 0.5)
        where (dict)            — ChromaDB metadata filter
    """
    started = time.time()
    request_id = payload.get("request_id", "unknown")
    inputs = payload.get("inputs") or {}

    # ── Parse inputs ─────────────────────────────────────────────────
    query_text = str(inputs.get("query_text") or inputs.get("query") or "").strip()
    collection = str(inputs.get("collection") or DEFAULT_COLLECTION).strip()
    return_k = _clamp_int(inputs.get("top_k"), DEFAULT_RETURN_K, 1, 200)
    semantic_k = _clamp_int(inputs.get("semantic_k"), DEFAULT_TOP_K, 1, 500)
    where = inputs.get("where") or inputs.get("filter") or None

    try:
        semantic_weight = float(inputs.get("semantic_weight", DEFAULT_SEMANTIC_WEIGHT))
        semantic_weight = max(0.0, min(1.0, semantic_weight))
    except (TypeError, ValueError):
        semantic_weight = DEFAULT_SEMANTIC_WEIGHT

    if not query_text:
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {"error": "Missing required input: query_text"},
            "artifacts": [],
            "provenance": {},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
        }

    logger.info(
        "agent_sync_start",
        request_id=request_id,
        task_type="RAG_RETRIEVE",
        collection=collection,
        semantic_k=semantic_k,
        return_k=return_k,
        semantic_weight=semantic_weight,
        has_filter=bool(where),
    )

    # ── 1. Semantic search via ChromaDB ──────────────────────────────
    try:
        hits = await chroma_query(
            query_text=query_text,
            collection_name=collection,
            k=semantic_k,
            where=where,
        )
    except Exception as e:
        logger.warning(
            "chroma_query_failed",
            request_id=request_id,
            error=type(e).__name__,
            error_msg=str(e)[:200],
        )
        return {
            "status": "degraded",
            "request_id": request_id,
            "outputs": {
                "chunks": [],
                "count": 0,
                "error": f"ChromaDB query failed: {type(e).__name__}",
            },
            "artifacts": [],
            "provenance": {"stages": ["semantic"], "error": True},
            "usage": {"duration_ms": int((time.time() - started) * 1000)},
        }

    logger.info(
        "semantic_search_complete",
        request_id=request_id,
        hit_count=len(hits),
    )

    # ── 2. BM25-lite reranking ───────────────────────────────────────
    rerank_input = [
        {
            "id": h.id,
            "text": h.document or "",
            "score": h.score,
            "metadata": dict(h.metadata),
            "distance": h.distance,
        }
        for h in hits
    ]

    reranked = bm25_rerank(
        query_text,
        rerank_input,
        text_key="text",
        semantic_weight=semantic_weight,
    )

    # ── 3. Build output (capped at return_k) ─────────────────────────
    chunks: List[Dict[str, Any]] = []
    citations: List[str] = []

    for item in reranked[:return_k]:
        doc_id = (
            item["metadata"].get("doc_id")
            or item["metadata"].get("document_id")
            or item["id"]
        )
        chunk = RetrievalChunk(
            chunk_id=item["id"],
            doc_id=doc_id,
            text=item.get("text", ""),
            score=item["score"],
            metadata=item["metadata"],
        )
        chunks.append(chunk.model_dump())
        citations.append(item["id"])

    retrieval_trace = RetrievalTrace(
        stages=["semantic", "bm25"],
        semantic_k=semantic_k,
        bm25_k=semantic_k,     # BM25 scored all semantic hits
        rerank_k=None,          # No LLM reranker yet
    )

    duration_ms = int((time.time() - started) * 1000)

    logger.info(
        "agent_sync_complete",
        request_id=request_id,
        task_type="RAG_RETRIEVE",
        duration_ms=duration_ms,
        semantic_hits=len(hits),
        returned_chunks=len(chunks),
        stages=retrieval_trace.stages,
    )

    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": {
            "chunks": chunks,
            "count": len(chunks),
            "retrieval_trace": retrieval_trace.model_dump(),
        },
        "artifacts": citations,
        "provenance": {
            "collection": collection,
            "stages": retrieval_trace.stages,
            "semantic_k": semantic_k,
            "bm25_k": semantic_k,
            "semantic_weight": semantic_weight,
        },
        "usage": {
            "duration_ms": duration_ms,
            "input_tokens": None,
            "output_tokens": None,
        },
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    SSE streaming wrapper — yields progress events then final result.
    """
    request_id = payload.get("request_id", "unknown")

    yield {
        "type": "status",
        "request_id": request_id,
        "step": "semantic_search",
        "progress": 20,
    }

    yield {
        "type": "status",
        "request_id": request_id,
        "step": "bm25_rerank",
        "progress": 60,
    }

    result = await run_sync(payload)

    yield {
        "type": "status",
        "request_id": request_id,
        "step": "complete",
        "progress": 100,
    }

    yield {
        "type": "final",
        "request_id": request_id,
        **result,
    }
