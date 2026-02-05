"""Contract test: POST /agents/run/sync returns AgentResponse shape."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
