"""
Dissemination Formatter Agent - LangSmith Proxy
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
    title="Dissemination Formatter Agent Proxy",
    description="LangSmith cloud proxy for agent-dissemination-formatter",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "agent-dissemination-formatter-proxy"}


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
            if response.status_code < 500:
                return {"status": "ready", "langsmith": "reachable"}
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"LangSmith API unhealthy: {response.status_code}"
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
    Proxies to LangSmith cloud agent for Dissemination Formatter
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
            "manuscript_text": request.inputs.get("manuscript_text", ""),
            "target_journal": request.inputs.get("target_journal", ""),
            "output_format": request.inputs.get("output_format", "text"),
            "citation_style": request.inputs.get("citation_style"),
            "include_cover_letter": request.inputs.get("include_cover_letter", True),
            "verify_references": request.inputs.get("verify_references", True),
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
        
        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"LangSmith API error ({response.status_code}): {error_detail}")
            return AgentRunResponse(
                ok=False,
                request_id=request.request_id,
                error=f"LangSmith API error: {response.status_code}"
            )
        
        # Parse LangSmith response
        langsmith_response = response.json()
        logger.info(f"LangSmith response received for {request.request_id}")
        
        # Transform LangSmith response to ResearchFlow format
        outputs = {
            "formatted_manuscript": langsmith_response.get("output", {}).get("formatted_manuscript", ""),
            "validation_report": langsmith_response.get("output", {}).get("validation_report", {}),
            "reference_verification_report": langsmith_response.get("output", {}).get("reference_verification_report", {}),
            "cover_letter": langsmith_response.get("output", {}).get("cover_letter"),
            "submission_email_draft": langsmith_response.get("output", {}).get("submission_email_draft"),
            "google_doc_url": langsmith_response.get("output", {}).get("google_doc_url"),
            "langsmith_run_id": langsmith_response.get("metadata", {}).get("run_id"),
        }
        
        return AgentRunResponse(
            ok=True,
            request_id=request.request_id,
            outputs=outputs
        )
        
    except httpx.TimeoutException:
        logger.error(f"LangSmith API timeout for {request.request_id}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error="LangSmith API timeout - formatting took too long"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Unexpected error: {str(e)}"
        )


@app.post("/agents/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """
    Streaming agent execution
    Returns Server-Sent Events (SSE) stream
    """
    logger.info(f"Received streaming request: {request.request_id} (task_type={request.task_type})")
    
    if not settings.langsmith_api_key:
        raise HTTPException(
            status_code=503,
            detail="LANGSMITH_API_KEY not configured"
        )
    
    # Transform to LangSmith format (same as sync)
    langsmith_payload = {
        "assistant_id": settings.langsmith_agent_id,
        "input": {
            "manuscript_text": request.inputs.get("manuscript_text", ""),
            "target_journal": request.inputs.get("target_journal", ""),
            "output_format": request.inputs.get("output_format", "text"),
            "citation_style": request.inputs.get("citation_style"),
            "include_cover_letter": request.inputs.get("include_cover_letter", True),
            "verify_references": request.inputs.get("verify_references", True),
            "request_id": request.request_id,
            "mode": request.mode,
        },
        "config": {
            "configurable": {
                "thread_id": request.request_id,
            }
        },
        "stream_mode": "updates"  # Stream updates for progress
    }
    
    async def event_generator():
        """Generate SSE events from LangSmith stream"""
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
                if response.status_code != 200:
                    yield f"data: {{\"error\": \"LangSmith API error: {response.status_code}\"}}\n\n"
                    return
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        # Forward SSE chunk
                        yield chunk
                        
        except httpx.TimeoutException:
            yield f"data: {{\"error\": \"LangSmith API timeout\"}}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {{\"error\": \"Stream error: {str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )
