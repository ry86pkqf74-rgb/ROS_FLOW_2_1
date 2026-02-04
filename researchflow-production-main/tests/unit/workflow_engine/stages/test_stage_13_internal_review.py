"""
Unit tests for Stage 13: InternalReviewAgent

Tests the InternalReviewAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with mocked bridge (peer-review, grammar-checker, readability)
- In-memory persona reviews and output shape
- Tool implementations
- Output schema (reviews, scores, improvement_suggestions, consensus_recommendations)
- Error handling
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_13_internal_review import InternalReviewAgent
from src.workflow_engine.types import StageContext


@pytest.fixture
def agent():
    """Create an InternalReviewAgent instance."""
    return InternalReviewAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with reviewer_personas and rubric."""
    return StageContext(
        job_id="test-job",
        config={
            "reviewer_personas": [
                {"id": "methodologist", "name": "Methodology Expert", "focus_areas": ["methodology"], "strictness": 0.8},
                {"id": "editor", "name": "Technical Editor", "focus_areas": ["clarity"], "strictness": 0.6},
            ],
            "rubric": {
                "methodology": {"weight": 0.3, "criteria": ["appropriate_methods", "reproducibility"]},
                "writing_quality": {"weight": 0.15, "criteria": ["grammar_and_style", "clarity"]},
            },
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
    )


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


@pytest.fixture
def mock_grammar_response():
    """Mock grammar-checker checkGrammar response."""
    return {
        "issues": [],
        "correctedText": "Sample corrected text.",
        "score": 92,
    }


@pytest.fixture
def mock_readability_response():
    """Mock readability calculateMetrics response."""
    return {
        "fleschKincaidGrade": 12.5,
        "fleschReadingEase": 45.0,
        "gunningFogIndex": 14.0,
        "averageSentenceLength": 18.0,
        "averageWordLength": 5.2,
        "complexWordPercentage": 25.0,
        "recommendation": "Text is appropriate for academic audience.",
    }


class TestInternalReviewAgent:
    """Tests for InternalReviewAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 13
        assert agent.stage_name == "Internal Review"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = InternalReviewAgent()
        assert a.stage_id == 13
        assert a.stage_name == "Internal Review"

    def test_get_tools(self, agent):
        """get_tools should return a list of five tools when LangChain available."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5
            names = [t.name for t in tools]
            assert "simulate_peer_review" in names
            assert "check_grammar_style" in names
            assert "analyze_readability" in names
            assert "generate_revision_suggestions" in names
            assert "score_manuscript_quality" in names

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        agent,
        sample_context,
        mock_peer_review_response,
        mock_grammar_response,
        mock_readability_response,
    ):
        """Execute should succeed with complete context and mocked bridge services."""
        async def mock_call(service_name, method_name, params):
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            if service_name == "grammar-checker" and method_name == "checkGrammar":
                return mock_grammar_response
            if service_name == "readability" and method_name == "calculateMetrics":
                return mock_readability_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "reviews" in result.output
        assert "scores" in result.output
        assert "improvement_suggestions" in result.output
        assert "consensus_recommendations" in result.output
        assert result.output.get("peer_review") == mock_peer_review_response
        assert result.output.get("grammar_check") == mock_grammar_response
        assert result.output.get("readability_metrics") == mock_readability_response
        assert len(result.output["reviews"]) == 2
        assert "overall" in result.output["scores"]
        assert "range" in result.output["scores"]
        assert "by_reviewer" in result.output["scores"]

    @pytest.mark.asyncio
    async def test_execute_missing_config(self, agent, tmp_path):
        """Missing reviewer_personas/rubric should yield defaults; stage still completes."""
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
        assert "reviews" in result.output
        assert len(result.output["reviews"]) >= 1

    @pytest.mark.asyncio
    async def test_execute_bridge_failure_adds_warnings(self, agent, sample_context):
        """Bridge failure should add warnings; stage still completes using in-memory flow."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert "reviews" in result.output
        assert len(result.output["reviews"]) == 2
        assert any("peer" in w.lower() or "grammar" in w.lower() or "readability" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_demo_mode(
        self,
        agent,
        sample_context,
        mock_peer_review_response,
        mock_grammar_response,
        mock_readability_response,
    ):
        """DEMO mode should be reflected in output and warnings."""
        async def mock_call(service_name, method_name, params):
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            if service_name == "grammar-checker" and method_name == "checkGrammar":
                return mock_grammar_response
            if service_name == "readability" and method_name == "calculateMetrics":
                return mock_readability_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert result.output.get("demo_mode") is True
        assert any("DEMO" in w for w in result.warnings)


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_simulate_peer_review_tool(self, agent):
        """Tool should return status and message or details."""
        inp = json.dumps({"manuscript": {"abstract": "Sample"}, "manuscriptId": "job-1"})
        result = agent._simulate_peer_review_tool(inp)
        assert len(result) > 0
        data = json.loads(result)
        assert "status" in data or "message" in data

    def test_check_grammar_style_tool(self, agent):
        """Tool should return status and message or details."""
        inp = json.dumps({"text": "Sample manuscript text for grammar check."})
        result = agent._check_grammar_style_tool(inp)
        assert len(result) > 0
        data = json.loads(result)
        assert "status" in data or "message" in data

    def test_analyze_readability_tool(self, agent):
        """Tool should return status and message or details."""
        inp = json.dumps({"text": "Sample manuscript text for readability."})
        result = agent._analyze_readability_tool(inp)
        assert len(result) > 0
        data = json.loads(result)
        assert "status" in data or "message" in data

    def test_generate_revision_suggestions_tool(self, agent):
        """Tool should return suggestions from reviews list."""
        reviews = [
            {
                "reviewer_id": "r1",
                "reviewer_name": "Reviewer 1",
                "overall_score": 7.0,
                "comments": [{"category": "methodology", "severity": "minor", "comment": "Improve methods."}],
                "recommendations": [],
            },
        ]
        inp = json.dumps({"reviews": reviews})
        result = agent._generate_revision_suggestions_tool(inp)
        assert len(result) > 0
        data = json.loads(result)
        assert "suggestions" in data or "status" in data

    def test_score_manuscript_quality_tool(self, agent):
        """Tool should return aggregate score from reviews list."""
        reviews = [
            {"reviewer_id": "r1", "overall_score": 7.5, "recommendations": ["Strengthen methods."]},
            {"reviewer_id": "r2", "overall_score": 8.0, "recommendations": ["Strengthen methods."]},
        ]
        inp = json.dumps({"reviews": reviews})
        result = agent._score_manuscript_quality_tool(inp)
        assert len(result) > 0
        data = json.loads(result)
        assert "average_score" in data or "status" in data
        if "average_score" in data:
            assert data["average_score"] == 7.75
            assert data["reviewer_count"] == 2

    def test_simulate_peer_review_tool_invalid_json(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._simulate_peer_review_tool("not valid json")
        assert "Failed" in result or "error" in result.lower()


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(
        self,
        agent,
        sample_context,
        mock_peer_review_response,
        mock_grammar_response,
        mock_readability_response,
    ):
        """Output should match required schema: reviews, scores, improvement_suggestions, consensus_recommendations."""
        async def mock_call(service_name, method_name, params):
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            if service_name == "grammar-checker" and method_name == "checkGrammar":
                return mock_grammar_response
            if service_name == "readability" and method_name == "calculateMetrics":
                return mock_readability_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        out = result.output
        assert "reviews" in out
        assert isinstance(out["reviews"], list)
        assert "scores" in out
        assert isinstance(out["scores"], dict)
        assert "overall" in out["scores"]
        assert "range" in out["scores"]
        assert "by_reviewer" in out["scores"]
        assert "improvement_suggestions" in out
        assert isinstance(out["improvement_suggestions"], list)
        assert "consensus_recommendations" in out
        assert isinstance(out["consensus_recommendations"], list)


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

    def test_simulate_peer_review_tool_invalid_json_returns_string(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._simulate_peer_review_tool("not valid json")
        assert isinstance(result, str)
        assert "Failed" in result or "error" in result.lower()
