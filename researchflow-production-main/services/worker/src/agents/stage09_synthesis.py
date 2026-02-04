"""
Stage 09 — Synthesis

Build a coherent synthesis: themes, consensus, disagreement, and takeaways.
Spec: docs/stages/STAGE_WORKER_SPECS.md (ANALYSIS Phase).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

from .stage_base import (
    call_llm_async,
    make_error,
    make_result,
    parse_json_from_llm,
    VALIDATION_ERROR,
    INCONSISTENT_OUTPUT,
)

logger = logging.getLogger(__name__)

STAGE = 9


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    vs = inputs.get("validatedSources")
    if not vs or not isinstance(vs, list):
        errors.append("validatedSources array is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 09: Synthesis.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: validatedSources, focus?.

    Returns:
        Canonical result with themes, consensus, disagreements, insights.
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

    validated_sources = inputs.get("validatedSources", [])
    focus = inputs.get("focus") or []
    source_ids: Set[str] = {str(s.get("id")) for s in validated_sources if s.get("id")}

    system_prompt = """You are a research synthesis expert. Output valid JSON only (no markdown).
Cite source IDs for each theme/claim. Do not invent facts not in the sources.
themes: array of { theme, description, supportingSourceIds }.
consensus: array of strings.
disagreements: array of { point, sides: [ { claim, sourceIds } ] }.
insights: array of strings."""

    sources_text = "\n".join(
        f"- id={s.get('id')}, verdict={s.get('verdict')}, summary={(s.get('summary') or '')[:200]}, keyClaims={s.get('keyClaims', [])}"
        for s in validated_sources[:40]
    )
    focus_text = f" Focus angles: {focus}." if focus else ""

    prompt = f"""Synthesize these validated sources into themes, consensus, disagreements, and insights.
{focus_text}

Sources:
{sources_text}

Produce:
1. themes: array of {{ theme, description, supportingSourceIds }} (use only source ids from the list).
2. consensus: array of points where sources agree.
3. disagreements: array of {{ point, sides: [ {{ claim, sourceIds }} ] }}.
4. insights: array of takeaway strings.

Return JSON: {{ "themes", "consensus", "disagreements", "insights" }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage09_synthesis",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage09_synthesis")
    except Exception as e:
        logger.exception("Stage 09 LLM failed: %s", e)
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
            errors=[make_error(INCONSISTENT_OUTPUT, "LLM did not return valid JSON", retryable=True)],
        )

    themes = parsed.get("themes") or []
    for t in themes:
        refs = t.get("supportingSourceIds") or t.get("supporting_source_ids") or []
        unknown = [r for r in refs if str(r) not in source_ids]
        if unknown:
            return make_result(
                ok=False,
                workflow_id=workflow_id,
                stage=STAGE,
                run_id=run_id,
                outputs={},
                errors=[make_error(INCONSISTENT_OUTPUT, f"Theme references unknown source ids: {unknown}")],
            )

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={
            "themes": themes,
            "consensus": parsed.get("consensus") or [],
            "disagreements": parsed.get("disagreements") or [],
            "insights": parsed.get("insights") or [],
        },
    )
