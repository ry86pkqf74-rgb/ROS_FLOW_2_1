"""
Clinical Bias Detection Agent - LangSmith Proxy
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
    title="Clinical Bias Detection Agent Proxy",
    description="LangSmith cloud proxy for agent-bias-detection",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "agent-bias-detection-proxy"}


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
    Proxies to LangSmith cloud agent for Clinical Bias Detection
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
            # Dataset inputs
            "dataset_summary": request.inputs.get("dataset_summary", ""),
            "dataset_url": request.inputs.get("dataset_url", ""),  # Google Sheets URL if provided
            "pasted_data": request.inputs.get("pasted_data", ""),
            
            # Analysis parameters
            "sensitive_attributes": request.inputs.get("sensitive_attributes", []),
            "outcome_variables": request.inputs.get("outcome_variables", []),
            "sample_size": request.inputs.get("sample_size"),
            
            # Optional configuration
            "few_shot_examples": request.inputs.get("few_shot_examples", []),
            "audit_spreadsheet_id": request.inputs.get("audit_spreadsheet_id", ""),
            "generate_report": request.inputs.get("generate_report", True),
            "output_email": request.inputs.get("output_email", ""),
            
            # Metadata
            "request_id": request.request_id,
            "mode": request.mode,
            "workflow_id": request.workflow_id,
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
        result = response.json()
        
        logger.info(f"LangSmith response received: {result.get('thread_id', 'N/A')}")
        
        # Transform LangSmith response to ResearchFlow format
        # LangSmith returns a structure like {"values": [...], "thread_id": "...", ...}
        # Extract the last message or final output
        outputs = {}
        if "values" in result and isinstance(result["values"], list) and len(result["values"]) > 0:
            last_value = result["values"][-1]
            outputs = last_value.get("output", last_value)
        elif "output" in result:
            outputs = result["output"]
        else:
            outputs = result
        
        return AgentRunResponse(
            ok=True,
            request_id=request.request_id,
            outputs={
                "bias_verdict": outputs.get("bias_verdict", ""),
                "bias_score": outputs.get("bias_score", 0),
                "bias_flags": outputs.get("bias_flags", []),
                "mitigation_plan": outputs.get("mitigation_plan", {}),
                "compliance_risk": outputs.get("compliance_risk", {}),
                "red_team_validation": outputs.get("red_team_validation", {}),
                "report_url": outputs.get("report_url", ""),
                "audit_log_url": outputs.get("audit_log_url", ""),
                "mitigated_data_url": outputs.get("mitigated_data_url", ""),
                "full_response": outputs
            }
        )
        
    except httpx.HTTPStatusError as e:
        error_detail = f"LangSmith API error: {e.response.status_code}"
        try:
            error_body = e.response.json()
            error_detail += f" - {error_body.get('detail', str(error_body))}"
        except:
            error_detail += f" - {e.response.text}"
        
        logger.error(error_detail)
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=error_detail
        )
        
    except httpx.RequestError as e:
        error_msg = f"Request to LangSmith failed: {str(e)}"
        logger.error(error_msg)
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=error_msg
        )
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return AgentRunResponse(
            ok=False,
            request_id=request.request_id,
            error=error_msg
        )


@app.post("/agents/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """
    Streaming agent execution
    Proxies to LangSmith cloud agent with streaming support
    """
    logger.info(f"Received stream request: {request.request_id} (task_type={request.task_type})")
    
    if not settings.langsmith_api_key:
        logger.error("LANGSMITH_API_KEY not configured")
        return JSONResponse(
            status_code=503,
            content={"error": "LANGSMITH_API_KEY not configured"}
        )
    
    # Transform ResearchFlow request to LangSmith format
    langsmith_payload = {
        "assistant_id": settings.langsmith_agent_id,
        "input": {
            "dataset_summary": request.inputs.get("dataset_summary", ""),
            "dataset_url": request.inputs.get("dataset_url", ""),
            "pasted_data": request.inputs.get("pasted_data", ""),
            "sensitive_attributes": request.inputs.get("sensitive_attributes", []),
            "outcome_variables": request.inputs.get("outcome_variables", []),
            "sample_size": request.inputs.get("sample_size"),
            "few_shot_examples": request.inputs.get("few_shot_examples", []),
            "audit_spreadsheet_id": request.inputs.get("audit_spreadsheet_id", ""),
            "generate_report": request.inputs.get("generate_report", True),
            "output_email": request.inputs.get("output_email", ""),
            "request_id": request.request_id,
            "mode": request.mode,
            "workflow_id": request.workflow_id,
        },
        "config": {
            "configurable": {
                "thread_id": request.request_id,
            }
        },
        "stream_mode": "updates"  # Stream updates
    }
    
    async def stream_response():
        """Generator for streaming LangSmith responses"""
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
                        yield chunk
                        
        except Exception as e:
            logger.error(f"Stream error: {str(e)}", exc_info=True)
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )
