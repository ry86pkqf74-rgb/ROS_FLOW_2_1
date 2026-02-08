"""Resilience Architecture Advisor Proxy Service

FastAPI proxy service that adapts ResearchFlow contract to LangSmith cloud API
for the Resilience Architecture Advisor agent.
"""
import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import settings

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Resilience Architecture Advisor Proxy",
    description="Proxy service for LangSmith Resilience Architecture Advisor agent",
    version="1.0.0"
)

# HTTP client for LangSmith API
http_client = httpx.AsyncClient(timeout=settings.langsmith_timeout_seconds)


# Request/Response Models
class AgentRunRequest(BaseModel):
    """Request model for agent execution"""
    input: Dict[str, Any] = Field(..., description="Input data for the agent")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Optional configuration")
    stream: bool = Field(default=False, description="Whether to stream the response")


class AgentRunResponse(BaseModel):
    """Response model for synchronous agent execution"""
    output: Any = Field(..., description="Agent output")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Execution metadata")


# Health Check Endpoints
@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "ok",
        "service": settings.service_name,
        "agent_id": settings.langsmith_agent_id
    }


@app.get("/health/ready")
async def health_ready():
    """Readiness check - verifies LangSmith API connectivity"""
    try:
        # Verify we can reach LangSmith API
        response = await http_client.get(
            f"{settings.langsmith_api_url}/assistants/{settings.langsmith_agent_id}",
            headers={
                "X-API-Key": settings.langsmith_api_key,
                "Content-Type": "application/json"
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            return {
                "status": "ready",
                "service": settings.service_name,
                "langsmith_api": "connected"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail=f"LangSmith API returned status {response.status_code}"
            )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="LangSmith API timeout"
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


# Agent Execution Endpoints
@app.post("/agents/run/sync", response_model=AgentRunResponse)
async def run_agent_sync(request: AgentRunRequest):
    """
    Execute agent synchronously and return complete response
    
    This endpoint invokes the LangSmith Resilience Architecture Advisor agent
    and waits for the complete response before returning.
    """
    try:
        logger.info(f"Executing agent synchronously with input: {request.input}")
        
        # Prepare LangSmith API payload
        langsmith_payload = {
            "assistant_id": settings.langsmith_agent_id,
            "input": request.input,
            "config": request.config or {}
        }
        
        # Call LangSmith API
        response = await http_client.post(
            f"{settings.langsmith_api_url}/assistants/{settings.langsmith_agent_id}/invoke",
            headers={
                "X-API-Key": settings.langsmith_api_key,
                "Content-Type": "application/json"
            },
            json=langsmith_payload
        )
        
        if response.status_code != 200:
            logger.error(f"LangSmith API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"LangSmith API error: {response.text}"
            )
        
        result = response.json()
        logger.info("Agent execution completed successfully")
        
        return AgentRunResponse(
            output=result.get("output", result),
            metadata={
                "agent_id": settings.langsmith_agent_id,
                "execution_mode": "sync"
            }
        )
        
    except httpx.TimeoutException:
        logger.error("Agent execution timed out")
        raise HTTPException(
            status_code=504,
            detail=f"Agent execution timed out after {settings.langsmith_timeout_seconds} seconds"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Agent execution failed: {str(e)}"
        )


async def stream_agent_response(request: AgentRunRequest) -> AsyncGenerator[str, None]:
    """
    Generator function to stream agent responses as SSE events
    
    Yields Server-Sent Events (SSE) formatted strings
    """
    try:
        logger.info(f"Executing agent in streaming mode with input: {request.input}")
        
        # Prepare LangSmith API payload
        langsmith_payload = {
            "assistant_id": settings.langsmith_agent_id,
            "input": request.input,
            "config": request.config or {},
            "stream": True
        }
        
        # Stream from LangSmith API
        async with http_client.stream(
            "POST",
            f"{settings.langsmith_api_url}/assistants/{settings.langsmith_agent_id}/stream",
            headers={
                "X-API-Key": settings.langsmith_api_key,
                "Content-Type": "application/json"
            },
            json=langsmith_payload
        ) as response:
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"LangSmith API streaming error: {response.status_code} - {error_text}")
                yield f"event: error\ndata: {json.dumps({'error': error_text.decode()})}\n\n"
                return
            
            # Stream events from LangSmith
            async for line in response.aiter_lines():
                if line.strip():
                    # Forward SSE events to client
                    yield f"{line}\n\n"
            
            logger.info("Agent streaming completed successfully")
            
    except httpx.TimeoutException:
        logger.error("Agent streaming timed out")
        yield f"event: error\ndata: {json.dumps({'error': 'Streaming timed out'})}\n\n"
    except Exception as e:
        logger.error(f"Agent streaming failed: {str(e)}")
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@app.post("/agents/run/stream")
async def run_agent_stream(request: AgentRunRequest):
    """
    Execute agent in streaming mode with Server-Sent Events (SSE)
    
    This endpoint streams agent responses in real-time as they are generated.
    """
    return StreamingResponse(
        stream_agent_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "agent_id": settings.langsmith_agent_id,
        "endpoints": {
            "health": "/health",
            "ready": "/health/ready",
            "sync": "/agents/run/sync",
            "stream": "/agents/run/stream"
        }
    }


# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info(f"Starting {settings.service_name}")
    logger.info(f"LangSmith Agent ID: {settings.langsmith_agent_id}")
    logger.info(f"LangSmith API URL: {settings.langsmith_api_url}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info(f"Shutting down {settings.service_name}")
    await http_client.aclose()
