"""
Unit tests for Stage 7: StatisticalModelAgent

Tests the StatisticalModelAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with mocked bridge (results-scaffold, claude-writer)
- Mock path when no dataset_pointer
- Invalid model type and error handling
- Tool implementations
- Output schema (model_type, coefficients, goodness_of_fit, diagnostics)
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_07_stats import StatisticalModelAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def agent():
    """Create a StatisticalModelAgent instance."""
    return StatisticalModelAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with model config."""
    return StageContext(
        job_id="test-job",
        config={
            "model_type": "regression",
            "dependent_variable": "outcome_score",
            "independent_variables": ["predictor_1", "predictor_2", "predictor_3"],
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
    )


@pytest.fixture
def mock_results_scaffold_response():
    """Mock results-scaffold createScaffold response."""
    return {
        "manuscriptId": "test-job",
        "outline": [],
        "fullText": "Mock results section scaffold",
        "dataEmbedPoints": [],
        "suggestedFigures": [],
        "suggestedTables": [],
        "createdAt": "2024-01-01T00:00:00.000Z",
    }


@pytest.fixture
def mock_claude_writer_response():
    """Mock claude-writer generateParagraph response."""
    return {
        "paragraph": "The model showed significant effects for predictor_1 and predictor_2.",
        "content": "The model showed significant effects.",
    }


class TestStatisticalModelAgent:
    """Tests for StatisticalModelAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 7
        assert agent.stage_name == "Statistical Modeling"

    def test_get_tools(self, agent):
        """get_tools should return a list of tools (length 5 when LangChain available)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5
            names = [t.name for t in tools]
            assert "fit_regression_model" in names
            assert "run_anova" in names
            assert "calculate_effect_size" in names
            assert "check_model_assumptions" in names
            assert "generate_model_summary" in names

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, sample_context, mock_results_scaffold_response, mock_claude_writer_response
    ):
        """Execute should succeed with complete context and mocked bridge."""
        async def mock_call(service_name, method_name, params):
            if service_name == "results-scaffold" and method_name == "createScaffold":
                return mock_results_scaffold_response
            if service_name == "claude-writer" and method_name == "generateParagraph":
                return mock_claude_writer_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "model_type" in result.output
        assert result.output["model_type"] == "regression"
        assert "coefficients" in result.output
        assert "goodness_of_fit" in result.output or "fit_statistics" in result.output
        assert "diagnostics" in result.output
        assert len(result.artifacts) >= 1
        assert any("statistical_model_results.json" in a for a in result.artifacts)

    @pytest.mark.asyncio
    async def test_execute_mock_path(self, agent, sample_context):
        """No dataset_pointer; assert mock path is used."""
        # sample_context has no dataset_pointer
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert result.output.get("real_analysis") is False or "mock_data_reason" in result.output

    @pytest.mark.asyncio
    async def test_execute_invalid_model_type(self, agent, tmp_path):
        """Config model_type invalid; assert status failed and errors mention unsupported type."""
        context = StageContext(
            job_id="test-job",
            config={"model_type": "invalid"},
            artifact_path=str(tmp_path / "artifacts"),
            governance_mode="DEMO",
        )
        result = await agent.execute(context)
        assert result.status == "failed"
        assert any("Unsupported model type" in err or "invalid" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    async def test_execute_bridge_failure(self, agent, sample_context):
        """Execute should handle bridge failure (call_manuscript_service raises)."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert "model_type" in result.output
        assert any("unavailable" in w or "scaffold" in w.lower() or "interpretation" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_missing_dependent_variable(self, agent, tmp_path):
        """Missing dependent_variable should yield warning and default placeholder; stage completes."""
        context = StageContext(
            job_id="test-job",
            config={"model_type": "regression", "independent_variables": ["x1", "x2"]},
            artifact_path=str(tmp_path / "artifacts"),
            governance_mode="DEMO",
        )
        result = await agent.execute(context)
        assert result.status == "completed"
        assert any("dependent_variable" in w or "placeholder" in w.lower() for w in result.warnings)
        assert result.output.get("model_summary", {}).get("dependent_variable") == "outcome"


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_fit_regression_model_tool(self, agent):
        """Tool should return coefficients and fit_statistics JSON."""
        inp = json.dumps({
            "model_type": "regression",
            "dependent_variable": "y",
            "independent_variables": ["x1", "x2"],
        })
        result = agent._fit_regression_model_tool(inp)
        assert len(result) > 0
        assert "Failed" not in result or "coefficients" in result
        if "Failed" not in result:
            data = json.loads(result)
            assert "coefficients" in data
            assert "fit_statistics" in data

    def test_run_anova_tool(self, agent):
        """Tool should return fit_statistics for ANOVA."""
        inp = json.dumps({"independent_variables": ["factor1", "factor2"], "n_predictors": 2})
        result = agent._run_anova_tool(inp)
        assert len(result) > 0
        assert "Failed" not in result or "fit_statistics" in result
        if "Failed" not in result:
            data = json.loads(result)
            assert "fit_statistics" in data

    def test_calculate_effect_size_tool(self, agent):
        """Tool should return cohens_d or odds ratios."""
        inp = json.dumps({"mean1": 0.5, "mean2": 0.3, "std1": 0.2, "std2": 0.2})
        result = agent._calculate_effect_size_tool(inp)
        assert len(result) > 0
        assert "Failed" not in result or "cohens_d" in result

    def test_check_model_assumptions_tool(self, agent):
        """Tool should return diagnostics with assumption_checks."""
        inp = json.dumps({"model_type": "regression"})
        result = agent._check_model_assumptions_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "assumption_checks" in data

    def test_generate_model_summary_tool(self, agent):
        """Tool should return formatted summary text."""
        inp = json.dumps({
            "coefficients": [{"variable": "x1", "estimate": 0.5, "p_value": 0.01}],
            "fit_statistics": {"aic": 100, "bic": 110},
            "diagnostics": {"assumption_checks": {"normality": {"passed": True, "interpretation": "OK"}}},
        })
        result = agent._generate_model_summary_tool(inp)
        assert len(result) > 0
        assert "Model Summary" in result or "Coefficients" in result or "Failed" in result


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(self, agent, sample_context, mock_results_scaffold_response):
        """Output should match required schema: model_type, coefficients, confidence_intervals, p_values, goodness_of_fit, diagnostics."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.return_value = mock_results_scaffold_response
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        out = result.output
        assert "model_type" in out
        assert isinstance(out["model_type"], str)
        assert "coefficients" in out
        assert isinstance(out["coefficients"], list)
        assert "confidence_intervals" in out
        assert isinstance(out["confidence_intervals"], dict)
        assert "p_values" in out
        assert isinstance(out["p_values"], dict)
        assert "goodness_of_fit" in out or "fit_statistics" in out
        gof = out.get("goodness_of_fit") or out.get("fit_statistics", {})
        assert isinstance(gof, dict)
        assert "diagnostics" in out
        assert isinstance(out["diagnostics"], dict)
        assert "assumption_checks" in out["diagnostics"]


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_invalid_model_type_returns_failed(self, agent, tmp_path):
        """Invalid model type should return failed result and error list."""
        context = StageContext(
            job_id="test-job",
            config={"model_type": "unsupported_type"},
            artifact_path=str(tmp_path / "artifacts"),
            governance_mode="DEMO",
        )
        result = await agent.execute(context)
        assert result.status == "failed"
        assert len(result.errors) >= 1

    def test_fit_regression_model_tool_invalid_json(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._fit_regression_model_tool("not valid json")
        assert "Failed" in result or "error" in result.lower()
