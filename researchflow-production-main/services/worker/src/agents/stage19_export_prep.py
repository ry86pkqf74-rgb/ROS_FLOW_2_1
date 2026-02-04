"""
Stage 19 — Export Prep

Convert markdown + citations into export-ready intermediate representation.
Spec: docs/stages/STAGE_WORKER_SPECS.md (PUBLISH Phase).
"""

from __future__ import annotations

import base64
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List

from .stage_base import (
    make_error,
    make_result,
    VALIDATION_ERROR,
    MISSING_ASSETS,
)

logger = logging.getLogger(__name__)

STAGE = 19

DOCX_MIMETYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MD_MIMETYPE = "text/markdown"


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    formatted = inputs.get("formatted")
    if not formatted or not isinstance(formatted, dict):
        errors.append("formatted object is required")
    else:
        content = formatted.get("contentMarkdown") or formatted.get("content_markdown")
        if content is None or (isinstance(content, str) and not content.strip()):
            errors.append("formatted.contentMarkdown is required")
    bibliography = inputs.get("bibliography")
    if not isinstance(bibliography, list):
        errors.append("bibliography array is required")
    return errors


def _markdown_to_docx_content(markdown: str, title: str) -> Dict[str, Any]:
    """
    Parse markdown into docx_generator shape: { title, sections: [ { heading, paragraphs?, bullets? } ] }.
    Uses first # line as title if not provided; ##/### as section headings; blocks as paragraphs; -/* as bullets.
    """
    title = (title or "").strip() or "Untitled"
    sections: List[Dict[str, Any]] = []
    lines = markdown.split("\n")
    current_heading: str | None = None
    current_paragraphs: List[str] = []
    current_bullets: List[str] = []

    def flush_section():
        nonlocal current_heading, current_paragraphs, current_bullets
        if current_heading is not None or current_paragraphs or current_bullets:
            sec: Dict[str, Any] = {"heading": current_heading or "Section"}
            if current_paragraphs:
                sec["paragraphs"] = [p for p in current_paragraphs if p.strip()]
            if current_bullets:
                sec["bullets"] = [b for b in current_bullets if b.strip()]
            if sec.get("paragraphs") or sec.get("bullets") or current_heading:
                sections.append(sec)
        current_heading = None
        current_paragraphs = []
        current_bullets = []

    # First # line (single #) -> document title
    seen_first_heading = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if re.match(r"^#\s+", stripped) and not seen_first_heading:
            seen_first_heading = True
            title = re.sub(r"^#\s+", "", stripped).strip() or title
            i += 1
            continue
        if re.match(r"^#{2,3}\s+", stripped):
            flush_section()
            current_heading = re.sub(r"^#{2,3}\s+", "", stripped).strip() or "Section"
            i += 1
            continue
        if re.match(r"^\s*[\*\-]\s+", stripped):
            bullet = re.sub(r"^\s*[\*\-]\s+", "", stripped).strip()
            current_bullets.append(bullet)
            i += 1
            continue
        if stripped:
            current_paragraphs.append(stripped)
        i += 1

    flush_section()

    if not sections and (markdown.strip() or title != "Untitled"):
        # Single section with all content as paragraphs
        paras = []
        for line in markdown.split("\n"):
            line = line.strip()
            if line and not re.match(r"^#+\s", line) and not re.match(r"^\s*[\*\-]\s+", line):
                paras.append(line)
        sections = [{"heading": "Content", "paragraphs": paras}] if paras else [{"heading": "Content", "paragraphs": [markdown[:5000].strip() or "(no content)"]}]

    return {"title": title, "sections": sections}


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 19: Export Prep.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: formatted, bibliography, exportOptions?.

    Returns:
        Canonical result with exportBundle: contentMarkdown, bibliographyMarkdown, assets (DOCX, MD).
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
    bibliography = inputs.get("bibliography") or []
    export_options = inputs.get("exportOptions") or inputs.get("export_options") or {}

    bibliography_md = "## References\n\n"
    for b in bibliography:
        if isinstance(b, dict):
            ct = b.get("citationText") or b.get("citation_text") or ""
            bibliography_md += f"- {ct}\n"
    bibliography_md = bibliography_md.strip()

    assets: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # DOCX: convert markdown -> structured content -> generate_docx
    try:
        from src.generators.docx_generator import generate_docx
    except ImportError as e:
        logger.warning("DOCX generator not available: %s", e)
        warnings.append(
            {"code": MISSING_ASSETS, "message": "DOCX export unavailable (python-docx not installed)"}
        )
    else:
        try:
            docx_content = _markdown_to_docx_content(content_md, "")
            docx_bytes = generate_docx(docx_content)
            docx_b64 = base64.b64encode(docx_bytes).decode("ascii")
            artifact_id = str(uuid.uuid4())
            assets.append(
                {
                    "id": artifact_id,
                    "type": "docx",
                    "name": "document.docx",
                    "mimeType": DOCX_MIMETYPE,
                    "stage": STAGE,
                    "createdAt": now_iso,
                    "contentBase64": docx_b64,
                }
            )
        except Exception as e:
            logger.exception("Stage 19 DOCX generation failed: %s", e)
            warnings.append(
                {"code": MISSING_ASSETS, "message": f"DOCX generation failed: {e}"}
            )

    # MD artifact: full markdown + bibliography
    full_md = content_md.strip() + "\n\n" + bibliography_md
    md_artifact_id = str(uuid.uuid4())
    assets.append(
        {
            "id": md_artifact_id,
            "type": "export",
            "name": "document.md",
            "mimeType": MD_MIMETYPE,
            "stage": STAGE,
            "createdAt": now_iso,
            "contentMarkdown": full_md[:500_000],
        }
    )

    export_bundle: Dict[str, Any] = {
        "contentMarkdown": content_md,
        "bibliographyMarkdown": bibliography_md,
        "assets": assets,
    }

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={"exportBundle": export_bundle},
        artifacts=assets,
        warnings=warnings if warnings else None,
    )
