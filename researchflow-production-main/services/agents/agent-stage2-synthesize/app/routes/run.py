import time
import orjson
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from agent.schemas import AgentError, AgentRunRequest, AgentRunResponse
from agent.impl import run_sync, run_stream

router = APIRouter()


@router.post("/agents/run/sync", response_model=AgentRunResponse)
async def agents_run_sync(req: AgentRunRequest) -> AgentRunResponse:
    """Always returns AgentRunResponse envelope (success or error)."""
    started = time.time()
    try:
        result = await run_sync(req.model_dump())
        result.setdefault("usage", {})
        result["usage"]["duration_ms"] = int((time.time() - started) * 1000)
        return AgentRunResponse(**result)
    except Exception as e:  # noqa: BLE001
        return AgentRunResponse(
            status="error",
            request_id=req.request_id,
            outputs={},
            error=AgentError(code="TASK_FAILED", message=str(e)[:500] or "Unknown error"),
        )


@router.post("/agents/run/stream")
async def agents_run_stream(req: Request):
    payload = await req.json()

    async def event_generator():
        async for evt in run_stream(payload):
            yield {
                "event": evt.get("type", "message"),
                "data": orjson.dumps(evt).decode("utf-8"),
            }

    return EventSourceResponse(event_generator())
