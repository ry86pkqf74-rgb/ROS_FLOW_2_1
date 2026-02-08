"""
Multilingual Literature Processor Agent - LangSmith Proxy
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
    logger.info("HTTP client initialized for Multilingual Literature Processor Proxy")
    yield
    await http_client.aclose()
    logger.info("HTTP client closed")


# FastAPI app
app = FastAPI(
    title="Multilingual Literature Processor Agent Proxy",
    description="LangSmith cloud proxy for agent-multilingual-literature-processor",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "agent-multilingual-literature-processor-proxy"}


@app.get("/health/ready")
async def health_ready():
    """Readiness check - validates LangSmith connectivity and configuration"""
    if not settings.langsmith_api_key:
        raise HTTPException(
            status_code=503,
            detail="LANGSMITH_API_KEY not configured"
        )
    
    if not settings.langsmith_agent_id:
        raise HTTPException(
            status_code=503,
            detail="LANGSMITH_AGENT_ID not configured (set LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID)"
        )
    
    # Verify LangSmith API is reachable
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.langsmith_api_url}/info",
                headers={"x-api-key": settings.langsmith_api_key}
            )
            # Accept 2xx or 4xx (auth errors are config issues, not readiness issues)
            if response.status_code < 500:
                return {
                    "status": "ready",
                    "langsmith": "reachable",
                    "agent_id_configured": bool(settings.langsmith_agent_id)
                }
            else:
                raise HTTPException(
                    status_code=503,
                    detail=f"LangSmith API unhealthy: HTTP {response.status_code}"
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
    Proxies to LangSmith cloud agent
    
    PHI-SAFE: Does not log request/response bodies
    """
    logger.info(
        f"Request received: {request.request_id} (task_type={request.task_type}, mode={request.mode})"
    )
    
    if not settings.langsmith_api_key:
        logger.error("LANGSMITH_API_KEY not configured")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error="LANGSMITH_API_KEY not configured"
        )
    
    if not settings.langsmith_agent_id:
        logger.error("LANGSMITH_AGENT_ID not configured")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error="LANGSMITH_AGENT_ID not configured (set LANGSMITH_MULTILINGUAL_LITERATURE_PROCESSOR_AGENT_ID)"
        )
    
    # Transform ResearchFlow request to LangSmith format
    langsmith_payload = {
        "assistant_id": settings.langsmith_agent_id,
        "input": {
            "query": request.inputs.get("query", ""),
            "language": request.inputs.get("language"),
            "languages": request.inputs.get("languages", []),
            "output_language": request.inputs.get("output_language", "English"),
            "date_range": request.inputs.get("date_range"),
            "citations": request.inputs.get("citations", True),
            "abstracts": request.inputs.get("abstracts", True),
            "full_text": request.inputs.get("full_text", False),
            "context": request.inputs.get("context", {}),
            "output_format": request.inputs.get("output_format", "structured"),
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
                "papers": output.get("papers", []),
                "translations": output.get("translations", {}),
                "synthesis": output.get("synthesis", {}),
                "google_doc_url": output.get("google_doc_url"),
                "citation_export": output.get("citation_export"),
                "language_distribution": output.get("language_distribution", {}),
                "quality_notes": output.get("quality_notes", []),
                "metadata": output.get("metadata", {}),
                "langsmith_run_id": langsmith_response.get("metadata", {}).get("run_id")
            }
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"LangSmith API error: {e.response.status_code}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"LangSmith API error: HTTP {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Network error calling LangSmith: {type(e).__name__}")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Network error: {str(e)}"
        )
    except Exception as e:
        logger.exception("Unexpected error in agent execution")
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=f"Unexpected error: {str(e)}"
        )


@app.post("/agents/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """
    Streaming agent execution (SSE)
    Proxies to LangSmith cloud agent with streaming
    
    PHI-SAFE: Does not log request/response bodies
    """
    logger.info(f"Streaming request received: {request.request_id}")
    
    if not settings.langsmith_api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "LANGSMITH_API_KEY not configured"}
        )
    
    if not settings.langsmith_agent_id:
        return JSONResponse(
            status_code=503,
            content={"error": "LANGSMITH_AGENT_ID not configured"}
        )
    
    # Transform ResearchFlow request to LangSmith format
    langsmith_payload = {
        "assistant_id": settings.langsmith_agent_id,
        "input": {
            "query": request.inputs.get("query", ""),
            "language": request.inputs.get("language"),
            "languages": request.inputs.get("languages", []),
            "output_language": request.inputs.get("output_language", "English"),
            "date_range": request.inputs.get("date_range"),
            "citations": request.inputs.get("citations", True),
            "abstracts": request.inputs.get("abstracts", True),
            "full_text": request.inputs.get("full_text", False),
            "context": request.inputs.get("context", {}),
            "output_format": request.inputs.get("output_format", "structured"),
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
        """Generator for SSE events - proxies LangSmith SSE verbatim"""
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
                
                # Forward LangSmith SSE events verbatim (no double-framing)
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        yield f"data: {chunk}\n\n"
                        
        except Exception as e:
            logger.exception("Streaming error occurred")
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler (PHI-safe: does not log request details)"""
    logger.exception("Unhandled exception occurred")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )
