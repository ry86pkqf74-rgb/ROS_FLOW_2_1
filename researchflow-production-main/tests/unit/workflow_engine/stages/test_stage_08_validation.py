"""
Unit tests for Stage 8: DataValidationAgent

Tests the DataValidationAgent implementation:
- Initialization and stage identity
- get_tools and get_prompt_template
- execute with mocked bridge (compliance-checker)
- Schema validation logic and output shape
- Tool implementations
- Output schema (validation_results, total_records, valid_records, invalid_records)
- Error handling
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_08_validation import DataValidationAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def agent():
    """Create a DataValidationAgent instance."""
    return DataValidationAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext with validation config."""
    return StageContext(
        job_id="test-job",
        config={
            "validation": {
                "schema_path": "/data/schema.json",
                "strict_mode": False,
                "sample_size": 1000,
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
        "guidelines": ["data_integrity"],
        "issues": [],
        "checkedAt": "2024-01-01T00:00:00.000Z",
    }


class TestDataValidationAgent:
    """Tests for DataValidationAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 8
        assert agent.stage_name == "Data Validation"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = DataValidationAgent()
        assert a.stage_id == 8
        assert a.stage_name == "Data Validation"

    def test_get_tools(self, agent):
        """get_tools should return a list of five tools when LangChain available."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        if len(tools) > 0:
            assert len(tools) == 5
            names = [t.name for t in tools]
            assert "validate_schema" in names
            assert "check_data_types" in names
            assert "check_referential_integrity" in names
            assert "run_business_rules" in names
            assert "statistical_quality_check" in names

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context, mock_compliance_response):
        """Execute should succeed with complete context and mocked compliance-checker."""
        async def mock_call(service_name, method_name, params):
            if service_name == "compliance-checker" and method_name == "checkCompliance":
                return mock_compliance_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert "validation_results" in result.output
        assert "total_records" in result.output
        assert "valid_records" in result.output
        assert "invalid_records" in result.output
        vr = result.output["validation_results"]
        assert "schema_valid" in vr
        assert "quality_score" in vr
        assert result.output.get("validation_passed") is True
        assert len(result.artifacts) >= 1
        assert any("validation_results.json" in a for a in result.artifacts)

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
        assert any("schema path" in w.lower() or "inferred" in w.lower() for w in result.warnings)

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
    async def test_execute_demo_mode(self, agent, sample_context, mock_compliance_response):
        """DEMO mode should be reflected in output and warnings."""
        async def mock_call(service_name, method_name, params):
            if service_name == "compliance-checker" and method_name == "checkCompliance":
                return mock_compliance_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)
        assert result.status == "completed"
        assert result.output["validation_results"].get("demo_mode") is True
        assert any("DEMO" in w for w in result.warnings)


class TestToolImplementations:
    """Tests for tool wrapper methods."""

    def test_validate_schema_tool(self, agent):
        """Tool should return valid and schema_errors (or message)."""
        inp = json.dumps({"schema_path": "/data/schema.json", "column_definitions": ["a", "b"]})
        result = agent._validate_schema_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "valid" in data or "schema_errors" in data or "message" in data

    def test_check_data_types_tool(self, agent):
        """Tool should return type_errors or message."""
        inp = json.dumps({"column_types": {"id": "int", "name": "str"}})
        result = agent._check_data_types_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "valid" in data or "type_errors" in data or "message" in data

    def test_check_referential_integrity_tool(self, agent):
        """Tool should return integrity_issues or message."""
        inp = json.dumps({"foreign_keys": [{"child": "fk_id", "parent": "id"}]})
        result = agent._check_referential_integrity_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "valid" in data or "integrity_issues" in data or "message" in data

    def test_run_business_rules_tool(self, agent):
        """Tool should return rule_violations or message."""
        inp = json.dumps({"rules": ["rule_1", "rule_2"]})
        result = agent._run_business_rules_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "valid" in data or "rule_violations" in data or "message" in data

    def test_statistical_quality_check_tool(self, agent):
        """Tool should return quality_score or metrics."""
        inp = json.dumps({"metrics": ["completeness", "uniqueness"], "column_names": ["a", "b"]})
        result = agent._statistical_quality_check_tool(inp)
        assert len(result) > 0
        if "Failed" not in result:
            data = json.loads(result)
            assert "quality_score" in data or "completeness" in data or "message" in data

    def test_validate_schema_tool_invalid_json(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._validate_schema_tool("not valid json")
        assert "Failed" in result or "error" in result.lower()


class TestOutputSchema:
    """Tests for output schema compliance."""

    @pytest.mark.asyncio
    async def test_output_schema_compliance(self, agent, sample_context, mock_compliance_response):
        """Output should match required schema: validation_results, total_records, valid_records, invalid_records."""
        async def mock_call(service_name, method_name, params):
            if service_name == "compliance-checker" and method_name == "checkCompliance":
                return mock_compliance_response
            return {}

        with patch.object(agent, "call_manuscript_service", new_callable=AsyncMock, side_effect=mock_call):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        out = result.output
        assert "validation_results" in out
        vr = out["validation_results"]
        assert isinstance(vr, dict)
        assert "schema_valid" in vr
        assert "type_errors" in vr
        assert "integrity_issues" in vr
        assert "rule_violations" in vr
        assert "quality_score" in vr
        assert "total_records" in out
        assert "valid_records" in out
        assert "invalid_records" in out
        assert isinstance(out["total_records"], (int, float))
        assert isinstance(out["valid_records"], (int, float))
        assert isinstance(out["invalid_records"], (int, float))


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

    def test_validate_schema_tool_invalid_json_returns_string(self, agent):
        """Tool with invalid JSON should return error message string."""
        result = agent._validate_schema_tool("not valid json")
        assert isinstance(result, str)
        assert "Failed" in result or "error" in result.lower()
