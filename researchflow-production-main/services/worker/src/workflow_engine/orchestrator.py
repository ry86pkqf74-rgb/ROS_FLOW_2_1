"""
Workflow Orchestrator

Single entry point to run the 20-stage pipeline (or a subset).
Uses runner.run_stages and the stage registry; no duplication of execution logic.
Phase 3: structured logging, metrics, and error recovery.
"""

import time
from typing import Any, Dict, List, Optional

from .types import StageContext
from .runner import run_stages
from .stages import STAGE_REGISTRY

from src.utils.logging import get_logger
from src.utils.error_handler import push_dlq

logger = get_logger("workflow_engine.orchestrator")


def get_default_stage_ids() -> List[int]:
    """Return the list of registered stage IDs (1-20) in order.

    Returns:
        Sorted list of stage IDs that are currently registered.
    """
    return sorted(STAGE_REGISTRY.keys())


async def run_pipeline(
    job_id: str,
    config: Dict[str, Any],
    artifact_path: str,
    stage_ids: Optional[List[int]] = None,
    stop_on_failure: bool = True,
    governance_mode: str = "DEMO",
    **context_kwargs: Any,
) -> Dict[str, Any]:
    """Run the workflow pipeline for the given job.

    Builds a StageContext and executes the requested stages (or all registered
    stages) via runner.run_stages. Returns the same structure as run_stages.

    Args:
        job_id: Unique identifier for the job.
        config: Job configuration dictionary.
        artifact_path: Base path for artifact storage.
        stage_ids: Stage IDs to run (1-20). If None, uses get_default_stage_ids().
        stop_on_failure: If True, stop on first failed stage.
        governance_mode: DEMO, STAGING, or PRODUCTION.
        **context_kwargs: Additional arguments for StageContext (e.g. dataset_pointer,
            previous_results, metadata).

    Returns:
        Dict with stages_completed, stages_failed, stages_skipped, results, success.
    """
    if stage_ids is None:
        stage_ids = get_default_stage_ids()

    context = StageContext(
        job_id=job_id,
        config=config,
        artifact_path=artifact_path,
        governance_mode=governance_mode,
        **context_kwargs,
    )

    logger.info(
        "pipeline_start",
        job_id=job_id,
        stage_ids=stage_ids,
        stop_on_failure=stop_on_failure,
    )
    start = time.perf_counter()

    result = await run_stages(
        stage_ids=stage_ids,
        context=context,
        stop_on_failure=stop_on_failure,
    )

    elapsed = time.perf_counter() - start
    logger.info(
        "pipeline_end",
        job_id=job_id,
        stages_completed=result.get("stages_completed", []),
        stages_failed=result.get("stages_failed", []),
        success=result.get("success", False),
        duration_seconds=round(elapsed, 3),
    )

    # Push failed stages to DLQ (metrics are recorded per-stage in runner)
    # results dict has int keys (from runner); support both int and str for JSON round-trips
    for sid in result.get("stages_failed", []):
        results_dict = result.get("results", {})
        stage_result = results_dict.get(sid) or results_dict.get(str(sid), {})
        errors = stage_result.get("errors", [])
        error_msg = errors[0] if errors else "Stage execution failed"
        push_dlq(
            job_id=job_id,
            stage_id=int(sid) if isinstance(sid, str) else sid,
            error=error_msg,
            stage_name=stage_result.get("stage_name"),
        )

    return result


async def execute_workflow(
    job_id: str,
    config: Dict[str, Any],
    artifact_path: str,
    stage_ids: Optional[List[int]] = None,
    stop_on_failure: bool = True,
    governance_mode: str = "DEMO",
    **context_kwargs: Any,
) -> Dict[str, Any]:
    """Async entry point for worker API: run the workflow pipeline.

    Delegates to run_pipeline.
    """
    return await run_pipeline(
        job_id=job_id,
        config=config,
        artifact_path=artifact_path,
        stage_ids=stage_ids,
        stop_on_failure=stop_on_failure,
        governance_mode=governance_mode,
        **context_kwargs,
    )
