"""Manuscript generation routes.

Implements:
- POST /api/manuscript/generate
- POST /api/manuscript/generate/section
- GET  /api/manuscript/{id}/status
- GET  /api/manuscript/{id}/download/{format}
- POST /api/manuscript/{id}/regenerate

This worker service does not run a dedicated Celery worker in-repo; instead,
we provide async background execution and Redis pub/sub progress updates.

If a Celery queue is available in the deployment, this module can be swapped
to call Celery tasks without changing the API contract.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Literal, Optional

import redis.asyncio as redis
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.generators.imrad_assembler import IMRaDAssembler, IMRaDAssembleInput
from src.generators.exporters.docx_exporter import DocxExporter
from src.generators.exporters.pdf_exporter import PdfExporter
from src.generators.exporters.latex_exporter import LatexExporter
from src.generators.exporters.markdown_exporter import MarkdownExporter


router = APIRouter(prefix="/api/manuscript", tags=["manuscript"])

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
PROGRESS_CHANNEL_PREFIX = os.getenv("MANUSCRIPT_PROGRESS_CHANNEL_PREFIX", "manuscript:progress")

# In-memory stores (bounded by env in real deployment; kept simple here)
_MANUSCRIPTS: Dict[str, Dict[str, Any]] = {}
_ARTIFACTS: Dict[str, Dict[str, bytes]] = {}


Format = Literal["docx", "pdf", "latex", "markdown"]
Section = Literal["title", "abstract", "methods", "results", "discussion"]


class ManuscriptGenerateRequest(BaseModel):
    manuscript_id: Optional[str] = None
    title: str = Field("Untitled Manuscript")
    data: Dict[str, Any] = Field(default_factory=dict)
    journal_style: str = Field("JAMA")
    citation_style: str = Field("Vancouver")
    include_supplementary: bool = True
    enforce_word_limits: bool = True
    word_limits: Optional[Dict[str, int]] = None


class ManuscriptGenerateResponse(BaseModel):
    manuscript_id: str
    status: str
    version: int
    warnings: list[str] = []


class SectionGenerateRequest(BaseModel):
    manuscript_id: Optional[str] = None
    section: Section
    title: str = Field("Untitled Manuscript")
    data: Dict[str, Any] = Field(default_factory=dict)
    journal_style: str = Field("JAMA")
    citation_style: str = Field("Vancouver")


class StatusResponse(BaseModel):
    manuscript_id: str
    status: str
    progress: Dict[str, Any] = Field(default_factory=dict)
    updated_at: str
    version: Optional[int] = None
    warnings: list[str] = []


async def _publish_progress(manuscript_id: str, payload: Dict[str, Any]) -> None:
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        channel = f"{PROGRESS_CHANNEL_PREFIX}:{manuscript_id}"
        await r.publish(channel, json.dumps(payload))
        await r.close()
    except Exception:
        # Progress updates are best-effort.
        return


def _set_status(manuscript_id: str, status: str, progress: Optional[Dict[str, Any]] = None, **extra: Any) -> None:
    existing = _MANUSCRIPTS.get(manuscript_id, {})
    now = datetime.utcnow().isoformat() + "Z"
    existing.update({"status": status, "updated_at": now, "progress": progress or {}, **extra})
    _MANUSCRIPTS[manuscript_id] = existing


async def _run_full_generation(req: ManuscriptGenerateRequest, manuscript_id: str) -> None:
    _set_status(manuscript_id, "running", {"stage": "starting"})
    await _publish_progress(manuscript_id, {"status": "running", "stage": "starting"})

    assembler = IMRaDAssembler()
    assemble_in = IMRaDAssembleInput(
        manuscript_id=manuscript_id,
        previous_version=_MANUSCRIPTS.get(manuscript_id, {}).get("version", 0),
        title=req.title,
        data=req.data,
        journal_style=req.journal_style,  # type: ignore[arg-type]
        citation_style=req.citation_style,  # type: ignore[arg-type]
        include_supplementary=req.include_supplementary,
        enforce_word_limits=req.enforce_word_limits,
        word_limits=req.word_limits,
    )

    await _publish_progress(manuscript_id, {"status": "running", "stage": "assembling"})
    bundle = await assembler.assemble(assemble_in)

    _set_status(
        manuscript_id,
        "completed",
        {"stage": "assembled"},
        version=bundle.version,
        warnings=bundle.warnings,
        bundle=bundle.to_dict(),
    )

    # Pre-generate artifacts for download
    artifacts: Dict[str, bytes] = {}
    artifacts["markdown"] = MarkdownExporter().export(bundle).encode("utf-8")
    artifacts["latex"] = LatexExporter().export(bundle).encode("utf-8")
    artifacts["docx"] = DocxExporter().export_bytes(bundle)
    artifacts["pdf"] = PdfExporter().export_bytes(bundle)
    _ARTIFACTS[manuscript_id] = artifacts

    await _publish_progress(
        manuscript_id,
        {"status": "completed", "stage": "done", "version": bundle.version, "warnings": bundle.warnings},
    )


@router.post("/generate", response_model=ManuscriptGenerateResponse)
async def generate_manuscript(body: ManuscriptGenerateRequest, background_tasks: BackgroundTasks):
    manuscript_id = body.manuscript_id or str(uuid.uuid4())

    # Initialize status record
    _set_status(manuscript_id, "queued", {"stage": "queued"}, version=_MANUSCRIPTS.get(manuscript_id, {}).get("version", 0))
    background_tasks.add_task(_run_full_generation, body, manuscript_id)

    return ManuscriptGenerateResponse(
        manuscript_id=manuscript_id,
        status="queued",
        version=int(_MANUSCRIPTS.get(manuscript_id, {}).get("version", 0)),
        warnings=[],
    )


@router.post("/generate/section")
async def generate_section(body: SectionGenerateRequest):
    assembler = IMRaDAssembler()
    assemble_in = IMRaDAssembleInput(
        manuscript_id=body.manuscript_id or str(uuid.uuid4()),
        previous_version=0,
        title=body.title,
        data=body.data,
        journal_style=body.journal_style,  # type: ignore[arg-type]
        citation_style=body.citation_style,  # type: ignore[arg-type]
        include_supplementary=False,
        enforce_word_limits=False,
    )

    sec = await assembler.generate_section(body.section, assemble_in)  # type: ignore[arg-type]
    return {"section": sec.name, "heading": sec.heading, "text": sec.text, "word_count": sec.word_count}


@router.get("/{manuscript_id}/status", response_model=StatusResponse)
async def get_status(manuscript_id: str):
    if manuscript_id not in _MANUSCRIPTS:
        raise HTTPException(status_code=404, detail="manuscript not found")
    rec = _MANUSCRIPTS[manuscript_id]
    return StatusResponse(
        manuscript_id=manuscript_id,
        status=rec.get("status", "unknown"),
        progress=rec.get("progress") or {},
        updated_at=rec.get("updated_at") or datetime.utcnow().isoformat() + "Z",
        version=rec.get("version"),
        warnings=rec.get("warnings") or [],
    )


@router.get("/{manuscript_id}/download/{format}")
async def download(manuscript_id: str, format: Format):
    if manuscript_id not in _ARTIFACTS:
        raise HTTPException(status_code=404, detail="no artifacts available")

    data = _ARTIFACTS[manuscript_id].get(format)
    if data is None:
        raise HTTPException(status_code=404, detail="format not available")

    media = {
        "markdown": "text/markdown; charset=utf-8",
        "latex": "application/x-latex; charset=utf-8",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
    }[format]

    filename = f"{manuscript_id}.{ 'tex' if format=='latex' else format }"
    return Response(content=data, media_type=media, headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.post("/{manuscript_id}/regenerate", response_model=ManuscriptGenerateResponse)
async def regenerate(manuscript_id: str, body: ManuscriptGenerateRequest, background_tasks: BackgroundTasks):
    # destructive: overwrites previous status/artifacts for the same manuscript_id
    body.manuscript_id = manuscript_id
    _set_status(manuscript_id, "queued", {"stage": "queued"})
    background_tasks.add_task(_run_full_generation, body, manuscript_id)

    return ManuscriptGenerateResponse(
        manuscript_id=manuscript_id,
        status="queued",
        version=int(_MANUSCRIPTS.get(manuscript_id, {}).get("version", 0)),
        warnings=[],
    )
