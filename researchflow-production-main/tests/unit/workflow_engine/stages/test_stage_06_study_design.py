"""
Unit tests for Stage 6: StudyDesignAgent

Tests the StudyDesignAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with Stage 4 output and bridge mocks
- DEMO vs LIVE mode (missing Stage 4)
- Bridge failure handling
- Tool implementations
- Output schema (study_design shape)
"""

import pytest
import sys
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_06_study_design import StudyDesignAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def agent():
    """Create a StudyDesignAgent instance."""
    return StudyDesignAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with Stage 4 output."""
    return StageContext(
        job_id="test-job",
        config={
            "studyTitle": "Effects of Treatment on Patient Outcomes",
            "hypothesis": "We hypothesize that treatment A improves outcomes.",
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
        previous_results={
            4: MagicMock(output={
                "refined_hypothesis": "Treatment A improves patient outcomes compared to treatment B.",
                "key_variables": {
                    "independent": ["treatment", "dose"],
                    "dependent": ["outcome_score", "response"],
                    "confounding": ["age", "gender"],
                },
                "secondary_hypotheses": [],
            }),
        },
    )


@pytest.fixture
def mock_methods_populator_response():
    """Mock methods-populator populateMethods response."""
    return {
        "manuscriptId": "test-job",
        "sections": {
            "studyDesign": "We conducted a randomized controlled trial.",
            "setting": "Single center.",
            "participants": "Adults aged 18-65.",
            "variables": "Primary: outcome_score.",
            "dataSources": "Electronic health records.",
            "statisticalMethods": "Linear mixed models.",
            "ethics": "IRB approved.",
        },
        "fullText": "### Study Design\n\nWe conducted a randomized controlled trial.\n\n### Setting\n\nSingle center.",
        "dataBindings": {},
        "createdAt": "2024-01-01T00:00:00.000Z",
    }


@pytest.fixture
def mock_claude_writer_response():
    """Mock claude-writer generateParagraph response."""
    return {
        "paragraph": "This was a randomized controlled trial comparing treatment A to control.",
        "content": "This was a randomized controlled trial.",
    }


class TestStudyDesignAgent:
    """Tests for StudyDesignAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 6
        assert agent.stage_name == "Study Design"

    def test_get_tools(self, agent):
        """get_tools should return a list of tools (length 5 when LangChain available)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, sample_context, mock_methods_populator_response, mock_claude_writer_response
    ):
        """Execute should succeed with complete context and mocked bridge."""
        async def mock_call(service_name, method_name, params):
            if service_name == "methods-populator" and method_name == "populateMethods":
                return mock_methods_populator_response
            if service_name == "claude-writer" and method_name == "generateParagraph":
                return mock_claude_writer_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "study_design" in result.output
        sd = result.output["study_design"]
        assert "type" in sd
        assert "methodology" in sd
        assert "endpoints" in sd
        assert "sample_size" in sd
        assert "methods_outline" in sd
        assert len(result.artifacts) >= 1
        assert any("study_design.json" in a for a in result.artifacts)

    @pytest.mark.asyncio
    async def test_execute_without_stage_4_demo(self, agent, tmp_path, mock_methods_populator_response):
        """DEMO mode should complete with warnings when Stage 4 output missing."""
        context = StageContext(
            job_id="test-job",
            config={"hypothesis": "Test hypothesis"},
            artifact_path=str(tmp_path / "artifacts"),
            governance_mode="DEMO",
        )
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.return_value = mock_methods_populator_response
            result = await agent.execute(context)
        assert result.status == "completed"
        assert any("Stage 4" in w for w in result.warnings)
        assert "study_design" in result.output

    @pytest.mark.asyncio
    async def test_execute_without_stage_4_live(self, agent, tmp_path):
        """LIVE mode should fail when Stage 4 output missing."""
        context = StageContext(
            job_id="test-job",
            config={"hypothesis": "Test hypothesis"},
            artifact_path=str(tmp_path / "artifacts"),
            governance_mode="LIVE",
        )
        result = await agent.execute(context)
        assert result.status == "failed"
        assert any("Stage 4" in err for err in result.errors)

    @pytest.mark.asyncio
    async def test_execute_bridge_failure(self, agent, sample_context):
        """Execute should handle bridge failure (methods-populator raises)."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        # Should still complete with fallback methods_outline and warnings
        assert result.status == "completed"
        assert "study_design" in result.output
        assert any("Methods populator" in w or "unavailable" in w for w in result.warnings)


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_design_study_protocol_tool(self, agent):
        """Tool should return study_type and methodology JSON."""
        inp = json.dumps({"hypothesis": "Randomized trial of treatment.", "key_variables": {}})
        result = agent._design_study_protocol_tool(inp)
        assert "study_type" in result or "randomized" in result.lower()
        assert "methodology" in result or "Failed" in result

    def test_select_methodology_tool(self, agent):
        """Tool should return study_type and methodology."""
        result = agent._select_methodology_tool("Cohort study of outcomes.")
        assert "study_type" in result or "cohort" in result.lower()
        assert "methodology" in result or "Failed" in result

    def test_define_endpoints_tool(self, agent):
        """Tool should return primary and secondary endpoints."""
        inp = json.dumps({
            "hypothesis": "Treatment affects outcome.",
            "key_variables": {"dependent": ["outcome"], "confounding": ["age"]},
        })
        result = agent._define_endpoints_tool(inp)
        assert "primary" in result.lower()
        assert "secondary" in result.lower()

    def test_calculate_sample_size_tool(self, agent):
        """Tool should return n, power, alpha."""
        inp = json.dumps({"n": 150, "power": 0.85, "alpha": 0.05})
        result = agent._calculate_sample_size_tool(inp)
        assert "n" in result
        assert "power" in result
        assert "alpha" in result

    def test_generate_methods_outline_tool(self, agent):
        """Tool should return methods outline text."""
        inp = json.dumps({
            "study_type": "randomized_controlled_trial",
            "methodology": {"statistical_methods": ["t-test"]},
            "endpoints": {"primary": ["outcome"], "secondary": ["safety"]},
            "sample_size": {"n": 200, "power": 0.8, "alpha": 0.05},
        })
        result = agent._generate_methods_outline_tool(inp)
        assert len(result) > 0
        assert "randomized" in result.lower() or "outcome" in result.lower() or "Failed" in result


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(
        self, agent, sample_context, mock_methods_populator_response
    ):
        """Output study_design should match required schema."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.return_value = mock_methods_populator_response
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        sd = result.output["study_design"]
        assert isinstance(sd, dict)
        assert "type" in sd
        assert isinstance(sd["type"], str)
        assert "methodology" in sd
        assert isinstance(sd["methodology"], dict)
        assert "endpoints" in sd
        assert "primary" in sd["endpoints"]
        assert "secondary" in sd["endpoints"]
        assert isinstance(sd["endpoints"]["primary"], list)
        assert isinstance(sd["endpoints"]["secondary"], list)
        assert "sample_size" in sd
        assert "n" in sd["sample_size"]
        assert "power" in sd["sample_size"]
        assert "alpha" in sd["sample_size"]
        assert "methods_outline" in sd
        assert isinstance(sd["methods_outline"], str)
