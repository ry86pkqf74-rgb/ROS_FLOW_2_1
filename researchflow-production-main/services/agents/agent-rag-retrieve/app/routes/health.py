from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-rag-retrieve"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "vector_backend": os.getenv("VECTOR_BACKEND", "chroma"),
        "chromadb_url": os.getenv("CHROMADB_URL", ""),
        "worker_rag_url": os.getenv("WORKER_RAG_URL", ""),
        "rag_collection": os.getenv("RAG_COLLECTION", "researchflow"),
    }
