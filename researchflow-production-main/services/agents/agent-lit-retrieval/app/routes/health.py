from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-lit-retrieval"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-lit-retrieval",
        "retrieval_backend": os.getenv("RETRIEVAL_BACKEND", "pubmed"),
    }
