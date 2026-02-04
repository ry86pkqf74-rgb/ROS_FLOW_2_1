"""
Literature Search API Routes

FastAPI endpoints for literature search functionality.

Endpoints:
- POST /literature/search - Execute literature search
- GET /literature/papers/{paper_id} - Get paper details
- POST /literature/rank - Rank papers by relevance
- POST /literature/citations - Generate citations
- GET /literature/search/{task_id}/status - Check search progress

Linear Issues: ROS-XXX
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Import agents
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agents.analysis import (
    LitSearchAgent,
    create_lit_search_agent,
    StudyContext,
    Paper,
    RankedPaper,
    Citation,
    LitSearchResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/literature", tags=["literature"])

# Task tracking
search_tasks: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Request/Response Models
# =============================================================================

class LiteratureSearchRequest(BaseModel):
    """Request for literature search."""
    study_context: StudyContext
    max_results: int = Field(50, ge=1, le=200)
    databases: Optional[List[str]] = Field(None, description="Databases to search")
    year_from: Optional[int] = None
    year_to: Optional[int] = None


class LiteratureSearchResponse(BaseModel):
    """Response from literature search."""
    task_id: str
    status: str  # queued, running, completed, failed
    result: Optional[LitSearchResult] = None
    error: Optional[str] = None


class PaperRankRequest(BaseModel):
    """Request to rank papers."""
    papers: List[Paper]
    study_context: StudyContext


class PaperRankResponse(BaseModel):
    """Response from ranking."""
    ranked_papers: List[RankedPaper]


class CitationGenerationRequest(BaseModel):
    """Request to generate citations."""
    papers: List[Paper]
    style: str = Field("AMA", description="Citation style (AMA, APA, MLA, Chicago, Vancouver)")


class CitationGenerationResponse(BaseModel):
    """Response from citation generation."""
    citations: List[Citation]
    style: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/search", response_model=LiteratureSearchResponse)
async def search_literature(request: LiteratureSearchRequest, background_tasks: BackgroundTasks):
    """
    Execute a literature search asynchronously.
    
    Returns immediately with task_id. Use /search/{task_id}/status to check progress.
    """
    task_id = f"lit_search_{datetime.utcnow().timestamp()}"
    
    # Initialize task status
    search_tasks[task_id] = {
        "status": "queued",
        "started_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }
    
    # Run search in background
    background_tasks.add_task(
        _execute_search_task,
        task_id=task_id,
        request=request,
    )
    
    return LiteratureSearchResponse(
        task_id=task_id,
        status="queued",
    )


@router.post("/search/sync", response_model=LiteratureSearchResponse)
async def search_literature_sync(request: LiteratureSearchRequest):
    """
    Execute a literature search synchronously (waits for completion).
    
    Use for simple searches or when immediate results are needed.
    """
    task_id = f"lit_search_sync_{datetime.utcnow().timestamp()}"
    
    try:
        agent = create_lit_search_agent()
        result = await agent.execute(
            study_context=request.study_context,
            max_results=request.max_results,
        )
        await agent.close()
        
        return LiteratureSearchResponse(
            task_id=task_id,
            status="completed",
            result=result,
        )
    except Exception as e:
        logger.error(f"Literature search failed: {e}")
        return LiteratureSearchResponse(
            task_id=task_id,
            status="failed",
            error=str(e),
        )


@router.get("/search/{task_id}/status", response_model=LiteratureSearchResponse)
async def get_search_status(task_id: str):
    """Get the status of an async literature search."""
    if task_id not in search_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = search_tasks[task_id]
    
    return LiteratureSearchResponse(
        task_id=task_id,
        status=task.get("status", "unknown"),
        result=task.get("result"),
        error=task.get("error"),
    )


@router.post("/rank", response_model=PaperRankResponse)
async def rank_papers(request: PaperRankRequest):
    """
    Rank papers by relevance to study context.
    
    Uses AI to evaluate and score papers based on research objectives.
    """
    try:
        agent = create_lit_search_agent()
        ranked_papers = await agent.rank_relevance(
            papers=request.papers,
            study_context=request.study_context,
        )
        await agent.close()
        
        return PaperRankResponse(ranked_papers=ranked_papers)
    except Exception as e:
        logger.error(f"Paper ranking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ranking failed: {e}")


@router.post("/citations", response_model=CitationGenerationResponse)
async def generate_citations(request: CitationGenerationRequest):
    """
    Generate formatted citations for papers.
    
    Supports multiple citation styles: AMA, APA, MLA, Chicago, Vancouver.
    """
    try:
        agent = create_lit_search_agent()
        citations = await agent.extract_citations(papers=request.papers)
        await agent.close()
        
        return CitationGenerationResponse(
            citations=citations,
            style=request.style,
        )
    except Exception as e:
        logger.error(f"Citation generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Citation generation failed: {e}")


@router.get("/papers/{paper_id}")
async def get_paper_details(paper_id: str):
    """
    Get detailed information about a specific paper.
    
    TODO: Implement paper metadata retrieval from database or external APIs.
    """
    # TODO: Implement paper retrieval logic
    raise HTTPException(status_code=501, detail="Paper retrieval not yet implemented")


@router.delete("/search/{task_id}")
async def clear_search_task(task_id: str):
    """Clear a completed search task from tracking."""
    if task_id in search_tasks:
        del search_tasks[task_id]
        return {"message": f"Task {task_id} cleared"}
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# =============================================================================
# Background Task Handlers
# =============================================================================

async def _execute_search_task(task_id: str, request: LiteratureSearchRequest):
    """Background task to execute literature search."""
    try:
        search_tasks[task_id]["status"] = "running"
        
        agent = create_lit_search_agent()
        result = await agent.execute(
            study_context=request.study_context,
            max_results=request.max_results,
        )
        await agent.close()
        
        search_tasks[task_id].update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f"Search task {task_id} failed: {e}")
        search_tasks[task_id].update({
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        })
