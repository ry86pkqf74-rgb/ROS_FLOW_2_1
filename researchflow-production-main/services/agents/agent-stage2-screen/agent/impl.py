"""
Stage 2 Literature Screening Agent Implementation
Performs deduplication, criteria screening, and study type tagging.
Uses AI Bridge for LLM-enhanced decisions (optional, deterministic by default).
"""
import time
import os
from typing import Any, AsyncGenerator, Dict, List, Optional
import structlog
import httpx

from agent.schemas import (
    PaperScreeningResult,
    ScreeningCriteria,
    ScreeningOutputs,
    StudyType,
)
from agent.screening import (
    PaperDeduplicator,
    StudyTypeClassifier,
    CriteriaScreener,
)

logger = structlog.get_logger()

TASK_TYPE = "STAGE2_SCREEN"
AI_BRIDGE_TASK_TYPE = "literature_screening"


def _ai_bridge_url() -> str:
    """Get AI Bridge URL from environment."""
    return (
        os.getenv("AI_BRIDGE_URL")
        or os.getenv("ORCHESTRATOR_INTERNAL_URL")
        or os.getenv("ORCHESTRATOR_URL")
        or "http://localhost:3001"
    ).rstrip("/")


def _auth_token() -> str:
    """Get authentication token."""
    return os.getenv("AI_BRIDGE_TOKEN") or os.getenv("WORKER_SERVICE_TOKEN") or ""


async def _invoke_bridge(
    prompt: str,
    governance_mode: str = "DEMO",
    request_id: str = "screen",
    max_tokens: int = 1500,
) -> str:
    """Call AI Bridge for LLM-based screening decisions (deterministic settings)."""
    base = _ai_bridge_url()
    token = _auth_token()
    
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    payload = {
        "prompt": prompt,
        "options": {
            "taskType": AI_BRIDGE_TASK_TYPE,
            "modelTier": "STANDARD",
            "governanceMode": governance_mode,
            "requirePhiCompliance": False,
            "maxTokens": max_tokens,
            "temperature": 0.0,  # Deterministic for screening
        },
        "metadata": {
            "agentId": "agent-stage2-screen",
            "projectId": "researchflow",
            "runId": request_id,
            "threadId": "thread-screen",
            "stageRange": [2, 2],
            "currentStage": 2,
        },
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{base}/api/ai-bridge/invoke",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()
            data = r.json()
            content = (data.get("content") or data.get("text") or "").strip()
            return content or ""
    except Exception as e:
        logger.warning("bridge_invoke_failed", error=str(type(e).__name__), message=str(e))
        return ""


def _normalize_inputs(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize and validate inputs."""
    inputs = payload.get("inputs", {})
    
    # Extract papers
    papers = inputs.get("papers", [])
    if not isinstance(papers, list):
        papers = []
    
    # Extract criteria
    criteria_dict = inputs.get("criteria", {})
    if not isinstance(criteria_dict, dict):
        criteria_dict = {}
    
    # Parse study types
    study_types_required = []
    if criteria_dict.get("study_types_required"):
        for st in criteria_dict["study_types_required"]:
            try:
                study_types_required.append(StudyType(st))
            except ValueError:
                logger.warning("invalid_study_type", study_type=st)
    
    study_types_excluded = []
    if criteria_dict.get("study_types_excluded"):
        for st in criteria_dict["study_types_excluded"]:
            try:
                study_types_excluded.append(StudyType(st))
            except ValueError:
                logger.warning("invalid_study_type", study_type=st)
    
    criteria = ScreeningCriteria(
        inclusion=criteria_dict.get("inclusion", []),
        exclusion=criteria_dict.get("exclusion", []),
        required_keywords=criteria_dict.get("required_keywords", []),
        excluded_keywords=criteria_dict.get("excluded_keywords", []),
        study_types_required=study_types_required,
        study_types_excluded=study_types_excluded,
        year_min=criteria_dict.get("year_min"),
        year_max=criteria_dict.get("year_max"),
        require_abstract=criteria_dict.get("require_abstract", True),
    )
    
    domain_id = inputs.get("domainId") or inputs.get("domain_id") or "clinical"
    governance_mode = (
        payload.get("mode")
        or inputs.get("governanceMode")
        or inputs.get("governance_mode")
        or "DEMO"
    )
    
    use_ai = inputs.get("use_ai", False)  # Disabled by default (deterministic)
    
    return {
        "papers": papers,
        "criteria": criteria,
        "domain_id": domain_id,
        "governance_mode": governance_mode,
        "use_ai": use_ai,
    }


async def _execute_screening(
    inputs: Dict[str, Any],
    request_id: str,
) -> ScreeningOutputs:
    """Execute the screening pipeline."""
    papers = inputs["papers"]
    criteria = inputs["criteria"]
    governance_mode = inputs["governance_mode"]
    use_ai = inputs["use_ai"]
    
    if not papers:
        return ScreeningOutputs(
            included=[],
            excluded=[],
            duplicates=[],
            total_processed=0,
            stats={
                "total_input": 0,
                "duplicates_removed": 0,
                "included_count": 0,
                "excluded_count": 0,
            },
        )
    
    # Step 1: Deduplication
    logger.info("deduplication_start", paper_count=len(papers))
    unique_papers, duplicate_papers, duplicate_map = PaperDeduplicator.find_duplicates(papers)
    
    duplicate_results = []
    for dup_paper in duplicate_papers:
        paper_id = dup_paper.get("id") or dup_paper.get("pmid") or f"paper_{len(duplicate_results)}"
        duplicate_results.append(
            PaperScreeningResult(
                paper_id=str(paper_id),
                title=dup_paper.get("title", "Untitled"),
                verdict="duplicate",
                reason="Duplicate of existing paper",
                duplicate_of=dup_paper.get("duplicate_of"),
                metadata={"signature": dup_paper.get("duplicate_signature", "")},
            )
        )
    
    logger.info(
        "deduplication_complete",
        unique_count=len(unique_papers),
        duplicate_count=len(duplicate_results),
    )
    
    # Step 2: Apply criteria screening
    logger.info("criteria_screening_start", paper_count=len(unique_papers))
    screener = CriteriaScreener(criteria)
    
    included_results = []
    excluded_results = []
    
    for paper in unique_papers:
        paper_id = paper.get("id") or paper.get("pmid") or paper.get("paper_id", "")
        title = paper.get("title", "Untitled")
        
        # Classify study type
        study_type = StudyTypeClassifier.classify(paper)
        
        # Apply criteria
        is_included, reason, matched_criteria = screener.screen_paper(paper)
        
        result = PaperScreeningResult(
            paper_id=str(paper_id),
            title=title,
            verdict="included" if is_included else "excluded",
            reason=reason,
            study_type=study_type,
            confidence=1.0,
            matched_criteria=matched_criteria,
            metadata={
                "year": paper.get("year") or paper.get("publication_year"),
                "authors": paper.get("authors", [])[:3],  # First 3 authors
                "doi": paper.get("doi"),
            },
        )
        
        if is_included:
            included_results.append(result)
        else:
            excluded_results.append(result)
    
    logger.info(
        "criteria_screening_complete",
        included_count=len(included_results),
        excluded_count=len(excluded_results),
    )
    
    # Step 3: Optional AI-enhanced screening for borderline cases
    # (Currently disabled - keeping deterministic for production safety)
    # In future iterations, can use AI Bridge to review borderline cases
    
    stats = {
        "total_input": len(papers),
        "duplicates_removed": len(duplicate_results),
        "unique_papers": len(unique_papers),
        "included_count": len(included_results),
        "excluded_count": len(excluded_results),
        "study_type_distribution": {},
    }
    
    # Calculate study type distribution
    for result in included_results:
        if result.study_type:
            st = result.study_type.value
            stats["study_type_distribution"][st] = (
                stats["study_type_distribution"].get(st, 0) + 1
            )
    
    return ScreeningOutputs(
        included=included_results,
        excluded=excluded_results,
        duplicates=duplicate_results,
        total_processed=len(papers),
        stats=stats,
    )


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous agent execution."""
    started = time.time()
    request_id = payload.get("request_id", "unknown")
    
    logger.info("agent_sync_start", request_id=request_id)
    
    try:
        # Normalize inputs
        inputs = _normalize_inputs(payload)
        
        # Execute screening
        outputs = await _execute_screening(inputs, request_id)
        
        duration_ms = int((time.time() - started) * 1000)
        
        logger.info(
            "agent_sync_complete",
            request_id=request_id,
            duration_ms=duration_ms,
            included=len(outputs.included),
            excluded=len(outputs.excluded),
            duplicates=len(outputs.duplicates),
        )
        
        return {
            "status": "ok",
            "request_id": request_id,
            "outputs": outputs.model_dump(by_alias=True),
            "artifacts": [],
            "provenance": {
                "governance_mode": inputs["governance_mode"],
                "domain_id": inputs["domain_id"],
            },
            "usage": {"duration_ms": duration_ms},
        }
    
    except Exception as e:
        logger.error("agent_sync_error", request_id=request_id, error=str(e))
        return {
            "status": "error",
            "request_id": request_id,
            "outputs": {},
            "error": {
                "code": "SCREENING_FAILED",
                "message": str(e)[:500],
            },
        }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Streaming agent execution with SSE events."""
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", TASK_TYPE)
    
    logger.info("agent_stream_start", request_id=request_id)
    
    # Emit started event
    yield {
        "type": "started",
        "request_id": request_id,
        "task_type": task_type,
    }
    
    try:
        # Normalize inputs
        yield {
            "type": "progress",
            "request_id": request_id,
            "progress": 10,
            "step": "normalizing_inputs",
        }
        
        inputs = _normalize_inputs(payload)
        papers_count = len(inputs["papers"])
        
        yield {
            "type": "progress",
            "request_id": request_id,
            "progress": 20,
            "step": "deduplicating",
            "papers_count": papers_count,
        }
        
        # Execute screening
        outputs = await _execute_screening(inputs, request_id)
        
        yield {
            "type": "progress",
            "request_id": request_id,
            "progress": 90,
            "step": "finalizing",
        }
        
        # Emit final event with outputs
        yield {
            "type": "final",
            "request_id": request_id,
            "task_type": task_type,
            "status": "ok",
            "success": True,
            "outputs": outputs.model_dump(by_alias=True),
            "provenance": {
                "governance_mode": inputs["governance_mode"],
                "domain_id": inputs["domain_id"],
            },
            "duration_ms": 0,
        }
        
        logger.info("agent_stream_complete", request_id=request_id)
    
    except Exception as e:
        logger.error("agent_stream_error", request_id=request_id, error=str(e))
        
        yield {
            "type": "final",
            "request_id": request_id,
            "task_type": task_type,
            "status": "error",
            "success": False,
            "outputs": {},
            "error": {
                "code": "SCREENING_FAILED",
                "message": str(e)[:500],
            },
            "duration_ms": 0,
        }
