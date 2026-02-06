"""
Contract test for POST /agents/run/stream: replays stream and asserts terminal event shape.

Prevents regressions on "terminal event missing request_id" (and task_type / payload schema).
Run against a running agent (e.g. agent-stage2-lit). Skips when agent is not reachable.

Run locally:
  # Start the agent (from repo root)
  docker compose up -d agent-stage2-lit
  # Or run the agent directly, e.g. from services/agents/agent-stage2-lit:
  # uvicorn app.main:app --host 0.0.0.0 --port 8000

  # Default: agent at http://localhost:8000
  pytest tests/e2e/test_agent_stream_contract.py -v

  # Or set base URL explicitly
  AGENT_STREAM_BASE_URL=http://localhost:8000 pytest tests/e2e/test_agent_stream_contract.py -v
"""

import json
import os
import pytest
import httpx


def _agent_stream_base_url() -> str:
    """Base URL for agent stream API (env AGENT_STREAM_BASE_URL or default)."""
    return os.environ.get("AGENT_STREAM_BASE_URL", "http://localhost:8000").rstrip("/")


@pytest.fixture
def agent_stream_base_url() -> str:
    """Base URL for the agent's /agents/run/stream endpoint."""
    return _agent_stream_base_url()


@pytest.fixture
async def agent_stream_available(agent_stream_base_url: str):
    """Skip tests in this module if the agent stream endpoint is not reachable."""
    try:
        # Agent may not expose /health; try OPTIONS or a short-lived GET to base
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{agent_stream_base_url}/docs")
            if r.status_code >= 500:
                pytest.skip("Agent returned server error")
    except Exception:
        pytest.skip(
            "Agent not reachable (start agent-stage2-lit for stream contract tests). "
            "E.g. docker compose up -d agent-stage2-lit"
        )


def _parse_sse_lines(lines):
    """Parse SSE lines into a list of event payloads (parsed data lines)."""
    events = []
    current_data = []
    for line in lines:
        if line.startswith("data:"):
            raw = line[5:].strip()
            if raw == "[DONE]" or not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return events


@pytest.mark.asyncio
async def test_stream_terminal_event_contract(agent_stream_available, agent_stream_base_url: str):
    """
    Call POST /agents/run/stream, consume events until stream ends, then assert:
    - Exactly one terminal event (type "final").
    - Terminal event includes request_id, task_type, and final payload (status, outputs).
    """
    url = f"{agent_stream_base_url}/agents/run/stream"
    body = {
        "request_id": "test-req-stream-contract-001",
        "task_type": "stage2_lit",
        "inputs": {"research_question": "vitamin D supplementation"},
        "mode": "DEMO",
    }

    lines = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            url,
            json=body,
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200, f"Stream returned {response.status_code}"
            async for line in response.aiter_lines():
                lines.append(line)

    events = _parse_sse_lines(lines)
    assert events, "Expected at least one SSE data event"

    terminal = [e for e in events if e.get("type") == "final"]
    assert len(terminal) == 1, (
        f"Expected exactly one terminal event (type=final), got {len(terminal)}. "
        f"Events: {[e.get('type') for e in events]}"
    )
    term = terminal[0]

    assert "request_id" in term, "Terminal event must include request_id"
    assert term["request_id"] == body["request_id"]

    assert "task_type" in term, "Terminal event must include task_type"
    assert term["task_type"] == body["task_type"]

    assert "status" in term, "Terminal event must include status (final payload schema)"
    assert isinstance(term["status"], str)

    assert "outputs" in term, "Terminal event must include outputs (final payload schema)"
    assert isinstance(term["outputs"], dict)
