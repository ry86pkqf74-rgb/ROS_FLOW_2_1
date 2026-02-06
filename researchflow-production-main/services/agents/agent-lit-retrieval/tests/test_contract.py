"""Contract test: POST /agents/run/sync returns AgentResponse shape; stream terminal event has request_id."""
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
    assert r.json() == {"status": "ok"}


def test_ready() -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_sync_contract_lit_retrieval() -> None:
    payload = {
        "request_id": "test-req-1",
        "task_type": "LIT_RETRIEVAL",
        "mode": "DEMO",
        "inputs": {"query": "diabetes", "max_results": 10},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("request_id") == "test-req-1"
    assert data.get("task_type") == "LIT_RETRIEVAL"
    assert "outputs" in data
    assert "papers" in data["outputs"]
    assert "count" in data["outputs"]
    assert isinstance(data["outputs"]["papers"], list)
    assert isinstance(data["warnings"], list)


def test_sync_contract_lit_retrieval_requires_inputs_query() -> None:
    """Contract-check payload must include inputs.query; minimal valid payload."""
    payload = {
        "request_id": "contract-check-1",
        "task_type": "LIT_RETRIEVAL",
        "inputs": {"query": "test query"},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    assert data.get("request_id") == "contract-check-1"
    assert data.get("task_type") == "LIT_RETRIEVAL"
    assert "outputs" in data and "papers" in data["outputs"]


def test_sync_rejects_wrong_task_type() -> None:
    r = client.post(
        "/agents/run/sync",
        json={
            "request_id": "x",
            "task_type": "OTHER",
            "inputs": {"query": "x"},
        },
    )
    assert r.status_code == 400
    # Contract-shaped error body (FastAPI puts it under "detail")
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("request_id") == "x"
        assert detail.get("ok") is False


def test_stream_terminal_event_has_request_id_task_type_status() -> None:
    """Stream contract: last event must be terminal and include request_id, task_type, status.
    Fails if a stream ends with a terminal event missing request_id (e.g. trailing 'complete' without fields).
    """
    payload = {
        "request_id": "stream-contract-req",
        "task_type": "LIT_RETRIEVAL",
        "inputs": {"query": "test query"},
    }
    r = client.post("/agents/run/stream", json=payload)
    assert r.status_code == 200
    events = _parse_sse_stream(r.text)
    assert len(events) >= 1, "stream must emit at least one event"
    terminal = events[-1].get("data")
    assert isinstance(terminal, dict), "terminal event data must be a JSON object"
    assert terminal.get("request_id") == "stream-contract-req", "terminal event missing request_id"
    assert terminal.get("task_type") == "LIT_RETRIEVAL", "terminal event missing task_type"
    assert terminal.get("status") in ("ok", "success"), "terminal event missing status"
    # Terminal type from SSE event line or from data.event (when only data: is sent)
    sse_type = events[-1].get("event") or terminal.get("event")
    assert sse_type in ("complete", "done", "final"), "stream must end with terminal event type"
