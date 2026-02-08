"""
ResearchFlow Worker - FastAPI entry and job consumer.

Phase 3: App Integration & Monitoring.
- FastAPI app with /health, /api/workflow/execute, /api/workflow/stages/{stage_id}/status, /metrics
- Optional Redis job consumer in lifespan (RUN_CONSUMER=1)
- Preserves WorkerService and all job logic for queue-based execution.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel, Field

from api.routes.manuscript_generate import router as manuscript_router
from api.routes.legend_generation import router as legend_router
from api.ai_endpoints import router as ai_router

# Analytics API routes
try:
    import sys
    sys.path.append('/'.join(__file__.split('/')[:-2]))  # Add parent directory to path
    from app.routes.analytics import router as analytics_router
    ANALYTICS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Analytics routes not available: {e}")
    ANALYTICS_AVAILABLE = False

from config import get_config
from services import (
    close_cumulative_data_client,
    get_cumulative_data_client,
)
from utils.logging import get_logger
from utils.metrics import get_metrics_content_type, get_metrics_output
from workflow_engine import (
    StageContext,
    list_stages,
    run_stages as workflow_run_stages,
)
from workflow_engine.registry import get_stage
from workflow_engine.orchestrator import execute_workflow

# Phase C - Literature and Data Processing
from jobs import (
    LiteratureIndexingConfig,
    SummarizationConfig,
    index_literature,
    summarize_literature,
)

logger = get_logger("worker")

# ---------------------------------------------------------------------------
# Execution store for stage status (in-memory, bounded)
# ---------------------------------------------------------------------------
_EXECUTION_STORE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_EXECUTION_STORE_MAX = int(os.getenv("WORKFLOW_EXECUTION_STORE_MAX", "500"))


def _store_execution(job_id: str, result: Dict[str, Any]) -> None:
    while len(_EXECUTION_STORE) >= _EXECUTION_STORE_MAX:
        _EXECUTION_STORE.popitem(last=False)
    _EXECUTION_STORE[job_id] = result


def _get_execution(job_id: str) -> Optional[Dict[str, Any]]:
    return _EXECUTION_STORE.get(job_id)


# ---------------------------------------------------------------------------
# Pydantic models for API
# ---------------------------------------------------------------------------
class WorkflowExecuteRequest(BaseModel):
    """Request body for POST /api/workflow/execute."""

    job_id: str = Field(..., description="Unique job identifier")
    config: Dict[str, Any] = Field(default_factory=dict)
    stage_ids: Optional[List[int]] = Field(
        default=None,
        description="Stage IDs to run (1-20). Omit to run all registered stages.",
    )
    stop_on_failure: bool = Field(default=True)
    governance_mode: str = Field(default="DEMO")
    dataset_pointer: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str = Field(..., description="Service health status (e.g. healthy)")
    service: str = Field(..., description="Service name (worker)")
    running: bool = Field(..., description="Whether the job consumer is running")
    current_job: Optional[str] = Field(None, description="Currently processing job ID if any")
    governance_mode: str = Field(..., description="Current governance mode (DEMO/LIVE)")
    timestamp: str = Field(..., description="ISO timestamp of the check")
    redis: Optional[str] = Field(None, description="Redis status when deep=1 (ok or error message)")


class WorkflowExecuteResponse(BaseModel):
    """Response for POST /api/workflow/execute."""

    job_id: str = Field(..., description="Job identifier")
    stages_completed: List[int] = Field(default_factory=list, description="Stage IDs completed successfully")
    stages_failed: List[int] = Field(default_factory=list, description="Stage IDs that failed")
    stages_skipped: List[int] = Field(default_factory=list, description="Stage IDs skipped")
    results: Dict[str, Any] = Field(default_factory=dict, description="Per-stage results")
    success: bool = Field(..., description="Whether the workflow run succeeded")


class StageStatusResponse(BaseModel):
    """Response for GET /api/workflow/stages/{stage_id}/status."""

    stage_id: int = Field(..., description="Stage identifier (1-20)")
    execution_id: Optional[str] = Field(None, description="Job ID when querying a specific run")
    status: Optional[str] = Field(None, description="Stage status (completed/failed/skipped)")
    stage_name: Optional[str] = Field(None, description="Human-readable stage name")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    errors: Optional[List[str]] = Field(None, description="Error messages from the stage run")
    registered: bool = Field(..., description="Whether the stage is registered")


class StageExecuteRequest(BaseModel):
    """Request body for POST /api/workflow/stages/{stage}/execute."""

    workflow_id: str = Field(..., description="Workflow identifier")
    research_question: str = Field(..., description="Research question for literature analysis")
    user_id: str = Field(..., description="User identifier")
    job_id: str = Field(..., description="Job identifier for tracking")


class StageExecuteResponse(BaseModel):
    """Response for POST /api/workflow/stages/{stage}/execute."""

    success: bool = Field(..., description="Whether the stage execution succeeded")
    stage: int = Field(..., description="Stage number that was executed")
    workflow_id: str = Field(..., description="Workflow identifier")
    job_id: str = Field(..., description="Job identifier")
    artifacts: List[str] = Field(default_factory=list, description="Generated artifacts")
    results: Dict[str, Any] = Field(default_factory=dict, description="Stage execution results")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    stage_name: str = Field(..., description="Human-readable stage name")


# ---------------------------------------------------------------------------
# WorkerService (unchanged job logic)
# ---------------------------------------------------------------------------
from dataclasses import asdict, dataclass


@dataclass
class JobRequest:
    """Represents a job request from the orchestrator."""

    job_id: str
    type: str
    config: Dict[str, Any]
    dataset_pointer: Optional[str] = None
    stages: Optional[list] = None
    callback_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class JobResult:
    """Represents a job result to send back to orchestrator."""

    job_id: str
    status: str
    completed_at: str
    duration: int
    stages_completed: list
    result: Optional[Dict[str, Any]] = None
    artifacts: Optional[list] = None
    manifest: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class WorkerService:
    """Main worker service class for job processing."""

    def __init__(self):
        cfg = get_config()
        self.redis_url = cfg.redis_url
        self.callback_base_url = cfg.orchestrator_url
        self.governance_mode = cfg.governance_mode
        self.artifact_path = cfg.artifact_path
        self.log_path = cfg.log_path
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.current_job: Optional[str] = None

    async def start(self) -> None:
        """Start the worker service."""
        logger.info(
            "starting_worker",
            governance_mode=self.governance_mode,
            redis_url=self.redis_url[:50] + "..." if len(self.redis_url) > 50 else self.redis_url,
        )
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        self.http_client = httpx.AsyncClient(timeout=30.0)
        await self.redis_client.ping()
        try:
            os.makedirs(self.artifact_path, exist_ok=True)
            os.makedirs(self.log_path, exist_ok=True)
        except PermissionError as e:
            raise RuntimeError(
                f"Cannot create storage dirs (artifact_path={self.artifact_path!r}, log_path={self.log_path!r}). "
                "Ensure /data/* paths exist and are writable; use a volume mount for /data in deployment."
            ) from e
        self.running = True
        logger.info("worker_started")

    async def stop(self) -> None:
        """Stop the worker service gracefully."""
        logger.info("stopping_worker")
        self.running = False
        if self.current_job:
            logger.warning("job_interrupted", current_job=self.current_job)
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
        await close_cumulative_data_client()
        logger.info("worker_stopped")

    async def consume_jobs(self) -> None:
        """Main job consumption loop."""
        job_queue = "researchflow:jobs:pending"
        processing_queue = "researchflow:jobs:processing"
        logger.info("listening_for_jobs", queue=job_queue)
        while self.running and self.redis_client:
            try:
                result = await self.redis_client.brpoplpush(
                    job_queue, processing_queue, timeout=5
                )
                if result is None:
                    continue
                job_data = json.loads(result)
                job = JobRequest(**job_data)
                self.current_job = job.job_id
                logger.info("processing_job", job_id=job.job_id, type=job.type)
                job_result = await self.process_job(job)
                await self.send_callback(job, job_result)
                await self.redis_client.lrem(processing_queue, 1, result)
                self.current_job = None
            except json.JSONDecodeError as e:
                logger.error("invalid_job_data", error=str(e))
            except Exception as e:
                logger.error("job_processing_error", error=str(e))
                await asyncio.sleep(1)

    async def process_job(self, job: JobRequest) -> JobResult:
        """Process a job based on type."""
        start_time = datetime.utcnow()

        # Validate job type
        if job.type not in ["workflow", "literature_indexing", "literature_summarization"]:
            return JobResult(
                job_id=job.job_id,
                status="failed",
                completed_at=datetime.utcnow().isoformat(),
                duration=0,
                stages_completed=[],
                error={
                    "code": "INVALID_JOB_TYPE",
                    "message": f"Unknown job type: {job.type}",
                    "retryable": False,
                },
            )

        try:
            # Process based on job type
            if job.type == "workflow":
                result = await self._process_workflow_job(job)
            elif job.type == "literature_indexing":
                result = await self._process_literature_indexing_job(job)
            elif job.type == "literature_summarization":
                result = await self._process_literature_summarization_job(job)
            else:
                raise ValueError(f"Unhandled job type: {job.type}")

            # Build result
            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds() * 1000)
            return JobResult(
                job_id=job.job_id,
                status="completed",
                completed_at=end_time.isoformat(),
                duration=duration,
                stages_completed=result.get("stages_completed", []),
                result=result,
                artifacts=result.get("artifacts"),
                manifest=result.get("manifest"),
            )

        except Exception as e:
            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds() * 1000)
            logger.exception("job_failed", job_id=job.job_id, error=str(e))
            return JobResult(
                job_id=job.job_id,
                status="failed",
                completed_at=end_time.isoformat(),
                duration=duration,
                stages_completed=[],
                error={
                    "code": "PROCESSING_ERROR",
                    "message": str(e),
                    "retryable": True,
                },
            )

    async def _process_workflow_job(self, job: JobRequest) -> Dict[str, Any]:
        """Process workflow execution job."""
        stage_ids = job.stages or list(range(1, 21))
        # Apply enablement from config
        enabled = get_config().enabled_stages
        if enabled:
            stage_ids = [s for s in stage_ids if s in enabled]

        # Stage context
        context = StageContext(
            job_id=job.job_id,
            config=job.config,
            dataset_pointer=job.dataset_pointer,
            artifact_path=self.artifact_path,
            log_path=self.log_path,
            governance_mode=self.governance_mode,
            metadata=job.metadata,
        )

        # Execute
        result = await execute_workflow(
            job_id=job.job_id,
            config=job.config,
            artifact_path=self.artifact_path,
            log_path=self.log_path,
            stage_ids=stage_ids,
            stop_on_failure=job.config.get("stop_on_failure", True),
            governance_mode=self.governance_mode,
            dataset_pointer=job.dataset_pointer,
            metadata=job.metadata,
        )

        # Store and return
        _store_execution(job.job_id, result)
        return result

    async def _process_literature_indexing_job(self, job: JobRequest) -> Dict[str, Any]:
        cfg = LiteratureIndexingConfig(**job.config)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: index_literature(cfg))

    async def _process_literature_summarization_job(self, job: JobRequest) -> Dict[str, Any]:
        cfg = SummarizationConfig(**job.config)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: summarize_literature(cfg))

    async def send_callback(self, job: JobRequest, result: JobResult) -> None:
        """Send job result callback to orchestrator."""
        if not job.callback_url:
            return

        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=30.0)

        try:
            response = await self.http_client.post(job.callback_url, json=asdict(result))
            response.raise_for_status()
            logger.info("callback_sent", job_id=job.job_id, url=job.callback_url)
        except Exception as e:
            logger.error("callback_failed", job_id=job.job_id, url=job.callback_url, error=str(e))


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ResearchFlow Worker",
    description="Workflow execution and job consumer for the ResearchFlow worker.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Additional API routers
app.include_router(manuscript_router)
app.include_router(legend_router)
app.include_router(ai_router)

# Analytics router (if available)
if ANALYTICS_AVAILABLE:
    app.include_router(analytics_router)
    logger.info("Analytics API routes registered")
else:
    logger.warning("Analytics API routes not available - skipping registration")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["Health"], summary="Health check")
async def health(deep: bool = Query(False, description="Include dependency checks (e.g. Redis)")) -> HealthResponse:
    cfg = get_config()
    payload: Dict[str, Any] = {
        "status": "healthy",
        "service": "worker",
        "running": False,
        "current_job": None,
        "governance_mode": cfg.governance_mode,
        "timestamp": datetime.utcnow().isoformat(),
        "redis": None,
    }

    # Deep Redis check
    if deep:
        try:
            r = redis.from_url(cfg.redis_url, decode_responses=True)
            await r.ping()
            await r.close()
            payload["redis"] = "ok"
        except Exception as e:
            payload["redis"] = str(e)
            payload["status"] = "degraded"

    return HealthResponse(**payload)


# ---------------------------------------------------------------------------
# Workflow endpoints
# ---------------------------------------------------------------------------
@app.post(
    "/api/workflow/execute",
    response_model=WorkflowExecuteResponse,
    tags=["Workflow"],
    summary="Execute workflow",
    description=(
        "Run the workflow pipeline for the given job. Supports partial execution via stage_ids (start from stage N)."
    ),
)
async def workflow_execute(body: WorkflowExecuteRequest) -> WorkflowExecuteResponse:
    try:
        result = await _process_workflow_execute_request(body)
        _store_execution(body.job_id, result)
        return WorkflowExecuteResponse(
            job_id=body.job_id,
            stages_completed=result.get("stages_completed", []),
            stages_failed=result.get("stages_failed", []),
            stages_skipped=result.get("stages_skipped", []),
            results=result.get("results", {}),
            success=result.get("success", False),
        )
    except Exception as e:
        logger.exception("workflow_execute_failed", job_id=body.job_id, error=str(e))
        raise HTTPException(status_code=500, detail={"code": "WORKFLOW_ERROR", "message": str(e)})


async def _process_workflow_execute_request(body: WorkflowExecuteRequest) -> Dict[str, Any]:
    cfg = get_config()

    # Apply enablement from env config
    stage_ids = body.stage_ids
    if cfg.enabled_stages:
        stage_ids = [s for s in (stage_ids or list(range(1, 21))) if s in cfg.enabled_stages]

    # Build execution context and call orchestrator
    context = {
        "job_id": body.job_id,
        "config": body.config,
        "stage_ids": stage_ids,
        "stop_on_failure": body.stop_on_failure,
        "governance_mode": body.governance_mode,
        "dataset_pointer": body.dataset_pointer,
        "metadata": body.metadata,
    }

    result = await execute_workflow(
        job_id=body.job_id,
        config=body.config,
        artifact_path=cfg.artifact_path,
        log_path=cfg.log_path,
        stage_ids=stage_ids,
        stop_on_failure=body.stop_on_failure,
        governance_mode=body.governance_mode,
        dataset_pointer=body.dataset_pointer,
        metadata=body.metadata,
    )

    return result


@app.get(
    "/api/workflow/stages/{stage_id}/status",
    response_model=StageStatusResponse,
    tags=["Workflow"],
    summary="Stage status",
    description=(
        "Return status for a stage. With execution_id, return that run's stage result; otherwise return registry info."
    ),
)
async def stage_status(stage_id: int, execution_id: Optional[str] = Query(None, alias="execution_id")) -> StageStatusResponse:
    if execution_id:
        stored = _get_execution(execution_id)
        if stored:
            results = stored.get("results", {})
            stage_result = results.get(stage_id) or results.get(str(stage_id))
            if stage_result is not None:
                return StageStatusResponse(
                    stage_id=stage_id,
                    execution_id=execution_id,
                    status=stage_result.get("status"),
                    stage_name=stage_result.get("stage_name"),
                    duration_ms=stage_result.get("duration_ms"),
                    errors=stage_result.get("errors", []),
                    registered=True,
                )

    cls = get_stage(stage_id)
    if cls is None:
        return StageStatusResponse(stage_id=stage_id, stage_name=None, registered=False)
    return StageStatusResponse(stage_id=stage_id, stage_name=cls.stage_name, registered=True)


@app.post(
    "/api/workflow/stages/{stage}/execute",
    response_model=StageExecuteResponse,
    tags=["Workflow"],
    summary="Execute individual workflow stage",
    description=(
        "Execute a specific workflow stage asynchronously. Called by BullMQ workers from orchestrator."
    ),
)
async def stage_execute(stage: int, body: StageExecuteRequest) -> StageExecuteResponse:
    """Execute an individual workflow stage."""
    start_time = datetime.utcnow()
    
    try:
        # Get stage class
        stage_cls = get_stage(stage)
        if stage_cls is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "STAGE_NOT_FOUND", "message": f"Stage {stage} is not registered"}
            )
        
        # Build stage context
        cfg = get_config()
        context = StageContext(
            job_id=body.job_id,
            config={
                "workflow_id": body.workflow_id,
                "research_question": body.research_question,
                "user_id": body.user_id,
            },
            dataset_pointer=None,  # Will be set by stage if needed
            artifact_path=cfg.artifact_path,
            log_path=cfg.log_path,
            governance_mode=cfg.governance_mode,
            previous_results={},  # TODO: Load from cumulative data if needed
            metadata={
                "workflow_id": body.workflow_id,
                "research_question": body.research_question,
                "user_id": body.user_id,
                "stage": stage,
            },
        )
        
        # Execute stage
        logger.info(
            "executing_stage",
            stage=stage,
            stage_name=stage_cls.stage_name,
            job_id=body.job_id,
            workflow_id=body.workflow_id
        )
        
        stage_instance = stage_cls()
        result = await stage_instance.execute(context)
        
        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        if result.success:
            logger.info(
                "stage_execution_completed",
                stage=stage,
                job_id=body.job_id,
                duration_ms=duration_ms,
                artifacts_count=len(result.artifacts)
            )
            
            return StageExecuteResponse(
                success=True,
                stage=stage,
                workflow_id=body.workflow_id,
                job_id=body.job_id,
                artifacts=result.artifacts,
                results={
                    "summary": result.summary,
                    "metadata": result.metadata,
                    "status": "completed",
                },
                duration_ms=duration_ms,
                stage_name=stage_cls.stage_name,
            )
        else:
            logger.error(
                "stage_execution_failed",
                stage=stage,
                job_id=body.job_id,
                errors=result.errors,
                duration_ms=duration_ms
            )
            
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "STAGE_EXECUTION_FAILED",
                    "message": f"Stage {stage} execution failed",
                    "errors": result.errors,
                }
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        logger.exception(
            "stage_execution_error",
            stage=stage,
            job_id=body.job_id,
            error=str(e),
            duration_ms=duration_ms
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": f"Internal error during stage {stage} execution: {str(e)}",
            }
        )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
@app.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Prometheus metrics",
    response_class=PlainTextResponse,
)
async def metrics() -> Response:
    return Response(content=get_metrics_output(), media_type=get_metrics_content_type())


# ---------------------------------------------------------------------------
# Legacy signal handling (for CLI consumer only)
# ---------------------------------------------------------------------------
async def _shutdown_signal_handler(sig: int, frame: Any) -> None:
    logger.info("shutdown_signal", signal=sig)


if __name__ == "__main__":
    import uvicorn

    # SIGTERM/SIGINT handling
    signal.signal(signal.SIGTERM, _shutdown_signal_handler)
    signal.signal(signal.SIGINT, _shutdown_signal_handler)

    uvicorn.run(
        "src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "").lower() in ("1", "true", "yes"),
    )
