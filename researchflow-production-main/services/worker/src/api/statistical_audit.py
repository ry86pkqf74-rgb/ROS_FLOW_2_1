"""
Statistical audit trail API.

Endpoints:
- GET /api/audit/statistical/{analysis_id}
- GET /api/audit/statistical/{analysis_id}/diagram
- GET /api/audit/statistical/{analysis_id}/summary
- POST /api/audit/statistical/{analysis_id}/export
- GET /api/audit/statistical/{analysis_id}/methodology
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from src.explanation.statistical_rationale import (
    StatisticalRationaleGenerator,
    StatisticalDecision,
)

router = APIRouter(prefix="/api/audit/statistical", tags=["statistical-audit"])

AUDIT_DIR = Path(os.getenv("STATISTICAL_AUDIT_DIR", "data/processed/statistical_audit"))
AUDIT_DIR.mkdir(parents=True, exist_ok=True)


class DecisionPayload(BaseModel):
    decision_type: str
    chosen_option: str
    alternatives_considered: List[str] = Field(default_factory=list)
    rationale: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None
    user_id: Optional[str] = None


class AuditRecord(BaseModel):
    analysis_id: str
    analysis_type: Optional[str] = None
    config_data: Dict[str, Any] = Field(default_factory=dict)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    decisions: List[DecisionPayload] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ExportRequest(BaseModel):
    format: str = Field(default="json")
    include_summary: bool = Field(default=False, alias="includeSummary")
    include_methodology: bool = Field(default=False, alias="includeMethodology")
    metadata: Optional[Dict[str, Any]] = None


def _sanitize_analysis_id(analysis_id: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", analysis_id)
    return cleaned[:200] if cleaned else "analysis"


def _candidate_paths(analysis_id: str) -> List[Path]:
    safe_id = _sanitize_analysis_id(analysis_id)
    return [
        AUDIT_DIR / f"{safe_id}.json",
        AUDIT_DIR / safe_id / "audit.json",
    ]


def _load_record(analysis_id: str) -> Optional[AuditRecord]:
    for path in _candidate_paths(analysis_id):
        if path.exists():
            try:
                payload = json.loads(path.read_text())
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "AUDIT_LOAD_FAILED",
                        "message": f"Failed to parse audit record: {path.name}",
                        "details": str(exc),
                    },
                )
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "AUDIT_INVALID_FORMAT",
                        "message": "Audit record must be a JSON object",
                    },
                )
            payload.setdefault("analysis_id", analysis_id)
            try:
                return AuditRecord.model_validate(payload)
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "AUDIT_SCHEMA_INVALID",
                        "message": "Audit record schema validation failed",
                        "details": str(exc),
                    },
                )
    return None


def _build_generator(record: AuditRecord) -> StatisticalRationaleGenerator:
    generator = StatisticalRationaleGenerator()
    for decision in record.decisions:
        generator.record_decision(
            StatisticalDecision(
                decision_type=decision.decision_type,
                chosen_option=decision.chosen_option,
                alternatives_considered=decision.alternatives_considered,
                rationale=decision.rationale,
                evidence=decision.evidence,
                timestamp=decision.timestamp or "",
                user_id=decision.user_id,
            )
        )
    return generator


def _record_metadata(record: AuditRecord) -> Dict[str, Any]:
    metadata = dict(record.metadata or {})
    metadata.setdefault("analysis_id", record.analysis_id)
    if record.analysis_type:
        metadata.setdefault("analysis_type", record.analysis_type)
    if record.created_at:
        metadata.setdefault("created_at", record.created_at)
    if record.updated_at:
        metadata.setdefault("updated_at", record.updated_at)
    return metadata


@router.get("/{analysis_id}")
async def get_audit_trail(analysis_id: str) -> dict:
    """Return full statistical decision trail."""
    record = _load_record(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AUDIT_NOT_FOUND",
                "message": "No statistical audit record found",
                "analysis_id": analysis_id,
            },
        )

    generator = _build_generator(record)
    export_payload = json.loads(generator.export_audit_trail(format="json"))
    export_payload["analysis_id"] = record.analysis_id
    export_payload["analysis_type"] = record.analysis_type
    export_payload["model_config"] = record.model_config
    export_payload["test_results"] = record.test_results
    export_payload["metadata"] = {**export_payload.get("metadata", {}), **_record_metadata(record)}

    return export_payload


@router.get("/{analysis_id}/diagram", response_class=PlainTextResponse)
async def get_decision_diagram(analysis_id: str) -> str:
    """Return Mermaid decision tree diagram."""
    record = _load_record(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AUDIT_NOT_FOUND",
                "message": "No statistical audit record found",
                "analysis_id": analysis_id,
            },
        )

    generator = _build_generator(record)
    return generator.generate_decision_tree_diagram()


@router.get("/{analysis_id}/summary")
async def get_summary(
    analysis_id: str,
    detail: str = Query("brief", description="brief, detailed, or technical"),
) -> dict:
    """Return natural language summary of decisions."""
    record = _load_record(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AUDIT_NOT_FOUND",
                "message": "No statistical audit record found",
                "analysis_id": analysis_id,
            },
        )

    if detail not in {"brief", "detailed", "technical"}:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_DETAIL_LEVEL",
                "message": "detail must be brief, detailed, or technical",
            },
        )

    generator = _build_generator(record)
    summary = generator.generate_natural_language_summary(detail_level=detail)

    return {
        "analysis_id": record.analysis_id,
        "detail_level": detail,
        "decision_count": len(record.decisions),
        "summary": summary,
    }


@router.post("/{analysis_id}/export")
async def export_audit_trail(analysis_id: str, body: ExportRequest) -> JSONResponse:
    """Export audit trail in the requested format."""
    record = _load_record(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AUDIT_NOT_FOUND",
                "message": "No statistical audit record found",
                "analysis_id": analysis_id,
            },
        )

    generator = _build_generator(record)
    export_format = body.format.lower()

    if export_format == "markdown":
        export_format = "md"
    if export_format == "text":
        export_format = "txt"

    payload_text = generator.export_audit_trail(format=export_format)

    if export_format == "json":
        data = json.loads(payload_text)
        data["analysis_id"] = record.analysis_id
        data["analysis_type"] = record.analysis_type
        data["model_config"] = record.model_config
        data["test_results"] = record.test_results
        data["metadata"] = {**data.get("metadata", {}), **_record_metadata(record)}

        if body.metadata:
            data["metadata"].update(body.metadata)

        if body.include_summary:
            data["summary"] = generator.generate_natural_language_summary(detail_level="brief")

        if body.include_methodology:
            methodology = generator.generate_methodology_section(
                analysis_type=record.analysis_type or "analysis",
                model_config=record.model_config,
                test_results=record.test_results,
            )
            data["methodology"] = {
                "title": methodology.title,
                "content": methodology.content,
                "citations": methodology.citations,
                "assumptions_stated": methodology.assumptions_stated,
                "limitations_noted": methodology.limitations_noted,
            }

        return JSONResponse(content=data)

    if export_format in {"jsonl", "csv", "md", "txt"}:
        media_type = {
            "jsonl": "application/x-ndjson",
            "csv": "text/csv",
            "md": "text/markdown",
            "txt": "text/plain",
        }[export_format]
        return PlainTextResponse(content=payload_text, media_type=media_type)

    raise HTTPException(
        status_code=400,
        detail={
            "error": "UNSUPPORTED_FORMAT",
            "message": f"Unsupported export format: {body.format}",
        },
    )


@router.get("/{analysis_id}/methodology")
async def get_methodology(
    analysis_id: str,
    analysisType: Optional[str] = Query(None, description="Optional override for analysis type"),
) -> dict:
    """Return a methodology section for the analysis."""
    record = _load_record(analysis_id)
    if not record:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "AUDIT_NOT_FOUND",
                "message": "No statistical audit record found",
                "analysis_id": analysis_id,
            },
        )

    analysis_type = analysisType or record.analysis_type or "analysis"
    generator = _build_generator(record)
    methodology = generator.generate_methodology_section(
        analysis_type=analysis_type,
        model_config=record.model_config,
        test_results=record.test_results,
    )

    return {
        "analysis_id": record.analysis_id,
        "analysis_type": analysis_type,
        "title": methodology.title,
        "content": methodology.content,
        "citations": methodology.citations,
        "assumptions_stated": methodology.assumptions_stated,
        "limitations_noted": methodology.limitations_noted,
    }
