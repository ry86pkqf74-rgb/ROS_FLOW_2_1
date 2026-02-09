"""
Waiting-for-human node utilities.

Handles idempotent pause/resume semantics and audit ingest for edit sessions.
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
import socket
from typing import Any, Dict, Optional, Set

from ...clients.orchestrator_client import OrchestratorClient

logger = logging.getLogger(__name__)

WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
_DEFAULT_ALLOWED_RESUME_STATUSES: Set[str] = {"approved", "merged"}


def build_edit_session_dedupe_key(run_id: str, trace_id: str, node_id: str, attempt: int) -> str:
    """Stable dedupe key for edit-session creation; includes attempt."""
    return f"{run_id}:{trace_id}:{node_id}:{attempt}"


def _build_event_dedupe_key(run_id: str, node_id: str, action: str, attempt: int) -> str:
    """Stable dedupe key for audit events; includes attempt."""
    return f"{run_id}:{node_id}:{action}:{attempt}"


def _get_actor_id() -> str:
    return os.environ.get("WORKER_ID", "").strip() or socket.gethostname() or "worker"


def _safe_emit_audit(event: Dict[str, Any]) -> None:
    try:
        from ...clients.orchestrator_audit_client import emit_audit_event
        emit_audit_event(event)
    except ValueError as exc:
        logger.debug("Audit emit skipped (config missing): %s", exc)
    except Exception as exc:
        logger.debug("Audit emit failed: %s", exc)


def _emit_edit_session_event(
    *,
    run_id: str,
    trace_id: str,
    node_id: str,
    attempt: int,
    action: str,
    edit_session_id: Optional[str],
) -> None:
    dedupe_key = _build_event_dedupe_key(run_id, node_id, action, attempt)
    payload = {
        "edit_session_id": edit_session_id or "",
        "attempt": attempt,
        "trace_id": trace_id or run_id,
        "node_id": node_id,
    }
    event = {
        "stream_type": "RUN",
        "stream_key": run_id,
        "run_id": run_id,
        "trace_id": trace_id or run_id,
        "node_id": node_id,
        "action": action,
        "actor_type": "WORKER",
        "actor_id": _get_actor_id(),
        "service": "worker",
        "resource_type": "EDIT_SESSION",
        "resource_id": edit_session_id or "",
        "payload_json": payload,
        "dedupe_key": dedupe_key,
    }
    _safe_emit_audit(event)


def enter_waiting_for_human(
    state: Dict[str, Any],
    orchestrator_client: Optional[OrchestratorClient],
    *,
    node_id: str,
) -> Dict[str, Any]:
    """Idempotently create (or reuse) an edit session and emit audit event."""
    run_id = state.get("run_id") or ""
    trace_id = state.get("trace_id") or run_id
    attempt = int(state.get("waiting_for_human_attempt") or 0)
    existing_session_id = state.get("edit_session_id")
    existing_attempt = state.get("edit_session_attempt")

    create_new = not existing_session_id or existing_attempt != attempt
    edit_session_id = existing_session_id
    edit_session_status = state.get("edit_session_status")

    if create_new:
        attempt += 1
        dedupe_key = build_edit_session_dedupe_key(run_id, trace_id, node_id, attempt)
        if orchestrator_client is not None:
            session = orchestrator_client.create_edit_session(
                run_id=run_id,
                trace_id=trace_id,
                node_id=node_id,
                attempt=attempt,
                dedupe_key=dedupe_key,
            )
            edit_session_id = session.get("id") or session.get("edit_session_id")
            edit_session_status = session.get("status")
        else:
            edit_session_id = None
            edit_session_status = None

    _emit_edit_session_event(
        run_id=run_id,
        trace_id=trace_id,
        node_id=node_id,
        attempt=attempt,
        action="EDIT_SESSION_WAITING_FOR_HUMAN",
        edit_session_id=edit_session_id,
    )

    return {
        "waiting_for_human_attempt": attempt,
        "edit_session_id": edit_session_id,
        "edit_session_attempt": attempt,
        "edit_session_status": edit_session_status,
        "edit_session_created_at": datetime.utcnow().isoformat(),
    }


def validate_resume(
    orchestrator_client: Optional[OrchestratorClient],
    *,
    edit_session_id: str,
    node_id: str,
    run_id: str,
    trace_id: str,
    attempt: int,
    allowed_statuses: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Validate edit session state before resuming a paused workflow."""
    if not edit_session_id:
        raise ValueError("edit_session_id is required to resume")
    if orchestrator_client is None:
        raise ValueError("orchestrator client is not configured")

    session = orchestrator_client.get_edit_session(edit_session_id)
    status = (session.get("status") or "").strip().lower()
    allowed = allowed_statuses or _DEFAULT_ALLOWED_RESUME_STATUSES
    if status not in allowed:
        raise ValueError(f"edit session {edit_session_id} not resumable: status={status}")

    _emit_edit_session_event(
        run_id=run_id,
        trace_id=trace_id,
        node_id=node_id,
        attempt=attempt,
        action="EDIT_SESSION_RESUMED",
        edit_session_id=edit_session_id,
    )
    return session
