#!/usr/bin/env python3
"""
FAISS Vector Database Client

Provides a resilient client for interacting with the FAISS vector database service.
Includes circuit breaker protection, connection pooling, and automatic retries.

Usage:
    from agents.utils import FAISSClient, get_faiss_client

    # Singleton instance
    client = get_faiss_client()

    # Search for similar vectors
    results = await client.search(
        query_vector=[0.1, 0.2, ...],
        top_k=10,
        index_name="research_papers"
    )

    # Add vectors to index
    await client.add_vectors(
        vectors=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
        ids=["doc1", "doc2"],
        index_name="research_papers"
    )
"""

import os
import logging
import asyncio
import httpx
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from functools import wraps

from .circuit_breaker import faiss_breaker, CircuitBreakerError

logger = logging.getLogger(__name__)


@dataclass
class FAISSConfig:
    """Configuration for FAISS client"""
    host: str = field(default_factory=lambda: os.getenv("FAISS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("FAISS_PORT", "5000")))
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    pool_size: int = 10

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class VectorSearchResult:
    """Result from a vector similarity search"""
    id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None


class FAISSClient:
    """
    Async client for FAISS vector database service.

    Features:
    - Circuit breaker protection for resilience
    - Connection pooling for performance
    - Automatic retries with exponential backoff
    - Batch operations support
    """

    _instance: Optional['FAISSClient'] = None

    def __init__(self, config: Optional[FAISSConfig] = None):
        """
        Initialize FAISS client.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or FAISSConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling"""
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        base_url=self.config.base_url,
                        timeout=httpx.Timeout(self.config.timeout),
                        limits=httpx.Limits(
                            max_connections=self.config.pool_size,
                            max_keepalive_connections=self.config.pool_size // 2,
                        ),
                    )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with circuit breaker and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx

        Returns:
            Response JSON data

        Raises:
            CircuitBreakerError: If circuit is open
            httpx.HTTPError: If all retries fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                with faiss_breaker:
                    client = await self._get_client()
                    response = await client.request(method, endpoint, **kwargs)
                    response.raise_for_status()
                    return response.json()

            except CircuitBreakerError:
                # Don't retry if circuit is open
                raise

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff with jitter
                    delay = self.config.retry_delay * (2 ** attempt)
                    jitter = delay * 0.1 * (asyncio.get_event_loop().time() % 1)
                    await asyncio.sleep(delay + jitter)
                    logger.warning(
                        f"FAISS request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                    )

        raise last_error or Exception("Request failed with no error captured")

    async def health_check(self) -> bool:
        """
        Check if FAISS service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            result = await self._request_with_retry("GET", "/health")
            return result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"FAISS health check failed: {e}")
            return False

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        index_name: str = "default",
        filters: Optional[Dict[str, Any]] = None,
        include_vectors: bool = False,
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            index_name: Name of the FAISS index
            filters: Optional metadata filters
            include_vectors: Whether to include vectors in results

        Returns:
            List of search results sorted by similarity
        """
        payload = {
            "vector": query_vector,
            "top_k": top_k,
            "index": index_name,
            "include_vectors": include_vectors,
        }
        if filters:
            payload["filters"] = filters

        try:
            result = await self._request_with_retry(
                "POST",
                "/search",
                json=payload
            )

            return [
                VectorSearchResult(
                    id=item["id"],
                    score=item["score"],
                    metadata=item.get("metadata", {}),
                    vector=item.get("vector") if include_vectors else None,
                )
                for item in result.get("results", [])
            ]

        except CircuitBreakerError:
            logger.error(f"FAISS circuit breaker open - search unavailable")
            raise
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            raise

    async def search_batch(
        self,
        query_vectors: List[List[float]],
        top_k: int = 10,
        index_name: str = "default",
    ) -> List[List[VectorSearchResult]]:
        """
        Batch search for similar vectors.

        Args:
            query_vectors: List of query embedding vectors
            top_k: Number of results per query
            index_name: Name of the FAISS index

        Returns:
            List of result lists, one per query
        """
        payload = {
            "vectors": query_vectors,
            "top_k": top_k,
            "index": index_name,
        }

        result = await self._request_with_retry(
            "POST",
            "/search/batch",
            json=payload
        )

        return [
            [
                VectorSearchResult(
                    id=item["id"],
                    score=item["score"],
                    metadata=item.get("metadata", {}),
                )
                for item in batch_results
            ]
            for batch_results in result.get("results", [])
        ]

    async def add_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        index_name: str = "default",
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Add vectors to an index.

        Args:
            vectors: List of embedding vectors
            ids: List of document IDs (must match vectors length)
            index_name: Name of the FAISS index
            metadata: Optional metadata for each vector

        Returns:
            Response with operation status
        """
        if len(vectors) != len(ids):
            raise ValueError("vectors and ids must have the same length")

        payload = {
            "vectors": vectors,
            "ids": ids,
            "index": index_name,
        }
        if metadata:
            if len(metadata) != len(vectors):
                raise ValueError("metadata must have the same length as vectors")
            payload["metadata"] = metadata

        return await self._request_with_retry(
            "POST",
            "/vectors",
            json=payload
        )

    async def delete_vectors(
        self,
        ids: List[str],
        index_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Delete vectors from an index.

        Args:
            ids: List of document IDs to delete
            index_name: Name of the FAISS index

        Returns:
            Response with operation status
        """
        return await self._request_with_retry(
            "DELETE",
            "/vectors",
            json={"ids": ids, "index": index_name}
        )

    async def create_index(
        self,
        index_name: str,
        dimension: int,
        index_type: str = "IVF,PQ",
        metric: str = "L2",
    ) -> Dict[str, Any]:
        """
        Create a new FAISS index.

        Args:
            index_name: Name for the new index
            dimension: Vector dimension
            index_type: FAISS index type (e.g., "IVF,PQ", "HNSW")
            metric: Distance metric ("L2" or "IP" for inner product)

        Returns:
            Response with index creation status
        """
        return await self._request_with_retry(
            "POST",
            "/indices",
            json={
                "name": index_name,
                "dimension": dimension,
                "index_type": index_type,
                "metric": metric,
            }
        )

    async def list_indices(self) -> List[Dict[str, Any]]:
        """
        List all available indices.

        Returns:
            List of index information dictionaries
        """
        result = await self._request_with_retry("GET", "/indices")
        return result.get("indices", [])

    async def get_index_stats(self, index_name: str = "default") -> Dict[str, Any]:
        """
        Get statistics for an index.

        Args:
            index_name: Name of the index

        Returns:
            Index statistics including vector count, dimension, etc.
        """
        return await self._request_with_retry(
            "GET",
            f"/indices/{index_name}/stats"
        )


# Singleton instance
_faiss_client: Optional[FAISSClient] = None
_client_lock = asyncio.Lock()


def get_faiss_client(config: Optional[FAISSConfig] = None) -> FAISSClient:
    """
    Get the singleton FAISS client instance.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        FAISSClient singleton instance
    """
    global _faiss_client

    if _faiss_client is None:
        _faiss_client = FAISSClient(config)

    return _faiss_client


async def close_faiss_client() -> None:
    """Close the singleton FAISS client"""
    global _faiss_client

    if _faiss_client:
        await _faiss_client.close()
        _faiss_client = None
