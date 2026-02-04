"""
Agent API Routes for ResearchFlow Worker

Exposes LangGraph agents via FastAPI endpoints with:
- WebSocket support for real-time progress
- Task queuing and status tracking
- RAG search integration

Linear Issues: ROS-67, ROS-68
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field
import redis.asyncio as redis

from src.agents import (
    get_agent_for_stage,
    get_agent_by_name,
    list_agents,
    AgentResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])

# Task status tracking
task_status: Dict[str, Dict[str, Any]] = {}
active_websockets: Dict[str, List[WebSocket]] = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class AgentRunRequest(BaseModel):
    """Request to run an agent."""
    task_id: str = Field(..., description="Unique task identifier")
    stage_id: int = Field(..., ge=1, le=20, description="Workflow stage (1-20)")
    research_id: str = Field(..., description="Parent research project ID")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Task input data")
    agent_name: Optional[str] = Field(None, description="Override agent selection by name")
    thread_id: Optional[str] = Field(None, description="Thread ID for checkpointing")


class AgentRunResponse(BaseModel):
    """Response from agent run."""
    task_id: str
    status: str  # queued, running, completed, failed
    agent_name: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Status of a running/completed agent task."""
    task_id: str
    status: str
    agent_name: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentListResponse(BaseModel):
    """List of available agents."""
    agents: List[Dict[str, Any]]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=AgentListResponse)
async def list_available_agents():
    """List all available research agents."""
    return AgentListResponse(agents=list_agents())


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest, background_tasks: BackgroundTasks):
    """
    Run an agent asynchronously.
    
    Returns immediately with task_id. Use /status/{task_id} or WebSocket to track progress.
    """
    # Get appropriate agent
    if request.agent_name:
        agent = get_agent_by_name(request.agent_name)
    else:
        agent = get_agent_for_stage(request.stage_id)
    
    if not agent:
        raise HTTPException(
            status_code=400,
            detail=f"No agent available for stage {request.stage_id}"
        )
    
    # Initialize task status
    task_status[request.task_id] = {
        "status": "queued",
        "agent_name": agent.config.name,
        "started_at": datetime.utcnow().isoformat(),
        "progress": {"stage": "initializing", "iteration": 0},
    }
    
    # Run in background
    background_tasks.add_task(
        _run_agent_task,
        agent=agent,
        task_id=request.task_id,
        stage_id=request.stage_id,
        research_id=request.research_id,
        input_data=request.input_data,
        thread_id=request.thread_id,
    )
    
    return AgentRunResponse(
        task_id=request.task_id,
        status="queued",
        agent_name=agent.config.name,
    )


@router.post("/run/sync", response_model=AgentRunResponse)
async def run_agent_sync(request: AgentRunRequest):
    """
    Run an agent synchronously (waits for completion).
    
    Use for simple tasks or when real-time progress isn't needed.
    """
    # Get appropriate agent
    if request.agent_name:
        agent = get_agent_by_name(request.agent_name)
    else:
        agent = get_agent_for_stage(request.stage_id)
    
    if not agent:
        raise HTTPException(
            status_code=400,
            detail=f"No agent available for stage {request.stage_id}"
        )
    
    try:
        result = await agent.run(
            task_id=request.task_id,
            stage_id=request.stage_id,
            research_id=request.research_id,
            input_data=request.input_data,
            thread_id=request.thread_id,
        )
        
        return AgentRunResponse(
            task_id=request.task_id,
            status="completed" if result.success else "failed",
            agent_name=agent.config.name,
            result=asdict(result) if result.success else None,
            error=result.error if not result.success else None,
        )
    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        return AgentRunResponse(
            task_id=request.task_id,
            status="failed",
            agent_name=agent.config.name,
            error=str(e),
        )
    finally:
        await agent.close()


@router.get("/status/{task_id}", response_model=AgentStatusResponse)
async def get_task_status(task_id: str):
    """Get the status of an agent task."""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    status = task_status[task_id]
    return AgentStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        agent_name=status.get("agent_name"),
        progress=status.get("progress"),
        result=status.get("result"),
        error=status.get("error"),
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
    )


@router.websocket("/ws/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for real-time agent progress updates.
    
    Connect to receive:
    - progress: {stage, iteration, quality_score}
    - complete: {result}
    - error: {message}
    """
    await websocket.accept()
    
    # Register websocket
    if task_id not in active_websockets:
        active_websockets[task_id] = []
    active_websockets[task_id].append(websocket)
    
    try:
        # Send initial status if task exists
        if task_id in task_status:
            await websocket.send_json({
                "type": "status",
                "data": task_status[task_id],
            })
        
        # Keep connection alive and wait for messages
        while True:
            try:
                # Wait for any client messages (ping/pong or commands)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})
                
    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        if task_id in active_websockets:
            active_websockets[task_id].remove(websocket)
            if not active_websockets[task_id]:
                del active_websockets[task_id]


@router.delete("/status/{task_id}")
async def clear_task_status(task_id: str):
    """Clear a completed task from status tracking."""
    if task_id in task_status:
        del task_status[task_id]
        return {"message": f"Task {task_id} cleared"}
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# =============================================================================
# Background Task Runner
# =============================================================================

async def _run_agent_task(
    agent,
    task_id: str,
    stage_id: int,
    research_id: str,
    input_data: Dict[str, Any],
    thread_id: Optional[str],
):
    """Background task to run agent and broadcast progress."""
    try:
        # Update status to running
        task_status[task_id]["status"] = "running"
        await _broadcast_progress(task_id, {
            "type": "progress",
            "data": {"stage": "starting", "iteration": 0},
        })
        
        # Run the agent
        result = await agent.run(
            task_id=task_id,
            stage_id=stage_id,
            research_id=research_id,
            input_data=input_data,
            thread_id=thread_id,
        )
        
        # Update status
        task_status[task_id].update({
            "status": "completed" if result.success else "failed",
            "result": asdict(result),
            "completed_at": datetime.utcnow().isoformat(),
            "error": result.error if not result.success else None,
        })
        
        # Broadcast completion
        await _broadcast_progress(task_id, {
            "type": "complete" if result.success else "error",
            "data": asdict(result),
        })
        
    except Exception as e:
        logger.error(f"Agent task {task_id} failed: {e}")
        task_status[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        })
        await _broadcast_progress(task_id, {
            "type": "error",
            "data": {"message": str(e)},
        })
    finally:
        await agent.close()


async def _broadcast_progress(task_id: str, message: Dict[str, Any]):
    """Broadcast progress to all connected WebSocket clients."""
    if task_id not in active_websockets:
        return
    
    disconnected = []
    for websocket in active_websockets[task_id]:
        try:
            await websocket.send_json(message)
        except Exception:
            disconnected.append(websocket)
    
    # Cleanup disconnected
    for ws in disconnected:
        active_websockets[task_id].remove(ws)


# =============================================================================
# RAG Search Endpoint (for orchestrator to call)
# =============================================================================

class RAGSearchRequest(BaseModel):
    """Request for RAG document search."""
    query: str
    collection: str
    top_k: int = 5
    filter: Optional[Dict[str, Any]] = None


class RAGSearchResponse(BaseModel):
    """Response from RAG search."""
    results: List[Dict[str, Any]]
    query: str
    collection: str


@router.post("/rag/search", response_model=RAGSearchResponse)
async def rag_search(request: RAGSearchRequest):
    """
    Search vector store for relevant documents.
    
    Called by agents during the RETRIEVE phase.
    """
    # Import here to avoid circular dependency
    try:
        from src.services.vector_store import get_vector_store
        
        store = await get_vector_store()
        results = await store.search(
            collection_name=request.collection,
            query=request.query,
            options={"topK": request.top_k, "filter": request.filter},
        )
        
        return RAGSearchResponse(
            results=[
                {
                    "id": r.id,
                    "content": r.content,
                    "metadata": r.metadata,
                    "score": r.score,
                }
                for r in results
            ],
            query=request.query,
            collection=request.collection,
        )
    except ImportError:
        # Vector store not configured
        logger.warning("Vector store not available")
        return RAGSearchResponse(
            results=[],
            query=request.query,
            collection=request.collection,
        )
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(status_code=500, detail=f"RAG search failed: {e}")


# =============================================================================
# RAG Index Endpoint (batch upsert for feedback guidance, etc.)
# =============================================================================

class RAGIndexDocument(BaseModel):
    """Single document for RAG index."""
    id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class RAGIndexRequest(BaseModel):
    """Request for batch RAG index/upsert."""
    collection: str
    documents: List[RAGIndexDocument]


class RAGIndexResponse(BaseModel):
    """Response from RAG index."""
    indexed_count: int
    updated_count: int
    collection: str


@router.post("/rag/index", response_model=RAGIndexResponse)
async def rag_index(request: RAGIndexRequest):
    """
    Batch upsert documents into a Chroma collection.
    Used by feedback->RAG loop (ai_feedback_guidance) and other RAG ingestion.
    """
    try:
        from src.services.vector_store import get_vector_store

        store = await get_vector_store()
        ids = [d.id for d in request.documents]
        documents = [d.content for d in request.documents]
        metadatas = [d.metadata or {} for d in request.documents]

        result = await store.index(
            collection_name=request.collection,
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )
        return RAGIndexResponse(
            indexed_count=result.indexed_count,
            updated_count=result.updated_count,
            collection=result.collection,
        )
    except ImportError:
        logger.warning("Vector store not available")
        raise HTTPException(
            status_code=503,
            detail="Vector store not configured",
        )
    except Exception as e:
        logger.error(f"RAG index failed: {e}")
        raise HTTPException(status_code=500, detail=f"RAG index failed: {e}")
