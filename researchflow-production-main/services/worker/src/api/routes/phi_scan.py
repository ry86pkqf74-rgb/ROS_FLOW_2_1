"""PHI scanning API routes.

Implements endpoints for PHI detection, batch/stream scanning, redaction,
pattern listing, audit log retrieval, and de-identification validation.

NOTE: This module is designed to be offline-safe. It relies on local regex
patterns plus optional spaCy NER if available in the deployment.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.phi.redaction.audit_logger import AuditEvent, AuditLogger
from src.phi.redaction.deidentifier import DeidentificationReport, Deidentifier, KAnonymityConfig
from src.phi.redaction.redactor import RedactionConfig, RedactionResult, Redactor
from src.phi.scanner.batch_scanner import BatchProgress, BatchScanConfig, BatchScanResult, BatchScanner
from src.phi.scanner.stream_scanner import StreamScanConfig, StreamScanResult, StreamScanner


router = APIRouter(prefix="/api/phi", tags=["phi"])


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class PHIScanRequest(BaseModel):
    content: str = Field(..., description="Text content to scan")
    sensitivity: str = Field(default="high", description="low|medium|high|paranoid")
    allowlist: Optional[List[str]] = Field(default=None, description="Regex allowlist patterns to suppress")
    project_id: Optional[str] = Field(default=None)
    user_id: Optional[str] = Field(default=None)
    user_context: Optional[Dict[str, Any]] = Field(default=None)


class PHIBatchItem(BaseModel):
    item_id: str = Field(..., description="Client-provided id")
    content: str = Field(..., description="Text content to scan")


class PHIBatchRequest(BaseModel):
    items: List[PHIBatchItem] = Field(..., description="Items to scan")
    sensitivity: str = Field(default="high", description="low|medium|high|paranoid")
    concurrency: int = Field(default=8, ge=1, le=64)
    include_redacted_preview: bool = Field(default=False)
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None


class PHIBatchResponse(BaseModel):
    result: BatchScanResult


class PHIRedactRequest(BaseModel):
    content: str
    sensitivity: str = Field(default="high")
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None


class PHIRedactResponse(BaseModel):
    result: RedactionResult


class PHIValidateRequest(BaseModel):
    content: str
    # Optional: provide expected k-anonymity thresholds for quasi-identifiers
    k: int = Field(default=5, ge=2)
    quasi_identifiers: Optional[List[str]] = Field(default=None, description="Field names for quasi-id generalization")
    sensitivity: str = Field(default="high")


class PHIValidateResponse(BaseModel):
    report: DeidentificationReport


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/scan", summary="Scan a single content string")
async def scan_single(body: PHIScanRequest) -> Dict[str, Any]:
    scanner = BatchScanner()
    # Use batch scanner for single item to keep logic consistent
    cfg = BatchScanConfig(
        sensitivity=body.sensitivity,
        allowlist=body.allowlist or [],
        concurrency=1,
        include_redacted_preview=False,
    )

    audit = AuditLogger()
    await audit.log_event(
        AuditEvent(
            project_id=body.project_id or "unknown",
            user_id=body.user_id or "unknown",
            action="scan_single",
            resource_id="inline",
            metadata={"sensitivity": body.sensitivity},
            user_context=body.user_context or {},
        )
    )

    res = await scanner.scan_items([{ "item_id": "inline", "content": body.content }], cfg)
    return {"result": res.results[0] if res.results else None}


@router.post("/scan/batch", response_model=PHIBatchResponse, summary="Batch scan multiple contents")
async def scan_batch(body: PHIBatchRequest) -> PHIBatchResponse:
    if not body.items:
        raise HTTPException(status_code=400, detail="items must not be empty")
    if len(body.items) > 1000:
        raise HTTPException(status_code=400, detail="maximum 1000 items per batch")

    audit = AuditLogger()
    await audit.log_event(
        AuditEvent(
            project_id=body.project_id or "unknown",
            user_id=body.user_id or "unknown",
            action="scan_batch",
            resource_id=f"batch:{len(body.items)}",
            metadata={"sensitivity": body.sensitivity, "count": len(body.items)},
            user_context=body.user_context or {},
        )
    )

    scanner = BatchScanner()
    cfg = BatchScanConfig(
        sensitivity=body.sensitivity,
        allowlist=[],
        concurrency=body.concurrency,
        include_redacted_preview=body.include_redacted_preview,
    )
    result = await scanner.scan_items([i.model_dump() for i in body.items], cfg)
    return PHIBatchResponse(result=result)


@router.post("/scan/stream", response_model=StreamScanResult, summary="Scan a large payload using streaming chunks")
async def scan_stream(body: PHIScanRequest) -> StreamScanResult:
    # For now, accept content in request body; StreamScanner will chunk internally.
    audit = AuditLogger()
    await audit.log_event(
        AuditEvent(
            project_id=body.project_id or "unknown",
            user_id=body.user_id or "unknown",
            action="scan_stream",
            resource_id="inline",
            metadata={"sensitivity": body.sensitivity, "bytes": len(body.content.encode('utf-8', errors='ignore'))},
            user_context=body.user_context or {},
        )
    )

    scanner = StreamScanner()
    cfg = StreamScanConfig(sensitivity=body.sensitivity, allowlist=body.allowlist or [])
    return await scanner.scan_text(body.content, cfg)


@router.get("/patterns", summary="List available PHI detection patterns")
async def list_patterns() -> Dict[str, Any]:
    scanner = BatchScanner()
    return {"patterns": scanner.list_patterns()}


@router.post("/redact", response_model=PHIRedactResponse, summary="Redact PHI with consistent tokens")
async def redact_phi(body: PHIRedactRequest) -> PHIRedactResponse:
    audit = AuditLogger()
    await audit.log_event(
        AuditEvent(
            project_id=body.project_id or "unknown",
            user_id=body.user_id or "unknown",
            action="redact",
            resource_id="inline",
            metadata={"sensitivity": body.sensitivity},
            user_context=body.user_context or {},
        )
    )

    redactor = Redactor()
    cfg = RedactionConfig(sensitivity=body.sensitivity)
    result = await redactor.redact(body.content, cfg)
    return PHIRedactResponse(result=result)


@router.get("/audit/{project_id}", summary="Get PHI access audit log")
async def get_audit(project_id: str, limit: int = 200) -> Dict[str, Any]:
    audit = AuditLogger()
    limit = max(1, min(limit, 2000))
    events = await audit.get_events(project_id=project_id, limit=limit)
    return {"project_id": project_id, "events": [e.model_dump() for e in events]}


@router.post("/validate", response_model=PHIValidateResponse, summary="Validate de-identification completeness")
async def validate_deidentification(body: PHIValidateRequest) -> PHIValidateResponse:
    deid = Deidentifier()
    cfg = KAnonymityConfig(k=body.k, quasi_identifiers=body.quasi_identifiers or [])
    report = await deid.validate(text=body.content, config=cfg, sensitivity=body.sensitivity)
    return PHIValidateResponse(report=report)
