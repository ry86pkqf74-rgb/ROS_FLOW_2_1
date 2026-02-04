"""
Stage 10 — Cross-Reference

Cross-check claims across sources and detect contradictions.
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

STAGE = 10


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    themes = inputs.get("themes")
    if not themes or not isinstance(themes, list):
        errors.append("themes array is required")
    sources = inputs.get("sources")
    if not sources or not isinstance(sources, list):
        errors.append("sources array is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 10: Cross-Reference.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: themes, sources.

    Returns:
        Canonical result with crossRefs and riskRegister.
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

    themes = inputs.get("themes", [])
    sources = inputs.get("sources", [])

    system_prompt = """You are a fact-checking analyst. Output valid JSON only (no markdown).
Explicitly mark corroboration vs contradiction. Do not overstate certainty.
crossRefs: array of { claim, corroborates (source ids), contradicts (source ids), notes }.
riskRegister: array of { risk, severity ("low"|"medium"|"high"), mitigation }."""

    themes_text = "\n".join(
        f"- theme={t.get('theme')}, supportingSourceIds={t.get('supportingSourceIds', t.get('supporting_source_ids', []))}"
        for t in themes[:30]
    )
    sources_text = "\n".join(
        f"- id={s.get('id')}, summary={(s.get('summary') or '')[:150]}, keyClaims={s.get('keyClaims', [])}"
        for s in sources[:30]
    )

    prompt = f"""Cross-reference claims across these themes and sources.

Themes:
{themes_text}

Sources:
{sources_text}

Produce:
1. crossRefs: array of {{ claim, corroborates (array of source ids), contradicts (array of source ids), notes }}.
2. riskRegister: array of {{ risk, severity ("low"|"medium"|"high"), mitigation }} for any contradictions or uncertainties.

Return JSON: {{ "crossRefs", "riskRegister" }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage10_cross_reference",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage10_cross_reference")
    except Exception as e:
        logger.exception("Stage 10 LLM failed: %s", e)
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

    cross_refs = parsed.get("crossRefs") or parsed.get("cross_refs") or []
    risk_register = parsed.get("riskRegister") or parsed.get("risk_register") or []
    warnings: List[Dict[str, Any]] = []
    if risk_register:
        warnings.append({"code": "CONTRADICTIONS_DETECTED", "message": f"{len(risk_register)} risks in risk register"})

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"crossRefs": cross_refs, "riskRegister": risk_register},
        warnings=warnings if warnings else None,
    )
