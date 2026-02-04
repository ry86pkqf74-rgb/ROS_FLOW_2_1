"""
Stage 13 — Draft Writing

Generate a first full draft from the outline.
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
    LOW_CONFIDENCE,
)

logger = logging.getLogger(__name__)

STAGE = 13
MIN_DRAFT_LENGTH = 200


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    outline = inputs.get("outline")
    if not outline or not isinstance(outline, dict):
        errors.append("outline object is required")
    else:
        if not outline.get("title"):
            errors.append("outline.title is required")
        secs = outline.get("sections")
        if not secs or not isinstance(secs, list):
            errors.append("outline.sections array is required")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 13: Draft Writing.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: outline, sources?, citationStyle?.

    Returns:
        Canonical result with draft: { title, contentMarkdown }, inlineCitations.
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

    outline = inputs.get("outline", {})
    title = outline.get("title", "")
    sections = outline.get("sections", [])
    sources = inputs.get("sources") or []
    citation_style = inputs.get("citationStyle") or inputs.get("citation_style") or "apa"

    outline_text = "\n".join(
        f"## {s.get('heading', '')}\n" + "\n".join(f"- {b}" for b in (s.get("bullets") or []))
        for s in sections
    )
    sources_text = ""
    if sources:
        sources_text = "\nSources (for citations):\n" + "\n".join(
            f"- id={s.get('id')}, summary={(s.get('summary') or '')[:150]}, keyClaims={s.get('keyClaims', [])}"
            for s in sources[:30]
        )

    system_prompt = """You are a research writer. Output valid JSON only (no markdown).
Expand the outline into full paragraphs. Produce coherent prose.
Keep citations consistent with markers (e.g. [1], [2]).
Return: { "draft": { "title", "contentMarkdown" }, "inlineCitations": [ { "marker", "sourceIds" } ] }."""

    prompt = f"""Write a first full draft from this outline.

Title: {title}

Outline:
{outline_text}
{sources_text}

Citation style: {citation_style}
Use inline markers like [1], [2] and list sourceIds in inlineCitations for each marker.

Produce:
1. draft: {{ title, contentMarkdown }} — full markdown content with headings and paragraphs.
2. inlineCitations: array of {{ marker (e.g. "[1]"), sourceIds (array of source ids) }}.

Return JSON: {{ "draft", "inlineCitations" }}."""

    try:
        result = await call_llm_async(
            prompt=prompt,
            system_prompt=system_prompt,
            task_name="stage13_draft_writing",
            max_tokens=8192,
        )
        text = result.text if hasattr(result, "text") else str(result)
        parsed = parse_json_from_llm(text, "stage13_draft_writing")
    except Exception as e:
        logger.exception("Stage 13 LLM failed: %s", e)
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

    draft_obj = parsed.get("draft") or parsed.get("draft_content") or {}
    content_md = draft_obj.get("contentMarkdown") or draft_obj.get("content_markdown") or ""
    draft_title = draft_obj.get("title") or title
    inline_citations = parsed.get("inlineCitations") or parsed.get("inline_citations") or []

    if not content_md or len(content_md.strip()) < MIN_DRAFT_LENGTH:
        return make_result(
            ok=False,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={},
            errors=[
                make_error(
                    LOW_CONFIDENCE,
                    f"contentMarkdown empty or too short (min {MIN_DRAFT_LENGTH} chars)",
                )
            ],
        )

    draft = {"title": draft_title, "contentMarkdown": content_md}
    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"draft": draft, "inlineCitations": inline_citations},
    )
