"""
Stage 18 — Quality Review

Run a quality gate before export/publish.
Spec: docs/stages/STAGE_WORKER_SPECS.md (PUBLISH Phase).
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
)

logger = logging.getLogger(__name__)

STAGE = 18


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    formatted = inputs.get("formatted")
    if not formatted or not isinstance(formatted, dict):
        errors.append("formatted object is required")
    else:
        content = formatted.get("contentMarkdown") or formatted.get("content_markdown")
        if content is None or (isinstance(content, str) and not content.strip()):
            errors.append("formatted.contentMarkdown is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 18: Quality Review.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: formatted, factChecks?, bibliography?.

    Returns:
        Canonical result with qualityReport: { score, pass, issues }.
        If pass=false, still return ok=true (block downstream publish in UI unless overridden).
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

    formatted = inputs.get("formatted") or {}
    content_md = (
        formatted.get("contentMarkdown") or formatted.get("content_markdown") or ""
    )
    fact_checks = inputs.get("factChecks") or inputs.get("fact_checks") or []
    bibliography = inputs.get("bibliography") or []

    system_prompt = """You are a document quality reviewer. Output valid JSON only (no markdown).
Check completeness, accuracy, and formatting. Be strict and enumerative.
Return: { "qualityReport": { "score": number (0-100), "pass": boolean, "issues": [ { "severity": "low"|"medium"|"high", "issue": string, "fix": string }, ... ] } }."""

    prompt = f"""Review this document for quality. Check completeness, accuracy, and formatting.
Document (markdown, excerpt):
---
{content_md[:8000]}
---
"""
    if fact_checks:
        prompt += f"\nFact-check summary: {len(fact_checks)} fact checks provided.\n"
    if bibliography:
        prompt += f"\nBibliography: {len(bibliography)} entries.\n"
    prompt += """
Produce:
1. score: 0-100
2. pass: true if document is ready for export, false if critical issues remain
3. issues: list of { severity, issue, fix }

Return JSON: { "qualityReport": { "score", "pass", "issues" } }."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage18_quality_review",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage18_quality_review")
    except Exception as e:
        logger.exception("Stage 18 LLM failed: %s", e)
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

    qr = parsed.get("qualityReport") or parsed.get("quality_report") or {}
    if not isinstance(qr, dict):
        qr = {}

    score = qr.get("score")
    if score is None:
        score = qr.get("score", 0)
    if not isinstance(score, (int, float)):
        try:
            score = int(score) if score is not None else 0
        except (TypeError, ValueError):
            score = 0
    score = max(0, min(100, int(score)))

    pass_flag = qr.get("pass")
    if pass_flag is None:
        pass_flag = qr.get("pass", score >= 70)
    if not isinstance(pass_flag, bool):
        pass_flag = bool(score >= 70)

    issues_raw = qr.get("issues") or []
    if not isinstance(issues_raw, list):
        issues_raw = []
    issues: List[Dict[str, Any]] = []
    for i in issues_raw:
        if not isinstance(i, dict):
            continue
        severity = (i.get("severity") or "medium").lower()
        if severity not in ("low", "medium", "high"):
            severity = "medium"
        issues.append(
            {
                "severity": severity,
                "issue": str(i.get("issue") or ""),
                "fix": str(i.get("fix") or ""),
            }
        )

    quality_report = {
        "score": score,
        "pass": pass_flag,
        "issues": issues,
    }

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"qualityReport": quality_report},
    )
