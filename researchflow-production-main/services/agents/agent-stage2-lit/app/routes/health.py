from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-stage2-lit"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "inference_policy": os.getenv("INFERENCE_POLICY", "local_only"),
        "vector_backend": os.getenv("VECTOR_BACKEND", "chroma"),
        "chromadb_url": os.getenv("CHROMADB_URL", ""),
        "ollama_url": os.getenv("OLLAMA_URL", ""),
    }
