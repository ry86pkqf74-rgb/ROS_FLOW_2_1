"""
Contract invariants for agent sync response and stream terminal event.

Pure unit tests: no server, no Docker. Validates payload/event shape only.
Run: pytest tests/contract -v (from repo root).
"""

from __future__ import annotations

import json
from typing import Any


# --- Helpers (mirror scripts/check-agent-contract.py and agent test_contract.py) ---

TERMINAL_EVENT_TYPES = ("complete", "done", "final")


def has_success_indicator(obj: dict[str, Any]) -> bool:
    if obj.get("ok") is True:
        return True
    if obj.get("status") in ("ok", "success"):
        return True
    if obj.get("success") is True:
        return True
    return False


def has_outputs_or_data(obj: dict[str, Any]) -> bool:
    if obj.get("outputs") is not None and isinstance(obj["outputs"], dict):
        return True
    if obj.get("data") is not None and isinstance(obj["data"], dict):
        return True
    return False


def is_terminal_event_type(ev: dict[str, Any]) -> bool:
    """True if SSE event is a terminal type (complete/done/final)."""
    sse_type = ev.get("event")
    data = ev.get("data") or {}
    data_type = data.get("type") if isinstance(data, dict) else data.get("event")
    return (sse_type in TERMINAL_EVENT_TYPES) or (
        data_type in TERMINAL_EVENT_TYPES if data_type else False
    )


# --- Sync response invariants ---


def test_sync_response_requires_request_id() -> None:
    """Sync response must include non-empty request_id."""
    valid = {"request_id": "req-1", "ok": True, "outputs": {}}
    assert isinstance(valid.get("request_id"), str) and valid["request_id"]
    invalid_missing = {"ok": True, "outputs": {}}
    assert not (isinstance(invalid_missing.get("request_id"), str) and invalid_missing.get("request_id"))


def test_sync_response_requires_success_indicator() -> None:
    """Sync response must include ok=true or status in ['ok','success']."""
    for good in (
        {"request_id": "x", "ok": True, "outputs": {}},
        {"request_id": "x", "status": "ok", "outputs": {}},
        {"request_id": "x", "status": "success", "outputs": {}},
    ):
        assert has_success_indicator(good), f"expected success indicator in {good}"
    bad = {"request_id": "x", "outputs": {}}
    assert not has_success_indicator(bad)


def test_sync_response_requires_outputs_or_data() -> None:
    """Sync response must include outputs or data object."""
    for good in (
        {"request_id": "x", "outputs": {"papers": []}},
        {"request_id": "x", "data": {"result": 1}},
    ):
        assert has_outputs_or_data(good), f"expected outputs/data in {good}"
    bad = {"request_id": "x", "ok": True}
    assert not has_outputs_or_data(bad)


# --- Stream terminal event invariants ---


def test_terminal_event_requires_request_id() -> None:
    """Terminal event (final/complete/done) must include request_id."""
    good = {"type": "final", "request_id": "stream-req-1", "task_type": "LIT_RETRIEVAL", "status": "ok", "outputs": {}}
    assert isinstance(good.get("request_id"), str) and good["request_id"]
    bad = {"type": "final", "task_type": "LIT_RETRIEVAL", "status": "ok"}
    assert not (isinstance(bad.get("request_id"), str) and bad.get("request_id"))


def test_terminal_event_requires_task_type() -> None:
    """Terminal event must include task_type."""
    good = {"type": "final", "request_id": "r", "task_type": "POLICY_REVIEW", "status": "ok", "outputs": {}}
    assert isinstance(good.get("task_type"), str) and good["task_type"]
    bad = {"type": "final", "request_id": "r", "status": "ok"}
    assert not (isinstance(bad.get("task_type"), str) and bad.get("task_type"))


def test_terminal_event_requires_status() -> None:
    """Terminal event must include status (ok/success)."""
    good = {"type": "final", "request_id": "r", "task_type": "X", "status": "ok", "outputs": {}}
    assert good.get("status") in ("ok", "success")
    bad = {"type": "final", "request_id": "r", "task_type": "X", "outputs": {}}
    assert bad.get("status") not in ("ok", "success")


def test_terminal_event_requires_success_indicator() -> None:
    """Terminal event must have ok=true or status or success=true."""
    for good in (
        {"type": "final", "request_id": "r", "task_type": "X", "status": "ok", "outputs": {}},
        {"type": "final", "request_id": "r", "task_type": "X", "success": True, "outputs": {}},
    ):
        assert has_success_indicator(good)
    bad = {"type": "final", "request_id": "r", "task_type": "X", "outputs": {}}
    assert has_success_indicator(bad) is False  # no status/success/ok


def test_terminal_event_requires_outputs_or_data() -> None:
    """Terminal event must include outputs or data."""
    good = {"type": "final", "request_id": "r", "task_type": "X", "status": "ok", "outputs": {"allowed": True}}
    assert has_outputs_or_data(good)
    bad = {"type": "final", "request_id": "r", "task_type": "X", "status": "ok"}
    assert not has_outputs_or_data(bad)


def test_parsed_sse_terminal_event_shape() -> None:
    """Parsed SSE terminal event (as from _parse_sse_stream) must satisfy invariants."""
    # Simulate parsed SSE: list of { "event": "<type>", "data": <obj> }
    events = [
        {"event": "started", "data": {"type": "started", "request_id": "e1", "task_type": "LIT_RETRIEVAL"}},
        {"event": "progress", "data": {"type": "progress", "request_id": "e1", "progress": 50}},
        {
            "event": "final",
            "data": {
                "type": "final",
                "request_id": "e1",
                "task_type": "LIT_RETRIEVAL",
                "status": "ok",
                "outputs": {"papers": [], "count": 0},
            },
        },
    ]
    terminal = [e for e in events if is_terminal_event_type(e)]
    assert len(terminal) == 1, "expected exactly one terminal event"
    data = terminal[0].get("data")
    assert isinstance(data, dict)
    assert data.get("request_id") == "e1"
    assert data.get("task_type") == "LIT_RETRIEVAL"
    assert data.get("status") in ("ok", "success")
    assert has_outputs_or_data(data)


def test_contract_fixture_sync_response() -> None:
    """Canonical sync response fixture passes all invariants."""
    fixture = {
        "status": "ok",
        "request_id": "contract-fixture-1",
        "outputs": {"allowed": True, "reasons": ["stub"]},
        "artifacts": [],
        "provenance": {},
        "usage": {"duration_ms": 10},
    }
    assert isinstance(fixture.get("request_id"), str) and fixture["request_id"]
    assert has_success_indicator(fixture)
    assert has_outputs_or_data(fixture)


def test_contract_fixture_stream_final_event() -> None:
    """Canonical stream final event fixture passes all invariants."""
    fixture = {
        "type": "final",
        "request_id": "stream-fixture-1",
        "task_type": "POLICY_REVIEW",
        "status": "ok",
        "success": True,
        "outputs": {"resource_id": "", "allowed": True, "risk_level": "low"},
    }
    assert fixture.get("request_id") and isinstance(fixture["request_id"], str)
    assert fixture.get("task_type") and isinstance(fixture["task_type"], str)
    assert fixture.get("status") in ("ok", "success")
    assert has_success_indicator(fixture)
    assert has_outputs_or_data(fixture)
