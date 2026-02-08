"""
Peer Review Simulator Agent - LangSmith Proxy
Adapts ResearchFlow agent contract to LangSmith API calls for peer review simulation
"""
import httpx
import logging
from typing import Any, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import settings

# Configure logging
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
    title="Peer Review Simulator Agent Proxy",
    description="LangSmith cloud proxy for agent-peer-review-simulator",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "agent-peer-review-simulator-proxy"}


@app.get("/health/ready")
async def health_ready():
    """Readiness check - validates LangSmith connectivity"""
    if not settings.langsmith_api_key:
        raise HTTPException(
            status_code=503,
            detail="LANGSMITH_API_KEY not configured"
        )
    
    # Verify LangSmith API is reachable (simple ping)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use LangSmith API heartbeat endpoint if available
            response = await client.get(
                f"{settings.langsmith_api_url}/info",
                headers={"x-api-key": settings.langsmith_api_key}
            )
            # Special-case auth failures for clarity
            if response.status_code in (401, 403):
                raise HTTPException(
                    status_code=503,
                    detail={"status": "not_ready", "langsmith": "auth_failed", "status_code": response.status_code}
                )
            # Only 2xx indicates truly ready
            if 200 <= response.status_code < 300:
                return {"status": "ready", "langsmith": "reachable"}
            # Any other non-2xx is not ready
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "langsmith": {"reachable": False, "status_code": response.status_code}
                }
            )
    except httpx.RequestError as e:
        logger.error(f"LangSmith readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach LangSmith API: {str(e)}"
        )


@app.post("/agents/run/sync", response_model=AgentRunResponse)
async def run_agent_sync(request: AgentRunRequest):
    """
    Synchronous agent execution
    Proxies to LangSmith cloud agent for peer review simulation
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
            "manuscript": request.inputs.get("manuscript", ""),
            "personas": request.inputs.get("personas", [
                "methodologist",
                "statistician", 
                "ethics_reviewer",
                "domain_expert"
            ]),
            "study_type": request.inputs.get("study_type", "observational"),
            "enable_iteration": request.inputs.get("enable_iteration", True),
            "max_cycles": request.inputs.get("max_cycles", 3),
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
        logger.info(f"LangSmith response received for {request.request_id}")
        
        # Transform LangSmith response to ResearchFlow format
        # LangSmith returns: {"output": {...}, "metadata": {...}}
        output = langsmith_response.get("output", {})
        
        return AgentRunResponse(
            ok=True,
            request_id=request.request_id,
            outputs={
                "peer_review_report": output.get("peer_review_report", {}),
                "checklists": output.get("checklists", []),
                "response_letter": output.get("response_letter"),
                "google_doc_url": output.get("google_doc_url"),
                "iterations": output.get("iterations", 1),
                "approved": output.get("approved", False),
                "metadata": output.get("metadata", {}),
                "langsmith_run_id": langsmith_response.get("metadata", {}).get("run_id")
            }
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"LangSmith API error: {e.response.status_code} - {e.response.text}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"LangSmith API error: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error calling LangSmith: {e}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Network error: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Unexpected error: {str(e)}"
        )


@app.post("/agents/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """
    Streaming agent execution (SSE)
    Proxies to LangSmith cloud agent with streaming for peer review
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
            "manuscript": request.inputs.get("manuscript", ""),
            "personas": request.inputs.get("personas", [
                "methodologist",
                "statistician",
                "ethics_reviewer",
                "domain_expert"
            ]),
            "study_type": request.inputs.get("study_type", "observational"),
            "enable_iteration": request.inputs.get("enable_iteration", True),
            "max_cycles": request.inputs.get("max_cycles", 3),
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
        """Generator for SSE events"""
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
                        # Forward LangSmith SSE events
                        yield f"data: {chunk}\n\n"
                        
        except Exception as e:
            logger.exception(f"Streaming error: {e}")
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
