"""
Integration tests for Stage 1 → Stage 3 data flow.

Tests the integration between Stage 1 (Data Ingestion/Protocol Design) 
and Stage 3 (IRB Drafting) to ensure PICO elements and other data
flows correctly between stages.
"""

import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock
from datetime import datetime

# Add worker src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "worker"))

from src.workflow_engine.stages.stage_01_upload import DataIngestionAgent
from src.workflow_engine.stages.stage_03_irb import IRBDraftingAgent
from src.workflow_engine.types import StageContext, StageResult


@pytest.fixture
def sample_stage1_output():
    """Sample Stage 1 output with rich PICO elements."""
    return {
        # Data ingestion metadata
        "file_name": "diabetes_study_2020_2023.csv",
        "row_count": 1250,
        "column_count": 15,
        "data_source": "Electronic Health Records System v3.2",
        "study_type": "retrospective",
        
        # Protocol Design Agent PICO elements
        "pico_elements": {
            "population": "Adults aged 18-75 with Type 2 diabetes mellitus",
            "intervention": "Continuous glucose monitoring (CGM) devices",
            "comparator": "Standard fingerstick glucose monitoring",
            "outcomes": [
                "HbA1c reduction at 6 months",
                "Time in range (70-180 mg/dL)",
                "Number of hypoglycemic episodes",
                "Patient-reported quality of life scores",
                "Healthcare utilization metrics"
            ]
        },
        
        # Hypotheses from Protocol Design Agent
        "primary_hypothesis": "CGM use reduces HbA1c by ≥0.5% compared to standard monitoring at 6 months",
        "hypotheses": {
            "primary": "CGM use reduces HbA1c by ≥0.5% compared to standard monitoring at 6 months",
            "secondary": [
                "CGM increases time-in-range by ≥10% compared to standard monitoring",
                "CGM reduces severe hypoglycemic episodes by ≥50%",
                "CGM improves diabetes-specific quality of life scores"
            ]
        },
        
        # Study design elements
        "study_design": {
            "type": "retrospective_cohort",
            "duration": "6 months follow-up",
            "sample_size_target": 1200,
            "inclusion_criteria": [
                "Adults 18-75 years old",
                "Type 2 diabetes diagnosis ≥6 months",
                "HbA1c 7.0-11.0% at baseline",
                "Stable diabetes medication regimen"
            ],
            "exclusion_criteria": [
                "Type 1 diabetes",
                "Pregnancy",
                "End-stage renal disease",
                "Active malignancy"
            ]
        }
    }


@pytest.fixture
def stage1_result(sample_stage1_output):
    """Mock Stage 1 result object."""
    return type('StageResult', (), {
        'stage_id': 1,
        'stage_name': 'Data Ingestion',
        'status': 'completed',
        'output': sample_stage1_output,
        'artifacts': ['/tmp/stage1_metadata.json'],
        'errors': [],
        'warnings': []
    })()


@pytest.fixture
def context_with_stage1(stage1_result):
    """StageContext with Stage 1 results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = StageContext(
            job_id="integration-test-123",
            config={},
            previous_results={1: stage1_result},
            governance_mode="DEMO",
            artifact_path=tmpdir,
        )
        yield context


@pytest.fixture
def context_with_cumulative_data(sample_stage1_output):
    """StageContext with cumulative data from orchestrator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        context = StageContext(
            job_id="integration-test-456",
            config={},
            governance_mode="LIVE",
            artifact_path=tmpdir,
            manifest_id="manifest-uuid-123",
            project_id="project-456",
            research_id="research-789",
            prior_stage_outputs={
                1: sample_stage1_output
            },
            cumulative_data={
                "total_stages_completed": 1,
                "project_timeline": "6 months",
                "research_domain": "endocrinology"
            }
        )
        yield context


@pytest.fixture
def mock_irb_protocol():
    """Mock IRB protocol response."""
    return {
        "protocolNumber": "IRB-2024-CGM-001",
        "generatedAt": "2024-01-15T10:30:00Z",
        "protocol": {
            "title": "Effectiveness of Continuous Glucose Monitoring in Type 2 Diabetes: A Retrospective Cohort Study",
            "principalInvestigator": "Dr. Sarah Johnson, MD, PhD",
            "studyType": "retrospective",
            "sections": {
                "background": "Type 2 diabetes affects millions globally. CGM technology offers potential benefits...",
                "objectives": {
                    "primary": "To evaluate the effectiveness of CGM on glycemic control in T2DM patients",
                    "secondary": ["Assess time-in-range improvements", "Evaluate hypoglycemia reduction"]
                },
                "methods": {
                    "design": "Retrospective cohort study",
                    "population": "Adults aged 18-75 with Type 2 diabetes mellitus",
                    "data_source": "Electronic Health Records System v3.2",
                    "variables": [
                        "HbA1c reduction at 6 months",
                        "Time in range (70-180 mg/dL)",
                        "Number of hypoglycemic episodes",
                        "Patient-reported quality of life scores",
                        "Healthcare utilization metrics"
                    ],
                    "analysis": "Propensity score matching followed by regression analysis"
                },
                "risks": "Minimal risk - retrospective chart review with no patient contact",
                "benefits": "Potential to improve CGM implementation strategies"
            }
        },
        "consentForm": {
            "template": "retrospective_waiver",
            "waiver_criteria": ["Minimal risk", "No adverse effect on welfare", "Impracticable without waiver"]
        },
        "attachments": {
            "dataManagementPlan": "Data stored in HIPAA-compliant systems...",
            "riskBenefitAssessment": "Risk: Minimal (chart review). Benefit: Improved diabetes care..."
        }
    }


class TestStage1ToStage3Integration:
    """Integration tests for Stage 1 → Stage 3 data flow."""

    @pytest.mark.asyncio
    async def test_pico_elements_integration(self, context_with_stage1, mock_irb_protocol):
        """Should integrate PICO elements from Stage 1 into IRB protocol."""
        agent = IRBDraftingAgent()
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context_with_stage1)

            assert result.status == "completed"
            
            # Verify PICO integration in service call
            call_kwargs = mock_generate.call_args.kwargs
            
            # Population from PICO
            assert call_kwargs["population"] == "Adults aged 18-75 with Type 2 diabetes mellitus"
            
            # Variables from PICO outcomes
            pico_outcomes = [
                "HbA1c reduction at 6 months",
                "Time in range (70-180 mg/dL)",
                "Number of hypoglycemic episodes",
                "Patient-reported quality of life scores",
                "Healthcare utilization metrics"
            ]
            assert call_kwargs["variables"] == pico_outcomes
            
            # Hypothesis from Stage 1
            assert "CGM use reduces HbA1c by ≥0.5%" in call_kwargs["hypothesis"]
            
            # Data source from Stage 1 file metadata
            assert "diabetes_study_2020_2023.csv" in call_kwargs["data_source"]

    @pytest.mark.asyncio
    async def test_hypothesis_extraction_primary_and_fallback(self, context_with_stage1, mock_irb_protocol):
        """Should extract primary hypothesis with fallbacks."""
        agent = IRBDraftingAgent()
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            # Test primary hypothesis extraction
            hypothesis = agent._extract_hypothesis_from_stages(context_with_stage1)
            assert hypothesis == "CGM use reduces HbA1c by ≥0.5% compared to standard monitoring at 6 months"
            
            # Test fallback to hypotheses dict
            stage1_output = context_with_stage1.previous_results[1].output.copy()
            del stage1_output["primary_hypothesis"]  # Remove primary
            context_with_stage1.previous_results[1].output = stage1_output
            
            hypothesis = agent._extract_hypothesis_from_stages(context_with_stage1)
            assert "CGM use reduces HbA1c by ≥0.5%" in hypothesis

    @pytest.mark.asyncio
    async def test_study_type_inheritance(self, context_with_stage1, mock_irb_protocol):
        """Should inherit study type from Stage 1 when not specified in config."""
        agent = IRBDraftingAgent()
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context_with_stage1)
            
            call_kwargs = mock_generate.call_args.kwargs
            # Should use study_type from Stage 1 output (retrospective)
            assert call_kwargs["study_type"] == "retrospective"

    @pytest.mark.asyncio
    async def test_config_override_stage1_data(self, context_with_stage1, mock_irb_protocol):
        """Config should override Stage 1 data when explicitly provided."""
        agent = IRBDraftingAgent()
        
        # Add explicit IRB config
        context_with_stage1.config = {
            "irb": {
                "study_title": "Custom IRB Study Title",
                "population": "Custom population override",
                "hypothesis": "Custom hypothesis override"
            }
        }
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context_with_stage1)
            
            call_kwargs = mock_generate.call_args.kwargs
            
            # Config should override Stage 1 data
            assert call_kwargs["study_title"] == "Custom IRB Study Title"
            assert call_kwargs["population"] == "Custom population override"
            assert call_kwargs["hypothesis"] == "Custom hypothesis override"
            
            # But variables should still come from Stage 1 PICO if not specified
            assert "HbA1c reduction at 6 months" in call_kwargs["variables"]

    @pytest.mark.asyncio
    async def test_cumulative_data_integration(self, context_with_cumulative_data, mock_irb_protocol):
        """Should integrate data from cumulative orchestrator data in LIVE mode."""
        agent = IRBDraftingAgent()
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context_with_cumulative_data)
            
            assert result.status == "completed"
            
            call_kwargs = mock_generate.call_args.kwargs
            
            # Should get population from prior_stage_outputs
            assert call_kwargs["population"] == "Adults aged 18-75 with Type 2 diabetes mellitus"
            
            # Should get variables from PICO outcomes
            assert "HbA1c reduction at 6 months" in call_kwargs["variables"]

    @pytest.mark.asyncio
    async def test_missing_stage1_graceful_fallback(self, mock_irb_protocol):
        """Should handle missing Stage 1 data gracefully with defaults."""
        agent = IRBDraftingAgent()
        
        # Context without Stage 1 results
        with tempfile.TemporaryDirectory() as tmpdir:
            context = StageContext(
                job_id="no-stage1-test",
                config={"irb": {"study_title": "Standalone IRB Test"}},
                previous_results={},  # No Stage 1 results
                governance_mode="DEMO",
                artifact_path=tmpdir,
            )
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context)
            
            assert result.status == "completed"
            assert len(result.warnings) > 0  # Should warn about missing data
            
            call_kwargs = mock_generate.call_args.kwargs
            
            # Should use defaults
            assert call_kwargs["population"] == "Study participants"
            assert call_kwargs["variables"] == ["Primary outcome", "Secondary outcomes"]
            assert call_kwargs["hypothesis"] == "To investigate the relationship between study variables and outcomes"

    @pytest.mark.asyncio
    async def test_partial_stage1_data_mixed_sources(self, context_with_stage1, mock_irb_protocol):
        """Should handle partial Stage 1 data and mix with config/defaults."""
        agent = IRBDraftingAgent()
        
        # Remove some PICO elements to test partial data handling
        stage1_output = context_with_stage1.previous_results[1].output.copy()
        del stage1_output["pico_elements"]["population"]  # Remove population
        del stage1_output["primary_hypothesis"]  # Remove primary hypothesis
        context_with_stage1.previous_results[1].output = stage1_output
        
        # Add partial config
        context_with_stage1.config = {
            "irb": {
                "principal_investigator": "Dr. Custom PI",
                "population": "Config-defined population"
            }
        }
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context)
            
            call_kwargs = mock_generate.call_args.kwargs
            
            # Should use config population (not Stage 1)
            assert call_kwargs["population"] == "Config-defined population"
            
            # Should still use Stage 1 PICO outcomes for variables
            assert "HbA1c reduction at 6 months" in call_kwargs["variables"]
            
            # Should use fallback hypothesis from hypotheses dict
            assert "CGM use reduces HbA1c" in call_kwargs["hypothesis"]

    @pytest.mark.asyncio
    async def test_irb_artifact_includes_stage1_reference(self, context_with_stage1, mock_irb_protocol):
        """IRB artifact should reference Stage 1 data sources."""
        agent = IRBDraftingAgent()
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context_with_stage1)
            
            assert result.status == "completed"
            assert len(result.artifacts) == 1
            
            # Check artifact content
            import json
            artifact_path = result.artifacts[0]
            with open(artifact_path, "r") as f:
                artifact_data = json.load(f)
            
            # Should contain the full protocol including Stage 1 references
            assert artifact_data["protocolNumber"] == "IRB-2024-CGM-001"
            assert "diabetes_study_2020_2023.csv" in str(artifact_data)  # File reference
            assert "Electronic Health Records System v3.2" in str(artifact_data)  # Data source


class TestDataValidationAcrossStages:
    """Test data validation when passing between stages."""

    @pytest.mark.asyncio
    async def test_invalid_stage1_pico_elements_handling(self, mock_irb_protocol):
        """Should handle invalid or malformed Stage 1 PICO elements gracefully."""
        agent = IRBDraftingAgent()
        
        # Stage 1 with malformed PICO
        malformed_stage1 = {
            "pico_elements": {
                "population": "",  # Empty population
                "outcomes": "not_a_list",  # Should be list
            },
            "primary_hypothesis": None,  # Null hypothesis
            "file_name": "test.csv"
        }
        
        stage1_result = type('StageResult', (), {
            'output': malformed_stage1
        })()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context = StageContext(
                job_id="malformed-test",
                config={},
                previous_results={1: stage1_result},
                governance_mode="DEMO",
                artifact_path=tmpdir,
            )
        
        with patch.object(agent, 'generate_irb_protocol', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_irb_protocol
            
            result = await agent.execute(context)
            
            # Should complete with warnings about malformed data
            assert result.status == "completed"
            assert len(result.warnings) > 0
            
            call_kwargs = mock_generate.call_args.kwargs
            
            # Should fall back to defaults for malformed data
            assert call_kwargs["population"] == "Study participants"
            assert call_kwargs["variables"] == ["Primary outcome", "Secondary outcomes"]

    @pytest.mark.asyncio 
    async def test_stage1_data_type_conversion(self, mock_irb_protocol):
        """Should handle type conversion from Stage 1 data."""
        agent = IRBDraftingAgent()
        
        # Stage 1 with various data types
        stage1_output = {
            "pico_elements": {
                "population": ["List", "of", "population", "elements"],  # List instead of string
                "outcomes": "outcome1, outcome2, outcome3"  # String instead of list
            },
            "primary_hypothesis": 123,  # Number instead of string
            "file_name": "test.csv"
        }
        
        stage1_result = type('StageResult', (), {
            'output': stage1_output
        })()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            context = StageContext(
                job_id="type-conversion-test",
                config={},
                previous_results={1: stage1_result},
                governance_mode="DEMO",
                artifact_path=tmpdir,
            )
        
        # Should extract and convert data types appropriately
        irb_data = agent._extract_irb_data(context)
        
        # Should convert population list to string
        assert isinstance(irb_data["population"], str)
        
        # Should convert hypothesis number to string
        assert isinstance(irb_data["hypothesis"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])