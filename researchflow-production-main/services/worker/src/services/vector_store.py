"""
Vector store adapter for RAG (agents/rag/search and agents/rag/index).

Wraps ChromaVectorStore with async interface using asyncio.to_thread.
Returns objects with id, content, metadata, score for API consistency.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RAGSearchHit:
    """Single RAG search result (content alias for Chroma document)."""
    id: str
    content: str
    metadata: Dict[str, Any]
    score: float


@dataclass
class RAGIndexResult:
    """Result of a batch index operation."""
    indexed_count: int
    updated_count: int
    collection: str


def _get_chroma_sync():
    """Sync getter for Chroma client (used from thread)."""
    from src.vectordb import get_chroma_client
    return get_chroma_client()


async def get_vector_store():
    """
    Return an async vector store wrapper (object with search and index methods).
    Uses asyncio.to_thread for Chroma's sync API.
    """
    return _VectorStoreAdapter()


class _VectorStoreAdapter:
    """Async adapter around ChromaVectorStore."""

    def __init__(self):
        self._chroma = None

    def _chroma_sync(self):
        if self._chroma is None:
            self._chroma = _get_chroma_sync()
        return self._chroma

    async def search(
        self,
        collection_name: str,
        query: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> List[RAGSearchHit]:
        """Search collection; options may include topK and filter (where)."""
        opts = options or {}
        top_k = opts.get("topK", 5)
        where = opts.get("filter")

        def _search():
            client = self._chroma_sync()
            results = client.search(
                collection_name=collection_name,
                query=query,
                k=top_k,
                where=where,
            )
            return [
                RAGSearchHit(
                    id=r.id,
                    content=r.document,
                    metadata=r.metadata or {},
                    score=r.score,
                )
                for r in results
            ]

        return await asyncio.to_thread(_search)

    async def index(
        self,
        collection_name: str,
        documents: List[str],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> RAGIndexResult:
        """Batch upsert documents into collection; then persist."""
        def _index():
            client = self._chroma_sync()
            result = client.index_documents(
                collection_name=collection_name,
                documents=documents,
                ids=ids,
                metadatas=metadatas,
            )
            client.persist()
            return RAGIndexResult(
                indexed_count=result.indexed_count,
                updated_count=result.updated_count,
                collection=result.collection,
            )

        return await asyncio.to_thread(_index)
