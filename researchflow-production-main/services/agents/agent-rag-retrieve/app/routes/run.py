import time
import orjson
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from agent.schemas import AgentRunRequest, AgentRunResponse
from agent.impl import run_sync, run_stream

router = APIRouter()


@router.post("/agents/run/sync", response_model=AgentRunResponse)
async def agents_run_sync(req: AgentRunRequest):
    started = time.time()
    result = await run_sync(req.model_dump())
    result.setdefault("usage", {})
    result["usage"]["duration_ms"] = int((time.time() - started) * 1000)
    return AgentRunResponse(**result)


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
