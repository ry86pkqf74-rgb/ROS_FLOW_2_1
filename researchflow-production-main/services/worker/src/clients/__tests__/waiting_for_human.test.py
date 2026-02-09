import os
import sys
import pytest

TEST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if TEST_ROOT not in sys.path:
    sys.path.insert(0, TEST_ROOT)

from agents.nodes.waiting_for_human import (
    build_edit_session_dedupe_key,
    enter_waiting_for_human,
    validate_resume,
    WAITING_FOR_HUMAN,
)


class FakeOrchestratorClient:
    def __init__(self) -> None:
        self.created = []
        self.sessions = {}

    def create_edit_session(self, *, run_id, trace_id, node_id, attempt, dedupe_key):
        self.created.append(
            {
                "run_id": run_id,
                "trace_id": trace_id,
                "node_id": node_id,
                "attempt": attempt,
                "dedupe_key": dedupe_key,
            }
        )
        session_id = f"sess-{len(self.created)}"
        session = {"id": session_id, "status": "waiting"}
        self.sessions[session_id] = session
        return session

    def get_edit_session(self, edit_session_id):
        return self.sessions[edit_session_id]


def test_build_edit_session_dedupe_key_is_stable():
    key1 = build_edit_session_dedupe_key("run-1", "trace-1", "human_gate", 2)
    key2 = build_edit_session_dedupe_key("run-1", "trace-1", "human_gate", 2)
    assert key1 == key2
    assert key1.endswith(":2")


def test_enter_waiting_for_human_is_idempotent():
    client = FakeOrchestratorClient()
    state = {
        "run_id": "run-1",
        "trace_id": "trace-1",
        "gate_status": None,
    }

    updates_first = enter_waiting_for_human(state, client, node_id="human_gate")
    state_first = {**state, **updates_first, "gate_status": WAITING_FOR_HUMAN}

    updates_second = enter_waiting_for_human(state_first, client, node_id="human_gate")

    assert len(client.created) == 1
    assert updates_first["edit_session_id"] == updates_second["edit_session_id"]
    assert updates_first["waiting_for_human_attempt"] == updates_second["waiting_for_human_attempt"]


def test_validate_resume_blocks_unapproved_sessions():
    client = FakeOrchestratorClient()
    session = client.create_edit_session(
        run_id="run-1",
        trace_id="trace-1",
        node_id="human_gate",
        attempt=1,
        dedupe_key="run-1:trace-1:human_gate:1",
    )
    client.sessions[session["id"]]["status"] = "waiting"

    with pytest.raises(ValueError):
        validate_resume(
            client,
            edit_session_id=session["id"],
            node_id="human_gate",
            run_id="run-1",
            trace_id="trace-1",
            attempt=1,
        )


def test_validate_resume_allows_approved_sessions():
    client = FakeOrchestratorClient()
    session = client.create_edit_session(
        run_id="run-1",
        trace_id="trace-1",
        node_id="human_gate",
        attempt=1,
        dedupe_key="run-1:trace-1:human_gate:1",
    )
    client.sessions[session["id"]]["status"] = "approved"

    result = validate_resume(
        client,
        edit_session_id=session["id"],
        node_id="human_gate",
        run_id="run-1",
        trace_id="trace-1",
        attempt=1,
    )
    assert result["id"] == session["id"]
