"""
Integration tests for LangChain/LangGraph agent orchestration.
Uses worker agents with mocked LLM bridge; tests state creation and graph build.
Run from repo root: PYTHONPATH=services/worker pytest tests/integration/test_langchain_agents.py -v
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Worker src must be on path for agent imports
_repo_root = Path(__file__).resolve().parents[2]
_worker_src = _repo_root / "services" / "worker" / "src"
if str(_worker_src) not in sys.path:
    sys.path.insert(0, str(_worker_src))

pytest.importorskip("langgraph", reason="langgraph not installed")
pytest.importorskip("agents.base.state", reason="worker agents not on path")

from agents.base.state import (
    AgentState,
    create_initial_state,
)
from agents.base.langgraph_base import LangGraphBaseAgent


@pytest.fixture
def mock_llm_bridge():
    """Mock AI Router bridge for LLM calls."""
    bridge = AsyncMock()
    bridge.invoke = AsyncMock(
        return_value={
            "content": "Test LLM response",
            "usage": {
                "total_tokens": 150,
                "input_tokens": 50,
                "output_tokens": 100,
            },
        }
    )
    return bridge


@pytest.mark.integration
class TestAgentOrchestration:
    """Agent orchestration integration tests."""

    def test_create_initial_state_shape(self):
        """create_initial_state returns AgentState with expected keys."""
        state = create_initial_state(
            agent_id="dataprep",
            project_id="proj-001",
            run_id="run-001",
            thread_id="thread-001",
            stage_range=(1, 5),
            governance_mode="DEMO",
            input_artifact_ids=["art-1"],
            max_iterations=3,
        )
        assert isinstance(state, dict)
        assert state["agent_id"] == "dataprep"
        assert state["project_id"] == "proj-001"
        assert state["run_id"] == "run-001"
        assert state["thread_id"] == "thread-001"
        assert state["stage_range"] == (1, 5)
        assert state["governance_mode"] == "DEMO"
        assert state["messages"] == []
        assert state["input_artifact_ids"] == ["art-1"]
        assert state["output_artifact_ids"] == []
        assert state["gate_status"] == "pending"
        assert state["iteration"] == 0
        assert state["max_iterations"] == 3

    def test_minimal_agent_graph_build(self, mock_llm_bridge):
        """A minimal LangGraphBaseAgent subclass can build a graph."""
        from langgraph.graph import StateGraph, END

        class MinimalAgent(LangGraphBaseAgent):
            def build_graph(self):
                graph = StateGraph(dict)
                graph.add_node("n1", lambda s: s)
                graph.add_edge("n1", END)
                graph.set_entry_point("n1")
                return graph.compile(checkpointer=self.checkpointer)

            def get_quality_criteria(self):
                return {"min_length": 0}

        agent = MinimalAgent(
            llm_bridge=mock_llm_bridge,
            stages=[1, 2, 3],
            agent_id="dataprep",
        )
        g = agent.graph
        assert g is not None
        # Invoke with empty state
        from langgraph.checkpoint.memory import MemorySaver
        config = {"configurable": {"thread_id": "test-thread"}}
        result = g.invoke({}, config=config)
        assert result == {}
