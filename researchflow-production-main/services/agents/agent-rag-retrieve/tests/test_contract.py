"""Contract tests: /health, /health/ready, POST /agents/run/sync envelope, stream terminal event."""
from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TASK_TYPE = "RAG_RETRIEVE"


def _parse_sse_stream(raw: str) -> list[dict[str, Any]]:
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
    assert data.get("service") == "agent-rag-retrieve"


def test_ready() -> None:
    r = client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("ready", "degraded")
    assert data.get("service") == "agent-rag-retrieve"


def test_sync_contract_rag_retrieve() -> None:
    """Sync response has request_id, outputs, status (ok or error)."""
    payload = {
        "request_id": "test-req-rag-1",
        "task_type": TASK_TYPE,
        "inputs": {"query": "test query", "knowledgeBase": "default", "topK": 5},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200, r.text[:500]
    data = r.json()
    assert data.get("request_id") == "test-req-rag-1"
    assert "outputs" in data
    assert isinstance(data["outputs"], dict)
    assert data.get("status") in ("ok", "error")
    if data.get("status") == "ok":
        assert "grounding" in data or "outputs" in data
        if data.get("grounding"):
            g = data["grounding"]
            assert "chunks" in g
            assert "citations" in g


def test_sync_contract_minimal_payload() -> None:
    """Minimal valid payload: request_id, task_type, inputs.query."""
    payload = {
        "request_id": "contract-check-rag-1",
        "task_type": TASK_TYPE,
        "inputs": {"query": "contract check query"},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("request_id") == "contract-check-rag-1"
    assert "outputs" in data


def test_sync_rejects_missing_query() -> None:
    """Empty or missing inputs.query yields 200 with status error."""
    payload = {
        "request_id": "c1",
        "task_type": TASK_TYPE,
        "inputs": {},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "error"
    assert data.get("error", {}).get("code") == "VALIDATION_ERROR"


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
    data = r.json()
    assert data.get("status") == "error"
    assert data.get("error", {}).get("code") == "UNSUPPORTED_TASK_TYPE"


def test_stream_terminal_event_has_request_id_task_type_status() -> None:
    payload = {
        "request_id": "stream-contract-req",
        "task_type": TASK_TYPE,
        "inputs": {"query": "test query"},
    }
    r = client.post("/agents/run/stream", json=payload)
    assert r.status_code == 200
    events = _parse_sse_stream(r.text)
    assert len(events) >= 1
    terminal_types = ("complete", "done", "final")
    last = events[-1]
    assert last.get("event") in terminal_types, f"last event: {last}"
    terminal = last.get("data")
    assert isinstance(terminal, dict)
    assert terminal.get("request_id") == "stream-contract-req"
    assert terminal.get("task_type") == TASK_TYPE
    assert terminal.get("status") in ("ok", "success")
    assert "outputs" in terminal or "data" in terminal


def test_sync_accepts_rerank_mode_none() -> None:
    """rerankMode=none is the default and should work without LLM."""
    payload = {
        "request_id": "rerank-none-test",
        "task_type": TASK_TYPE,
        "inputs": {"query": "test query", "rerankMode": "none"},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in ("ok", "degraded")
    # Provenance should show rerank_mode
    prov = data.get("provenance", {})
    assert prov.get("rerank_mode") == "none"
    # Stages should not include llm_rerank
    stages = prov.get("stages", [])
    assert "llm_rerank" not in stages


def test_sync_rerank_mode_defaults_to_none() -> None:
    """When rerankMode is omitted, it defaults to none."""
    payload = {
        "request_id": "rerank-default-test",
        "task_type": TASK_TYPE,
        "inputs": {"query": "test query"},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    prov = data.get("provenance", {})
    assert prov.get("rerank_mode") == "none"


def test_sync_invalid_rerank_mode_falls_back_to_none() -> None:
    """Invalid rerankMode values fall back to none."""
    payload = {
        "request_id": "rerank-invalid-test",
        "task_type": TASK_TYPE,
        "inputs": {"query": "test query", "rerankMode": "invalid_mode"},
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    prov = data.get("provenance", {})
    assert prov.get("rerank_mode") == "none"


def test_stream_with_rerank_mode_llm_emits_llm_step() -> None:
    """When rerankMode=llm, stream should emit llm_rerank status event."""
    payload = {
        "request_id": "stream-llm-rerank",
        "task_type": TASK_TYPE,
        "inputs": {"query": "test query", "rerankMode": "llm"},
    }
    r = client.post("/agents/run/stream", json=payload)
    assert r.status_code == 200
    events = _parse_sse_stream(r.text)

    # Find llm_rerank step event
    steps = [e["data"].get("step") for e in events if e["data"].get("step")]
    assert "llm_rerank" in steps
