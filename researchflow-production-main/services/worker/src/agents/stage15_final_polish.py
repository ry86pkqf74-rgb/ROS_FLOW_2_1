"""
Stage 15 — Final Polish

Final pass for grammar, tone, and consistency.
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
    POTENTIAL_MEANING_SHIFT,
)

logger = logging.getLogger(__name__)

STAGE = 15
# Heuristic: if polished content length differs by >30%, flag possible meaning shift
LENGTH_DIFF_THRESHOLD = 0.3


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    revised = inputs.get("revisedDraft") or inputs.get("revised_draft")
    if not revised or not isinstance(revised, dict):
        errors.append("revisedDraft object is required")
    else:
        content = revised.get("contentMarkdown") or revised.get("content_markdown")
        if content is None or (isinstance(content, str) and not content.strip()):
            errors.append("revisedDraft.contentMarkdown is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 15: Final Polish.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: revisedDraft, tone?, styleGuide?.

    Returns:
        Canonical result with finalDraft: { contentMarkdown }, qualitySignals.
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

    revised = inputs.get("revisedDraft") or inputs.get("revised_draft") or {}
    content_md = revised.get("contentMarkdown") or revised.get("content_markdown") or ""
    tone = inputs.get("tone") or "neutral"
    style_guide = inputs.get("styleGuide") or inputs.get("style_guide") or {}
    use_oxford = style_guide.get("useOxfordComma", style_guide.get("use_oxford_comma", True))
    spelling = style_guide.get("spelling") or "US"

    style_text = f"Oxford comma: {use_oxford}. Spelling: {spelling}."

    system_prompt = """You are an editing expert. Output valid JSON only (no markdown).
Do a final pass for grammar, tone, and consistency. Edit only — preserve meaning. Do not rewrite content substantively.
Return: { "finalDraft": { "contentMarkdown" }, "qualitySignals": { "readability"?: string, "issuesFound": number } }."""

    prompt = f"""Final polish this draft. Fix grammar, style, and formatting only. Preserve meaning exactly.
Tone: {tone}
Style: {style_text}

Draft (markdown):
---
{content_md[:12000]}
---

Produce:
1. finalDraft: {{ contentMarkdown }} — polished markdown (grammar, punctuation, consistency only).
2. qualitySignals: {{ readability (optional short note), issuesFound (number of issues fixed) }}.

Return JSON: {{ "finalDraft", "qualitySignals" }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage15_final_polish",
            max_tokens=8192,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage15_final_polish")
    except Exception as e:
        logger.exception("Stage 15 LLM failed: %s", e)
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

    final_obj = parsed.get("finalDraft") or parsed.get("final_draft") or {}
    final_md = final_obj.get("contentMarkdown") or final_obj.get("content_markdown") or ""
    quality = parsed.get("qualitySignals") or parsed.get("quality_signals") or {}
    if not isinstance(quality, dict):
        quality = {}
    readability = quality.get("readability")
    issues_found = quality.get("issuesFound", quality.get("issues_found", 0))
    if not isinstance(issues_found, (int, float)):
        issues_found = 0
    quality_signals: Dict[str, Any] = {"issuesFound": int(issues_found)}
    if readability is not None:
        quality_signals["readability"] = str(readability)

    final_draft = {"contentMarkdown": final_md}

    warnings: List[Dict[str, Any]] = []
    if content_md and final_md:
        orig_len = len(content_md)
        new_len = len(final_md)
        if orig_len > 0:
            diff_ratio = abs(new_len - orig_len) / orig_len
            if diff_ratio > LENGTH_DIFF_THRESHOLD:
                warnings.append(
                    {
                        "code": POTENTIAL_MEANING_SHIFT,
                        "message": f"Polished content length changed by {diff_ratio:.0%}; possible meaning shift",
                    }
                )

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"finalDraft": final_draft, "qualitySignals": quality_signals},
        warnings=warnings if warnings else None,
    )
