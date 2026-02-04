"""
Test Suite for Results Interpretation Agent

Comprehensive tests for the ResultsInterpretationAgent including unit tests,
integration tests, and quality validation tests.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import numpy as np

from .results_interpretation_agent import (
    ResultsInterpretationAgent,
    create_results_interpretation_agent,
    process_interpretation_request
)
from .results_types import (
    ResultsInterpretationState,
    Finding,
    ClinicalSignificanceLevel,
    ConfidenceLevel,
    InterpretationRequest,
    InterpretationResponse
)
from .results_utils import (
    interpret_p_value,
    assess_clinical_magnitude,
    calculate_nnt,
    interpret_cohens_d
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_statistical_results():
    """Sample statistical results for testing."""
    return {
        "primary_outcomes": [
            {
                "hypothesis": "Treatment reduces pain scores",
                "p_value": 0.025,
                "effect_size": 0.65,
                "confidence_interval": {"lower": 0.2, "upper": 1.1},
                "test_statistic": "t = 2.45",
                "degrees_freedom": 118
            },
            {
                "hypothesis": "Treatment improves quality of life",
                "p_value": 0.08,
                "effect_size": 0.35,
                "confidence_interval": {"lower": -0.05, "upper": 0.75}
            }
        ],
        "secondary_outcomes": [
            {
                "hypothesis": "Treatment reduces medication usage",
                "p_value": 0.15,
                "effect_size": 0.25,
                "confidence_interval": {"lower": -0.1, "upper": 0.6}
            }
        ],
        "sample_info": {
            "total_n": 120,
            "treatment_n": 60,
            "control_n": 60,
            "missing_data_rate": 0.05,
            "attrition_rate": 0.08
        },
        "assumptions": {
            "normality": {"passed": True, "p_value": 0.12},
            "homoscedasticity": {"passed": True, "p_value": 0.35},
            "independence": {"passed": True}
        }
    }


@pytest.fixture
def sample_study_context():
    """Sample study context for testing."""
    return {
        "protocol": {
            "study_design": "randomized controlled trial",
            "randomized": True,
            "blinding": "double",
            "follow_up_duration": "12 weeks"
        },
        "sample_size": 120,
        "primary_outcome": "pain reduction on VAS scale",
        "baseline_risk": 0.3,
        "inclusion_criteria": [
            "Adults aged 18-65",
            "Chronic pain >3 months",
            "Pain score >4/10"
        ],
        "exclusion_criteria": [
            "Pregnancy",
            "Severe comorbidities",
            "Current opioid use"
        ]
    }


@pytest.fixture
def sample_interpretation_state(sample_statistical_results, sample_study_context):
    """Sample interpretation state for testing."""
    return ResultsInterpretationState(
        study_id="TEST_001",
        statistical_results=sample_statistical_results,
        visualizations=["chart1.png", "chart2.png"],
        study_context=sample_study_context
    )


@pytest.fixture
def mock_agent():
    """Mock agent for testing without LLM calls."""
    agent = Mock(spec=ResultsInterpretationAgent)
    agent.quality_threshold = 0.85
    agent.phi_protection = True
    return agent


# =============================================================================
# Unit Tests
# =============================================================================

class TestResultsInterpretationAgent:
    """Test the main ResultsInterpretationAgent class."""
    
    def test_agent_initialization(self):
        """Test agent initialization with default parameters."""
        agent = ResultsInterpretationAgent()
        
        assert agent.primary_model == "claude-3-5-sonnet-20241022"
        assert agent.fallback_model == "gpt-4o"
        assert agent.quality_threshold == 0.85
        assert agent.max_timeout_seconds == 300
        assert agent.phi_protection is True
    
    def test_agent_initialization_custom(self):
        """Test agent initialization with custom parameters."""
        agent = ResultsInterpretationAgent(
            primary_model="claude-3-haiku-20240307",
            quality_threshold=0.9,
            phi_protection=False
        )
        
        assert agent.primary_model == "claude-3-haiku-20240307"
        assert agent.quality_threshold == 0.9
        assert agent.phi_protection is False
    
    def test_factory_function(self):
        """Test the factory function."""
        agent = create_results_interpretation_agent(quality_threshold=0.75)
        
        assert isinstance(agent, ResultsInterpretationAgent)
        assert agent.quality_threshold == 0.75


class TestUtilityFunctions:
    """Test utility functions used by the agent."""
    
    def test_interpret_p_value(self):
        """Test p-value interpretation function."""
        # Highly significant
        result = interpret_p_value(0.0005, "pain reduction")
        assert "highly statistically significant" in result.lower()
        assert "p < 0.001" in result
        
        # Significant
        result = interpret_p_value(0.025, "quality of life")
        assert "statistically significant" in result.lower()
        assert "p = 0.025" in result
        
        # Non-significant
        result = interpret_p_value(0.15, "medication usage")
        assert "not statistically significant" in result.lower()
        
        # Approaching significance
        result = interpret_p_value(0.08, "sleep quality")
        assert "approached statistical significance" in result.lower()
    
    def test_assess_clinical_magnitude(self):
        """Test clinical magnitude assessment."""
        assert assess_clinical_magnitude(1.0, 0.2) == "large"
        assert assess_clinical_magnitude(0.5, 0.2) == "moderate"
        assert assess_clinical_magnitude(0.15, 0.2) == "small"
        assert assess_clinical_magnitude(0.05, 0.2) == "negligible"
    
    def test_calculate_nnt(self):
        """Test NNT calculation."""
        # Valid calculation
        nnt = calculate_nnt(0.8, 0.3)
        assert nnt is not None
        assert nnt > 0
        
        # Invalid baseline risk
        nnt = calculate_nnt(0.8, 0.0)
        assert nnt is None
        
        # Invalid effect size
        nnt = calculate_nnt(0.0, 0.3)
        assert nnt is None
    
    def test_interpret_cohens_d(self):
        """Test Cohen's d interpretation."""
        # Large effect
        result = interpret_cohens_d(1.0)
        assert result["magnitude"].value == "large"
        assert result["direction"] == "increase"
        
        # Small effect
        result = interpret_cohens_d(0.2)
        assert result["magnitude"].value == "small"
        
        # Negative effect
        result = interpret_cohens_d(-0.5)
        assert result["direction"] == "decrease"
        assert result["magnitude"].value == "medium"


class TestInterpretationState:
    """Test the interpretation state model."""
    
    def test_state_initialization(self, sample_interpretation_state):
        """Test state initialization."""
        state = sample_interpretation_state
        
        assert state.study_id == "TEST_001"
        assert len(state.statistical_results["primary_outcomes"]) == 2
        assert len(state.primary_findings) == 0  # Empty initially
        assert state.interpretation_version == "1.0"
    
    def test_add_primary_finding(self, sample_interpretation_state):
        """Test adding primary findings."""
        state = sample_interpretation_state
        
        state.add_primary_finding(
            hypothesis="Test hypothesis",
            statistical_result="p = 0.025",
            clinical_interpretation="Clinically significant improvement",
            confidence=ConfidenceLevel.HIGH,
            significance=ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT,
            effect_size=0.65
        )
        
        assert len(state.primary_findings) == 1
        finding = state.primary_findings[0]
        assert finding.hypothesis == "Test hypothesis"
        assert finding.effect_size == 0.65
        assert finding.confidence_level == ConfidenceLevel.HIGH
    
    def test_validate_completeness(self, sample_interpretation_state):
        """Test completeness validation."""
        state = sample_interpretation_state
        
        # Empty state should have issues
        issues = state.validate_completeness()
        assert len(issues) > 0
        assert any("primary findings" in issue.lower() for issue in issues)
        
        # Add content and recheck
        state.add_primary_finding(
            "Test", "p=0.05", "Significant", 
            ConfidenceLevel.HIGH, ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT
        )
        state.clinical_significance = "Clinically meaningful"
        state.limitations_identified = ["Sample size limitation"]
        state.confidence_statements = ["High confidence in findings"]
        
        issues = state.validate_completeness()
        assert len(issues) == 0
    
    def test_get_summary(self, sample_interpretation_state):
        """Test state summary generation."""
        state = sample_interpretation_state
        summary = state.get_summary()
        
        assert summary["study_id"] == "TEST_001"
        assert summary["num_primary_findings"] == 0
        assert "created_at" in summary


# =============================================================================
# Integration Tests
# =============================================================================

class TestAgentWorkflow:
    """Test the complete agent workflow."""
    
    @pytest.mark.asyncio
    async def test_load_analysis_results(self, sample_interpretation_state):
        """Test loading and validating analysis results."""
        agent = ResultsInterpretationAgent()
        
        # Test with valid results
        result_state = await agent._load_analysis_results(sample_interpretation_state)
        assert len(result_state.errors) == 0
        
        # Test with empty results
        empty_state = ResultsInterpretationState(
            study_id="EMPTY_001",
            statistical_results={},
            study_context={}
        )
        result_state = await agent._load_analysis_results(empty_state)
        assert len(result_state.warnings) > 0
        assert any("no statistical results" in warning.lower() for warning in result_state.warnings)
    
    @pytest.mark.asyncio
    async def test_assess_clinical_significance(self, sample_interpretation_state):
        """Test clinical significance assessment."""
        agent = ResultsInterpretationAgent()
        
        # Add some findings first
        sample_interpretation_state.add_primary_finding(
            "Test finding",
            "p = 0.025",
            "Test interpretation",
            ConfidenceLevel.HIGH,
            ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT,
            effect_size=0.8  # Large effect
        )
        
        result_state = await agent._assess_clinical_significance(sample_interpretation_state)
        
        assert result_state.clinical_significance != ""
        assert len(result_state.errors) == 0
        
        # Check if large effect size elevated significance
        finding = result_state.primary_findings[0]
        assert finding.clinical_significance == ClinicalSignificanceLevel.HIGHLY_SIGNIFICANT
    
    @pytest.mark.asyncio
    async def test_identify_limitations(self, sample_interpretation_state):
        """Test limitation identification."""
        agent = ResultsInterpretationAgent()
        
        result_state = await agent._identify_limitations(sample_interpretation_state)
        
        assert len(result_state.limitations_identified) > 0
        assert len(result_state.errors) == 0
        
        # Should identify blinding as positive (double-blind)
        # Should identify follow-up duration
        limitations_text = " ".join(result_state.limitations_identified)
        assert len(limitations_text) > 0
    
    @pytest.mark.asyncio
    async def test_validate_quality(self, sample_interpretation_state):
        """Test quality validation."""
        agent = ResultsInterpretationAgent()
        
        # Add content to meet quality threshold
        sample_interpretation_state.add_primary_finding(
            "Primary finding",
            "p = 0.025",
            "Clinically significant",
            ConfidenceLevel.HIGH,
            ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT,
            effect_size=0.65
        )
        sample_interpretation_state.clinical_significance = "Clinically meaningful"
        sample_interpretation_state.limitations_identified = ["Some limitation"]
        sample_interpretation_state.confidence_statements = ["High confidence"]
        sample_interpretation_state.effect_interpretations = {"finding": "moderate effect"}
        
        result_state = await agent._validate_quality(sample_interpretation_state)
        
        # Should pass quality threshold
        quality_warning = any("quality score" in warning.lower() for warning in result_state.warnings)
        assert not quality_warning


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_missing_statistical_results(self):
        """Test handling of missing statistical results."""
        agent = ResultsInterpretationAgent()
        
        state = ResultsInterpretationState(
            study_id="ERROR_001",
            statistical_results={},
            study_context={}
        )
        
        result_state = await agent.execute_interpretation(state)
        
        # Should complete without errors but with warnings
        assert len(result_state.warnings) > 0
        assert len(result_state.errors) == 0
    
    @pytest.mark.asyncio
    async def test_malformed_data(self):
        """Test handling of malformed data."""
        agent = ResultsInterpretationAgent()
        
        state = ResultsInterpretationState(
            study_id="MALFORMED_001",
            statistical_results={
                "primary_outcomes": [
                    {
                        "hypothesis": "Test",
                        "p_value": "not_a_number",  # Invalid p-value
                        "effect_size": None
                    }
                ]
            },
            study_context={}
        )
        
        result_state = await agent.execute_interpretation(state)
        
        # Should handle gracefully
        assert result_state.study_id == "MALFORMED_001"


class TestLLMIntegration:
    """Test LLM integration components."""
    
    @pytest.mark.asyncio
    @patch('services.worker.agents.writing.results_interpretation_agent.ChatAnthropic')
    @patch('services.worker.agents.writing.results_interpretation_agent.ChatOpenAI')
    async def test_llm_generation_fallback(self, mock_openai, mock_anthropic):
        """Test LLM generation with fallback."""
        # Setup mocks
        mock_anthropic_response = Mock()
        mock_anthropic_response.content = "Anthropic interpretation result"
        
        mock_openai_response = Mock()
        mock_openai_response.content = "OpenAI interpretation result"
        
        # Mock primary model failure, fallback success
        mock_anthropic_instance = Mock()
        mock_anthropic_instance.ainvoke = AsyncMock(side_effect=Exception("Primary failed"))
        mock_anthropic.return_value = mock_anthropic_instance
        
        mock_openai_instance = Mock()
        mock_openai_instance.ainvoke = AsyncMock(return_value=mock_openai_response)
        mock_openai.return_value = mock_openai_instance
        
        agent = ResultsInterpretationAgent()
        
        context_data = {
            "study_id": "TEST_001",
            "study_design": "RCT",
            "sample_size": 100,
            "primary_outcome": "Pain reduction",
            "statistical_results": "Mock results",
            "study_context": "Mock context"
        }
        
        # Should use fallback model
        result = await agent._generate_interpretation(context_data)
        assert result == "OpenAI interpretation result"
    
    @pytest.mark.asyncio
    @patch('services.worker.agents.writing.results_interpretation_agent.scan_for_phi_in_interpretation')
    async def test_phi_protection(self, mock_phi_scan, sample_interpretation_state):
        """Test PHI protection functionality."""
        # Setup mock to detect PHI
        mock_phi_scan.return_value = {
            "has_phi": True,
            "phi_types": ["dates", "ssn"],
            "total_matches": 2
        }
        
        agent = ResultsInterpretationAgent(phi_protection=True)
        
        # Add some content that would be scanned
        sample_interpretation_state.clinical_significance = "Test significance statement"
        
        result_state = await agent._scan_for_phi(sample_interpretation_state)
        
        # Should detect PHI and add warning
        phi_warnings = [w for w in result_state.warnings if "phi" in w.lower()]
        assert len(phi_warnings) > 0


# =============================================================================
# Integration Tests with Mock Data
# =============================================================================

class TestFullWorkflow:
    """Test complete workflow with realistic data."""
    
    @pytest.mark.asyncio
    async def test_complete_interpretation_workflow(self, sample_interpretation_state):
        """Test the complete interpretation workflow."""
        # Note: This test would require API keys for actual LLM calls
        # For CI/CD, we'll mock the LLM responses
        
        with patch.object(ResultsInterpretationAgent, '_generate_interpretation') as mock_interpret:
            mock_interpret.return_value = """
            Clinical Interpretation:
            
            The study demonstrates statistically significant improvements in pain reduction
            with a moderate to large effect size (d=0.65, p=0.025). This finding has
            clear clinical relevance and suggests meaningful benefit for patients.
            
            The quality of life improvement approached significance (p=0.08) with a
            small to moderate effect size (d=0.35), indicating potential benefit
            that warrants further investigation.
            """
            
            agent = ResultsInterpretationAgent()
            result_state = await agent.execute_interpretation(sample_interpretation_state)
            
            # Check that workflow completed
            assert len(result_state.errors) == 0
            assert len(result_state.primary_findings) > 0
            assert result_state.clinical_significance != ""
            assert len(result_state.limitations_identified) > 0
            assert len(result_state.confidence_statements) > 0
    
    @pytest.mark.asyncio
    async def test_process_interpretation_request(self, sample_statistical_results, sample_study_context):
        """Test the high-level request processing function."""
        request = InterpretationRequest(
            study_id="REQUEST_TEST_001",
            statistical_results=sample_statistical_results,
            visualizations=["chart1.png"],
            study_context=sample_study_context
        )
        
        with patch.object(ResultsInterpretationAgent, '_generate_interpretation') as mock_interpret:
            mock_interpret.return_value = "Mock interpretation result"
            
            response = await process_interpretation_request(request)
            
            assert isinstance(response, InterpretationResponse)
            assert response.study_id == "REQUEST_TEST_001"
            assert response.processing_time_ms > 0
            
            if response.success:
                assert response.interpretation_state is not None
                assert len(response.interpretation_state.errors) == 0
            else:
                assert response.error_message is not None


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        # Create agent with very short timeout
        agent = ResultsInterpretationAgent(max_timeout_seconds=1)
        
        # This would timeout in real LLM calls, but we'll test the setup
        assert agent.max_timeout_seconds == 1
    
    def test_memory_usage(self, sample_interpretation_state):
        """Test memory usage with large datasets."""
        # Add many findings to test memory handling
        for i in range(100):
            sample_interpretation_state.add_primary_finding(
                f"Finding {i}",
                f"p = 0.05",
                f"Interpretation {i}",
                ConfidenceLevel.MODERATE,
                ClinicalSignificanceLevel.CLINICALLY_SIGNIFICANT
            )
        
        # Should handle large numbers of findings
        assert len(sample_interpretation_state.primary_findings) == 100
        summary = sample_interpretation_state.get_summary()
        assert summary["num_primary_findings"] == 100


# =============================================================================
# Test Configuration
# =============================================================================

@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests."""
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise in tests


# =============================================================================
# Test Runner
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])