"""
Unit tests for Stage 9: InterpretationAgent

Tests the InterpretationAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with mocked bridge (discussion-builder)
- Interpretation logic and output shape
- Tool implementations
- Output schema (interpretation block, key_findings, implications, limitations)
- Error handling
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_09_interpretation import InterpretationAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def agent():
    """Create an InterpretationAgent instance."""
    return InterpretationAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with interpretation config."""
    return StageContext(
        job_id="test-job",
        config={
            "interpretation": {
                "findings": [
                    {"id": "f1", "summary": "Finding one", "priority": "high", "category": "efficacy"},
                    {"id": "f2", "summary": "Finding two", "priority": "medium", "category": "safety"},
                ],
                "auto_generate_threads": True,
                "annotation_types": ["highlight", "note"],
            },
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
    )


@pytest.fixture
def mock_discussion_builder_response():
    """Mock discussion-builder build response (data returned by bridge)."""
    return {
        "clinical_significance": "Findings suggest clinical relevance.",
        "comparison_to_literature": [{"source": "lit1", "note": "Consistent with prior work."}],
        "implications": {"clinical": ["Apply in practice"], "research": ["Replicate in larger cohort"]},
        "limitations": ["Sample size limited"],
        "future_directions": ["Prospective validation"],
    }


class TestInterpretationAgent:
    """Tests for InterpretationAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 9
        assert agent.stage_name == "Result Interpretation"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = InterpretationAgent()
        assert a.stage_id == 9
        assert a.stage_name == "Result Interpretation"

    def test_get_tools(self, agent):
        """get_tools should return a list of five tools when LangChain available."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5
            names = [t.name for t in tools]
            assert "interpret_statistics" in names
            assert "compare_to_literature" in names
            assert "identify_clinical_significance" in names
            assert "generate_implications" in names
            assert "identify_limitations" in names

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context, mock_discussion_builder_response):
        """Execute should succeed with complete context and mocked discussion-builder."""
        async def mock_call(service_name, method_name, params):
            if service_name == "discussion-builder" and method_name == "build":
                return mock_discussion_builder_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "interpretation" in result.output
        assert "key_findings" in result.output
        assert "interpretations" in result.output
        assert "discussion_threads" in result.output
        assert "annotations" in result.output
        assert "summary" in result.output
        interp = result.output["interpretation"]
        assert "key_findings" in interp
        assert "clinical_significance" in interp
        assert "comparison_to_literature" in interp
        assert "implications" in interp
        assert "limitations" in interp
        assert "future_directions" in interp
        assert len(result.output["key_findings"]) == 2
        assert len(result.artifacts) >= 1
        assert any("interpretation_results.json" in a for a in result.artifacts)

    @pytest.mark.asyncio
    async def test_execute_missing_interpretation_config(self, agent, tmp_path):
        """Missing interpretation config should yield warnings; stage still completes."""
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
        assert any("findings" in w.lower() or "empty" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_discussion_builder_failure(self, agent, sample_context):
        """Discussion-builder failure should add warning; stage still completes."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert "interpretation" in result.output
        assert any("unavailable" in w.lower() or "discussion" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_demo_mode(self, agent, sample_context, mock_discussion_builder_response):
        """DEMO mode should be reflected in output and warnings."""
        async def mock_call(service_name, method_name, params):
            if service_name == "discussion-builder" and method_name == "build":
                return mock_discussion_builder_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert result.output.get("demo_mode") is True
        assert any("DEMO" in w for w in result.warnings)


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_interpret_statistics_tool(self, agent):
        """Tool should return interpretation and clinical_context (or message)."""
        inp = json.dumps({"findings": [{"summary": "Effect size 0.5"}]})
        result = agent._interpret_statistics_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "interpretation" in data or "clinical_context" in data or "message" in data

    def test_compare_to_literature_tool(self, agent):
        """Tool should return comparisons or message."""
        inp = json.dumps({"findings": [{"summary": "Finding A"}], "key_points": ["point1"]})
        result = agent._compare_to_literature_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "comparisons" in data or "message" in data

    def test_identify_clinical_significance_tool(self, agent):
        """Tool should return clinical_significance or message."""
        inp = json.dumps({"findings": [{"summary": "p < 0.05"}], "effect_sizes": {}})
        result = agent._identify_clinical_significance_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "clinical_significance" in data or "message" in data

    def test_generate_implications_tool(self, agent):
        """Tool should return clinical/research implications or message."""
        inp = json.dumps({"findings": [{"summary": "Key result"}], "summary": "Brief summary"})
        result = agent._generate_implications_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "clinical" in data or "research" in data or "message" in data

    def test_identify_limitations_tool(self, agent):
        """Tool should return limitations and future_directions or message."""
        inp = json.dumps({"study_design": "RCT", "findings": []})
        result = agent._identify_limitations_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "limitations" in data or "future_directions" in data or "message" in data

    def test_interpret_statistics_tool_invalid_json(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._interpret_statistics_tool("not valid json")
        assert "Failed" in result or "error" in result.lower()


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(self, agent, sample_context, mock_discussion_builder_response):
        """Output should match required schema: interpretation block and backward-compat keys."""
        async def mock_call(service_name, method_name, params):
            if service_name == "discussion-builder" and method_name == "build":
                return mock_discussion_builder_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        out = result.output
        assert "interpretation" in out
        interp = out["interpretation"]
        assert isinstance(interp, dict)
        assert "key_findings" in interp
        assert "clinical_significance" in interp
        assert "comparison_to_literature" in interp
        assert "implications" in interp
        assert "limitations" in interp
        assert "future_directions" in interp
        assert isinstance(interp["implications"], dict)
        assert "clinical" in interp["implications"]
        assert "research" in interp["implications"]
        assert isinstance(interp["limitations"], list)
        assert isinstance(interp["future_directions"], list)
        assert "key_findings" in out
        assert "interpretations" in out
        assert "summary" in out


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

    def test_interpret_statistics_tool_invalid_json_returns_string(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._interpret_statistics_tool("not valid json")
        assert isinstance(result, str)
        assert "Failed" in result or "error" in result.lower()
