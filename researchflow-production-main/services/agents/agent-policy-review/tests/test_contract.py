"""Contract test: POST /agents/run/sync returns AgentRunResponse shape; stream terminal event has request_id."""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _parse_sse_stream(raw: str) -> list[dict[str, Any]]:
    """Parse SSE body into list of { event, data } (data parsed as JSON when possible)."""
    events: list[dict[str, Any]] = []
    current_event: str | None = None
    current_data: list[str] = []
    for line in raw.splitlines():
        line = line.rstrip("\r\n")
        if line.startswith("event:"):
            current_event = line[6:].strip()
            continue
        if line.startswith("data:"):
            current_data.append(line[5:].lstrip() if len(line) > 5 else "")
            continue
        if line == "" and (current_event is not None or current_data):
            data_joined = "\n".join(current_data) if current_data else "{}"
            try:
                data_obj = json.loads(data_joined) if data_joined.strip() else {}
            except json.JSONDecodeError:
                data_obj = {}
            events.append({"event": current_event or "message", "data": data_obj})
            current_event = None
            current_data = []
    return events


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("service") == "agent-policy-review"


def test_ready() -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ready"
    assert data.get("service") == "agent-policy-review"


def test_sync_contract_policy_review() -> None:
    """Sync response must have status, request_id, outputs (contract shape)."""
    payload = {
        "request_id": "test-req-policy-1",
        "task_type": "POLICY_REVIEW",
        "mode": "DEMO",
        "inputs": {"resource_id": "res-1", "domain": "clinical"},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:500]}"
    data = r.json()
    assert data.get("status") == "ok", f"expected status=ok, got {data.get('status')}"
    assert data.get("request_id") == "test-req-policy-1", f"expected request_id, got {data.get('request_id')}"
    assert "outputs" in data, f"expected outputs, keys: {list(data.keys())}"
    assert isinstance(data["outputs"], dict)
    assert "allowed" in data["outputs"]
    assert "reasons" in data["outputs"]


def test_sync_contract_minimal_payload() -> None:
    """Minimal valid payload: request_id, task_type, inputs (empty ok for policy)."""
    payload = {
        "request_id": "contract-check-policy-1",
        "task_type": "POLICY_REVIEW",
        "inputs": {},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("request_id") == "contract-check-policy-1"
    assert "outputs" in data and isinstance(data["outputs"], dict)


TERMINAL_EVENT_TYPES = ("complete", "done", "final")


def _is_terminal_event(ev: dict[str, Any]) -> bool:
    sse_type = ev.get("event")
    data = ev.get("data") or {}
    data_type = data.get("type") if isinstance(data, dict) else data.get("event")
    return (sse_type in TERMINAL_EVENT_TYPES) or (
        data_type in TERMINAL_EVENT_TYPES if data_type else False
    )


def test_stream_terminal_event_has_request_id_task_type_status() -> None:
    """Stream contract: exactly one terminal event at end; must include request_id, task_type, status."""
    payload = {
        "request_id": "stream-contract-policy-req",
        "task_type": "POLICY_REVIEW",
        "inputs": {"text": "sample"},
    }
    r = client.post("/agents/run/stream", json=payload)
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:500]}"
    events = _parse_sse_stream(r.text)
    assert len(events) >= 1, "stream must emit at least one event"

    terminal_count = sum(1 for e in events if _is_terminal_event(e))
    assert terminal_count == 1, (
        f"expected exactly one terminal event, got {terminal_count}. "
        f"Events: {[e.get('event') for e in events]}"
    )

    last = events[-1]
    assert _is_terminal_event(last), "stream must end with a terminal event (complete, done, or final)"

    terminal = last.get("data")
    assert isinstance(terminal, dict), "terminal event data must be a JSON object"
    assert terminal.get("request_id") == "stream-contract-policy-req", "terminal event missing request_id"
    assert terminal.get("task_type") == "POLICY_REVIEW", "terminal event missing task_type"
    assert terminal.get("status") in ("ok", "success"), "terminal event missing status"
