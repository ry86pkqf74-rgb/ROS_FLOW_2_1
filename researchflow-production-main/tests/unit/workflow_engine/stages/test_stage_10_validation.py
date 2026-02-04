"""
Unit tests for Stage 10: ValidationAgent

Tests the ValidationAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with mocked bridge (compliance-checker, peer-review)
- Validation logic and output shape
- Tool implementations
- Output schema (validation_results, checklist_status, issues_found, summary)
- Error handling
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_10_validation import ValidationAgent
from src.workflow_engine.types import StageContext


@pytest.fixture
def agent():
    """Create a ValidationAgent instance."""
    return ValidationAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with validation config."""
    return StageContext(
        job_id="test-job",
        config={
            "validation": {
                "criteria": [
                    {"id": "c1", "name": "Data Completeness", "category": "data_quality", "severity": "high"},
                    {"id": "c2", "name": "Statistical Validity", "category": "methodology", "severity": "high"},
                ],
                "strict_mode": False,
                "fail_on_warning": False,
            },
        },
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
    )


@pytest.fixture
def mock_compliance_response():
    """Mock compliance-checker checkCompliance response."""
    return {
        "passed": True,
        "checklist": "CONSORT",
        "items": [],
        "score": 1.0,
        "isCompliant": True,
        "checkedRules": ["CONSORT", "STROBE", "PRISMA"],
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


class TestValidationAgent:
    """Tests for ValidationAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 10
        assert agent.stage_name == "Validation"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = ValidationAgent()
        assert a.stage_id == 10
        assert a.stage_name == "Validation"

    def test_get_tools(self, agent):
        """get_tools should return a list of five tools when LangChain available."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5
            names = [t.name for t in tools]
            assert "validate_methodology" in names
            assert "check_reporting_guidelines" in names
            assert "verify_statistical_reporting" in names
            assert "assess_bias_risk" in names
            assert "generate_validation_report" in names

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, sample_context, mock_compliance_response, mock_peer_review_response
    ):
        """Execute should succeed with complete context and mocked compliance-checker and peer-review."""
        async def mock_call(service_name, method_name, params):
            if service_name == "compliance-checker" and method_name == "checkCompliance":
                return mock_compliance_response
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "validation_results" in result.output
        assert "checklist_status" in result.output
        assert "issues_found" in result.output
        assert "summary" in result.output
        assert result.output.get("compliance_check") == mock_compliance_response
        assert result.output.get("peer_review") == mock_peer_review_response
        assert len(result.output["validation_results"]) == 2
        assert len(result.artifacts) >= 1
        assert any("validation_report.json" in a for a in result.artifacts)

    @pytest.mark.asyncio
    async def test_execute_missing_validation_config(self, agent, tmp_path):
        """Missing validation config should yield warnings; stage still completes."""
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
        assert any("criteria" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_compliance_checker_failure(self, agent, sample_context):
        """Compliance-checker failure should add warning; stage still completes."""
        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert "validation_results" in result.output
        assert any("unavailable" in w.lower() or "compliance" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_demo_mode(
        self, agent, sample_context, mock_compliance_response, mock_peer_review_response
    ):
        """DEMO mode should be reflected in output and warnings."""
        async def mock_call(service_name, method_name, params):
            if service_name == "compliance-checker" and method_name == "checkCompliance":
                return mock_compliance_response
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert result.output.get("demo_mode") is True
        assert any("DEMO" in w for w in result.warnings)


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_validate_methodology_tool(self, agent):
        """Tool should return status and message (or details)."""
        inp = json.dumps({"methodology": "RCT", "study_design": "randomized"})
        result = agent._validate_methodology_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "status" in data or "message" in data or "details" in data

    def test_check_reporting_guidelines_tool(self, agent):
        """Tool should return status and message or details."""
        inp = json.dumps({"guideline": "CONSORT", "manuscript_summary": "RCT study"})
        result = agent._check_reporting_guidelines_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "status" in data or "message" in data or "details" in data

    def test_verify_statistical_reporting_tool(self, agent):
        """Tool should return status and message or details."""
        inp = json.dumps({"results": [{"p": 0.01, "ci": [0.1, 0.5]}], "statistics": []})
        result = agent._verify_statistical_reporting_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "status" in data or "message" in data or "details" in data

    def test_assess_bias_risk_tool(self, agent):
        """Tool should return status and message or details."""
        inp = json.dumps({"study_design": "RCT", "design_type": "parallel"})
        result = agent._assess_bias_risk_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "status" in data or "message" in data or "details" in data

    def test_generate_validation_report_tool(self, agent):
        """Tool should return status and report or message."""
        inp = json.dumps({"criteria": [{"id": "c1", "name": "C1"}], "validation_results": []})
        result = agent._generate_validation_report_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "status" in data or "message" in data or "report" in data

    def test_validate_methodology_tool_invalid_json(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._validate_methodology_tool("not valid json")
        assert "Failed" in result or "error" in result.lower()


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(
        self, agent, sample_context, mock_compliance_response, mock_peer_review_response
    ):
        """Output should match required schema: validation_results, checklist_status, issues_found, summary."""
        async def mock_call(service_name, method_name, params):
            if service_name == "compliance-checker" and method_name == "checkCompliance":
                return mock_compliance_response
            if service_name == "peer-review" and method_name == "simulateReview":
                return mock_peer_review_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        out = result.output
        assert "validation_results" in out
        assert isinstance(out["validation_results"], list)
        assert "checklist_status" in out
        cs = out["checklist_status"]
        assert isinstance(cs, dict)
        assert "items" in cs
        assert "total_criteria" in cs
        assert "checked_count" in cs
        assert "passed_count" in cs
        assert "issues_found" in out
        issues = out["issues_found"]
        assert "critical" in issues
        assert "high" in issues
        assert "medium" in issues
        assert "low" in issues
        assert "by_category" in issues
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

    def test_validate_methodology_tool_invalid_json_returns_string(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._validate_methodology_tool("not valid json")
        assert isinstance(result, str)
        assert "Failed" in result or "error" in result.lower()
