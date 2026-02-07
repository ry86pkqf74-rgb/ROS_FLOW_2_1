"""Chroma HTTP client for RAG retrieval. Uses CHROMADB_URL and optional CHROMADB_AUTH_TOKEN."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()


@dataclass
class SearchHit:
    """Single hit from Chroma query."""

    id: str
    document: str
    metadata: Dict[str, Any]
    distance: float
    score: float  # 1 / (1 + distance) for similarity-like score


def _get_chroma_client():
    """Lazy singleton Chroma HTTP client. Uses CHROMADB_URL (e.g. http://chromadb:8000)."""
    import chromadb

    url = os.getenv("CHROMADB_URL", "http://localhost:8000").strip().rstrip("/")
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    auth_token = os.getenv("CHROMADB_AUTH_TOKEN", "").strip()

    if auth_token and hasattr(chromadb.auth, "token"):
        try:
            from chromadb.config import Settings
            creds = chromadb.auth.token.TokenAuthCredentialsProvider(auth_token)
            settings = Settings(chroma_client_auth_credentials_provider=creds)
            return chromadb.HttpClient(host=host, port=port, settings=settings)
        except Exception:
            pass
    return chromadb.HttpClient(host=host, port=port)


_client: Optional[Any] = None


def get_client():
    global _client
    if _client is None:
        _client = _get_chroma_client()
    return _client


def query(
    collection_name: str,
    query_text: str,
    k: int = 10,
    where: Optional[Dict[str, Any]] = None,
    query_embedding: Optional[List[float]] = None,
) -> List[SearchHit]:
    """
    Query a Chroma collection. Embeds query_text via OpenAI if query_embedding not provided.

    Returns list of SearchHit with id (chunk id), document, metadata, distance, score.
    """
    from app.embeddings import embed_query

    client = get_client()
    coll = client.get_or_create_collection(
        name=collection_name,
        metadata={"description": f"RAG collection: {collection_name}"},
    )

    embedding = query_embedding
    if embedding is None:
        embedding = embed_query(query_text)
    if embedding is None:
        logger.warning("no_embedding_available", collection=collection_name)
        return []

    results = coll.query(
        query_embeddings=[embedding],
        n_results=min(k, 100),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    hits: List[SearchHit] = []
    if not results or not results.get("ids") or not results["ids"][0]:
        return hits

    ids = results["ids"][0]
    docs = results.get("documents") and results["documents"][0] or [""] * len(ids)
    metadatas = results.get("metadatas") and results["metadatas"][0] or [{}] * len(ids)
    distances = results.get("distances") and results["distances"][0] or [0.0] * len(ids)

    for i, chunk_id in enumerate(ids):
        dist = distances[i] if i < len(distances) else 0.0
        score = 1.0 / (1.0 + dist) if dist >= 0 else 0.0
        hits.append(
            SearchHit(
                id=chunk_id,
                document=docs[i] if i < len(docs) else "",
                metadata=metadatas[i] if i < len(metadatas) else {},
                distance=dist,
                score=score,
            )
        )
    return hits
