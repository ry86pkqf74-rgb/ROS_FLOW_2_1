"""FastAPI application for Evidence Synthesis Agent"""
from __future__ import annotations
import json
from typing import Any, AsyncGenerator, Dict
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse

from agent.schemas import AgentResponse, AgentTask
from agent.evidence_synthesis import run_evidence_synthesis

app = FastAPI(
    title="agent-evidence-synthesis",
    description="Biomedical & Clinical Research Evidence Synthesis Agent with GRADE methodology",
    version="1.0.0"
)


@app.get("/health")
def health() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> Dict[str, str]:
    """Readiness check endpoint"""
    return {"status": "ready"}


@app.post("/agents/run/sync")
async def run_sync(task: AgentTask) -> Dict[str, Any]:
    """
    Synchronous execution endpoint
    
    Task type must be "EVIDENCE_SYNTHESIS"
    """
    if task.task_type != "EVIDENCE_SYNTHESIS":
        raise HTTPException(
            status_code=400, 
            detail=f"task_type must be EVIDENCE_SYNTHESIS, got {task.task_type}"
        )

    try:
        outputs, warnings = await run_evidence_synthesis(task.inputs, task.mode)
        
        resp = AgentResponse(
            ok=True,
            request_id=task.request_id,
            task_type=task.task_type,
            outputs=outputs,
            warnings=warnings,
        )
        return resp.model_dump()
    
    except Exception as e:
        return AgentResponse(
            ok=False,
            request_id=task.request_id,
            task_type=task.task_type,
            outputs={"error": str(e)},
            warnings=[f"Execution failed: {str(e)}"],
        ).model_dump()


@app.post("/agents/run/stream")
async def run_stream(task: AgentTask) -> Response:
    """
    Streaming execution endpoint with progress updates
    
    Task type must be "EVIDENCE_SYNTHESIS"
    """
    if task.task_type != "EVIDENCE_SYNTHESIS":
        raise HTTPException(
            status_code=400, 
            detail=f"task_type must be EVIDENCE_SYNTHESIS, got {task.task_type}"
        )

    async def gen() -> AsyncGenerator[bytes, None]:
        """Generate SSE stream"""
        try:
            yield b"data: " + json.dumps({
                "event": "start", 
                "request_id": task.request_id,
                "step": "initialization"
            }).encode() + b"\n\n"
            
            yield b"data: " + json.dumps({
                "event": "progress", 
                "pct": 10,
                "step": "question_decomposition"
            }).encode() + b"\n\n"
            
            yield b"data: " + json.dumps({
                "event": "progress", 
                "pct": 25,
                "step": "evidence_retrieval"
            }).encode() + b"\n\n"
            
            # Run the synthesis
            outputs, warnings = await run_evidence_synthesis(task.inputs, task.mode)
            
            yield b"data: " + json.dumps({
                "event": "progress", 
                "pct": 80,
                "step": "synthesis_complete"
            }).encode() + b"\n\n"
            
            yield b"data: " + json.dumps({
                "event": "final", 
                "request_id": task.request_id,
                "outputs": outputs,
                "warnings": warnings
            }).encode() + b"\n\n"
            
        except Exception as e:
            yield b"data: " + json.dumps({
                "event": "error",
                "request_id": task.request_id,
                "message": str(e)
            }).encode() + b"\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
