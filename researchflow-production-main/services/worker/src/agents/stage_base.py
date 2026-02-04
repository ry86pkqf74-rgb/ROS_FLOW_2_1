"""
Shared base for ANALYSIS (Stages 6-11), WRITING (Stages 12-15), and PUBLISH (Stages 16-20) phase workers.

Provides canonical envelope types, error codes, and LLM/JSON helpers
per docs/stages/STAGE_WORKER_SPECS.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from src.llm.router import generate_text

logger = logging.getLogger(__name__)

# Standard error codes from STAGE_WORKER_SPECS
VALIDATION_ERROR = "VALIDATION_ERROR"
UPSTREAM_4XX = "UPSTREAM_4XX"
UPSTREAM_5XX = "UPSTREAM_5XX"
TIMEOUT = "TIMEOUT"
RATE_LIMITED = "RATE_LIMITED"
LLM_REFUSAL = "LLM_REFUSAL"
LOW_CONFIDENCE = "LOW_CONFIDENCE"
INCONSISTENT_OUTPUT = "INCONSISTENT_OUTPUT"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"

# Warning codes
LOW_COVERAGE = "LOW_COVERAGE"
LOW_TRUST_SET = "LOW_TRUST_SET"
LOW_FACT_RISK = "LOW_FACT_RISK"
HIGH_FACT_RISK = "HIGH_FACT_RISK"
# WRITING phase (12-15)
TRIMMED_OUTLINE = "TRIMMED_OUTLINE"
NEW_CLAIMS_DETECTED = "NEW_CLAIMS_DETECTED"
POTENTIAL_MEANING_SHIFT = "POTENTIAL_MEANING_SHIFT"
# PUBLISH phase (16-20)
FORMAT_REPAIR = "FORMAT_REPAIR"
INCOMPLETE_METADATA = "INCOMPLETE_METADATA"
MISSING_ASSETS = "MISSING_ASSETS"


def make_result(
    ok: bool,
    workflow_id: str,
    stage: int,
    run_id: str,
    outputs: Dict[str, Any],
    *,
    status: str = "ok",
    next_stage: Optional[int] = None,
    errors: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[Dict[str, Any]]] = None,
    artifacts: Optional[List[Dict[str, Any]]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build canonical worker result envelope."""
    if next_stage is None and ok:
        next_stage = min(stage + 1, 20)
    out: Dict[str, Any] = {
        "ok": ok,
        "status": "error" if not ok else status,
        "workflowId": workflow_id,
        "stage": stage,
        "runId": run_id,
        "outputs": outputs,
        "output": outputs,
        "next_stage": next_stage,
    }
    if errors:
        out["errors"] = errors
    if warnings:
        out["warnings"] = warnings
    if artifacts:
        out["artifacts"] = artifacts
    if metrics:
        out["metrics"] = metrics
    return out


def make_error(
    code: str,
    message: str,
    retryable: bool = False,
) -> Dict[str, Any]:
    return {"code": code, "message": message, "retryable": retryable}


async def call_llm_async(
    prompt: str,
    system_prompt: str,
    task_name: str,
    model: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> Any:
    """Run sync generate_text in thread pool for use from async process()."""
    return await asyncio.to_thread(
        generate_text,
        task_name=task_name,
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def parse_json_from_llm(text: str, task_name: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM text (strip markdown code blocks if present)."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("%s: JSON parse failed: %s", task_name, e)
        return None
