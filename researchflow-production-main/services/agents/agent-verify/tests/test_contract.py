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
    assert data.get("service") == "agent-verify"


def test_ready() -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ready"
    assert data.get("service") == "agent-verify"


def test_sync_contract_claim_verify() -> None:
    """Sync response must have status, request_id, outputs with claim_verdicts and overallPass."""
    payload = {
        "request_id": "test-req-verify-1",
        "task_type": "CLAIM_VERIFY",
        "mode": "DEMO",
        "inputs": {
            "claims": ["The study was randomized."],
            "groundingPack": {
                "sources": [
                    {"id": "chunk-1", "text": "This was a randomized controlled trial."},
                ],
            },
            "governanceMode": "DEMO",
            "strictness": "normal",
        },
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:500]}"
    data = r.json()
    assert data.get("status") == "ok", f"expected status=ok, got {data.get('status')}"
    assert data.get("request_id") == "test-req-verify-1"
    assert "outputs" in data
    assert isinstance(data["outputs"], dict)
    assert "claim_verdicts" in data["outputs"]
    assert "overallPass" in data["outputs"]
    verdicts = data["outputs"]["claim_verdicts"]
    assert isinstance(verdicts, list)
    assert len(verdicts) == 1
    assert verdicts[0].get("verdict") in ("pass", "fail", "unclear")
    assert "claim" in verdicts[0]


def test_sync_contract_minimal_payload() -> None:
    """Minimal valid payload: request_id, task_type, inputs with empty claims."""
    payload = {
        "request_id": "contract-check-verify-1",
        "task_type": "CLAIM_VERIFY",
        "inputs": {"claims": []},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert data.get("request_id") == "contract-check-verify-1"
    assert "outputs" in data and isinstance(data["outputs"], dict)
    assert data["outputs"].get("overallPass") is True
    assert data["outputs"].get("claim_verdicts") == []


def test_live_fail_closed_no_evidence() -> None:
    """In LIVE mode, claim with no evidence must not be pass (fail-closed)."""
    payload = {
        "request_id": "test-fail-closed-1",
        "task_type": "CLAIM_VERIFY",
        "mode": "LIVE",
        "inputs": {
            "claims": ["Some claim with no grounding."],
            "groundingPack": {"sources": []},
            "governanceMode": "LIVE",
        },
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    verdicts = data["outputs"].get("claim_verdicts") or []
    assert len(verdicts) == 1
    # No evidence -> must be fail or unclear, not pass
    assert verdicts[0]["verdict"] in ("fail", "unclear")


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
        "request_id": "stream-contract-verify-req",
        "task_type": "CLAIM_VERIFY",
        "inputs": {"claims": ["One claim."]},
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
    assert terminal.get("request_id") == "stream-contract-verify-req", "terminal event missing request_id"
    assert terminal.get("task_type") == "CLAIM_VERIFY", "terminal event missing task_type"
    assert terminal.get("status") in ("ok", "success"), "terminal event missing status"
