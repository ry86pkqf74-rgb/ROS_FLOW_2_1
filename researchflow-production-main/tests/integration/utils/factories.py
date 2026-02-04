"""Factories for integration test payloads.

These are intentionally minimal and schema-tolerant so they work across
deployments where the orchestrator may validate additional fields.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict


def uuid_str(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4()}"


def workflow_create_payload(*, name: str | None = None, description: str | None = None) -> Dict[str, Any]:
    # Keep payload permissive: most APIs accept at least name.
    return {
        "name": name or f"it-{uuid_str('wf-')}",
        "description": description or "integration test workflow",
    }


def workflow_update_payload(*, name: str | None = None) -> Dict[str, Any]:
    return {
        "name": name or f"it-{uuid_str('wf-updated-')}",
    }


def stage_inputs_payload(*, inputs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "inputs": inputs or {"example": "value"},
    }
