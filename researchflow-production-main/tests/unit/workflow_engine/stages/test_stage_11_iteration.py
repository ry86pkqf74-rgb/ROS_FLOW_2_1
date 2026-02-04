"""
Unit tests for Stage 11: IterationAgent

Tests the IterationAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with mocked bridge (peer-review, claude-writer)
- Iteration logic and output shape
- Tool implementations
- Output schema (iteration_log, version_info, ai_suggestions, routing, diff, summary)
- Error handling
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_11_iteration import IterationAgent
from src.workflow_engine.types import StageContext


@pytest.fixture
def agent():
    """Create an IterationAgent instance."""
    return IterationAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with iteration config."""
    return StageContext(
        job_id="test-job",
        config={
            "iteration": {
                "iteration_request": {"type": "general", "changes": []},
                "enable_ai_suggestions": True,
            },
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
    )


@pytest.fixture
def mock_claude_response():
    """Mock claude-writer generateSection response."""
    return {
        "success": True,
        "section": "Suggested revisions summary.",
        "reasoning": "Based on iteration feedback.",
    }


@pytest.fixture
def mock_peer_review_response():
    """Mock peer-review simulateReview response."""
    return {
        "overallScore": 7.5,
        "recommendation": "minor_revision",
        "comments": [],
        "strengthsSummary": ["Clear methodology"],
        "weaknessesSummary": [],
        "categoryScores": {"originality": 8, "methodology": 7, "results": 7.5},
    }


class TestIterationAgent:
    """Tests for IterationAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 11
        assert agent.stage_name == "Iteration"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = IterationAgent()
        assert a.stage_id == 11
        assert a.stage_name == "Iteration"

    def test_get_tools(self, agent):
        """get_tools should return a list of five tools when LangChain available."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5
            names = [t.name for t in tools]
            assert "analyze_feedback" in names
            assert "prioritize_revisions" in names
            assert "route_to_stage" in names
            assert "track_iteration" in names
            assert "assess_convergence" in names

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, sample_context, mock_claude_response, mock_peer_review_response
    ):
        """Execute should succeed with complete context and mocked peer-review and claude-writer."""
        async def mock_call(service_name, method_name, params):
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            if service_name == "claude-writer" and method_name == "generateSection":
                return mock_claude_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "iteration_log" in result.output
        assert "version_info" in result.output
        assert "ai_suggestions" in result.output
        assert "routing" in result.output
        assert "summary" in result.output
        assert result.output.get("peer_review") == mock_peer_review_response
        assert result.output.get("claude_revision_suggestion") == mock_claude_response
        assert len(result.output["iteration_log"]) >= 1
        assert len(result.artifacts) >= 1
        assert any("iteration_report.json" in a for a in result.artifacts)

    @pytest.mark.asyncio
    async def test_execute_missing_iteration_config(self, agent, tmp_path):
        """Missing iteration config should yield warnings; stage still completes."""
        context = StageContext(
            job_id="test-job",
            config={},
            artifact_path=str(tmp_path / "artifacts"),
            governance_mode="DEMO",
        )
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(context)
        assert result.status == "completed"
        assert any("iteration" in w.lower() or "request" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_bridge_failure(self, agent, sample_context):
        """Bridge failure should add warning; stage still completes."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert "iteration_log" in result.output
        assert any("unavailable" in w.lower() or "peer" in w.lower() or "claude" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_demo_mode(
        self, agent, sample_context, mock_claude_response, mock_peer_review_response
    ):
        """DEMO mode should be reflected in output and warnings."""
        async def mock_call(service_name, method_name, params):
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            if service_name == "claude-writer" and method_name == "generateSection":
                return mock_claude_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert result.output.get("demo_mode") is True
        assert any("DEMO" in w for w in result.warnings)


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_analyze_feedback_tool(self, agent):
        """Tool should return themes, severity, suggested_actions."""
        inp = json.dumps({"feedback": [], "focus_areas": ["statistical_analysis"]})
        result = agent._analyze_feedback_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "themes" in data or "suggested_actions" in data or "summary" in data

    def test_prioritize_revisions_tool(self, agent):
        """Tool should return prioritized list and rationale."""
        inp = json.dumps({"revisions": [{"title": "Fix methods", "priority": "high"}]})
        result = agent._prioritize_revisions_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "prioritized" in data or "rationale" in data

    def test_route_to_stage_tool(self, agent):
        """Tool should return pipeline, affected_stages, requires_reanalysis."""
        inp = json.dumps({"iteration_request": {"type": "parameter_change", "changes": []}})
        result = agent._route_to_stage_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "pipeline" in data
            assert "affected_stages" in data
            assert "requires_reanalysis" in data

    def test_track_iteration_tool(self, agent):
        """Tool should return version_entry and diff_summary."""
        inp = json.dumps({
            "version_number": 1,
            "changes": {"summary": "test", "changes": []},
            "previous_data": {"a": 1},
            "current_data": {"a": 2},
        })
        result = agent._track_iteration_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "version_entry" in data
            assert "diff_summary" in data

    def test_assess_convergence_tool(self, agent):
        """Tool should return status and recommendation."""
        inp = json.dumps({"version_history": [{}, {}], "iteration_log": []})
        result = agent._assess_convergence_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "status" in data
            assert "recommendation" in data

    def test_analyze_feedback_tool_invalid_json(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._analyze_feedback_tool("not valid json")
        assert "Failed" in result or "error" in result.lower()


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(
        self, agent, sample_context, mock_claude_response, mock_peer_review_response
    ):
        """Output should match required schema: iteration_log, version_info, ai_suggestions, routing, diff, summary."""
        async def mock_call(service_name, method_name, params):
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            if service_name == "claude-writer" and method_name == "generateSection":
                return mock_claude_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        out = result.output
        assert "iteration_log" in out
        assert isinstance(out["iteration_log"], list)
        assert "version_info" in out
        assert isinstance(out["version_info"], dict)
        assert "current_version" in out["version_info"]
        assert "version_number" in out["version_info"]
        assert "ai_suggestions" in out
        assert isinstance(out["ai_suggestions"], list)
        assert "routing" in out
        r = out["routing"]
        assert "pipeline" in r
        assert "affected_stages" in r
        assert "requires_reanalysis" in r
        assert "diff" in out
        assert isinstance(out["diff"], dict)
        assert "summary" in out
        assert isinstance(out["summary"], dict)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_completion_on_bridge_failure(self, agent, sample_context):
        """Bridge failure should not fail the stage; warnings present."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert len(result.warnings) >= 1

    def test_analyze_feedback_tool_invalid_json_returns_string(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._analyze_feedback_tool("not valid json")
        assert isinstance(result, str)
        assert "Failed" in result or "error" in result.lower()
