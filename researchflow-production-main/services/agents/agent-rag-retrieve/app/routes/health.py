"""Liveness and readiness probes. Readiness checks Chroma when CHROMADB_URL is set."""
import os
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-rag-retrieve"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    status = "ready"
    details = {"service": "agent-rag-retrieve"}
    chroma_url = os.getenv("CHROMADB_URL", "").strip()
    if chroma_url:
        try:
            from app.chroma_client import get_client
            c = get_client()
            if hasattr(c, "list_collections"):
                c.list_collections()
            else:
                c.get_or_create_collection("_ready_check", metadata={"description": "readiness"})
            details["chroma"] = "ok"
        except Exception:
            status = "degraded"
            details["chroma"] = "unavailable"
    return {"status": status, **details}
