"""
Tests for audit event emissions from LangGraph base agent nodes.

Verifies that:
- quality_gate_node emits NODE_STARTED and NODE_FINISHED
- human_review_node emits NODE_STARTED and NODE_FINISHED
- save_version_node emits NODE_STARTED and NODE_FINISHED
- invoke() emits RUN_STARTED and RUN_FINISHED (or RUN_FAILED)
- _emit_node_audit includes all required fields
- Audit failures don't break agent execution (logged as debug)
"""

import hashlib
import json
import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure src/ packages are importable AND stub missing heavy deps so
# agents/__init__.py doesn't blow up on local dev (no langchain_anthropic).
# ---------------------------------------------------------------------------
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Pre-register the `agents` package module so Python skips agents/__init__.py
# (which imports heavy deps like langchain_anthropic, redis, etc.).
# We only need `agents.base.langgraph_base` and `agents.base.state`.
_agents_pkg = types.ModuleType("agents")
_agents_pkg.__path__ = [str(Path(_src) / "agents")]
_agents_pkg.__package__ = "agents"
sys.modules.setdefault("agents", _agents_pkg)

_agents_base_pkg = types.ModuleType("agents.base")
_agents_base_pkg.__path__ = [str(Path(_src) / "agents" / "base")]
_agents_base_pkg.__package__ = "agents.base"
sys.modules.setdefault("agents.base", _agents_base_pkg)

# Stub the clients package (used by relative imports from langgraph_base)
_clients_pkg = types.ModuleType("clients")
_clients_pkg.__path__ = [str(Path(_src) / "clients")]
sys.modules.setdefault("clients", _clients_pkg)

# Stub the tracing package
_tracing_pkg = types.ModuleType("tracing")
_tracing_pkg.__path__ = [str(Path(_src) / "tracing")]
sys.modules.setdefault("tracing", _tracing_pkg)

# Now safe to import (relative imports in langgraph_base.py resolve via agents.base)
from agents.base.langgraph_base import (  # noqa: E402
    LangGraphBaseAgent,
    _content_hash,
    _emit_node_audit,
    _safe_emit_audit,
    _state_minimal,
)
from agents.base.state import (  # noqa: E402
    AgentState,
    create_initial_state,
)

_SAFE_EMIT_PATH = "agents.base.langgraph_base._safe_emit_audit"
_EMIT_AUDIT_PATH = "agents.base.langgraph_base.emit_audit_event"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CapturedEvents:
    """Captures audit events emitted via _safe_emit_audit."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def capture(self, event: Dict[str, Any]) -> None:
        self.events.append(event)

    def clear(self):
        self.events.clear()

    def find(self, action: str, node_id: str | None = None) -> List[Dict[str, Any]]:
        return [
            e for e in self.events
            if e.get("action") == action
            and (node_id is None or e.get("node_id") == node_id)
        ]


def _make_state(**overrides) -> AgentState:
    """Create a minimal AgentState for testing."""
    state = create_initial_state(
        agent_id="test_agent",
        project_id="proj_test",
        run_id="run_abc123",
        thread_id="thread_xyz",
        stage_range=(1, 3),
        governance_mode="DEMO",
    )
    state.update(overrides)
    return state


REQUIRED_EVENT_FIELDS = {
    "stream_type",
    "stream_key",
    "run_id",
    "trace_id",
    "node_id",
    "action",
    "actor_type",
    "actor_id",
    "service",
    "resource_type",
    "resource_id",
    "payload_json",
    "dedupe_key",
}


# ---------------------------------------------------------------------------
# Tests: module-level helpers
# ---------------------------------------------------------------------------


class TestContentHash:
    def test_deterministic(self):
        obj = {"a": 1, "b": "hello"}
        h1 = _content_hash(obj)
        h2 = _content_hash(obj)
        assert h1 == h2
        assert len(h1) == 32

    def test_fallback_on_unusual_types(self):
        # _content_hash uses default=str, so even unusual types produce a hash
        h = _content_hash(set())
        assert isinstance(h, str) and len(h) == 32


class TestStateMinimal:
    def test_extracts_safe_fields(self):
        state = _make_state()
        minimal = _state_minimal(state)
        assert "run_id" in minimal
        assert "agent_id" in minimal
        # Should NOT contain messages or current_output
        assert "messages" not in minimal
        assert "current_output" not in minimal


class TestEmitNodeAudit:
    """Test _emit_node_audit at the module level."""

    def test_event_has_required_fields(self):
        captured = _CapturedEvents()
        state = _make_state()

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            _emit_node_audit(state, "test_node", "NODE_STARTED", 0, started_at_ms=1000)

        assert len(captured.events) == 1
        event = captured.events[0]
        missing = REQUIRED_EVENT_FIELDS - set(event.keys())
        assert not missing, f"Missing fields: {missing}"

    def test_started_and_finished_events(self):
        captured = _CapturedEvents()
        state = _make_state()

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            _emit_node_audit(state, "n1", "NODE_STARTED", 0, started_at_ms=1000)
            _emit_node_audit(
                state, "n1", "NODE_FINISHED", 0,
                started_at_ms=1000, duration_ms=42,
                input_hash="aaa", output_hash="bbb",
            )

        started = captured.find("NODE_STARTED", "n1")
        finished = captured.find("NODE_FINISHED", "n1")
        assert len(started) == 1
        assert len(finished) == 1
        assert finished[0]["payload_json"]["duration_ms"] == 42
        assert finished[0]["payload_json"]["input_hash"] == "aaa"
        assert finished[0]["payload_json"]["output_hash"] == "bbb"

    def test_failed_event_includes_error(self):
        captured = _CapturedEvents()
        state = _make_state()

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            _emit_node_audit(
                state, "n1", "NODE_FAILED", 0,
                started_at_ms=1000, duration_ms=5,
                error_class="ValueError",
                error_message="boom",
            )

        failed = captured.find("NODE_FAILED", "n1")
        assert len(failed) == 1
        assert failed[0]["payload_json"]["error_class"] == "ValueError"
        assert failed[0]["payload_json"]["error_message"] == "boom"

    def test_dedupe_key_unique_per_action(self):
        captured = _CapturedEvents()
        state = _make_state()

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            _emit_node_audit(state, "n1", "NODE_STARTED", 0)
            _emit_node_audit(state, "n1", "NODE_FINISHED", 0)

        keys = [e["dedupe_key"] for e in captured.events]
        assert len(set(keys)) == 2, "Dedupe keys should differ for STARTED vs FINISHED"


class TestSafeEmitAudit:
    """Verify _safe_emit_audit swallows errors."""

    def test_value_error_logged_as_debug(self, caplog):
        """Audit failures are swallowed and logged at DEBUG."""
        with caplog.at_level(logging.DEBUG):
            # _safe_emit_audit does a lazy import inside; failures are caught.
            _safe_emit_audit({"action": "TEST"})
        # Should log *something* at debug level (either config missing or import failure)
        assert caplog.text.strip(), "Expected debug-level log from _safe_emit_audit"

    def test_runtime_error_logged_as_debug(self, caplog):
        with caplog.at_level(logging.DEBUG):
            with patch(
                "clients.orchestrator_audit_client.emit_audit_event",
                side_effect=RuntimeError("network error"),
            ):
                _safe_emit_audit({"action": "TEST"})
        assert "Audit emit failed" in caplog.text or "network error" in caplog.text


# ---------------------------------------------------------------------------
# Tests: quality_gate_node, human_review_node, save_version_node
# ---------------------------------------------------------------------------


class _StubAgent(LangGraphBaseAgent):
    """Minimal concrete agent for testing base-class node methods."""

    def build_graph(self):
        pass  # Not needed for node-level tests

    def get_quality_criteria(self):
        return {"min_length": 10}


class TestQualityGateNode:
    def test_emits_started_and_finished(self):
        captured = _CapturedEvents()
        agent = _StubAgent(llm_bridge=MagicMock(), stages=[1, 2], agent_id="test")
        state = _make_state(current_output="This is enough text for the quality gate check.")

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            result = agent.quality_gate_node(state)

        started = captured.find("NODE_STARTED", "quality_gate")
        finished = captured.find("NODE_FINISHED", "quality_gate")
        assert len(started) == 1
        assert len(finished) == 1
        assert "gate_status" in result


class TestHumanReviewNode:
    def test_emits_started_and_finished(self):
        captured = _CapturedEvents()
        agent = _StubAgent(llm_bridge=MagicMock(), stages=[1, 2], agent_id="test")
        state = _make_state()

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            result = agent.human_review_node(state)

        started = captured.find("NODE_STARTED", "human_review")
        finished = captured.find("NODE_FINISHED", "human_review")
        assert len(started) == 1
        assert len(finished) == 1
        assert result["awaiting_approval"] is True


class TestSaveVersionNode:
    def test_emits_started_and_finished(self):
        captured = _CapturedEvents()
        agent = _StubAgent(llm_bridge=MagicMock(), stages=[1, 2], agent_id="test")
        state = _make_state(current_output="draft output", gate_score=0.9)

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            result = agent.save_version_node(state)

        started = captured.find("NODE_STARTED", "save_version")
        finished = captured.find("NODE_FINISHED", "save_version")
        assert len(started) == 1
        assert len(finished) == 1
        assert result["iteration"] == 1


# ---------------------------------------------------------------------------
# Tests: invoke() and resume() audit emissions
# ---------------------------------------------------------------------------


class TestInvokeAuditEmissions:
    """Verify invoke() emits RUN_STARTED / RUN_FINISHED / RUN_FAILED."""

    def test_invoke_emits_run_started_and_finished(self):
        import asyncio
        from unittest.mock import AsyncMock

        captured = _CapturedEvents()
        agent = _StubAgent(llm_bridge=MagicMock(), stages=[1, 2], agent_id="test")

        # Mock the graph — ainvoke must be a coroutine
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value=_make_state(current_output="done")
        )
        agent._graph = mock_graph

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            result = asyncio.get_event_loop().run_until_complete(
                agent.invoke(project_id="proj_test")
            )

        started = captured.find("RUN_STARTED", "__invoke__")
        finished = captured.find("RUN_FINISHED", "__invoke__")
        assert len(started) == 1, f"Expected 1 RUN_STARTED, got {len(started)}"
        assert len(finished) == 1, f"Expected 1 RUN_FINISHED, got {len(finished)}"
        # Finished should have duration_ms
        assert "duration_ms" in finished[0]["payload_json"]

    def test_invoke_emits_run_failed_on_error(self):
        import asyncio
        from unittest.mock import AsyncMock

        captured = _CapturedEvents()
        agent = _StubAgent(llm_bridge=MagicMock(), stages=[1, 2], agent_id="test")

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("kaboom"))
        agent._graph = mock_graph

        with patch(
            _SAFE_EMIT_PATH,
            side_effect=captured.capture,
        ):
            with pytest.raises(RuntimeError, match="kaboom"):
                asyncio.get_event_loop().run_until_complete(
                    agent.invoke(project_id="proj_test")
                )

        started = captured.find("RUN_STARTED", "__invoke__")
        failed = captured.find("RUN_FAILED", "__invoke__")
        assert len(started) == 1
        assert len(failed) == 1
        assert failed[0]["payload_json"]["error_class"] == "RuntimeError"
        assert "kaboom" in failed[0]["payload_json"]["error_message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
