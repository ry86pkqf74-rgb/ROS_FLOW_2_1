from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthResponse)
async def ready():
    """Readiness probe."""
    return {"status": "ready"}
