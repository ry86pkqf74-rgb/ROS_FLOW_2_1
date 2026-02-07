"""
agent-intro-writer: write Introduction section from outline, verifiedClaims, extractionRows, groundingPack.
Uses AI Bridge; every claim must have evidence references (chunk_id/doc_id).
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Dict

import structlog

from shared.section_writer import (
    build_section_prompt,
    enforce_claims_evidence,
    get_grounding_chunk_and_doc_ids,
    invoke_ai_bridge,
    parse_section_response,
)

logger = structlog.get_logger()

TASK_TYPE = "SECTION_WRITE_INTRO"
SECTION_NAME = "Introduction"


def _normalize_inputs(inputs: Dict[str, Any]) -> Dict[str, Any]:
    outline = inputs.get("outline") or []
    if isinstance(outline, str):
        outline = [outline]
    verified_claims = inputs.get("verifiedClaims") or inputs.get("verified_claims") or []
    extraction_rows = inputs.get("extractionRows") or inputs.get("extraction_rows") or []
    grounding_pack = inputs.get("groundingPack") or inputs.get("grounding_pack") or {}
    style_params = inputs.get("styleParams") or inputs.get("style_params") or {}
    return {
        "outline": outline,
        "verified_claims": verified_claims,
        "extraction_rows": extraction_rows,
        "grounding_pack": grounding_pack,
        "style_params": style_params,
    }


async def _execute_section_write(inputs: Dict[str, Any], mode: str, request_id: str) -> Dict[str, Any]:
    norm = _normalize_inputs(inputs)
    outline = norm["outline"]
    verified_claims = norm["verified_claims"]
    extraction_rows = norm["extraction_rows"]
    grounding_pack = norm["grounding_pack"]
    style_params = norm["style_params"]
    governance_mode = (inputs.get("governanceMode") or inputs.get("governance_mode") or mode or "DEMO").strip()

    system_prompt, user_prompt = build_section_prompt(
        section_name=SECTION_NAME,
        outline=outline,
        verified_claims=verified_claims,
        extraction_rows=extraction_rows,
        grounding_pack=grounding_pack,
        style_params=style_params,
    )
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    options = {
        "taskType": TASK_TYPE,
        "modelTier": "STANDARD",
        "governanceMode": governance_mode,
        "requirePhiCompliance": False,
        "maxTokens": 4096,
    }
    metadata = {
        "agentId": "agent-intro-writer",
        "projectId": "researchflow",
        "runId": request_id,
        "threadId": "thread-intro-writer",
        "stageRange": [1, 20],
        "currentStage": 12,
    }

    try:
        raw = await invoke_ai_bridge(full_prompt, options, metadata, timeout=120.0)
    except Exception as e:
        logger.warning("intro_writer_bridge_failed", error=str(type(e).__name__))
        return {
            "section_markdown": "",
            "sectionMarkdown": "",
            "claims_with_evidence": [],
            "claimsWithEvidence": [],
            "warnings": [f"AI Bridge invoke failed: {e!s}"],
            "overallPass": False,
        }

    parsed = parse_section_response(raw)
    section_markdown = parsed.get("section_markdown") or ""
    claims_with_evidence = parsed.get("claims_with_evidence") or []

    chunk_ids, doc_ids = get_grounding_chunk_and_doc_ids(grounding_pack)
    claims_with_evidence, warnings, overall_pass = enforce_claims_evidence(
        claims_with_evidence,
        governance_mode,
        valid_chunk_ids=chunk_ids or None,
        valid_doc_ids=doc_ids or None,
    )

    return {
        "section_markdown": section_markdown,
        "sectionMarkdown": section_markdown,
        "claims_with_evidence": claims_with_evidence,
        "claimsWithEvidence": claims_with_evidence,
        "warnings": warnings,
        "overallPass": overall_pass,
    }


async def run_sync(payload: Dict[str, Any]) -> Dict[str, Any]:
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", TASK_TYPE)
    inputs = payload.get("inputs", {})
    mode = payload.get("mode", "DEMO")

    logger.info("agent_sync_start", request_id=request_id, task_type=task_type)
    outputs = await _execute_section_write(inputs, mode, request_id)
    logger.info("agent_sync_complete", request_id=request_id, task_type=task_type)

    return {
        "status": "ok",
        "request_id": request_id,
        "outputs": outputs,
        "artifacts": [],
        "provenance": {"section": SECTION_NAME, "governance_mode": mode},
    }


async def run_stream(payload: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    request_id = payload.get("request_id", "unknown")
    task_type = payload.get("task_type", TASK_TYPE)
    inputs = payload.get("inputs", {})
    mode = payload.get("mode", "DEMO")

    yield {"type": "started", "request_id": request_id, "task_type": task_type}
    yield {"type": "progress", "request_id": request_id, "progress": 50, "step": "writing_section"}

    outputs = await _execute_section_write(inputs, mode, request_id)

    yield {
        "type": "final",
        "request_id": request_id,
        "task_type": task_type,
        "status": "ok",
        "success": True,
        "outputs": outputs,
        "duration_ms": 0,
    }
