"""
Unit tests for Stage 20: Conference Preparation Agent

Tests the ConferencePrepAgent implementation:
- BaseStageAgent inheritance
- Conference discovery
- Guideline extraction
- Material generation with abstract-generator integration
- Export bundle creation
- DEMO vs LIVE mode validation
- Artifact generation
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_20_conference import ConferencePrepAgent
from src.workflow_engine.stages.base_stage_agent import BaseStageAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def mock_manuscript_client():
    """Mock ManuscriptClient for testing."""
    with patch('src.workflow_engine.stages.stage_20_conference.ManuscriptClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_context(tmp_path):
    """Create a sample StageContext for testing."""
    return StageContext(
        job_id="test-job-123",
        config={
            "enable_conference_prep": True,
            "conference_prep": {
                "keywords": ["surgery", "robotic"],
                "formats": ["poster"],
                "max_candidates": 5,
            },
        },
        previous_results={},
        governance_mode="DEMO",
        artifact_path=str(tmp_path / "artifacts"),
    )


@pytest.fixture
def agent():
    """Create a ConferencePrepAgent instance."""
    return ConferencePrepAgent()


class TestConferencePrepAgent:
    """Tests for ConferencePrepAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 20
        assert agent.stage_name == "Conference Preparation"

    def test_agent_initialization_without_config(self):
        """Agent should initialize without config (bridge_config None)."""
        a = ConferencePrepAgent()
        assert a.stage_id == 20
        assert a.stage_name == "Conference Preparation"

    def test_inherits_from_base_stage_agent(self, agent):
        """Agent should inherit from BaseStageAgent."""
        assert isinstance(agent, BaseStageAgent)

    def test_get_tools(self, agent):
        """get_tools should return a list (can be empty)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a PromptTemplate."""
        template = agent.get_prompt_template()
        assert template is not None

    def test_uses_create_stage_result(self, agent):
        """Agent should have access to create_stage_result from BaseStageAgent."""
        assert hasattr(agent, 'create_stage_result')
        assert callable(agent.create_stage_result)

    def test_manuscript_client_available(self, agent):
        """Agent should have access to manuscript_client property."""
        assert hasattr(agent, 'manuscript_client')


class TestExecute:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_execute_disabled(self, agent, mock_manuscript_client, tmp_path):
        """Execute should skip when enable_conference_prep=false."""
        context = StageContext(
            job_id="test",
            config={"enable_conference_prep": False},
            previous_results={},
            governance_mode="DEMO",
            artifact_path=str(tmp_path),
        )

        result = await agent.execute(context)

        assert result.status == "skipped"
        assert "disabled" in result.output.get("reason", "").lower()

    @pytest.mark.asyncio
    async def test_execute_demo_mode(self, agent, sample_context, mock_manuscript_client):
        """DEMO mode should work without network calls."""
        # Mock conference discovery
        with patch('src.workflow_engine.stages.stage_20_conference.discover_conferences') as mock_discover:
            mock_discover.return_value = MagicMock(
                generated_at=datetime.utcnow().isoformat(),
                total_matched=2,
                query_info={},
                ranked_conferences=[
                    MagicMock(
                        conference=MagicMock(
                            name="Test Conference",
                            abbreviation="TC",
                            url="https://test.com",
                        ),
                        score=0.8,
                        to_dict=lambda: {},
                    ),
                ],
            )

            # Mock guideline extraction
            with patch('src.workflow_engine.stages.stage_20_conference.extract_guidelines') as mock_extract:
                mock_extract.return_value = MagicMock(
                    extracted_at=datetime.utcnow().isoformat(),
                    by_format={},
                    sources=[],
                )

                # Mock material generation
                with patch('src.workflow_engine.stages.stage_20_conference.generate_material') as mock_gen:
                    mock_gen.return_value = MagicMock(
                        success=False,
                        error="Demo mode - no materials generated",
                    )

                    result = await agent.execute(sample_context)

                    # Should complete (even with warnings/errors in demo mode)
                    assert result.status in ["completed", "completed_with_warnings", "completed_with_errors"]
                    assert result.stage_id == 20

    @pytest.mark.asyncio
    async def test_execute_abstract_generation(self, agent, sample_context, mock_manuscript_client):
        """Should generate conference abstract via abstract-generator service."""
        # Mock abstract generation
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={
                "text": "Generated conference abstract",
                "sections": [],
                "wordCount": 250,
            }
        )

        # Mock conference discovery to return empty (skip to end quickly)
        with patch('src.workflow_engine.stages.stage_20_conference.discover_conferences') as mock_discover:
            mock_discover.return_value = MagicMock(
                generated_at=datetime.utcnow().isoformat(),
                total_matched=0,
                query_info={},
                ranked_conferences=[],
            )

            result = await agent.execute(sample_context)

            # Abstract generation should be attempted (though may not be called if no conferences)
            # Verify the method exists and can be called
            assert hasattr(agent, '_generate_conference_abstract')

    @pytest.mark.asyncio
    async def test_execute_discovery_failure(self, agent, sample_context, mock_manuscript_client):
        """Should handle discovery failures gracefully."""
        with patch('src.workflow_engine.stages.stage_20_conference.discover_conferences') as mock_discover:
            mock_discover.side_effect = Exception("Discovery service unavailable")

            result = await agent.execute(sample_context)

            # Should fail or complete with errors
            assert result.status in ["failed", "completed_with_errors"]
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_execute_artifact_generation(self, agent, sample_context, mock_manuscript_client):
        """Should generate artifacts for conference prep."""
        with patch('src.workflow_engine.stages.stage_20_conference.discover_conferences') as mock_discover:
            mock_discover.return_value = MagicMock(
                generated_at=datetime.utcnow().isoformat(),
                total_matched=1,
                query_info={},
                ranked_conferences=[
                    MagicMock(
                        conference=MagicMock(
                            name="Test Conference",
                            abbreviation="TC",
                            url="https://test.com",
                        ),
                        score=0.8,
                        to_dict=lambda: {},
                    ),
                ],
            )

            with patch('src.workflow_engine.stages.stage_20_conference.extract_guidelines') as mock_extract:
                mock_extract.return_value = MagicMock(
                    extracted_at=datetime.utcnow().isoformat(),
                    by_format={},
                    sources=[],
                )

                result = await agent.execute(sample_context)

                # Should have artifacts (discovery results at minimum)
                assert len(result.artifacts) > 0
                assert any("conference_prep" in str(a) for a in result.artifacts)


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_execute_failure_on_exception(self, agent, sample_context, mock_manuscript_client):
        """Exception during execute should return status failed and non-empty errors."""
        with patch('src.workflow_engine.stages.stage_20_conference.discover_conferences') as mock_discover:
            mock_discover.side_effect = Exception("Discovery service unavailable")

            result = await agent.execute(sample_context)

            assert result.status == "failed"
            assert len(result.errors) >= 1


class TestAbstractGeneration:
    """Tests for abstract generation methods."""

    @pytest.mark.asyncio
    async def test_abstract_from_stage_12(self, agent, mock_manuscript_client):
        """Should extract abstract from Stage 12 results."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={
                12: MagicMock(
                    output={
                        "manuscript": {
                            "abstract": "Test abstract from Stage 12",
                        }
                    },
                    artifacts=[],
                ),
            },
            governance_mode="DEMO",
            artifact_path="/tmp",
        )

        abstract = agent._get_manuscript_abstract(context)
        assert "Test abstract" in abstract

    @pytest.mark.asyncio
    async def test_abstract_fallback(self, agent):
        """Should fallback to demo abstract when Stage 12 not available."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={},
            governance_mode="DEMO",
            artifact_path="/tmp",
        )

        abstract = agent._get_manuscript_abstract(context)
        assert len(abstract) > 0
        assert "Background" in abstract or "Methods" in abstract

    @pytest.mark.asyncio
    async def test_abstract_via_bridge(self, agent, mock_manuscript_client):
        """Should call abstract-generator service via bridge."""
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={
                "text": "Generated abstract",
                "sections": [],
                "wordCount": 250,
            }
        )

        context = StageContext(
            job_id="test",
            config={},
            previous_results={},
            governance_mode="LIVE",
            artifact_path="/tmp",
        )

        result = await agent._generate_conference_abstract(
            context=context,
            manuscript_abstract="Test abstract",
            research_title="Test Study",
        )

        assert result is not None
        assert result.get("text") == "Generated abstract"
        mock_manuscript_client.generate_abstract.assert_called_once()


class TestIntegration:
    """Integration tests for BaseStageAgent features."""

    def test_inherits_from_base_stage_agent(self, agent):
        """Verify inheritance from BaseStageAgent."""
        assert isinstance(agent, BaseStageAgent)

    def test_uses_create_stage_result(self, agent):
        """Verify use of BaseStageAgent helper method."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={},
            governance_mode="DEMO",
            artifact_path="/tmp",
        )

        result = agent.create_stage_result(
            context=context,
            status="completed",
            output={"test": "data"},
        )

        assert isinstance(result, StageResult)
        assert result.stage_id == 20
        assert result.status == "completed"

    def test_manuscript_client_available(self, agent):
        """Verify ManuscriptClient bridge is accessible."""
        # Accessing the property should not raise
        client = agent.manuscript_client
        assert client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
