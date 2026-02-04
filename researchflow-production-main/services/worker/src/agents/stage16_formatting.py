"""
Stage 16 — Formatting

Normalize headings, lists, tables; ensure consistent document structure.
Spec: docs/stages/STAGE_WORKER_SPECS.md (PUBLISH Phase).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from .stage_base import (
    call_llm_async,
    make_error,
    make_result,
    parse_json_from_llm,
    VALIDATION_ERROR,
    INCONSISTENT_OUTPUT,
    FORMAT_REPAIR,
)

logger = logging.getLogger(__name__)

STAGE = 16


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    final_draft = inputs.get("finalDraft") or inputs.get("final_draft")
    if not final_draft or not isinstance(final_draft, dict):
        errors.append("finalDraft object is required")
    else:
        content = final_draft.get("contentMarkdown") or final_draft.get("content_markdown")
        if content is None or (isinstance(content, str) and not content.strip()):
            errors.append("finalDraft.contentMarkdown is required")
    return errors


def _format_markdown_deterministic(md: str, profile: str) -> tuple[str, List[str]]:
    """
    Apply deterministic formatting: normalize headings, trim blank lines, consistent list markers.
    Returns (formatted_markdown, formatting_notes).
    """
    notes: List[str] = []
    lines = md.split("\n")
    out: List[str] = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        # Normalize list markers: * or - -> -
        if re.match(r"^\s*[\*\-]\s+", stripped):
            stripped = re.sub(r"^\s*\*\s+", "  - ", stripped, count=1)
            if not stripped.startswith("  - "):
                stripped = re.sub(r"^\s*-\s+", "  - ", stripped, count=1)
        # Collapse multiple blank lines to one
        if not stripped:
            if prev_blank:
                continue
            prev_blank = True
            out.append("")
            continue
        prev_blank = False
        # Normalize heading levels: ensure single space after #
        if stripped.startswith("#"):
            m = re.match(r"^(#{1,6})\s*(.*)$", stripped)
            if m:
                level, rest = m.groups()
                rest = rest.strip()
                stripped = f"{level} {rest}"
        out.append(stripped)
    result = "\n".join(out).strip()
    # Remove leading/trailing blank lines
    if result != md:
        notes.append("Normalized headings and list markers; collapsed blank lines.")
    return result, notes


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 16: Formatting.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: finalDraft, formatProfile?.

    Returns:
        Canonical result with formatted: { contentMarkdown }, formattingNotes.
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

    final_draft = inputs.get("finalDraft") or inputs.get("final_draft") or {}
    content_md = (
        final_draft.get("contentMarkdown") or final_draft.get("content_markdown") or ""
    )
    format_profile = (
        inputs.get("formatProfile") or inputs.get("format_profile") or "docx"
    )
    if format_profile not in ("docx", "web", "pdf"):
        format_profile = "docx"

    # Prefer deterministic formatting
    formatted_md, formatting_notes = _format_markdown_deterministic(
        content_md, format_profile
    )

    # Optional LLM structure cleanup for malformed headings/structure
    if not formatted_md or len(formatted_md) < 50:
        return make_result(
            ok=True,
            workflow_id=workflow_id,
            stage=STAGE,
            run_id=run_id,
            outputs={
                "formatted": {"contentMarkdown": formatted_md},
                "formattingNotes": formatting_notes,
            },
        )

    # Validate result looks like valid markdown (has some structure or text)
    repaired = False
    if not any(
        c in formatted_md
        for c in ("#", "\n", "-", "*", "1.", " ", "\t")
    ) and len(formatted_md) > 200:
        # Might be a single long line; try LLM repair
        try:
            system_prompt = """You are a document formatter. Output valid JSON only (no markdown).
Return: { "formatted": { "contentMarkdown": string }, "formattingNotes": string[] }.
Ensure contentMarkdown is valid markdown with headings (# or ##), paragraphs, and lists as appropriate."""
            prompt = f"""Fix markdown structure for this content. Preserve all text. Output valid JSON with "formatted" and "formattingNotes".

Content:
---
{formatted_md[:8000]}
---

Return JSON: {{ "formatted": {{ "contentMarkdown": "..." }}, "formattingNotes": ["..."] }}."""
            result = await call_llm_async(
                prompt=prompt,
                system_prompt=system_prompt,
                task_name="stage16_formatting_repair",
                max_tokens=8192,
            )
            text = result.text if hasattr(result, "text") else str(result)
            parsed = parse_json_from_llm(text, "stage16_formatting_repair")
            if parsed:
                fmt = parsed.get("formatted") or {}
                formatted_md = fmt.get("contentMarkdown") or fmt.get("content_markdown") or formatted_md
                extra = parsed.get("formattingNotes") or []
                if isinstance(extra, list):
                    formatting_notes.extend(str(n) for n in extra)
                repaired = True
        except Exception as e:
            logger.warning("Stage 16 LLM structure repair failed: %s", e)

    warnings: List[Dict[str, Any]] = []
    if repaired:
        warnings.append(
            {"code": FORMAT_REPAIR, "message": "Applied LLM structure cleanup to markdown"}
        )

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={
            "formatted": {"contentMarkdown": formatted_md},
            "formattingNotes": formatting_notes,
        },
        warnings=warnings if warnings else None,
    )
