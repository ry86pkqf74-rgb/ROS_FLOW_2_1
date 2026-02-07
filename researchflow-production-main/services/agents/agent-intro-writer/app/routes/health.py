from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-intro-writer"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-intro-writer",
    }
