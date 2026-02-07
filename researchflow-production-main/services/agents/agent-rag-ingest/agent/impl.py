"""
RAG Ingest agent: chunk documents, embed with OpenAI, store in Chroma.
Outputs strict JSON: ingestedCount, chunkCount, collection, docIds, chunkIds, errors[].
"""

import os
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()

# Defaults from docs/RAG_PIPELINE.md
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " "]
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_BATCH_SIZE = 100


def _chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    Split text into overlapping chunks. Tries separators in order for break points.
    """
    if not text or not text.strip():
        return []
    separators = separators or DEFAULT_SEPARATORS
    chunks: List[str] = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            # Look for a separator to break on
            segment = text[start:end]
            best_break = -1
            for sep in separators:
                idx = segment.rfind(sep)
                if idx > 0 and (best_break < 0 or idx > best_break):
                    best_break = idx
            if best_break > 0:
                end = start + best_break + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - chunk_overlap if (end - chunk_overlap > start) else end
        if start >= len(text):
            break
    return chunks


def _get_chroma_client():
    """Lazy Chroma HTTP client with optional token auth."""
    from urllib.parse import urlparse

    url = os.getenv("CHROMADB_URL", "http://localhost:8000").strip()
    token = os.getenv("CHROMADB_AUTH_TOKEN", "").strip() or None
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 8000)
    use_ssl = parsed.scheme == "https"

    import chromadb
    from chromadb.config import Settings

    kwargs = {"host": host, "port": port}
    if use_ssl:
        kwargs["ssl"] = True
    if token:
        kwargs["settings"] = Settings(
            chroma_client_auth_provider="chromadb.auth.token_authn.TokenAuthClientProvider",
            chroma_client_auth_credentials=token,
        )
    return chromadb.HttpClient(**kwargs)


def _embed_batch(texts: List[str], model: str = DEFAULT_EMBEDDING_MODEL) -> List[List[float]]:
    """Call OpenAI embeddings API. Raises on missing key or API error."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set for embeddings")

    import httpx

    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), OPENAI_BATCH_SIZE):
        batch = texts[i : i + OPENAI_BATCH_SIZE]
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"input": batch, "model": model},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in sorted(data["data"], key=lambda x: x["index"]):
            all_embeddings.append(item["embedding"])
    return all_embeddings


def _sanitize_metadata(m: Dict[str, Any]) -> Dict[str, Any]:
    """Chroma accepts only str, int, float, bool in metadata; no None, list, dict."""
    out = {}
    for k, v in (m or {}).items():
        if v is None:
            continue
        if isinstance(v, (list, dict)):
            continue
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
    return out


async def _execute_rag_ingest(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest documents into Chroma: chunk, embed, store.
    Returns dict suitable for outputs with ingestedCount, chunkCount, collection, docIds, chunkIds, errors[].
    """
    documents = inputs.get("documents") or []
    knowledge_base = (inputs.get("knowledgeBase") or "").strip() or "default"
    domain_id = (inputs.get("domainId") or "").strip() or "default"
    project_id = (inputs.get("projectId") or "").strip() or "default"

    chunk_config = inputs.get("chunkConfig") or {}
    chunk_size = chunk_config.get("chunkSize", chunk_config.get("chunk_size", DEFAULT_CHUNK_SIZE))
    chunk_overlap = chunk_config.get("chunkOverlap", chunk_config.get("chunk_overlap", DEFAULT_CHUNK_OVERLAP))
    separators = chunk_config.get("separators", DEFAULT_SEPARATORS)

    errors: List[str] = []
    all_chunk_ids: List[str] = []
    ingested_doc_ids: List[str] = []
    total_chunks = 0

    if not documents:
        return {
            "ingestedCount": 0,
            "chunkCount": 0,
            "collection": knowledge_base,
            "docIds": [],
            "chunkIds": [],
            "errors": ["No documents provided"],
        }

    # Normalize document list: support list of dicts with docId/title/source/text/metadata
    doc_list: List[Dict[str, Any]] = []
    for d in documents:
        if isinstance(d, dict):
            doc_list.append(d)
        else:
            errors.append("Invalid document entry: not an object")
            continue

    all_texts: List[str] = []
    all_metadatas: List[Dict[str, Any]] = []
    for doc in doc_list:
        doc_id = doc.get("docId") or doc.get("doc_id") or ""
        text = doc.get("text") or ""
        if not doc_id:
            errors.append("Document missing docId")
            continue
        if not text or not str(text).strip():
            errors.append(f"Document {doc_id} has no text")
            continue
        chunks = _chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=separators)
        for idx, chunk_text in enumerate(chunks):
            chunk_id = f"{doc_id}__chunk_{idx}"
            all_chunk_ids.append(chunk_id)
            all_texts.append(chunk_text)
            meta = {
                "knowledgeBase": knowledge_base,
                "domainId": domain_id,
                "projectId": project_id,
                "docId": doc_id,
                "chunkIndex": idx,
            }
            if doc.get("title") is not None:
                meta["title"] = str(doc["title"])[:500]
            if doc.get("source") is not None:
                meta["source"] = str(doc["source"])[:500]
            for k, v in (doc.get("metadata") or {}).items():
                if k not in ("knowledgeBase", "domainId", "projectId", "docId", "chunkIndex") and v is not None:
                    if isinstance(v, (str, int, float, bool)):
                        meta[k] = v
            all_metadatas.append(_sanitize_metadata(meta))
        ingested_doc_ids.append(doc_id)
        total_chunks += len(chunks)

    if not all_texts:
        return {
            "ingestedCount": 0,
            "chunkCount": 0,
            "collection": knowledge_base,
            "docIds": list(dict.fromkeys(ingested_doc_ids)),
            "chunkIds": [],
            "errors": errors if errors else ["No chunks produced from documents"],
        }

    try:
        client = _get_chroma_client()
        collection = client.get_or_create_collection(
            name=knowledge_base,
            metadata={"description": f"RAG collection: {knowledge_base}"},
        )
        embeddings = _embed_batch(all_texts)
        if len(embeddings) != len(all_texts):
            errors.append("Embedding count mismatch")
        else:
            collection.upsert(
                ids=all_chunk_ids,
                documents=all_texts,
                metadatas=all_metadatas,
                embeddings=embeddings,
            )
    except Exception as e:  # noqa: BLE001
        errors.append(str(e)[:500])
        logger.warning("rag_ingest_chroma_error", error=str(type(e).__name__))

    return {
        "ingestedCount": len(ingested_doc_ids),
        "chunkCount": total_chunks,
        "collection": knowledge_base,
        "docIds": list(dict.fromkeys(ingested_doc_ids)),
        "chunkIds": all_chunk_ids,
        "errors": errors,
    }


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous agent execution for RAG ingest."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    inputs = payload.get("inputs", {})

    logger.info("agent_sync_start", request_id=request_id, task_type=task_type)

    outputs = await _execute_rag_ingest(inputs)

    logger.info(
        "agent_sync_complete",
        request_id=request_id,
        task_type=task_type,
        ingested_count=outputs.get("ingestedCount", 0),
        chunk_count=outputs.get("chunkCount", 0),
    )

    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": outputs,
        "artifacts": [],
        "provenance": {"collection": outputs.get("collection", "")},
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming agent execution with SSE events."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    inputs = payload.get("inputs", {})

    logger.info("agent_stream_start", request_id=request_id, task_type=task_type)

    yield {"type": "started", "request_id": request_id, "task_type": task_type}
    yield {"type": "progress", "request_id": request_id, "progress": 30, "step": "chunking"}
    yield {"type": "progress", "request_id": request_id, "progress": 60, "step": "embedding"}

    started = time.perf_counter()
    outputs = await _execute_rag_ingest(inputs)
    duration_ms = int((time.perf_counter() - started) * 1000)

    yield {
        "type": "final",
        "request_id": request_id,
        "task_type": task_type,
        "status": "ok",
        "success": True,
        "outputs": outputs,
        "duration_ms": duration_ms,
    }

    logger.info("agent_stream_complete", request_id=request_id, task_type=task_type)
