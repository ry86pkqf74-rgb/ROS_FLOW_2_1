from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Liveness probe")
def health():
    return {"status": "ok", "service": "agent-discussion-writer"}


@router.get("/health/ready", summary="Readiness probe")
def ready():
    return {
        "status": "ready",
        "service": "agent-discussion-writer",
    }
