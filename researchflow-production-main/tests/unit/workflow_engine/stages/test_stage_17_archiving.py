"""
Unit tests for Stage 17: ArchivingAgent

Tests the ArchivingAgent implementation:
- Initialization and stage identity
- get_tools (empty) and get_prompt_template
- execute with mocked bridge (runStageArchiving)
- Error handling on bridge failure
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "services" / "worker"))

from src.workflow_engine.stages.stage_17_archiving import ArchivingAgent
from src.workflow_engine.types import StageContext


@pytest.fixture
def agent():
    """Create an ArchivingAgent instance."""
    return ArchivingAgent({"bridge_url": "http://localhost:3001"})


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext."""
    return StageContext(
        job_id="test-job",
        config={"retention_policy": "standard"},
        artifact_path=str(tmp_path / "artifacts"),
        governance_mode="DEMO",
    )


class TestArchivingAgent:
    """Tests for ArchivingAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 17
        assert agent.stage_name == "Archiving"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = ArchivingAgent()
        assert a.stage_id == 17
        assert a.stage_name == "Archiving"

    def test_get_tools(self, agent):
        """get_tools should return an empty list."""
        tools = agent.get_tools()
        assert isinstance(tools, list)
        assert len(tools) == 0

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a template."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExecute:
    """Tests for execute() method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context):
        """Execute should succeed with mocked bridge response."""
        mock_response = {"ok": True, "archive_manifest": []}
        with patch.object(
            agent, "call_manuscript_service", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert result.output == mock_response

    @pytest.mark.asyncio
    async def test_execute_bridge_failure(self, agent, sample_context):
        """Bridge failure should return status failed and set errors."""
        with patch.object(
            agent, "call_manuscript_service", new_callable=AsyncMock
        ) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert "error" in result.output or "Bridge" in str(result.errors)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_completion_on_bridge_failure(self, agent, sample_context):
        """Bridge failure should not complete; status failed and errors present."""
        with patch.object(
            agent, "call_manuscript_service", new_callable=AsyncMock
        ) as mock_svc:
            mock_svc.side_effect = Exception("Bridge unavailable")
            result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert len(result.errors) >= 1
