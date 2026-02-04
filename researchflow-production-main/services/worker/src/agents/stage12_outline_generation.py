"""
Stage 12 — Outline Generation

Create a structured outline aligned to the synthesis.
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
    TRIMMED_OUTLINE,
)

logger = logging.getLogger(__name__)

STAGE = 12


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    if not inputs.get("topic"):
        errors.append("topic is required")
    themes = inputs.get("themes")
    if not themes or not isinstance(themes, list):
        errors.append("themes array is required")
    return errors


def _normalize_section(s: Dict[str, Any]) -> Dict[str, Any]:
    heading = s.get("heading") or s.get("title") or ""
    bullets = s.get("bullets") or s.get("bullet_points") or []
    if not isinstance(bullets, list):
        bullets = [str(bullets)] if bullets else []
    rationale = s.get("rationale")
    out: Dict[str, Any] = {"heading": heading, "bullets": bullets}
    if rationale is not None:
        out["rationale"] = str(rationale)
    return out


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 12: Outline Generation.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: topic, audience?, tone?, themes, constraints?.

    Returns:
        Canonical result with outline: { title, sections }.
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
    audience = inputs.get("audience") or ""
    tone = inputs.get("tone") or "neutral"
    themes = inputs.get("themes", [])
    constraints = inputs.get("constraints") or {}
    max_sections = constraints.get("maxSections") or constraints.get("max_sections")
    required_sections = constraints.get("requiredSections") or constraints.get("required_sections") or []

    themes_text = "\n".join(
        f"- {t.get('theme', '')}: {t.get('description', '')}"
        for t in themes[:50]
    )

    system_prompt = """You are a research writing expert. Output valid JSON only (no markdown).
Create a logical document outline. Ensure logical ordering. Include bullets that map to the given themes.
Return: { "title": string, "sections": [ { "heading": string, "bullets": string[], "rationale"?: string } ] }."""

    prompt = f"""Create a structured document outline for this research.

Topic: {topic}
Audience: {audience or "general"}
Tone: {tone}
Required sections (if any): {required_sections}

Themes to cover (each section should map to these):
{themes_text}

Produce:
1. title: document title
2. sections: array of {{ heading, bullets (array of strings), rationale (optional) }}, in logical order.

Return JSON: {{ "title", "sections" }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage12_outline_generation",
            max_tokens=4096,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage12_outline_generation")
    except Exception as e:
        logger.exception("Stage 12 LLM failed: %s", e)
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

    title = parsed.get("title") or parsed.get("name") or topic
    raw_sections = parsed.get("sections") or parsed.get("sections_list") or []
    sections = [_normalize_section(s) for s in raw_sections if isinstance(s, dict)]

    warnings: List[Dict[str, Any]] = []
    if max_sections is not None and len(sections) > max_sections:
        sections = sections[: max_sections]
        warnings.append(
            {"code": TRIMMED_OUTLINE, "message": f"Outline trimmed to maxSections={max_sections}"}
        )

    outline = {"title": title, "sections": sections}
    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"outline": outline},
        warnings=warnings if warnings else None,
    )
