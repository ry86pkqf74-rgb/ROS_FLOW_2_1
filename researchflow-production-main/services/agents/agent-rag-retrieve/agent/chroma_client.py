"""
Lightweight ChromaDB HTTP client for agent-rag-retrieve.

Talks to the ChromaDB instance (or the worker RAG search endpoint)
via HTTP.  Falls back to a DEMO stub when CHROMADB_URL is unset.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

CHROMADB_URL = os.getenv("CHROMADB_URL", "")
WORKER_RAG_URL = os.getenv("WORKER_RAG_URL", "")  # e.g. http://worker:8000
DEFAULT_COLLECTION = os.getenv("RAG_COLLECTION", "researchflow")


@dataclass
class ChromaHit:
    """Mirrors the shape returned by ChromaDB / worker search."""
    id: str
    document: str
    score: float
    distance: float
    metadata: Dict[str, Any] = field(default_factory=dict)


async def chroma_query(
    query_text: str,
    collection_name: str = DEFAULT_COLLECTION,
    k: int = 50,
    where: Optional[Dict[str, Any]] = None,
) -> List[ChromaHit]:
    """
    Query ChromaDB for the top-k semantic results.

    Strategy (in order):
    1. If WORKER_RAG_URL is set → call ``POST /api/rag/search``
    2. If CHROMADB_URL is set   → call ChromaDB HTTP API directly
    3. Else                     → return DEMO stub results
    """
    if WORKER_RAG_URL:
        return await _query_via_worker(query_text, collection_name, k, where)

    if CHROMADB_URL:
        return await _query_chromadb_direct(query_text, collection_name, k, where)

    # ── DEMO / no-backend stub ──
    logger.info("chroma_query_demo_stub", collection=collection_name, k=k)
    return _demo_stub_results(query_text, k)


# ── backend implementations ─────────────────────────────────────────

async def _query_via_worker(
    query_text: str,
    collection_name: str,
    k: int,
    where: Optional[Dict[str, Any]],
) -> List[ChromaHit]:
    """Call worker's /api/rag/search endpoint."""
    url = f"{WORKER_RAG_URL.rstrip('/')}/api/rag/search"
    body: Dict[str, Any] = {
        "query": query_text,
        "collection": collection_name,
        "top_k": k,
    }
    if where:
        body["filter"] = where

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    hits: List[ChromaHit] = []
    for item in data.get("results", []):
        hits.append(ChromaHit(
            id=item.get("id", ""),
            document=item.get("content", item.get("document", "")),
            score=float(item.get("score", 0.0)),
            distance=float(item.get("distance", 0.0)),
            metadata=item.get("metadata", {}),
        ))
    return hits


async def _query_chromadb_direct(
    query_text: str,
    collection_name: str,
    k: int,
    where: Optional[Dict[str, Any]],
) -> List[ChromaHit]:
    """Query ChromaDB HTTP API directly (requires embedding service)."""
    url = f"{CHROMADB_URL.rstrip('/')}/api/v1/collections/{collection_name}/query"
    body: Dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        body["where"] = where

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

    hits: List[ChromaHit] = []
    ids = (data.get("ids") or [[]])[0]
    docs = (data.get("documents") or [[]])[0]
    metas = (data.get("metadatas") or [[]])[0]
    dists = (data.get("distances") or [[]])[0]

    for i, doc_id in enumerate(ids):
        dist = dists[i] if i < len(dists) else 0.0
        # ChromaDB returns distances; convert to similarity score
        score = max(0.0, 1.0 - dist)
        hits.append(ChromaHit(
            id=doc_id,
            document=docs[i] if i < len(docs) else "",
            score=score,
            distance=dist,
            metadata=metas[i] if i < len(metas) else {},
        ))
    return hits


def _demo_stub_results(query_text: str, k: int) -> List[ChromaHit]:
    """Return synthetic results for DEMO mode / local dev without ChromaDB."""
    stubs = [
        ChromaHit(
            id=f"demo-chunk-{i}",
            document=f"Demo chunk {i} for query: {query_text[:60]}",
            score=round(1.0 - i * 0.05, 4),
            distance=round(i * 0.05, 4),
            metadata={"source": "demo", "chunk_index": i},
        )
        for i in range(min(k, 10))
    ]
    return stubs
