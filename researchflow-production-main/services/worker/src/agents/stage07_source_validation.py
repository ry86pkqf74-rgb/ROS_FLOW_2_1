"""
Stage 07 — Source Validation

Evaluate credibility/quality of collected sources.
Spec: docs/stages/STAGE_WORKER_SPECS.md (ANALYSIS Phase).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .stage_base import (
    call_llm_async,
    make_error,
    make_result,
    parse_json_from_llm,
    VALIDATION_ERROR,
    INCONSISTENT_OUTPUT,
    LOW_TRUST_SET,
)

logger = logging.getLogger(__name__)

STAGE = 7


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    sources = inputs.get("sources")
    if not sources or not isinstance(sources, list):
        errors.append("sources array is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 07: Source Validation.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with workflowId, stage, runId, inputs (sources, rubric?).

    Returns:
        Canonical result envelope with validatedSources.
    """
    run_id = stage_data.get("runId", "")
    inputs = stage_data.get("inputs") or stage_data
    validation_errors = _validate_inputs(inputs)
    if validation_errors:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error(VALIDATION_ERROR, "; ".join(validation_errors))],
        )

    sources = inputs.get("sources", [])
    rubric = inputs.get("rubric") or {}
    source_ids = {s.get("id") for s in sources if s.get("id")}

    system_prompt = """You are a source credibility evaluator. Output valid JSON only (no markdown).
For each source provide: id, score (0-100), verdict ("accept"|"caution"|"reject"), rationale, flags (array of strings, e.g. "no-author", "blog-opinion", "primary-source")."""

    rubric_text = f"Rubric: requireAuthor={rubric.get('requireAuthor')}, preferPrimary={rubric.get('preferPrimary')}, minRecencyDays={rubric.get('minRecencyDays')}"
    sources_text = "\n".join(
        f"- id={s.get('id')}, title={s.get('title')}, url={s.get('url')}, publisher={s.get('publisher')}, publishedAt={s.get('publishedAt')}"
        for s in sources[:50]
    )

    prompt = f"""Validate the credibility of these sources.

{rubric_text}

Sources:
{sources_text}

For each source id, return:
- score (0-100)
- verdict: "accept" | "caution" | "reject"
- rationale (short)
- flags: array of strings (e.g. "no-author", "blog-opinion", "primary-source")

Return JSON: {{ "validatedSources": [ {{ "id", "score", "verdict", "rationale", "flags" }} ] }}
Use only the same source ids as in the input."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage07_source_validation",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage07_source_validation")
    except Exception as e:
        logger.exception("Stage 07 LLM failed: %s", e)
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error("UPSTREAM_5XX", str(e), retryable=True)],
        )

    if not parsed or "validatedSources" not in parsed:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error(INCONSISTENT_OUTPUT, "LLM did not return validatedSources JSON", retryable=True)],
        )

    validated = parsed.get("validatedSources") or []
    validated_ids = {v.get("id") for v in validated if v.get("id")}
    if validated_ids and not validated_ids.issubset(source_ids):
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error(INCONSISTENT_OUTPUT, "validatedSources contain ids not in input sources")],
        )

    warnings: List[Dict[str, Any]] = []
    rejected = sum(1 for v in validated if v.get("verdict") == "reject")
    if validated and rejected > len(validated) / 2:
        warnings.append({"code": LOW_TRUST_SET, "message": f"More than 50% of sources rejected ({rejected}/{len(validated)})"})

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"validatedSources": validated},
        warnings=warnings if warnings else None,
    )
