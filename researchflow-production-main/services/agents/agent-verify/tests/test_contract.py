"""
Contract tests for agent-verify: LIVE mode fail-closed behavior and response schema validation.

Tests verify:
- Claims WITHOUT evidence must NOT pass in LIVE mode (fail-closed)
- Claims WITH evidence quote referencing a returned chunkId CAN pass
- Response schema matches AGENT_CONTRACT.md
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import (
    CLINICAL_GROUNDING_PACK,
    EMPTY_GROUNDING_PACK,
    make_bridge_response_pass_with_evidence,
    make_bridge_response_pass_no_evidence,
    make_bridge_response_pass_empty_quote,
    make_bridge_response_multi_claims,
)

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


# ============ Health Check Tests ============


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


# ============ Sync Contract Tests ============


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


# ============ LIVE Mode Fail-Closed Tests ============


def test_live_fail_closed_no_grounding() -> None:
    """In LIVE mode with empty grounding pack, all claims must be unclear (fail-closed)."""
    payload = {
        "request_id": "test-live-no-grounding-1",
        "task_type": "CLAIM_VERIFY",
        "mode": "LIVE",
        "inputs": {
            "claims": ["Some claim with no grounding.", "Another claim."],
            "groundingPack": EMPTY_GROUNDING_PACK,
            "governanceMode": "LIVE",
        },
    }
    r = client.post("/agents/run/sync", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"

    verdicts = data["outputs"].get("claim_verdicts") or []
    assert len(verdicts) == 2

    for v in verdicts:
        assert v["verdict"] == "unclear", \
            f"LIVE mode with no grounding must return unclear, got {v['verdict']}"

    assert data["outputs"]["overallPass"] is False


def test_live_claim_with_evidence_can_pass() -> None:
    """In LIVE mode, a claim WITH valid evidence quote CAN pass."""
    # Mock the bridge to return a verdict with evidence
    mock_response = make_bridge_response_pass_with_evidence(
        claim="The study was a randomized controlled trial.",
        chunk_id="chunk-rct-001",
        quote="This was a randomized controlled trial with 250 participants.",
    )

    with patch("agent.impl._invoke_bridge", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_response

        payload = {
            "request_id": "test-live-with-evidence-1",
            "task_type": "CLAIM_VERIFY",
            "mode": "LIVE",
            "inputs": {
                "claims": ["The study was a randomized controlled trial."],
                "groundingPack": CLINICAL_GROUNDING_PACK,
                "governanceMode": "LIVE",
            },
        }

        r = client.post("/agents/run/sync", json=payload)
        assert r.status_code == 200
        data = r.json()

        # Schema validation
        assert data.get("status") == "ok"
        assert data.get("request_id") == "test-live-with-evidence-1"
        assert "outputs" in data

        verdicts = data["outputs"].get("claim_verdicts", [])
        assert len(verdicts) == 1

        v = verdicts[0]
        assert v["claim"] == "The study was a randomized controlled trial."
        assert v["verdict"] == "pass", "Claim with valid evidence should pass in LIVE mode"
        assert len(v["evidence"]) >= 1
        assert v["evidence"][0]["chunkId"] == "chunk-rct-001"
        assert v["evidence"][0]["quote"]  # Has non-empty quote

        assert data["outputs"]["overallPass"] is True


def test_live_claim_without_evidence_cannot_pass() -> None:
    """In LIVE mode, a claim WITHOUT evidence quote must NOT pass (fail-closed)."""
    # Mock the bridge to return pass verdict but NO evidence
    mock_response = make_bridge_response_pass_no_evidence(
        claim="Some ungrounded claim."
    )

    with patch("agent.impl._invoke_bridge", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_response

        payload = {
            "request_id": "test-live-no-evidence-1",
            "task_type": "CLAIM_VERIFY",
            "mode": "LIVE",
            "inputs": {
                "claims": ["Some ungrounded claim."],
                "groundingPack": CLINICAL_GROUNDING_PACK,
                "governanceMode": "LIVE",
            },
        }

        r = client.post("/agents/run/sync", json=payload)
        assert r.status_code == 200
        data = r.json()

        verdicts = data["outputs"].get("claim_verdicts", [])
        assert len(verdicts) == 1

        v = verdicts[0]
        # Fail-closed: verdict must be "unclear" (converted from "pass" due to no evidence)
        assert v["verdict"] in ("fail", "unclear"), \
            f"LIVE mode fail-closed violated: got verdict={v['verdict']} with no evidence"
        assert v["verdict"] != "pass", "LIVE mode must not allow pass without evidence"

        assert data["outputs"]["overallPass"] is False


def test_live_empty_quote_not_valid_evidence() -> None:
    """In LIVE mode, evidence with empty quote string is not valid - claim cannot pass."""
    mock_response = make_bridge_response_pass_empty_quote(
        claim="The study used HPLC.",
        chunk_id="chunk-methods-004",
    )

    with patch("agent.impl._invoke_bridge", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_response

        payload = {
            "request_id": "test-live-empty-quote-1",
            "task_type": "CLAIM_VERIFY",
            "mode": "LIVE",
            "inputs": {
                "claims": ["The study used HPLC."],
                "groundingPack": CLINICAL_GROUNDING_PACK,
                "governanceMode": "LIVE",
            },
        }

        r = client.post("/agents/run/sync", json=payload)
        data = r.json()
        verdicts = data["outputs"].get("claim_verdicts", [])

        # Empty quote = no valid evidence = cannot pass in LIVE
        assert verdicts[0]["verdict"] in ("fail", "unclear"), \
            "Empty quote should not count as valid evidence"


def test_live_whitespace_quote_not_valid_evidence() -> None:
    """In LIVE mode, evidence with whitespace-only quote is not valid."""
    mock_response = json.dumps([{
        "claim": "Some claim.",
        "verdict": "pass",
        "evidence": [{"chunk_id": "chunk-1", "quote": "   \t\n  "}],
    }])

    with patch("agent.impl._invoke_bridge", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_response

        payload = {
            "request_id": "test-live-whitespace-quote-1",
            "task_type": "CLAIM_VERIFY",
            "mode": "LIVE",
            "inputs": {
                "claims": ["Some claim."],
                "groundingPack": CLINICAL_GROUNDING_PACK,
                "governanceMode": "LIVE",
            },
        }

        r = client.post("/agents/run/sync", json=payload)
        data = r.json()
        verdicts = data["outputs"].get("claim_verdicts", [])

        # Whitespace-only quote = no valid evidence = cannot pass in LIVE
        assert verdicts[0]["verdict"] in ("fail", "unclear"), \
            "Whitespace-only quote should not count as valid evidence"


def test_live_multiple_claims_mixed_evidence() -> None:
    """In LIVE mode with multiple claims, only claims WITH evidence can pass."""
    mock_response = make_bridge_response_multi_claims([
        {
            "claim": "The study was randomized.",
            "verdict": "pass",
            "evidence": [{
                "chunk_id": "chunk-rct-001",
                "quote": "randomly assigned in a 1:1 ratio"
            }]
        },
        {
            "claim": "The study was FDA approved.",
            "verdict": "pass",  # AI says pass but...
            "evidence": []  # No evidence
        },
        {
            "claim": "HbA1c was measured.",
            "verdict": "pass",
            "evidence": [{
                "chunk_id": "chunk-methods-004",
                "quote": "HbA1c was measured using HPLC"
            }]
        }
    ])

    with patch("agent.impl._invoke_bridge", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_response

        payload = {
            "request_id": "test-live-mixed-1",
            "task_type": "CLAIM_VERIFY",
            "mode": "LIVE",
            "inputs": {
                "claims": [
                    "The study was randomized.",
                    "The study was FDA approved.",
                    "HbA1c was measured."
                ],
                "groundingPack": CLINICAL_GROUNDING_PACK,
                "governanceMode": "LIVE",
            },
        }

        r = client.post("/agents/run/sync", json=payload)
        data = r.json()
        verdicts = data["outputs"]["claim_verdicts"]

        assert len(verdicts) == 3

        # Claim 1: has evidence -> can pass
        assert verdicts[0]["verdict"] == "pass"
        assert len(verdicts[0]["evidence"]) > 0

        # Claim 2: no evidence -> fail-closed to unclear
        assert verdicts[1]["verdict"] in ("fail", "unclear"), \
            f"Claim without evidence must not pass, got {verdicts[1]['verdict']}"

        # Claim 3: has evidence -> can pass
        assert verdicts[2]["verdict"] == "pass"
        assert len(verdicts[2]["evidence"]) > 0

        # Overall: not all pass, so overallPass = False
        assert data["outputs"]["overallPass"] is False


# ============ Response Schema Validation ============


def test_response_schema_matches_contract() -> None:
    """Verify response schema matches AGENT_CONTRACT.md requirements."""
    payload = {
        "request_id": "test-schema-check-1",
        "task_type": "CLAIM_VERIFY",
        "mode": "DEMO",
        "inputs": {
            "claims": ["Test claim."],
            "groundingPack": {"sources": [{"id": "c1", "text": "Test text"}]},
            "governanceMode": "DEMO",
        },
    }

    r = client.post("/agents/run/sync", json=payload)
    data = r.json()

    # Required fields per AGENT_CONTRACT.md
    assert "status" in data
    assert data["status"] in ("ok", "success")

    assert "request_id" in data
    assert data["request_id"] == "test-schema-check-1"

    assert "outputs" in data
    assert isinstance(data["outputs"], dict)

    # Verify outputs structure for CLAIM_VERIFY
    outputs = data["outputs"]
    assert "claim_verdicts" in outputs
    assert isinstance(outputs["claim_verdicts"], list)

    assert "overallPass" in outputs
    assert isinstance(outputs["overallPass"], bool)

    # Verify verdict structure
    if outputs["claim_verdicts"]:
        v = outputs["claim_verdicts"][0]
        assert "claim" in v
        assert "verdict" in v
        assert v["verdict"] in ("pass", "fail", "unclear")
        assert "evidence" in v
        assert isinstance(v["evidence"], list)

        # If evidence exists, verify EvidenceQuote structure
        if v["evidence"]:
            ev = v["evidence"][0]
            # Uses alias chunkId (not chunk_id) per schema Config
            assert "chunkId" in ev, "Evidence must use 'chunkId' alias per schema"
            assert "quote" in ev


def test_response_schema_evidence_uses_chunkid_alias() -> None:
    """Verify evidence uses 'chunkId' alias (not 'chunk_id') in JSON output."""
    mock_response = make_bridge_response_pass_with_evidence(
        claim="Test claim.",
        chunk_id="test-chunk-id",
        quote="Test quote from chunk.",
    )

    with patch("agent.impl._invoke_bridge", new_callable=AsyncMock) as mock_bridge:
        mock_bridge.return_value = mock_response

        payload = {
            "request_id": "test-alias-check-1",
            "task_type": "CLAIM_VERIFY",
            "mode": "LIVE",
            "inputs": {
                "claims": ["Test claim."],
                "groundingPack": CLINICAL_GROUNDING_PACK,
                "governanceMode": "LIVE",
            },
        }

        r = client.post("/agents/run/sync", json=payload)
        data = r.json()

        verdicts = data["outputs"]["claim_verdicts"]
        assert len(verdicts) == 1
        assert len(verdicts[0]["evidence"]) == 1

        ev = verdicts[0]["evidence"][0]
        assert "chunkId" in ev, "JSON output must use 'chunkId' alias"
        assert "chunk_id" not in ev, "JSON output must NOT use 'chunk_id' (use alias instead)"
        assert ev["chunkId"] == "test-chunk-id"


# ============ Stream Contract Tests ============


TERMINAL_EVENT_TYPES = ("complete", "done", "final")


def _is_terminal_event(ev: dict[str, Any]) -> bool:
    sse_type = ev.get("event")
    data = ev.get("data") or {}
    data_type = data.get("type") if isinstance(data, dict) else None
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
