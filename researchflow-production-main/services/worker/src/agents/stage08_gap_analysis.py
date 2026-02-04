"""
Stage 08 — Gap Analysis

Identify what is missing to answer the research question.
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
)

logger = logging.getLogger(__name__)

STAGE = 8


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    if not inputs.get("topic"):
        errors.append("topic is required")
    vs = inputs.get("validatedSources")
    if vs is not None and not isinstance(vs, list):
        errors.append("validatedSources must be an array if provided")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 08: Gap Analysis.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: topic, researchQuestion?, validatedSources.

    Returns:
        Canonical result with gaps and nextActions.
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

    topic = inputs.get("topic", "")
    research_question = inputs.get("researchQuestion") or inputs.get("research_question", "")
    validated_sources = inputs.get("validatedSources") or []

    system_prompt = """You are a research synthesis expert. Output valid JSON only (no markdown).
Identify research gaps and next actions. Be explicit about unknowns vs assumptions.
gaps: array of { gapId, description, impact ("low"|"medium"|"high"), suggestedQueries (array of strings) }.
nextActions: array of { action ("collect-more"|"clarify-scope"|"proceed"), reason }."""

    sources_summary = "\n".join(
        f"- id={s.get('id')}, verdict={s.get('verdict')}, rationale={s.get('rationale')}"
        for s in validated_sources[:30]
    )

    prompt = f"""Topic: {topic}
Research question: {research_question or "Not specified"}

Validated sources:
{sources_summary or "None"}

Identify:
1. Gaps: what is missing to answer the research question? For each: gapId, description, impact (low|medium|high), suggestedQueries (specific search queries).
2. Next actions: array of {{ action: "collect-more"|"clarify-scope"|"proceed", reason }}.
If no gaps found, return empty gaps array and nextActions including {{ action: "proceed", reason: "..." }}.

Return JSON: {{ "gaps": [ {{ "gapId", "description", "impact", "suggestedQueries" }} ], "nextActions": [ {{ "action", "reason" }} ] }}"""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage08_gap_analysis",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage08_gap_analysis")
    except Exception as e:
        logger.exception("Stage 08 LLM failed: %s", e)
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error("UPSTREAM_5XX", str(e), retryable=True)],
        )

    if not parsed:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[make_error("INCONSISTENT_OUTPUT", "LLM did not return valid JSON", retryable=True)],
        )

    gaps = parsed.get("gaps") or []
    next_actions = parsed.get("nextActions") or parsed.get("next_actions") or []
    if not next_actions:
        next_actions = [{"action": "proceed", "reason": "No gaps requiring action"}]

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"gaps": gaps, "nextActions": next_actions},
    )
