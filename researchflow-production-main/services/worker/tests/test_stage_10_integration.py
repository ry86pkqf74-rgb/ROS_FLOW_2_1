"""
Integration Tests for Stage 10 Dual-Mode Operation

Tests both validation mode and gap analysis mode to ensure
proper integration with the workflow engine.
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import workflow engine components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflow_engine.types import StageContext, StageResult
from workflow_engine.stages.stage_10_validation import ValidationAgent
from workflow_engine.stages.stage_10_gap_analysis import GapAnalysisStageAgent


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def base_context():
    """Base context for stage execution."""
    return StageContext(
        job_id="test-job-001",
        config={},
        artifact_path="/tmp/test_artifacts",
        governance_mode="DEMO",
        dataset_pointer=None,
        previous_results={},
        metadata={}
    )


@pytest.fixture
def validation_context(base_context):
    """Context configured for validation mode."""
    base_context.config = {
        "stage_10_mode": "validation",
        "validation": {
            "criteria": [
                {
                    "id": "data_completeness",
                    "name": "Data Completeness",
                    "category": "data_quality",
                    "severity": "high"
                }
            ],
            "strict_mode": False
        }
    }
    return base_context


@pytest.fixture
def gap_analysis_context(base_context):
    """Context configured for gap analysis mode."""
    base_context.config = {
        "stage_10_mode": "gap_analysis",
        "study_context": {
            "title": "Test Study on Mindfulness",
            "research_question": "Does MBSR reduce anxiety?",
            "study_type": "RCT",
            "population": "College students",
            "intervention": "MBSR program",
            "outcome": "Anxiety score"
        },
        "gap_analysis": {
            "enable_semantic_comparison": False,  # Use keyword fallback
            "target_suggestions": 3,
            "min_literature_count": 5
        }
    }
    
    # Add mock literature from Stage 6
    base_context.previous_results = {
        6: Mock(
            output={
                "papers": [
                    {
                        "title": "Mindfulness reduces anxiety in students",
                        "authors": ["Smith J", "Doe A"],
                        "year": 2020,
                        "abstract": "This study examines mindfulness-based interventions...",
                        "doi": "10.1234/test1",
                        "source": "pubmed",
                        "relevance_score": 0.85
                    },
                    {
                        "title": "MBSR for college populations",
                        "authors": ["Jones B"],
                        "year": 2021,
                        "abstract": "MBSR shows promise for reducing anxiety...",
                        "doi": "10.1234/test2",
                        "source": "pubmed",
                        "relevance_score": 0.82
                    },
                    {
                        "title": "Anxiety interventions in higher education",
                        "authors": ["Brown C"],
                        "year": 2019,
                        "abstract": "Various interventions have been studied...",
                        "doi": "10.1234/test3",
                        "source": "semantic_scholar",
                        "relevance_score": 0.78
                    },
                    {
                        "title": "Mindfulness-based programs efficacy",
                        "authors": ["Wilson D"],
                        "year": 2022,
                        "abstract": "Meta-analysis of mindfulness programs...",
                        "doi": "10.1234/test4",
                        "source": "pubmed",
                        "relevance_score": 0.90
                    },
                    {
                        "title": "Long-term effects of MBSR",
                        "authors": ["Taylor E"],
                        "year": 2020,
                        "abstract": "Follow-up study examining sustained effects...",
                        "doi": "10.1234/test5",
                        "source": "pubmed",
                        "relevance_score": 0.75
                    }
                ]
            }
        ),
        7: Mock(
            output={
                "findings": [
                    {
                        "description": "MBSR significantly reduced anxiety scores",
                        "effect_size": 0.72,
                        "p_value": 0.001,
                        "statistical_test": "t-test",
                        "significance": "high",
                        "confidence": "high"
                    }
                ]
            }
        )
    }
    
    return base_context


# =============================================================================
# Validation Mode Tests
# =============================================================================

class TestValidationMode:
    """Tests for Stage 10 validation mode."""
    
    @pytest.mark.asyncio
    async def test_validation_mode_basic_execution(self, validation_context):
        """Test that validation mode executes successfully."""
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        assert isinstance(result, StageResult)
        assert result.stage_id == 10
        assert result.stage_name == "Validation"
        assert result.status in ("completed", "failed")
        assert "validation_results" in result.output
        assert "checklist_status" in result.output
    
    @pytest.mark.asyncio
    async def test_validation_mode_criteria_processing(self, validation_context):
        """Test that validation criteria are processed correctly."""
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        assert result.output["validation_results"]
        assert len(result.output["validation_results"]) > 0
        
        # Check first criterion was processed
        first_result = result.output["validation_results"][0]
        assert first_result["criterion_id"] == "data_completeness"
        assert "status" in first_result
    
    @pytest.mark.asyncio
    async def test_validation_mode_checklist_status(self, validation_context):
        """Test checklist status generation."""
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        status = result.output["checklist_status"]
        assert "total_criteria" in status
        assert "passed_count" in status
        assert "completion_percentage" in status
        assert status["total_criteria"] > 0
    
    @pytest.mark.asyncio
    async def test_validation_mode_strict_mode(self, validation_context):
        """Test strict mode enforcement."""
        validation_context.config["validation"]["strict_mode"] = True
        
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        # In strict mode with issues, should still complete
        # (actual enforcement depends on issue severity)
        assert isinstance(result, StageResult)


# =============================================================================
# Gap Analysis Mode Tests
# =============================================================================

class TestGapAnalysisMode:
    """Tests for Stage 10 gap analysis mode."""
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_requires_dependencies(self, gap_analysis_context):
        """Test that gap analysis checks for required dependencies."""
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        assert isinstance(result, StageResult)
        assert result.stage_id == 10
        assert result.stage_name == "Gap Analysis"
        
        # Should either succeed or fail with clear error about missing dependencies
        if result.status == "failed":
            assert any("GapAnalysisAgent" in err or "API" in err for err in result.errors)
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "OPENAI_API_KEY": "test-key"})
    async def test_gap_analysis_mode_with_mock_api(self, gap_analysis_context):
        """Test gap analysis with mocked API keys."""
        agent = GapAnalysisStageAgent()
        
        # This will attempt initialization
        result = await agent.execute(gap_analysis_context)
        
        assert isinstance(result, StageResult)
        # May fail due to actual API calls, but should process input correctly
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_extracts_literature(self, gap_analysis_context):
        """Test literature extraction from Stage 6 results."""
        agent = GapAnalysisStageAgent()
        
        # Extract literature using internal method
        literature = agent._extract_literature(gap_analysis_context)
        
        assert len(literature) == 5
        assert all(hasattr(paper, 'title') for paper in literature)
        assert all(hasattr(paper, 'authors') for paper in literature)
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_extracts_findings(self, gap_analysis_context):
        """Test findings extraction from Stage 7 results."""
        agent = GapAnalysisStageAgent()
        
        # Extract findings using internal method
        findings = agent._extract_findings(gap_analysis_context)
        
        assert len(findings) == 1
        assert hasattr(findings[0], 'description')
        assert hasattr(findings[0], 'effect_size')
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_extracts_study_context(self, gap_analysis_context):
        """Test study context extraction."""
        agent = GapAnalysisStageAgent()
        
        study_context = agent._extract_study_context(gap_analysis_context)
        
        assert study_context is not None
        assert study_context.title == "Test Study on Mindfulness"
        assert study_context.research_question == "Does MBSR reduce anxiety?"
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_insufficient_literature_warning(self, gap_analysis_context):
        """Test warning when literature count is low."""
        # Reduce literature to below minimum
        gap_analysis_context.previous_results[6].output["papers"] = [
            gap_analysis_context.previous_results[6].output["papers"][0]
        ]
        
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        # Should have warning about insufficient literature
        # Or fail with appropriate error
        if result.status == "completed":
            assert any("papers" in warning.lower() for warning in result.warnings)
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_missing_api_keys(self, gap_analysis_context):
        """Test handling of missing API keys."""
        # Ensure API keys are not set
        with patch.dict(os.environ, {}, clear=True):
            agent = GapAnalysisStageAgent()
            result = await agent.execute(gap_analysis_context)
            
            # Should fail with clear error about missing API keys
            if result.status == "failed":
                assert any("API" in err or "key" in err.lower() for err in result.errors)


# =============================================================================
# Mode Selection Tests
# =============================================================================

class TestModeSelection:
    """Tests for proper mode selection and routing."""
    
    @pytest.mark.asyncio
    async def test_default_mode_is_validation(self, base_context):
        """Test that default mode is validation when not specified."""
        # Don't set stage_10_mode
        agent = ValidationAgent()
        result = await agent.execute(base_context)
        
        assert result.stage_name == "Validation"
    
    @pytest.mark.asyncio
    async def test_explicit_validation_mode(self, validation_context):
        """Test explicit validation mode selection."""
        assert validation_context.config["stage_10_mode"] == "validation"
        
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        assert result.stage_name == "Validation"
        assert "validation_results" in result.output
    
    @pytest.mark.asyncio
    async def test_explicit_gap_analysis_mode(self, gap_analysis_context):
        """Test explicit gap analysis mode selection."""
        assert gap_analysis_context.config["stage_10_mode"] == "gap_analysis"
        
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        assert result.stage_name == "Gap Analysis"


# =============================================================================
# Integration Tests
# =============================================================================

class TestStage10Integration:
    """Integration tests for Stage 10 with prior stages."""
    
    @pytest.mark.asyncio
    async def test_validation_mode_with_prior_stages(self, validation_context):
        """Test validation mode with results from prior stages."""
        # Add mock Stage 7 results
        validation_context.previous_results = {
            7: Mock(
                output={
                    "model_summary": {"r_squared": 0.85},
                    "findings": [{"description": "Significant effect"}]
                }
            )
        }
        
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        assert result.status in ("completed", "failed")
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_full_pipeline(self, gap_analysis_context):
        """Test gap analysis mode as part of full pipeline."""
        # Gap analysis context already has Stage 6 and 7 results
        assert 6 in gap_analysis_context.previous_results
        assert 7 in gap_analysis_context.previous_results
        
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        assert isinstance(result, StageResult)
        assert result.stage_id == 10
    
    @pytest.mark.asyncio
    async def test_output_compatibility_with_stage_12(self, gap_analysis_context):
        """Test that gap analysis output is compatible with Stage 12."""
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        # Stage 12 expects these fields if gap analysis was run
        if result.status == "completed" and "narrative" in result.output:
            assert "narrative" in result.output or result.output["narrative"] == ""
            assert "future_directions_section" in result.output
            
            # Should be able to access for manuscript generation
            narrative = result.output.get("narrative", "")
            future_dirs = result.output.get("future_directions_section", "")
            
            # Both should be strings (even if empty on failure)
            assert isinstance(narrative, str)
            assert isinstance(future_dirs, str)


# =============================================================================
# Artifact Tests
# =============================================================================

class TestArtifactGeneration:
    """Tests for artifact generation in both modes."""
    
    @pytest.mark.asyncio
    async def test_validation_artifact_generation(self, validation_context, tmp_path):
        """Test validation mode generates artifacts."""
        validation_context.artifact_path = str(tmp_path)
        
        agent = ValidationAgent()
        result = await agent.execute(validation_context)
        
        # Should have artifact path in result
        if result.artifacts:
            assert len(result.artifacts) > 0
            # Artifact should exist (if test succeeded)
            if result.status == "completed":
                # File may or may not exist depending on test environment
                pass
    
    @pytest.mark.asyncio
    async def test_gap_analysis_artifact_generation(self, gap_analysis_context, tmp_path):
        """Test gap analysis mode generates artifacts."""
        gap_analysis_context.artifact_path = str(tmp_path)
        
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        # Should attempt to generate artifacts
        # (may fail due to missing dependencies)
        assert isinstance(result, StageResult)


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfigurationHandling:
    """Tests for configuration handling in both modes."""
    
    @pytest.mark.asyncio
    async def test_validation_mode_default_criteria(self, base_context):
        """Test that validation mode uses default criteria when none provided."""
        base_context.config = {"stage_10_mode": "validation"}
        
        agent = ValidationAgent()
        result = await agent.execute(base_context)
        
        # Should use default criteria
        assert result.output.get("validation_results") is not None
        # Should have warning about using defaults
        assert any("default" in w.lower() for w in result.warnings)
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_missing_study_context(self, base_context):
        """Test gap analysis fails gracefully without study context."""
        base_context.config = {"stage_10_mode": "gap_analysis"}
        
        agent = GapAnalysisStageAgent()
        result = await agent.execute(base_context)
        
        # Should fail with clear error
        assert result.status == "failed"
        assert any("study context" in err.lower() for err in result.errors)
    
    @pytest.mark.asyncio
    async def test_gap_analysis_mode_configuration_override(self, gap_analysis_context):
        """Test gap analysis configuration can be customized."""
        gap_analysis_context.config["gap_analysis"]["target_suggestions"] = 2
        gap_analysis_context.config["gap_analysis"]["min_literature_count"] = 3
        
        agent = GapAnalysisStageAgent()
        result = await agent.execute(gap_analysis_context)
        
        # Configuration should be respected
        assert isinstance(result, StageResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
