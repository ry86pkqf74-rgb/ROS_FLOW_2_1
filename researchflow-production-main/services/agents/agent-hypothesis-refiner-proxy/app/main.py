"""
Hypothesis Refiner Agent - LangSmith Proxy
Adapts ResearchFlow agent contract to LangSmith API calls
"""
import httpx
import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import settings

# Configure logging (PHI-safe: never log request/response bodies)
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Schemas
class AgentRunRequest(BaseModel):
    """Standard ResearchFlow agent request schema"""
    task_type: str
    request_id: str
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    mode: str = "DEMO"
    risk_tier: str = "NON_SENSITIVE"
    domain_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)


class AgentRunResponse(BaseModel):
    """Standard ResearchFlow agent response schema"""
    ok: bool
    request_id: str
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# HTTP client lifecycle
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage HTTP client lifecycle"""
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.langsmith_timeout_seconds, connect=10.0),
        follow_redirects=True
    )
    logger.info("HTTP client initialized")
    yield
    await http_client.aclose()
    logger.info("HTTP client closed")


# FastAPI app
app = FastAPI(
    title="Hypothesis Refiner Agent Proxy",
    description="LangSmith cloud proxy for agent-hypothesis-refiner",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "agent-hypothesis-refiner-proxy"}


@app.get("/health/ready")
async def health_ready():
    """Readiness check - validates LangSmith connectivity"""
    if not settings.langsmith_api_key:
        raise HTTPException(
            status_code=503,
            detail="LANGSMITH_API_KEY not configured"
        )
    
    # Verify LangSmith API is reachable
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.langsmith_api_url}/info",
                headers={"x-api-key": settings.langsmith_api_key}
            )
            # Require 2xx from LangSmith /info for readiness (fail on 4xx/5xx)
            if 200 <= response.status_code < 300:
                return {"status": "ready", "langsmith": "ok", "upstream_status": response.status_code}
            raise HTTPException(
                status_code=503,
                detail=f"LangSmith /info not ready: {response.status_code}"
            )
except httpx.RequestError as e:
        logger.error(f"LangSmith readiness check failed: {type(e).__name__}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach LangSmith API: {type(e).__name__}"
        )


@app.post("/agents/run/sync", response_model=AgentRunResponse)
async def run_agent_sync(request: AgentRunRequest):
    """
    Synchronous agent execution
    Proxies to LangSmith cloud agent for Hypothesis Refiner
    """
    logger.info(f"Received request: {request.request_id} (task_type={request.task_type})")
    
    if not settings.langsmith_api_key:
        logger.error("LANGSMITH_API_KEY not configured")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error="LANGSMITH_API_KEY not configured"
        )
    
    # Transform ResearchFlow request to LangSmith format
    langsmith_payload = {
        "assistant_id": settings.langsmith_agent_id,
        "input": {
            "research_question": request.inputs.get("research_question"),
            "hypothesis": request.inputs.get("hypothesis"),
            "context": request.inputs.get("context"),
            "constraints": request.inputs.get("constraints"),
            "variables": request.inputs.get("variables"),
            "population": request.inputs.get("population"),
            "intervention": request.inputs.get("intervention"),
            "comparison": request.inputs.get("comparison"),
            "outcomes": request.inputs.get("outcomes"),
            "study_design": request.inputs.get("study_design"),
            "citations": request.inputs.get("citations"),
            "output_format": request.inputs.get("output_format"),
            "request_id": request.request_id,
            "mode": request.mode,
        },
        "config": {
            "configurable": {
                "thread_id": request.request_id,  # Use request_id as thread_id for traceability
            }
        },
        "stream_mode": "values"  # Get final values only
    }
    
    try:
        # Call LangSmith agent
        logger.info(f"Calling LangSmith agent {settings.langsmith_agent_id}")
        response = await http_client.post(
            f"{settings.langsmith_api_url}/assistants/{settings.langsmith_agent_id}/invoke",
            json=langsmith_payload,
            headers={
                "x-api-key": settings.langsmith_api_key,
                "Content-Type": "application/json"
            }
        )
        
        response.raise_for_status()
        langsmith_response = response.json()
        logger.info(f"LangSmith response received for {request.request_id} (status={response.status_code})")
        
        # Transform LangSmith response to ResearchFlow format
        output = langsmith_response.get("output", {})
        
        return AgentRunResponse(
            ok=True,
            request_id=request.request_id,
            outputs={
                "refined_hypotheses": output.get("refined_hypotheses", []),
                "evidence_summary": output.get("evidence_summary"),
                "scoring_matrix": output.get("scoring_matrix"),
                "google_doc_url": output.get("google_doc_url"),
                "recommendations": output.get("recommendations"),
                "metadata": output.get("metadata", {}),
                "langsmith_run_id": langsmith_response.get("metadata", {}).get("run_id")
            }
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"LangSmith API error: status_code={e.response.status_code}, exception={type(e).__name__}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"LangSmith API error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error calling LangSmith: exception={type(e).__name__}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Network error: {type(e).__name__}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error: exception={type(e).__name__}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Unexpected error: {type(e).__name__}"
        )


@app.post("/agents/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """
    Streaming agent execution (SSE)
    Proxies to LangSmith cloud agent with streaming
    """
    logger.info(f"Received streaming request: {request.request_id}")
    
    if not settings.langsmith_api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "LANGSMITH_API_KEY not configured"}
        )
    
    # Transform ResearchFlow request to LangSmith format
    langsmith_payload = {
        "assistant_id": settings.langsmith_agent_id,
        "input": {
            "research_question": request.inputs.get("research_question"),
            "hypothesis": request.inputs.get("hypothesis"),
            "context": request.inputs.get("context"),
            "constraints": request.inputs.get("constraints"),
            "variables": request.inputs.get("variables"),
            "population": request.inputs.get("population"),
            "intervention": request.inputs.get("intervention"),
            "comparison": request.inputs.get("comparison"),
            "outcomes": request.inputs.get("outcomes"),
            "study_design": request.inputs.get("study_design"),
            "citations": request.inputs.get("citations"),
            "output_format": request.inputs.get("output_format"),
            "request_id": request.request_id,
            "mode": request.mode,
        },
        "config": {
            "configurable": {
                "thread_id": request.request_id,
            }
        },
        "stream_mode": "updates"  # Stream updates
    }
    
    async def event_stream():
        """Generator for SSE events (proxy verbatim, no double-framing)"""
        try:
            async with http_client.stream(
                "POST",
                f"{settings.langsmith_api_url}/assistants/{settings.langsmith_agent_id}/stream",
                json=langsmith_payload,
                headers={
                    "x-api-key": settings.langsmith_api_key,
                    "Content-Type": "application/json"
                }
            ) as response:
                response.raise_for_status()
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        # Forward LangSmith SSE events verbatim (no double-framing)
                        yield chunk
                        
        except Exception as e:
            logger.exception(f"Streaming error: exception={type(e).__name__}")
            yield f"data: {{'error': '{type(e).__name__}'}}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler (PHI-safe)"""
    logger.exception(f"Unhandled exception: exception={type(exc).__name__}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": type(exc).__name__}
    )
