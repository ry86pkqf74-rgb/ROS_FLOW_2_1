from fastapi import APIRouter
import os

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-policy-review"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-policy-review",
        "governance_mode": os.getenv("GOVERNANCE_MODE", "DEMO"),
    }
