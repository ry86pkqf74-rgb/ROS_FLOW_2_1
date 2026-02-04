"""
Unit tests for Stage 03: IRB Drafting Agent

Tests the IRBDraftingAgent implementation:
- IRB data extraction from multiple config sources
- Stage 1 PICO elements integration
- Protocol generation via ManuscriptClient
- Study type normalization
- DEMO vs LIVE mode handling
- Required field validation
- Artifact generation
- Error handling scenarios
"""

import pytest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_03_irb import IRBDraftingAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def sample_context():
    """Create a sample StageContext for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = StageContext(
            job_id="test-job-123",
            config={},
            previous_results={},
            governance_mode="DEMO",
            artifact_path=tmpdir,
        )
        yield context


@pytest.fixture
def agent():
    """Create an IRBDraftingAgent instance."""
    return IRBDraftingAgent()


@pytest.fixture
def complete_irb_config():
    """Complete IRB configuration for testing."""
    return {
        "irb": {
            "study_title": "Impact of Novel Treatment on Patient Outcomes",
            "principal_investigator": "Dr. Jane Smith",
            "study_type": "retrospective",
            "hypothesis": "Novel treatment improves patient outcomes compared to standard care",
            "population": "Adult patients with chronic condition",
            "data_source": "Electronic health records from 2020-2023",
            "variables": ["age", "treatment_type", "outcome_score", "follow_up_time"],
            "analysis_approach": "Propensity score matching and regression analysis",
            "institution": "Academic Medical Center",
            "expected_duration": "12 months",
            "risks": ["Minimal risk - retrospective chart review"],
            "benefits": ["Potential improvement in treatment protocols"]
        }
    }


@pytest.fixture
def minimal_irb_config():
    """Minimal IRB configuration for testing fallbacks."""
    return {
        "study_title": "Research Study",
        "principal_investigator": "Dr. John Doe",
        "hypothesis": "Test hypothesis"
    }


@pytest.fixture
def stage1_pico_output():
    """Sample Stage 1 output with PICO elements."""
    return {
        "pico_elements": {
            "population": "Adults aged 18-65 with diabetes",
            "intervention": "Continuous glucose monitoring",
            "comparator": "Standard glucose monitoring",
            "outcomes": ["HbA1c reduction", "Quality of life scores", "Hypoglycemic episodes"]
        },
        "primary_hypothesis": "CGM improves glycemic control compared to standard monitoring",
        "hypotheses": {
            "primary": "CGM reduces HbA1c by 0.5% compared to standard care",
            "secondary": "CGM improves quality of life scores"
        }
    }


@pytest.fixture
def mock_protocol_response():
    """Mock response from IRB protocol generation service."""
    return {
        "protocolNumber": "IRB-2024-001",
        "generatedAt": "2024-01-15T10:30:00Z",
        "protocol": {
            "title": "Impact of Novel Treatment on Patient Outcomes",
            "principalInvestigator": "Dr. Jane Smith",
            "studyType": "retrospective",
            "sections": {
                "background": "Research background...",
                "objectives": "Study objectives...",
                "methods": "Study methodology...",
                "risks": "Risk assessment...",
                "benefits": "Potential benefits..."
            }
        },
        "consentForm": {
            "template": "standard_retrospective",
            "sections": ["purpose", "procedures", "risks", "benefits"]
        },
        "attachments": {
            "dataManagementPlan": "Data will be stored securely...",
            "riskBenefitAssessment": "Minimal risk study..."
        }
    }


class TestIRBDraftingAgent:
    """Tests for IRBDraftingAgent class."""

    def test_agent_initialization(self, agent):
        """Agent should initialize with correct stage ID and name."""
        assert agent.stage_id == 3
        assert agent.stage_name == "IRB Drafting"

    def test_get_tools(self, agent):
        """get_tools should return a list (can be empty)."""
        tools = agent.get_tools()
        assert isinstance(tools, list)

    def test_get_prompt_template(self, agent):
        """get_prompt_template should return a PromptTemplate."""
        template = agent.get_prompt_template()
        assert template is not None


class TestIRBDataExtraction:
    """Tests for _extract_irb_data method."""

    def test_extract_from_complete_config(self, agent, sample_context, complete_irb_config):
        """Should extract data from complete IRB config."""
        sample_context.config = complete_irb_config
        irb_data = agent._extract_irb_data(sample_context)

        assert irb_data["studyTitle"] == "Impact of Novel Treatment on Patient Outcomes"
        assert irb_data["principalInvestigator"] == "Dr. Jane Smith"
        assert irb_data["studyType"] == "retrospective"
        assert irb_data["hypothesis"] == "Novel treatment improves patient outcomes compared to standard care"
        assert irb_data["population"] == "Adult patients with chronic condition"
        assert irb_data["dataSource"] == "Electronic health records from 2020-2023"
        assert irb_data["variables"] == ["age", "treatment_type", "outcome_score", "follow_up_time"]
        assert irb_data["analysisApproach"] == "Propensity score matching and regression analysis"
        assert irb_data["institution"] == "Academic Medical Center"
        assert irb_data["expectedDuration"] == "12 months"
        assert irb_data["risks"] == ["Minimal risk - retrospective chart review"]
        assert irb_data["benefits"] == ["Potential improvement in treatment protocols"]

    def test_extract_with_root_level_fallbacks(self, agent, sample_context, minimal_irb_config):
        """Should fall back to root-level config when IRB section missing."""
        sample_context.config = minimal_irb_config
        irb_data = agent._extract_irb_data(sample_context)

        assert irb_data["studyTitle"] == "Research Study"
        assert irb_data["principalInvestigator"] == "Dr. John Doe"
        assert irb_data["hypothesis"] == "Test hypothesis"

    def test_extract_with_stage1_pico_integration(self, agent, sample_context, stage1_pico_output):
        """Should integrate Stage 1 PICO elements for variables and population."""
        sample_context.previous_results = {
            1: type('MockResult', (), {
                'output': stage1_pico_output
            })()
        }
        
        irb_data = agent._extract_irb_data(sample_context)

        # Should get PICO outcomes as variables
        assert "HbA1c reduction" in irb_data["variables"]
        assert "Quality of life scores" in irb_data["variables"]
        
        # Should get Stage 1 hypothesis
        assert "CGM improves glycemic control" in irb_data["hypothesis"]

    def test_extract_with_cumulative_data(self, agent, sample_context, stage1_pico_output):
        """Should extract from prior_stage_outputs in LIVE mode."""
        sample_context.prior_stage_outputs = {
            1: stage1_pico_output
        }
        
        irb_data = agent._extract_irb_data(sample_context)

        # Should get population from PICO
        assert irb_data["population"] == "Adults aged 18-65 with diabetes"

    def test_study_type_normalization(self, agent, sample_context):
        """Should normalize study type variations."""
        test_cases = [
            ("retrospective", "retrospective"),
            ("prospective", "prospective"), 
            ("clinical_trial", "clinical_trial"),
            ("clinical trial", "clinical_trial"),
            ("trial", "clinical_trial"),
            ("randomized", "retrospective"),  # fallback
        ]

        for input_type, expected in test_cases:
            sample_context.config = {
                "irb": {"study_type": input_type}
            }
            irb_data = agent._extract_irb_data(sample_context)
            assert irb_data["studyType"] == expected

    def test_variables_list_conversion(self, agent, sample_context):
        """Should convert string variables to list."""
        sample_context.config = {
            "irb": {"variables": "age, gender, treatment, outcome"}
        }
        irb_data = agent._extract_irb_data(sample_context)
        
        expected_vars = ["age", "gender", "treatment", "outcome"]
        assert irb_data["variables"] == expected_vars

    def test_risks_benefits_list_conversion(self, agent, sample_context):
        """Should convert string risks/benefits to lists."""
        sample_context.config = {
            "irb": {
                "risks": "minimal risk, data breach",
                "benefits": "improved care, research contribution"
            }
        }
        irb_data = agent._extract_irb_data(sample_context)
        
        assert irb_data["risks"] == ["minimal risk", "data breach"]
        assert irb_data["benefits"] == ["improved care", "research contribution"]


class TestStageIntegration:
    """Tests for integration with previous stages."""

    def test_extract_hypothesis_from_stage1(self, agent, sample_context, stage1_pico_output):
        """Should extract hypothesis from Stage 1 output."""
        sample_context.previous_results = {
            1: type('MockResult', (), {
                'output': stage1_pico_output
            })()
        }
        
        hypothesis = agent._extract_hypothesis_from_stages(sample_context)
        assert "CGM improves glycemic control" in hypothesis

    def test_extract_hypothesis_from_prior_outputs(self, agent, sample_context, stage1_pico_output):
        """Should extract hypothesis from prior_stage_outputs."""
        sample_context.prior_stage_outputs = {
            1: stage1_pico_output
        }
        
        hypothesis = agent._extract_hypothesis_from_stages(sample_context)
        assert "CGM improves glycemic control" in hypothesis

    def test_extract_population_from_pico(self, agent, sample_context, stage1_pico_output):
        """Should extract population from Stage 1 PICO elements."""
        sample_context.previous_results = {
            1: type('MockResult', (), {
                'output': stage1_pico_output
            })()
        }
        
        population = agent._extract_population_from_stages(sample_context)
        assert population == "Adults aged 18-65 with diabetes"

    def test_extract_data_source_from_stage1(self, agent, sample_context):
        """Should extract data source from Stage 1 file metadata."""
        stage1_output = {
            "file_name": "patient_data_2020_2023.csv",
            "data_source": "EHR System v2.1"
        }
        sample_context.previous_results = {
            1: type('MockResult', (), {
                'output': stage1_output
            })()
        }
        
        data_source = agent._extract_data_source_from_stages(sample_context)
        assert "patient_data_2020_2023.csv" in data_source


class TestProtocolGeneration:
    """Tests for protocol generation via ManuscriptClient."""

    @pytest.mark.asyncio
    async def test_execute_success_with_complete_data(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should successfully generate protocol with complete data."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            assert result.stage_id == 3
            assert "protocol" in result.output
            assert "protocol_number" in result.output
            assert result.output["protocol_number"] == "IRB-2024-001"
            
            # Verify generate_irb_protocol was called with correct params
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["study_title"] == "Impact of Novel Treatment on Patient Outcomes"
            assert call_kwargs["principal_investigator"] == "Dr. Jane Smith"
            assert call_kwargs["study_type"] == "retrospective"

    @pytest.mark.asyncio
    async def test_execute_missing_required_fields_live_mode(self, agent, sample_context):
        """Should fail in LIVE mode when required fields missing."""
        sample_context.governance_mode = "LIVE"
        sample_context.config = {"irb": {"study_title": "Test Study"}}  # Missing required fields
        
        result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert any("Missing required fields" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_execute_missing_fields_demo_mode_with_defaults(self, agent, sample_context):
        """Should succeed in DEMO mode with default values for missing fields."""
        sample_context.governance_mode = "DEMO"
        sample_context.config = {"irb": {"study_title": "Test Study"}}
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            assert len(result.warnings) > 0
            assert any("Missing required fields in DEMO mode" in warning for warning in result.warnings)
            
            # Verify defaults were applied
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs["hypothesis"] == "To investigate the relationship between study variables and outcomes"
            assert call_kwargs["population"] == "Study participants"

    @pytest.mark.asyncio
    async def test_execute_empty_variables_gets_defaults(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should add default variables when none specified."""
        config = complete_irb_config.copy()
        config["irb"]["variables"] = []
        sample_context.config = config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            assert len(result.warnings) > 0
            assert any("No variables specified" in warning for warning in result.warnings)
            
            call_kwargs = mock_generate.call_args.kwargs
            assert "Primary outcome" in call_kwargs["variables"]
            assert "Secondary outcomes" in call_kwargs["variables"]

    @pytest.mark.asyncio
    async def test_execute_manuscript_client_error(self, agent, sample_context, complete_irb_config):
        """Should handle ManuscriptClient errors gracefully."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = Exception("Service unavailable")
            
            result = await agent.execute(sample_context)

            assert result.status == "failed"
            assert len(result.errors) > 0
            assert any("Failed to generate IRB protocol" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_execute_with_stage1_integration(self, agent, sample_context, stage1_pico_output, mock_protocol_response):
        """Should integrate Stage 1 PICO data into protocol generation."""
        sample_context.config = {"irb": {"study_title": "CGM Study"}}
        sample_context.previous_results = {
            1: type('MockResult', (), {
                'output': stage1_pico_output
            })()
        }
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            
            # Verify PICO integration
            call_kwargs = mock_generate.call_args.kwargs
            assert "CGM improves glycemic control" in call_kwargs["hypothesis"]
            assert call_kwargs["population"] == "Adults aged 18-65 with diabetes"
            assert "HbA1c reduction" in call_kwargs["variables"]


class TestArtifactGeneration:
    """Tests for artifact generation."""

    @pytest.mark.asyncio
    async def test_protocol_artifact_creation(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should create protocol JSON artifact."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            assert len(result.artifacts) == 1
            
            artifact_path = result.artifacts[0]
            assert os.path.exists(artifact_path)
            assert artifact_path.endswith(".json")
            assert "irb_protocol" in artifact_path
            assert sample_context.job_id in artifact_path

    @pytest.mark.asyncio
    async def test_artifact_json_structure(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should create well-structured JSON artifact."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            artifact_path = result.artifacts[0]
            with open(artifact_path, "r", encoding="utf-8") as f:
                artifact_data = json.load(f)
            
            # Verify artifact structure matches protocol response
            assert artifact_data["protocolNumber"] == "IRB-2024-001"
            assert artifact_data["generatedAt"] == "2024-01-15T10:30:00Z"
            assert "protocol" in artifact_data
            assert "consentForm" in artifact_data
            assert "attachments" in artifact_data

    @pytest.mark.asyncio
    async def test_output_includes_protocol_metadata(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should include protocol metadata in output."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.output["protocol_number"] == "IRB-2024-001"
            assert result.output["generated_at"] == "2024-01-15T10:30:00Z"
            assert "protocol_file" in result.output
            assert result.output["protocol_file"].endswith(".json")


class TestGovernanceModes:
    """Tests for different governance modes."""

    @pytest.mark.asyncio
    async def test_demo_mode_behavior(self, agent, sample_context, mock_protocol_response):
        """DEMO mode should allow processing with warnings for missing data."""
        sample_context.governance_mode = "DEMO"
        sample_context.config = {"irb": {"study_title": "Demo Study"}}
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            assert result.metadata["governance_mode"] == "DEMO"
            assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_live_mode_strict_validation(self, agent, sample_context):
        """LIVE mode should enforce strict validation."""
        sample_context.governance_mode = "LIVE"
        sample_context.config = {"irb": {"study_title": "Live Study"}}  # Missing required fields
        
        result = await agent.execute(sample_context)

        assert result.status == "failed"
        assert result.metadata["governance_mode"] == "LIVE"
        assert len(result.errors) > 0


class TestErrorHandling:
    """Tests for error handling scenarios."""

    @pytest.mark.asyncio
    async def test_langchain_not_available(self, agent, sample_context):
        """Should handle missing LangChain gracefully."""
        with patch('src.workflow_engine.stages.stage_03_irb.LANGCHAIN_AVAILABLE', False):
            tools = agent.get_tools()
            assert tools == []
            
            template = agent.get_prompt_template()
            assert template is not None

    @pytest.mark.asyncio
    async def test_artifact_directory_creation(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should create artifact directory if it doesn't exist."""
        # Remove the artifact directory
        import shutil
        if os.path.exists(sample_context.artifact_path):
            shutil.rmtree(sample_context.artifact_path)
        
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert result.status == "completed"
            assert os.path.exists(sample_context.artifact_path)
            assert len(result.artifacts) == 1

    @pytest.mark.asyncio
    async def test_json_serialization_error_handling(self, agent, sample_context, complete_irb_config):
        """Should handle JSON serialization errors."""
        sample_context.config = complete_irb_config
        
        # Mock protocol response with non-serializable content
        bad_response = {
            "protocolNumber": "IRB-2024-001",
            "generatedAt": datetime.now(),  # This will cause JSON serialization error
        }
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = bad_response
            
            result = await agent.execute(sample_context)

            # Should still complete but handle the serialization error
            assert result.status in ["completed", "failed"]


class TestStageResultCreation:
    """Tests for StageResult creation."""

    @pytest.mark.asyncio
    async def test_result_timing_calculation(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should calculate execution timing correctly."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            start_time = datetime.utcnow()
            result = await agent.execute(sample_context)
            end_time = datetime.utcnow()

            assert result.status == "completed"
            assert isinstance(result.duration_ms, int)
            assert result.duration_ms >= 0
            
            # Verify timestamps are reasonable
            result_start = datetime.fromisoformat(result.started_at.replace("Z", "+00:00"))
            result_end = datetime.fromisoformat(result.completed_at.replace("Z", "+00:00"))
            
            assert start_time <= result_start <= result_end <= end_time

    @pytest.mark.asyncio
    async def test_metadata_inclusion(self, agent, sample_context, complete_irb_config, mock_protocol_response):
        """Should include appropriate metadata in result."""
        sample_context.config = complete_irb_config
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_protocol_response
            
            result = await agent.execute(sample_context)

            assert "governance_mode" in result.metadata
            assert "protocol_generated" in result.metadata
            assert result.metadata["protocol_generated"] is True
            assert result.metadata["governance_mode"] == sample_context.governance_mode


if __name__ == "__main__":
    pytest.main([__file__, "-v"])