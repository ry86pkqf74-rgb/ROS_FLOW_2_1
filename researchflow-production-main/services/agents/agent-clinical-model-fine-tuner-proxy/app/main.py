"""
Clinical Model Fine-Tuner Agent - LangSmith Proxy
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
    title="Clinical Model Fine-Tuner Agent Proxy",
    description="LangSmith cloud proxy for clinical model fine-tuning lifecycle management",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "agent-clinical-model-fine-tuner-proxy"}


@app.get("/health/ready")
async def health_ready():
    """Readiness check - validates LangSmith connectivity"""
    if not settings.langsmith_api_key:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "LANGSMITH_API_KEY not configured"}
        )
    
    # Verify LangSmith API is reachable with 2xx response
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.langsmith_api_url}/info",
                headers={"x-api-key": settings.langsmith_api_key}
            )
            
            # Only 2xx status means ready
            if 200 <= response.status_code < 300:
                return JSONResponse(
                    status_code=200,
                    content={"status": "ready", "langsmith": "reachable"}
                )
            # Auth failures are configuration issues
            elif response.status_code in (401, 403):
                logger.error(f"LangSmith authentication failed: {response.status_code}")
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "LangSmith authentication failed"}
                )
            # Other non-2xx responses
            else:
                logger.error(f"LangSmith API returned non-2xx: {response.status_code}")
                return JSONResponse(
                    status_code=503,
                    content={"status": "not_ready", "reason": "LangSmith API unhealthy", "status_code": response.status_code}
                )
    except httpx.RequestError as e:
        logger.error(f"LangSmith readiness check failed: {type(e).__name__}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Cannot reach LangSmith API"}
        )


@app.post("/agents/run/sync", response_model=AgentRunResponse)
async def run_agent_sync(request: AgentRunRequest):
    """
    Synchronous agent execution
    Proxies to LangSmith cloud agent for Clinical Model Fine-Tuner
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
            # Fine-tuning workflow inputs
            "clinical_domain": request.inputs.get("clinical_domain", ""),
            "target_task": request.inputs.get("target_task", ""),
            "model_provider": request.inputs.get("model_provider", "openai"),
            "dataset_specifications": request.inputs.get("dataset_specifications", {}),
            "evaluation_criteria": request.inputs.get("evaluation_criteria", {}),
            "compliance_requirements": request.inputs.get("compliance_requirements", ["HIPAA"]),
            "fine_tune_config": request.inputs.get("fine_tune_config", {}),
            "workflow_phase": request.inputs.get("workflow_phase", "data_preparation"),
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
                # Data preparation outputs
                "synthetic_dataset": output.get("synthetic_dataset", []),
                "dataset_schema": output.get("dataset_schema", {}),
                "dataset_metadata_url": output.get("dataset_metadata_url"),
                
                # HIPAA compliance outputs
                "compliance_report": output.get("compliance_report", {}),
                "audit_status": output.get("audit_status", "pending"),
                "compliance_doc_url": output.get("compliance_doc_url"),
                
                # Fine-tuning outputs
                "fine_tune_job_id": output.get("fine_tune_job_id"),
                "model_id": output.get("model_id"),
                "training_metrics": output.get("training_metrics", {}),
                "cost_estimate": output.get("cost_estimate", {}),
                
                # Evaluation outputs
                "evaluation_report": output.get("evaluation_report", {}),
                "evaluation_metrics": output.get("evaluation_metrics", {}),
                "regression_test_results": output.get("regression_test_results", {}),
                
                # Documentation
                "model_card_url": output.get("model_card_url"),
                "github_issue_url": output.get("github_issue_url"),
                "tracking_sheet_url": output.get("tracking_sheet_url"),
                
                # Metadata
                "workflow_status": output.get("workflow_status", "in_progress"),
                "next_steps": output.get("next_steps", []),
                "metadata": output.get("metadata", {}),
                "langsmith_run_id": langsmith_response.get("metadata", {}).get("run_id")
            }
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(
            f"LangSmith API error for request_id={request.request_id}, "
            f"task_type={request.task_type}, status_code={e.response.status_code}"
        )
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
            "clinical_domain": request.inputs.get("clinical_domain", ""),
            "target_task": request.inputs.get("target_task", ""),
            "model_provider": request.inputs.get("model_provider", "openai"),
            "dataset_specifications": request.inputs.get("dataset_specifications", {}),
            "evaluation_criteria": request.inputs.get("evaluation_criteria", {}),
            "compliance_requirements": request.inputs.get("compliance_requirements", ["HIPAA"]),
            "fine_tune_config": request.inputs.get("fine_tune_config", {}),
            "workflow_phase": request.inputs.get("workflow_phase", "data_preparation"),
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
        """Generator for SSE events - proxy upstream verbatim"""
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
                
                # Proxy upstream SSE stream verbatim (already framed)
                async for chunk in response.aiter_text():
                    yield chunk
                        
        except Exception as e:
            logger.error(
                f"Streaming error for request_id={request.request_id}, "
                f"task_type={request.task_type}, error_type={type(e).__name__}"
            )
            # Emit valid JSON error event
            import json
            error_data = json.dumps({"error": "STREAM_ERROR", "type": type(e).__name__})
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: type={type(exc).__name__}, path={request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Proxy error",
            "type": type(exc).__name__
        }
    )
