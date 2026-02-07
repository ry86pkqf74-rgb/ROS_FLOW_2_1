import time
import orjson
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import structlog

from agent.schemas import AgentError, AgentRunRequest, AgentRunResponse
from agent.impl import run_sync, run_stream

logger = structlog.get_logger()

router = APIRouter()


@router.post("/agents/run/sync", response_model=AgentRunResponse)
async def agents_run_sync(req: AgentRunRequest) -> AgentRunResponse:
    """Always returns AgentRunResponse envelope (success or error)."""
    started = time.time()
    logger.info(
        "sync_request",
        request_id=req.request_id,
        task_type=req.task_type,
    )
    try:
        result = await run_sync(req.model_dump())
        result.setdefault("usage", {})
        result["usage"]["duration_ms"] = int((time.time() - started) * 1000)
        logger.info(
            "sync_complete",
            request_id=req.request_id,
            duration_ms=result["usage"]["duration_ms"],
        )
        return AgentRunResponse(**result)
    except Exception as e:  # noqa: BLE001
        logger.warning("sync_error", request_id=req.request_id, error=str(type(e).__name__))
        return AgentRunResponse(
            status="error",
            request_id=req.request_id,
            outputs={},
            error=AgentError(code="TASK_FAILED", message=str(e)[:500] or "Unknown error"),
        )


@router.post("/agents/run/stream")
async def agents_run_stream(req: Request):
    payload = await req.json()
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", "unknown")
    
    logger.info(
        "stream_request_start",
        request_id=request_id,
        task_type=task_type,
    )

    async def event_generator():
        async for evt in run_stream(payload):
            yield {
                "event": evt.get("type", "message"),
                "data": orjson.dumps(evt).decode("utf-8"),
            }

    return EventSourceResponse(event_generator())
