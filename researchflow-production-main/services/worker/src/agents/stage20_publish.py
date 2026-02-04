"""
Stage 20 — Publish

Finalize publish state and generate deliverables.
Spec: docs/stages/STAGE_WORKER_SPECS.md (PUBLISH Phase).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from .stage_base import make_error, make_result, VALIDATION_ERROR

logger = logging.getLogger(__name__)

STAGE = 20


def _validate_inputs(inputs: Dict[str, Any]) -> List[str]:
    errors = []
    export_bundle = inputs.get("exportBundle") or inputs.get("export_bundle")
    if not export_bundle or not isinstance(export_bundle, dict):
        errors.append("exportBundle object is required")
    else:
        content = export_bundle.get("contentMarkdown") or export_bundle.get("content_markdown")
        if content is None and not export_bundle.get("assets"):
            errors.append("exportBundle must have contentMarkdown or assets")
    return errors


async def process(workflow_id: str, stage_data: dict) -> dict:
    """
    Process Stage 20: Publish.

    Args:
        workflow_id: Workflow identifier.
        stage_data: Envelope with inputs: exportBundle, publishTarget?.

    Returns:
        Canonical result with published: { status, publishedAt? }, deliverables.
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

    export_bundle = inputs.get("exportBundle") or inputs.get("export_bundle") or {}
    publish_target = (
        inputs.get("publishTarget") or inputs.get("publish_target") or "download"
    )
    if publish_target not in ("download", "cms", "email"):
        publish_target = "download"

    now_iso = datetime.utcnow().isoformat() + "Z"

    # Deliverables = pass-through of export assets (DOCX, MD) plus delivery confirmation
    assets: List[Dict[str, Any]] = export_bundle.get("assets") or []
    if not isinstance(assets, list):
        assets = []

    # Add delivery confirmation artifact
    deliverables: List[Dict[str, Any]] = [
        {
            "id": "delivery-confirmation",
            "type": "export",
            "name": "delivery_confirmation.json",
            "mimeType": "application/json",
            "stage": STAGE,
            "createdAt": now_iso,
            "status": "published",
            "workflowId": workflow_id,
            "publishedAt": now_iso,
            "publishTarget": publish_target,
        }
    ]
    deliverables.extend(assets)

    published = {
        "status": "published",
        "publishedAt": now_iso,
    }

    return make_result(
        ok=True,
        workflow_id=workflow_id,
        stage=STAGE,
        run_id=run_id,
        outputs={
            "published": published,
            "deliverables": deliverables,
        },
        artifacts=deliverables,
    )
