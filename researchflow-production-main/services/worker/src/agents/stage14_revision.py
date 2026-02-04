"""
Stage 14 — Revision

Revise for clarity, structure, and correctness; incorporate fact-check edits.
Spec: docs/stages/STAGE_WORKER_SPECS.md (WRITING Phase).
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
    NEW_CLAIMS_DETECTED,
)

logger = logging.getLogger(__name__)

STAGE = 14
# Heuristic: if revised content is >2x input length, flag possible new claims
LENGTH_RATIO_WARN = 2.0


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    draft = inputs.get("draft")
    if not draft or not isinstance(draft, dict):
        errors.append("draft object is required")
    else:
        content = draft.get("contentMarkdown") or draft.get("content_markdown")
        if content is None or (isinstance(content, str) and not content.strip()):
            errors.append("draft.contentMarkdown is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 14: Revision.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: draft, factChecks?, requiredEdits?.

    Returns:
        Canonical result with revisedDraft: { contentMarkdown }, changeLog.
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

    draft = inputs.get("draft", {})
    content_md = draft.get("contentMarkdown") or draft.get("content_markdown") or ""
    fact_checks = inputs.get("factChecks") or inputs.get("fact_checks") or []
    required_edits = inputs.get("requiredEdits") or inputs.get("required_edits") or []

    fact_checks_text = ""
    if fact_checks:
        fact_checks_text = "\nFact-check results to incorporate:\n" + "\n".join(
            f"- Claim: {fc.get('claim', '')}; Status: {fc.get('status', '')}; Notes: {fc.get('notes', '')}"
            for fc in fact_checks[:30]
        )
    required_edits_text = ""
    if required_edits:
        required_edits_text = "\nRequired edits:\n" + "\n".join(f"- {e}" for e in required_edits[:20])

    system_prompt = """You are a revision editor. Output valid JSON only (no markdown).
Revise for clarity, structure, and correctness. Preserve intent. Do not introduce new uncited factual claims.
Return: { "revisedDraft": { "contentMarkdown" }, "changeLog": [ { "type": "remove"|"rewrite"|"add"|"reorder", "summary" } ] }."""

    prompt = f"""Revise this draft for clarity, flow, and correctness. Incorporate the fact-check and required edits below.
{fact_checks_text}
{required_edits_text}

Draft (markdown):
---
{content_md[:12000]}
---

Produce:
1. revisedDraft: {{ contentMarkdown }} — the revised full markdown (preserve structure; fix issues).
2. changeLog: array of {{ type: "remove"|"rewrite"|"add"|"reorder", summary: string }} describing changes.

Return JSON: {{ "revisedDraft", "changeLog" }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage14_revision",
            max_tokens=8192,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage14_revision")
    except Exception as e:
        logger.exception("Stage 14 LLM failed: %s", e)
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

    revised_obj = parsed.get("revisedDraft") or parsed.get("revised_draft") or {}
    revised_md = revised_obj.get("contentMarkdown") or revised_obj.get("content_markdown") or ""
    change_log = parsed.get("changeLog") or parsed.get("change_log") or []
    if not isinstance(change_log, list):
        change_log = []

    revised_draft = {"contentMarkdown": revised_md}

    warnings: List[Dict[str, Any]] = []
    if content_md and revised_md and len(revised_md) > LENGTH_RATIO_WARN * len(content_md):
        warnings.append(
            {
                "code": NEW_CLAIMS_DETECTED,
                "message": "Revised content significantly longer than input; possible new claims added",
            }
        )

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"revisedDraft": revised_draft, "changeLog": change_log},
        warnings=warnings if warnings else None,
    )
