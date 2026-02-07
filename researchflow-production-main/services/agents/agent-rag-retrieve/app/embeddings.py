"""Query embedding for RAG. Uses OpenAI when OPENAI_API_KEY set."""
from __future__ import annotations

import os
from typing import List

import httpx
import structlog

logger = structlog.get_logger()

EMBEDDING_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


def embed_query(text: str) -> List[float] | None:
    """
    Embed a single query string. Returns 1536-dim vector from OpenAI or None if unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        logger.warning("OPENAI_API_KEY not set; cannot embed query")
        return None

    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                OPENAI_EMBED_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": EMBEDDING_MODEL, "input": text[:8000]},
            )
            r.raise_for_status()
            data = r.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.warning("embed_query_failed", error=str(type(e).__name__))
        return None
