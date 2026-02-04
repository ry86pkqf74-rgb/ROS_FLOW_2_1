"""
Health check routes for Docker and Kubernetes probes.
GET /health - liveness (ok if server is up)
GET /health/ready - readiness (config, artifacts, optional Redis)
"""
import os
import sys
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Runtime config: api_server adds src to path, so this works when router is loaded
try:
    from runtime_config import RuntimeConfig
    _config = RuntimeConfig.from_env_and_optional_yaml()
except Exception:
    _config = None

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health():
    """Basic liveness - returns ok if server is running."""
    config = _config
    mode_info = {}
    if config:
        mode_info = {
            "ros_mode": config.ros_mode,
            "no_network": config.no_network,
            "mock_only": config.mock_only,
        }
    return {
        "status": "healthy",
        "service": "ros-worker",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": mode_info,
    }


@router.get("/health/ready", summary="Readiness probe")
async def ready():
    """Readiness with config, artifacts, python path, optional Redis."""
    checks = {}
    all_ok = True
    config = _config

    # Config invariants
    try:
        if config is None:
            checks["config"] = "failed: config not loaded"
            all_ok = False
        elif not hasattr(config, "ros_mode"):
            checks["config"] = "failed: ros_mode not set"
            all_ok = False
        elif config.ros_mode not in ("DEMO", "LIVE", "OFFLINE"):
            checks["config"] = f"failed: invalid ros_mode '{config.ros_mode}'"
            all_ok = False
        else:
            checks["config"] = "ok"
    except Exception as e:
        checks["config"] = f"failed: {str(e)}"
        all_ok = False

    # Artifact path
    artifact_path = os.environ.get("ARTIFACT_PATH", "/data/artifacts")
    try:
        artifact_dir = Path(artifact_path)
        if artifact_dir.exists() and artifact_dir.is_dir():
            checks["artifacts"] = "ok"
        else:
            checks["artifacts"] = "warning: directory not found"
    except Exception as e:
        checks["artifacts"] = f"warning: {str(e)}"

    # Python path
    try:
        src_in_path = any("src" in p for p in sys.path)
        checks["python_path"] = "ok" if src_in_path else "warning: src not in PYTHONPATH"
    except Exception as e:
        checks["python_path"] = f"warning: {str(e)}"

    # Optional Redis check
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, decode_responses=True)
        await client.ping()
        await client.close()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"warning: {str(e)}"

    response = {
        "status": "ready" if all_ok else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": {
            "ros_mode": config.ros_mode if config else "DEMO",
            "no_network": getattr(config, "no_network", False) if config else False,
            "mock_only": getattr(config, "mock_only", False) if config else False,
            "allow_uploads": getattr(config, "allow_uploads", False) if config else False,
        },
    }

    if all_ok:
        return response
    return JSONResponse(status_code=503, content=response)
