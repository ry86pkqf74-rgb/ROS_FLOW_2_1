"""
Unit tests for Stage 12: Manuscript Drafting Agent

Tests the ManuscriptDraftingAgent implementation:
- Data extraction with fallbacks
- Section generation via bridge
- Abstract generation
- DEMO vs LIVE mode validation
- Artifact generation
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_12_manuscript import ManuscriptDraftingAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def mock_manuscript_client():
    """Mock ManuscriptClient for testing."""
    with patch('src.workflow_engine.stages.stage_12_manuscript.ManuscriptClient') as mock_client_class:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_context():
    """Create a sample StageContext for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = StageContext(
            job_id="test-job-123",
            config={
                "study_title": "Test Study",
                "study_type": "observational",
                "hypothesis": "Test hypothesis",
                "methods": "Test methods",
                "results": "Test results",
            },
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tmpdir,
        )
        yield context


@pytest.fixture
def agent():
    """Create a ManuscriptDraftingAgent instance."""
    return ManuscriptDraftingAgent()


class TestManuscriptDraftingAgent:
    """Tests for ManuscriptDraftingAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 12
        assert agent.stage_name == "Manuscript Drafting"

    def test_get_tools(self, agent):
        """get_tools should return a list (can be empty)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a PromptTemplate."""
        template = agent.get_prompt_template()
        assert template is not None


class TestExtractManuscriptData:
    """Tests for _extract_manuscript_data method."""

    def test_extract_from_manuscript_config(self, agent):
        """Should extract data from manuscript config section."""
        context = StageContext(
            job_id="test",
            config={
                "manuscript": {
                    "study_title": "Config Title",
                    "study_type": "clinical_trial",
                    "hypothesis": "Config hypothesis",
                }
            },
            previous_results={},
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        data = agent._extract_manuscript_data(context)
        assert data["studyTitle"] == "Config Title"
        assert data["studyType"] == "clinical_trial"
        assert data["hypothesis"] == "Config hypothesis"

    def test_extract_from_root_config(self, agent):
        """Should fallback to root config if manuscript config missing."""
        context = StageContext(
            job_id="test",
            config={
                "study_title": "Root Title",
                "study_type": "prospective",
            },
            previous_results={},
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        data = agent._extract_manuscript_data(context)
        assert data["studyTitle"] == "Root Title"
        assert data["studyType"] == "prospective"

    def test_extract_from_previous_stages(self, agent):
        """Should extract data from previous stage outputs."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={
                1: MagicMock(output={"title": "Stage 1 Title"}),
                3: MagicMock(output={"protocol": {"hypothesis": "Stage 3 Hypothesis"}}),
            },
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        data = agent._extract_manuscript_data(context)
        assert data["studyTitle"] == "Stage 1 Title"
        assert data["hypothesis"] == "Stage 3 Hypothesis"

    def test_default_values(self, agent):
        """Should use default values when no data available."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={},
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        data = agent._extract_manuscript_data(context)
        assert data["studyTitle"] == "Research Study"
        assert data["studyType"] == "observational"
        assert "hypothesis" in data
        assert data["journalStyle"] == "academic"
        assert data["citationFormat"] == "numbered"

    def test_discussion_points_parsing(self, agent):
        """Should parse discussion points from string or list."""
        # Test string parsing
        context = StageContext(
            job_id="test",
            config={"discussion_points": "point1, point2, point3"},
            previous_results={},
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        data = agent._extract_manuscript_data(context)
        assert isinstance(data["discussionPoints"], list)
        assert len(data["discussionPoints"]) == 3

        # Test list parsing
        context.config = {"discussion_points": ["point1", "point2"]}
        data = agent._extract_manuscript_data(context)
        assert isinstance(data["discussionPoints"], list)
        assert len(data["discussionPoints"]) == 2


class TestExecute:
    """Tests for execute method."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, sample_context, mock_manuscript_client):
        """Execute should generate manuscript successfully."""
        # Mock paragraph generation
        mock_manuscript_client.generate_paragraph = AsyncMock(
            return_value={
                "paragraph": "Generated paragraph text",
                "metadata": {"wordCount": 100},
            }
        )

        # Mock abstract generation
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={
                "text": "Generated abstract",
                "sections": [],
                "wordCount": 50,
            }
        )

        result = await agent.execute(sample_context)

        assert result.status == "completed"
        assert result.stage_id == 12
        assert "manuscript" in result.output
        assert result.output["manuscript"]["title"] == "Test Study"
        assert len(result.artifacts) > 0

    @pytest.mark.asyncio
    async def test_execute_missing_fields_demo_mode(self, agent, mock_manuscript_client):
        """DEMO mode should allow missing fields with warnings."""
        context = StageContext(
            job_id="test",
            config={},  # No required fields
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tempfile.mkdtemp(),
        )

        mock_manuscript_client.generate_paragraph = AsyncMock(
            return_value={"paragraph": "Generated", "metadata": {"wordCount": 50}}
        )
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={"text": "Abstract", "sections": [], "wordCount": 30}
        )

        result = await agent.execute(context)

        assert result.status == "completed"
        assert len(result.warnings) > 0
        assert any("DEMO mode" in w for w in result.warnings)

    @pytest.mark.asyncio
    async def test_execute_missing_fields_live_mode(self, agent, mock_manuscript_client):
        """LIVE mode should fail if required fields missing."""
        context = StageContext(
            job_id="test",
            config={},  # No required fields
            previous_results={},
            governance_mode="LIVE",
            artifact_path=tempfile.mkdtemp(),
        )

        result = await agent.execute(context)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert any("Missing required fields" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_execute_section_generation_failure(self, agent, sample_context, mock_manuscript_client):
        """Should continue with other sections if one fails."""
        # Mock one section to fail, others to succeed
        call_count = 0

        async def mock_generate_paragraph(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First section (introduction) fails
                raise Exception("Service error")
            return {"paragraph": "Generated", "metadata": {"wordCount": 50}}

        mock_manuscript_client.generate_paragraph = mock_generate_paragraph
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={"text": "Abstract", "sections": [], "wordCount": 30}
        )

        result = await agent.execute(sample_context)

        # Should have errors but still complete other sections
        assert len(result.errors) > 0
        assert result.status == "completed"  # Other sections succeeded
        assert "manuscript" in result.output

    @pytest.mark.asyncio
    async def test_execute_abstract_generation_failure(self, agent, sample_context, mock_manuscript_client):
        """Should continue without abstract if abstract generation fails (non-fatal)."""
        mock_manuscript_client.generate_paragraph = AsyncMock(
            return_value={"paragraph": "Generated", "metadata": {"wordCount": 50}}
        )
        mock_manuscript_client.generate_abstract = AsyncMock(side_effect=Exception("Abstract error"))

        result = await agent.execute(sample_context)

        # Abstract failure should NOT cause stage to fail - should only be a warning
        assert result.status == "completed"
        # Should have warning but NOT error for abstract failure
        assert len(result.warnings) > 0
        assert any("abstract" in w.lower() for w in result.warnings)
        # Abstract failure should NOT be in errors list (Bug 2 fix)
        assert not any("abstract" in e.lower() for e in result.errors)
        assert result.output["manuscript"]["abstract"] == ""

    @pytest.mark.asyncio
    async def test_execute_artifact_generation(self, agent, sample_context, mock_manuscript_client):
        """Should generate JSON artifact file."""
        mock_manuscript_client.generate_paragraph = AsyncMock(
            return_value={"paragraph": "Generated", "metadata": {"wordCount": 50}}
        )
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={"text": "Abstract", "sections": [], "wordCount": 30}
        )

        result = await agent.execute(sample_context)

        assert len(result.artifacts) > 0
        artifact_path = result.artifacts[0]
        assert os.path.exists(artifact_path)
        assert artifact_path.endswith(".json")
        assert "manuscript" in artifact_path

        # Verify artifact content
        import json
        with open(artifact_path, "r") as f:
            artifact_data = json.load(f)
        assert "title" in artifact_data
        assert "sections" in artifact_data
        assert "abstract" in artifact_data


class TestExtractFromStages:
    """Tests for stage extraction helper methods."""

    def test_extract_title_from_stages(self, agent):
        """Should extract title from Stage 1 or Stage 3."""
        # Test Stage 1 extraction
        context = StageContext(
            job_id="test",
            config={},
            previous_results={
                1: MagicMock(output={"title": "Stage 1 Title"}),
            },
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        title = agent._extract_title_from_stages(context)
        assert title == "Stage 1 Title"

        # Test Stage 3 extraction
        context.previous_results = {
            3: MagicMock(output={"protocol": {"studyTitle": "Stage 3 Title"}}),
        }
        title = agent._extract_title_from_stages(context)
        assert title == "Stage 3 Title"

    def test_extract_hypothesis_from_stages(self, agent):
        """Should extract hypothesis from multiple stages."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={
                2: MagicMock(output={"research_question": "Stage 2 Question"}),
            },
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        hypothesis = agent._extract_hypothesis_from_stages(context)
        assert hypothesis == "Stage 2 Question"

    def test_extract_methods_from_stages(self, agent):
        """Should extract methods from Stage 6 or Stage 7."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={
                6: MagicMock(output={"methods": "Stage 6 Methods"}),
            },
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        methods = agent._extract_methods_from_stages(context)
        assert methods == "Stage 6 Methods"

    def test_extract_results_from_stages(self, agent):
        """Should extract results from Stage 6, 7, or 9."""
        context = StageContext(
            job_id="test",
            config={},
            previous_results={
                9: MagicMock(output={"interpretation": "Stage 9 Results"}),
            },
            governance_mode="DEMO",
            artifact_path="/tmp",
        )
        results = agent._extract_results_from_stages(context)
        assert results == "Stage 9 Results"


class TestSentinelValues:
    """Tests for sentinel value detection (Bug 1 fix)."""

    @pytest.mark.asyncio
    async def test_sentinel_hypothesis_detected(self, agent, mock_manuscript_client):
        """Should detect hypothesis field with sentinel value as missing."""
        from src.workflow_engine.stages.stage_12_manuscript import SENTINEL_VALUES

        context = StageContext(
            job_id="test",
            config={
                "study_title": "Valid Title",
                "hypothesis": SENTINEL_VALUES["hypothesis"],  # Sentinel value
            },
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tempfile.mkdtemp(),
        )

        mock_manuscript_client.generate_paragraph = AsyncMock(
            return_value={"paragraph": "Generated", "metadata": {"wordCount": 50}}
        )
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={"text": "Abstract", "sections": [], "wordCount": 30}
        )

        result = await agent.execute(context)

        # Should detect sentinel value and treat as missing in DEMO mode
        assert result.status == "completed"
        assert len(result.warnings) > 0
        assert any("hypothesis" in w.lower() or "missing" in w.lower() for w in result.warnings)

    @pytest.mark.asyncio
    async def test_sentinel_empty_string_detected(self, agent, mock_manuscript_client):
        """Should detect empty string hypothesis as missing."""
        context = StageContext(
            job_id="test",
            config={
                "study_title": "Valid Title",
                "hypothesis": "",  # Empty string
            },
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tempfile.mkdtemp(),
        )

        mock_manuscript_client.generate_paragraph = AsyncMock(
            return_value={"paragraph": "Generated", "metadata": {"wordCount": 50}}
        )
        mock_manuscript_client.generate_abstract = AsyncMock(
            return_value={"text": "Abstract", "sections": [], "wordCount": 30}
        )

        result = await agent.execute(context)

        # Should detect empty string and treat as missing
        assert result.status == "completed"
        assert len(result.warnings) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
