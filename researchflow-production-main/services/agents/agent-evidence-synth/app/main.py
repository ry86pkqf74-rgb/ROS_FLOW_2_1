from __future__ import annotations
import json
from typing import Any, AsyncGenerator, Dict
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from app.schemas import AgentResponse, AgentTask
from app.synth import run_evidence_synth

app = FastAPI(title="agent-evidence-synth")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> Dict[str, str]:
    return {"status": "ready"}


@app.post("/agents/run/sync")
async def run_sync(task: AgentTask) -> Dict[str, Any]:
    if task.task_type != "EVIDENCE_SYNTH":
        raise HTTPException(status_code=400, detail="task_type must be EVIDENCE_SYNTH")

    outputs, warnings = await run_evidence_synth(task.inputs)
    resp = AgentResponse(
        ok=True,
        request_id=task.request_id,
        task_type=task.task_type,
        outputs=outputs,
        warnings=warnings,
    )
    return resp.model_dump()


@app.post("/agents/run/stream")
async def run_stream(task: AgentTask) -> Response:
    if task.task_type != "EVIDENCE_SYNTH":
        raise HTTPException(status_code=400, detail="task_type must be EVIDENCE_SYNTH")

    async def gen() -> AsyncGenerator[bytes, None]:
        yield b"data: " + json.dumps({"event": "start", "request_id": task.request_id}).encode() + b"\n\n"
        yield b"data: " + json.dumps({"event": "progress", "pct": 25}).encode() + b"\n\n"
        outputs, _warnings = await run_evidence_synth(task.inputs)
        yield b"data: " + json.dumps({"event": "final", "request_id": task.request_id, "outputs": {"paper_count": outputs.get("paper_count")}}).encode() + b"\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
