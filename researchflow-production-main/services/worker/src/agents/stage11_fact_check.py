"""
Stage 11 — Fact Check

Produce a fact-check report for key assertions.
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
    HIGH_FACT_RISK,
)

logger = logging.getLogger(__name__)

STAGE = 11


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    claims = inputs.get("draftClaims") or inputs.get("draft_claims")
    if not claims or not isinstance(claims, list):
        errors.append("draftClaims array is required")
    sources = inputs.get("sources")
    if not sources or not isinstance(sources, list):
        errors.append("sources array is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 11: Fact Check.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: draftClaims, sources.

    Returns:
        Canonical result with factChecks and requiredEdits.
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

    draft_claims = inputs.get("draftClaims") or inputs.get("draft_claims", [])
    sources = inputs.get("sources", [])

    system_prompt = """You are a fact-checker. Output valid JSON only (no markdown).
Label uncertainty. Provide evidenceSourceIds for each claim.
factChecks: array of { claim, status ("supported"|"uncertain"|"unsupported"), evidenceSourceIds, notes }.
requiredEdits: array of strings (edits to make for unsupported/uncertain claims)."""

    claims_text = "\n".join(f"- {c}" for c in draft_claims[:50])
    sources_text = "\n".join(
        f"- id={s.get('id')}, url={s.get('url')}, summary={(s.get('summary') or '')[:150]}, keyClaims={s.get('keyClaims', [])}"
        for s in sources[:30]
    )

    prompt = f"""Fact-check these draft claims against the sources.

Draft claims (intended for final doc):
{claims_text}

Sources:
{sources_text}

For each claim, return:
- status: "supported" | "uncertain" | "unsupported"
- evidenceSourceIds: array of source ids that support or contradict
- notes: short explanation

Also produce requiredEdits: array of specific edits to make for unsupported or uncertain claims.

Return JSON: {{ "factChecks": [ {{ "claim", "status", "evidenceSourceIds", "notes" }} ], "requiredEdits": [] }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage11_fact_check",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage11_fact_check")
    except Exception as e:
        logger.exception("Stage 11 LLM failed: %s", e)
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

    fact_checks = parsed.get("factChecks") or parsed.get("fact_checks") or []
    required_edits = parsed.get("requiredEdits") or parsed.get("required_edits") or []
    unsupported = sum(1 for f in fact_checks if f.get("status") == "unsupported")
    total = len(fact_checks) or 1
    warnings: List[Dict[str, Any]] = []
    if total and (unsupported / total) > 0.2:
        warnings.append(
            {"code": HIGH_FACT_RISK, "message": f">20% of claims unsupported ({unsupported}/{total})"}
        )

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"factChecks": fact_checks, "requiredEdits": required_edits},
        warnings=warnings if warnings else None,
    )
