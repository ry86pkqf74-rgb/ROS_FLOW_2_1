from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.retrieval import run_lit_retrieval
from app.schemas import AgentResponse, AgentTask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="agent-lit-retrieval")

DEMO_OVERRIDE = os.getenv("LIT_RETRIEVAL_DEMO", "").lower() in ("1", "true", "yes")

# Timeout for retrieval (seconds); prevents hung PubMed calls
RETRIEVAL_TIMEOUT = int(os.getenv("LIT_RETRIEVAL_TIMEOUT_SECONDS", "60"))


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> Dict[str, str]:
    return {"status": "ready"}


@app.post("/agents/run/sync")
def run_sync(task: AgentTask) -> Dict[str, Any]:
    if task.task_type != "LIT_RETRIEVAL":
        # Contract-shaped error for orchestrator
        body = {
            "ok": False,
            "request_id": task.request_id,
            "task_type": task.task_type,
            "outputs": {},
            "warnings": ["task_type must be LIT_RETRIEVAL"],
        }
        raise HTTPException(status_code=400, detail=body)

    # PHI-safe: do not log task.inputs or query; include request_id for tracing
    logger.info("LIT_RETRIEVAL sync request_id=%s task_type=%s", task.request_id, task.task_type)
    started = time.perf_counter()

    demo = DEMO_OVERRIDE or (task.mode == "DEMO")
    papers, warnings = run_lit_retrieval(
        task.inputs,
        mode=task.mode or None,
        demo_override=demo,
        timeout_seconds=RETRIEVAL_TIMEOUT,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info("LIT_RETRIEVAL completed request_id=%s count=%s duration_ms=%s", task.request_id, len(papers), duration_ms)

    resp = AgentResponse(
        ok=True,
        request_id=task.request_id,
        task_type=task.task_type,
        outputs={"papers": papers, "count": len(papers), "duration_ms": duration_ms},
        warnings=warnings,
    )
    return resp.model_dump()


@app.post("/agents/run/stream")
async def run_stream(task: AgentTask) -> Response:
    if task.task_type != "LIT_RETRIEVAL":
        body = {
            "ok": False,
            "request_id": task.request_id,
            "task_type": task.task_type,
            "outputs": {},
            "warnings": ["task_type must be LIT_RETRIEVAL"],
        }
        raise HTTPException(status_code=400, detail=body)

    async def gen() -> AsyncGenerator[bytes, None]:
        yield b"data: " + json.dumps({"event": "start", "request_id": task.request_id}).encode() + b"\n\n"
        yield b"data: " + json.dumps({"event": "progress", "pct": 50}).encode() + b"\n\n"
        demo = DEMO_OVERRIDE or (task.mode == "DEMO")
        papers, _ = run_lit_retrieval(
            task.inputs, mode=task.mode or None, demo_override=demo, timeout_seconds=RETRIEVAL_TIMEOUT
        )
        yield b"data: " + json.dumps(
            {"event": "final", "request_id": task.request_id, "outputs": {"count": len(papers)}}
        ).encode() + b"\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
