"""
Unit tests for ML Study Design Optimizer

Tests the ML-enhanced study design selection and optimization functionality
including Bayesian optimization, evidence synthesis, and recommendation generation.

Author: Stage 6 Enhancement Team
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import numpy as np
from typing import Dict, Any

# Import the module under test
from services.worker.src.workflow_engine.stages.study_analyzers.ml_study_optimizer import (
    MLStudyDesignOptimizer,
    StudyDesignRecommendation,
    StudyDesignType,
    AllocationStrategy,
    BayesianOptimizer,
    EvidenceSynthesizer
)


@pytest.fixture
def sample_study_requirements():
    """Sample study requirements for testing."""
    return {
        "research_question": "Does intervention X reduce cardiovascular events?",
        "research_type": "intervention",
        "target_population": {
            "size": 1000,
            "age_range": [45, 75],
            "conditions": ["cardiovascular_disease"]
        },
        "primary_endpoint": {
            "type": "binary",
            "description": "Major cardiovascular events"
        },
        "expected_effect_size": 0.25,
        "significance_level": 0.05,
        "target_power": 0.8,
        "budget_constraints": {
            "max_budget": 500000,
            "cost_per_participant": 800
        },
        "timeline_constraints": {
            "max_duration_months": 24
        },
        "domain": "cardiovascular"
    }


@pytest.fixture
def ml_optimizer():
    """Create ML study design optimizer instance."""
    return MLStudyDesignOptimizer(
        confidence_threshold=0.8,
        enable_clinical_models=True,
        literature_integration=True
    )


class TestMLStudyDesignOptimizer:
    """Test cases for MLStudyDesignOptimizer class."""

    def test_initialization(self):
        """Test proper initialization of MLStudyDesignOptimizer."""
        optimizer = MLStudyDesignOptimizer(
            confidence_threshold=0.9,
            enable_clinical_models=False,
            literature_integration=False
        )
        
        assert optimizer.confidence_threshold == 0.9
        assert optimizer.enable_clinical_models is False
        assert optimizer.literature_integration is False
        assert optimizer.bayesian_optimizer is not None
        assert optimizer.evidence_synthesizer is not None

    @pytest.mark.asyncio
    async def test_optimize_study_design_basic(self, ml_optimizer, sample_study_requirements):
        """Test basic study design optimization functionality."""
        result = await ml_optimizer.optimize_study_design(sample_study_requirements)
        
        # Validate result structure
        assert isinstance(result, StudyDesignRecommendation)
        assert isinstance(result.design_type, StudyDesignType)
        assert isinstance(result.allocation_strategy, AllocationStrategy)
        assert 0.0 <= result.confidence_score <= 1.0
        assert result.estimated_sample_size > 0
        assert result.expected_power > 0.0
        assert result.estimated_duration_months > 0
        assert result.estimated_cost > 0.0

    @pytest.mark.asyncio
    async def test_recommend_design_type_intervention(self, ml_optimizer):
        """Test design type recommendation for intervention studies."""
        requirements = {
            "research_type": "intervention",
            "intervention_type": "drug_therapy"
        }
        
        design_type = await ml_optimizer._recommend_design_type(requirements)
        assert design_type == StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL

    @pytest.mark.asyncio
    async def test_recommend_design_type_observational(self, ml_optimizer):
        """Test design type recommendation for observational studies."""
        requirements = {
            "research_type": "observational retrospective"
        }
        
        design_type = await ml_optimizer._recommend_design_type(requirements)
        assert design_type == StudyDesignType.CASE_CONTROL

    @pytest.mark.asyncio
    async def test_recommend_allocation_strategy_stratified(self, ml_optimizer):
        """Test allocation strategy recommendation with stratification."""
        requirements = {
            "stratification_factors": ["age", "gender"]
        }
        
        strategy = await ml_optimizer._recommend_allocation_strategy(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL, requirements
        )
        assert strategy == AllocationStrategy.STRATIFIED_RANDOMIZATION

    @pytest.mark.asyncio
    async def test_recommend_allocation_strategy_adaptive(self, ml_optimizer):
        """Test allocation strategy recommendation for adaptive studies."""
        requirements = {
            "enable_adaptive": True
        }
        
        strategy = await ml_optimizer._recommend_allocation_strategy(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL, requirements
        )
        assert strategy == AllocationStrategy.ADAPTIVE_ALLOCATION

    @pytest.mark.asyncio
    async def test_optimize_sample_size_success(self, ml_optimizer):
        """Test successful sample size optimization."""
        requirements = {
            "expected_effect_size": 0.3,
            "significance_level": 0.05,
            "cost_per_participant": 1000,
            "fixed_costs": 50000,
            "min_sample_size": 50,
            "max_sample_size": 500
        }
        
        result = await ml_optimizer._optimize_sample_size(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL, requirements
        )
        
        assert "optimal_sample_size" in result
        assert "optimal_power" in result
        assert "optimal_cost" in result
        assert 50 <= result["optimal_sample_size"] <= 500

    @pytest.mark.asyncio
    async def test_calculate_confidence_score_high(self, ml_optimizer):
        """Test confidence score calculation with good parameters."""
        sample_size_result = {
            "optimization_success": True,
            "optimal_power": 0.85
        }
        similar_studies = [
            {"similarity_score": 0.8},
            {"similarity_score": 0.9}
        ]
        
        score = await ml_optimizer._calculate_confidence_score(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL,
            sample_size_result,
            similar_studies
        )
        
        assert 0.8 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_confidence_score_low(self, ml_optimizer):
        """Test confidence score calculation with poor parameters."""
        sample_size_result = {
            "optimization_success": False,
            "optimal_power": 0.6
        }
        similar_studies = []
        
        score = await ml_optimizer._calculate_confidence_score(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL,
            sample_size_result,
            similar_studies
        )
        
        assert 0.4 <= score <= 0.7

    @pytest.mark.asyncio
    async def test_estimate_study_duration(self, ml_optimizer):
        """Test study duration estimation."""
        sample_size_result = {"optimal_sample_size": 200}
        
        duration = await ml_optimizer._estimate_study_duration(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL,
            sample_size_result
        )
        
        assert isinstance(duration, int)
        assert 12 <= duration <= 60  # Reasonable duration range

    @pytest.mark.asyncio
    async def test_assess_feasibility_budget_constraints(self, ml_optimizer):
        """Test feasibility assessment with budget constraints."""
        requirements = {
            "budget_constraints": {"max_budget": 50000},
            "timeline_constraints": {"max_duration_months": 6}
        }
        
        assessment = await ml_optimizer._assess_feasibility(
            requirements, StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL
        )
        
        assert "score" in assessment
        assert "risks" in assessment
        assert "mitigations" in assessment
        assert len(assessment["risks"]) > 0  # Should identify risks

    @pytest.mark.asyncio
    async def test_assess_regulatory_complexity(self, ml_optimizer):
        """Test regulatory complexity assessment."""
        complexity = await ml_optimizer._assess_regulatory_complexity(
            StudyDesignType.ADAPTIVE_TRIAL
        )
        assert complexity == "very_high"
        
        complexity = await ml_optimizer._assess_regulatory_complexity(
            StudyDesignType.CASE_CONTROL
        )
        assert complexity == "low"

    @pytest.mark.asyncio
    async def test_get_required_approvals(self, ml_optimizer):
        """Test required approvals identification."""
        approvals = await ml_optimizer._get_required_approvals(
            StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL
        )
        
        assert "IRB/Ethics Committee" in approvals
        assert len(approvals) >= 2  # Should have multiple approvals for RCT

    @pytest.mark.asyncio
    async def test_create_fallback_recommendation(self, ml_optimizer):
        """Test fallback recommendation creation."""
        recommendation = await ml_optimizer._create_fallback_recommendation()
        
        assert isinstance(recommendation, StudyDesignRecommendation)
        assert recommendation.design_type == StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL
        assert recommendation.confidence_score == 0.5
        assert recommendation.estimated_sample_size == 100

    def test_to_dict_conversion(self):
        """Test StudyDesignRecommendation to dictionary conversion."""
        recommendation = StudyDesignRecommendation(
            design_type=StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL,
            confidence_score=0.85,
            estimated_sample_size=200,
            allocation_strategy=AllocationStrategy.BLOCK_RANDOMIZATION,
            expected_power=0.8,
            estimated_duration_months=18,
            estimated_cost=250000.0
        )
        
        result_dict = recommendation.to_dict()
        
        assert result_dict["design_type"] == "rct"
        assert result_dict["confidence_score"] == 0.85
        assert result_dict["estimated_sample_size"] == 200
        assert result_dict["allocation_strategy"] == "block"

    @pytest.mark.asyncio
    async def test_error_handling_invalid_requirements(self, ml_optimizer):
        """Test error handling with invalid study requirements."""
        invalid_requirements = {}  # Empty requirements
        
        # Should not raise exception, should return fallback
        result = await ml_optimizer.optimize_study_design(invalid_requirements)
        
        assert isinstance(result, StudyDesignRecommendation)
        assert result.confidence_score <= 0.7  # Low confidence for poor input


class TestBayesianOptimizer:
    """Test cases for BayesianOptimizer class."""

    def test_initialization(self):
        """Test BayesianOptimizer initialization."""
        optimizer = BayesianOptimizer(
            acquisition_function="expected_improvement",
            n_random_starts=5,
            exploration_weight=0.2
        )
        
        assert optimizer.acquisition_function == "expected_improvement"
        assert optimizer.n_random_starts == 5
        assert optimizer.exploration_weight == 0.2
        assert optimizer.optimization_history == []

    def test_optimize_sample_size_basic(self):
        """Test basic sample size optimization."""
        optimizer = BayesianOptimizer()
        
        def cost_function(sample_size, **params):
            return 1000 * sample_size + 50000
        
        def power_function(sample_size, **params):
            effect_size = params.get("effect_size", 0.3)
            if sample_size <= 0:
                return 0.0
            return min(0.95, effect_size * np.sqrt(sample_size / 100))
        
        study_params = {"effect_size": 0.3}
        
        result = optimizer.optimize_sample_size(
            study_params, cost_function, power_function, (50, 500)
        )
        
        assert "optimal_sample_size" in result
        assert "optimal_power" in result
        assert "optimal_cost" in result
        assert 50 <= result["optimal_sample_size"] <= 500

    def test_optimize_sample_size_error_handling(self):
        """Test error handling in sample size optimization."""
        optimizer = BayesianOptimizer()
        
        def failing_cost_function(sample_size, **params):
            raise ValueError("Cost calculation failed")
        
        def power_function(sample_size, **params):
            return 0.8
        
        result = optimizer.optimize_sample_size(
            {}, failing_cost_function, power_function
        )
        
        assert result["optimization_success"] is False
        assert "error" in result


class TestEvidenceSynthesizer:
    """Test cases for EvidenceSynthesizer class."""

    def test_initialization(self):
        """Test EvidenceSynthesizer initialization."""
        synthesizer = EvidenceSynthesizer(enable_literature_search=True)
        
        assert synthesizer.enable_literature_search is True
        assert synthesizer.evidence_database is not None
        assert "randomized_controlled_trials" in synthesizer.evidence_database

    def test_find_similar_studies(self):
        """Test finding similar studies."""
        synthesizer = EvidenceSynthesizer()
        
        study_params = {
            "domain": "cardiovascular",
            "target_sample_size": 600,
            "target_power": 0.8
        }
        
        similar_studies = synthesizer.find_similar_studies(
            study_params, StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL, top_k=2
        )
        
        assert isinstance(similar_studies, list)
        assert len(similar_studies) <= 2
        
        if len(similar_studies) > 0:
            assert "similarity_score" in similar_studies[0]

    def test_calculate_similarity_high(self):
        """Test similarity calculation with high similarity."""
        synthesizer = EvidenceSynthesizer()
        
        target_params = {
            "domain": "cardiovascular",
            "target_sample_size": 500,
            "target_power": 0.8
        }
        
        study = {
            "domain": "cardiovascular",
            "sample_size": 500,
            "power": 0.8
        }
        
        similarity = synthesizer._calculate_similarity(target_params, study)
        
        assert 0.8 <= similarity <= 1.0

    def test_calculate_similarity_low(self):
        """Test similarity calculation with low similarity."""
        synthesizer = EvidenceSynthesizer()
        
        target_params = {
            "domain": "cardiovascular",
            "target_sample_size": 100,
            "target_power": 0.8
        }
        
        study = {
            "domain": "oncology",
            "sample_size": 2000,
            "power": 0.9
        }
        
        similarity = synthesizer._calculate_similarity(target_params, study)
        
        assert 0.0 <= similarity <= 0.5

    def test_calculate_similarity_error_handling(self):
        """Test error handling in similarity calculation."""
        synthesizer = EvidenceSynthesizer()
        
        # Invalid parameters that might cause errors
        target_params = {"invalid": None}
        study = {"invalid": None}
        
        similarity = synthesizer._calculate_similarity(target_params, study)
        
        assert similarity == 0.0  # Should return 0 on error


class TestMLPowerEngineIntegration:
    """Test integration between ML optimizer and statistical power engine."""
    
    @pytest.mark.asyncio
    async def test_advanced_power_integration(self, sample_study_requirements):
        """Test ML optimizer with advanced power analysis enabled."""
        optimizer = MLStudyDesignOptimizer(
            enable_advanced_power=True,
            enable_clinical_models=True
        )
        
        # Run optimization with power engine integration
        recommendation = await optimizer.optimize_study_design(sample_study_requirements)
        
        # Should have enhanced analysis
        assert recommendation.optimization_parameters.get("advanced_analysis", False) is True
        assert "test_type" in recommendation.optimization_parameters
        assert "power_curve_points" in recommendation.optimization_parameters
    
    @pytest.mark.asyncio
    async def test_adaptive_study_design(self, sample_study_requirements):
        """Test adaptive study design capability."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=True)
        
        # Design adaptive study
        adaptive_result = await optimizer.design_adaptive_study(
            study_requirements=sample_study_requirements,
            adaptive_type="group_sequential"
        )
        
        assert adaptive_result["integration_success"] is True
        assert "basic_recommendation" in adaptive_result
        assert "adaptive_design" in adaptive_result
        
        # Validate adaptive design components
        adaptive_design = adaptive_result["adaptive_design"]
        assert adaptive_design["design_type"] == "group_sequential"
        assert adaptive_design["initial_sample_size"] > 0
        assert adaptive_design["maximum_sample_size"] > adaptive_design["initial_sample_size"]
        assert "efficacy_boundaries" in adaptive_design
    
    @pytest.mark.asyncio
    async def test_bayesian_evidence_calculation(self, sample_study_requirements):
        """Test Bayesian evidence integration."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=True)
        
        prior_beliefs = {
            "prior_mean": 0.2,
            "prior_variance": 0.5,
            "non_informative": False
        }
        
        # Calculate Bayesian evidence
        bayesian_result = await optimizer.calculate_bayesian_evidence(
            study_requirements=sample_study_requirements,
            prior_beliefs=prior_beliefs
        )
        
        assert bayesian_result["bayesian_analysis"] is True
        assert "posterior_power" in bayesian_result
        assert "credible_interval" in bayesian_result
        assert "probability_of_success" in bayesian_result
        assert bayesian_result["method"] == "conjugate"
    
    @pytest.mark.asyncio
    async def test_test_type_mapping(self):
        """Test mapping from study design to statistical test types."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=True)
        
        # Test different study types
        test_cases = [
            {
                "research_type": "intervention",
                "primary_endpoint": {"type": "continuous"},
                "expected_test": "two_sample_t"
            },
            {
                "research_type": "observational",
                "primary_endpoint": {"type": "binary"},
                "expected_test": "prop_two_sample"
            }
        ]
        
        for case in test_cases:
            result = await optimizer.optimize_study_design(case)
            if result.optimization_parameters.get("advanced_analysis"):
                test_type = result.optimization_parameters.get("test_type")
                # Test type should be appropriately mapped
                assert test_type is not None
    
    @pytest.mark.asyncio
    async def test_fallback_when_advanced_disabled(self, sample_study_requirements):
        """Test fallback to simple methods when advanced power is disabled."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=False)
        
        result = await optimizer.optimize_study_design(sample_study_requirements)
        
        # Should fall back to simple optimization
        assert result.optimization_parameters.get("advanced_analysis", True) is False
        assert "test_type" not in result.optimization_parameters
    
    @pytest.mark.asyncio
    async def test_enhanced_recommendation_structure(self, sample_study_requirements):
        """Test enhanced recommendation with advanced components."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=True)
        
        result = await optimizer.optimize_study_design(sample_study_requirements)
        
        # Convert to dict and check for advanced components
        result_dict = result.to_dict()
        
        # Should have advanced analysis indicators
        if result.optimization_parameters.get("advanced_analysis"):
            assert "test_type" in result.optimization_parameters
            # May have power analysis details
            if "power_analysis_details" in result_dict:
                assert isinstance(result_dict["power_analysis_details"], dict)


class TestIntegration:
    """Integration tests for the complete ML optimization workflow."""

    @pytest.mark.asyncio
    async def test_full_optimization_workflow(self, sample_study_requirements):
        """Test complete optimization workflow from requirements to recommendation."""
        optimizer = MLStudyDesignOptimizer()
        
        # Run full optimization
        recommendation = await optimizer.optimize_study_design(sample_study_requirements)
        
        # Validate comprehensive recommendation
        assert isinstance(recommendation, StudyDesignRecommendation)
        assert recommendation.confidence_score > 0.0
        assert recommendation.estimated_sample_size > 0
        assert recommendation.expected_power > 0.0
        assert recommendation.estimated_duration_months > 0
        assert recommendation.estimated_cost > 0.0
        assert isinstance(recommendation.risk_factors, list)
        assert isinstance(recommendation.mitigation_strategies, list)
        assert isinstance(recommendation.required_approvals, list)
        
        # Test dictionary conversion
        rec_dict = recommendation.to_dict()
        assert isinstance(rec_dict, dict)
        assert "design_type" in rec_dict
        assert "confidence_score" in rec_dict

    @pytest.mark.asyncio
    async def test_different_study_types(self):
        """Test optimization for different study types."""
        optimizer = MLStudyDesignOptimizer()
        
        # Cohort study
        cohort_requirements = {
            "research_type": "observational",
            "domain": "epidemiology"
        }
        
        cohort_result = await optimizer.optimize_study_design(cohort_requirements)
        assert cohort_result.design_type in [
            StudyDesignType.COHORT_STUDY, StudyDesignType.CASE_CONTROL
        ]
        
        # Intervention study
        rct_requirements = {
            "research_type": "intervention",
            "intervention_type": "drug_therapy"
        }
        
        rct_result = await optimizer.optimize_study_design(rct_requirements)
        assert rct_result.design_type == StudyDesignType.RANDOMIZED_CONTROLLED_TRIAL

    @pytest.mark.asyncio
    async def test_optimization_reproducibility(self, sample_study_requirements):
        """Test that optimization produces consistent results."""
        optimizer1 = MLStudyDesignOptimizer()
        optimizer2 = MLStudyDesignOptimizer()
        
        result1 = await optimizer1.optimize_study_design(sample_study_requirements)
        result2 = await optimizer2.optimize_study_design(sample_study_requirements)
        
        # Should produce similar results (design type should be same)
        assert result1.design_type == result2.design_type
        assert result1.allocation_strategy == result2.allocation_strategy
        
        # Confidence scores should be reasonably close
        assert abs(result1.confidence_score - result2.confidence_score) < 0.2
    
    @pytest.mark.asyncio
    async def test_comprehensive_workflow_with_all_features(self, sample_study_requirements):
        """Test comprehensive workflow with all advanced features enabled."""
        optimizer = MLStudyDesignOptimizer(
            confidence_threshold=0.85,
            enable_clinical_models=True,
            literature_integration=True,
            enable_advanced_power=True
        )
        
        # Basic optimization
        basic_rec = await optimizer.optimize_study_design(sample_study_requirements)
        
        # Adaptive design
        adaptive_result = await optimizer.design_adaptive_study(
            sample_study_requirements, "group_sequential"
        )
        
        # Bayesian evidence
        bayesian_result = await optimizer.calculate_bayesian_evidence(
            sample_study_requirements,
            {"prior_mean": 0.0, "prior_variance": 1.0}
        )
        
        # All components should be successful
        assert isinstance(basic_rec, StudyDesignRecommendation)
        assert adaptive_result["integration_success"] is True
        assert bayesian_result["bayesian_analysis"] is True


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling in ML-Power integration."""
    
    @pytest.mark.asyncio
    async def test_invalid_adaptive_design_request(self):
        """Test handling of invalid adaptive design requests."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=False)
        
        # Should handle gracefully when advanced power is disabled
        result = await optimizer.design_adaptive_study(
            study_requirements={},
            adaptive_type="group_sequential"
        )
        
        assert result["integration_success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_bayesian_analysis_without_power_engine(self):
        """Test Bayesian analysis when power engine is disabled."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=False)
        
        result = await optimizer.calculate_bayesian_evidence(
            study_requirements={},
            prior_beliefs={}
        )
        
        assert result["bayesian_analysis"] is False
    
    @pytest.mark.asyncio
    async def test_optimization_with_missing_parameters(self):
        """Test optimization with missing or invalid parameters."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=True)
        
        minimal_requirements = {
            "research_type": "intervention"
            # Missing many expected parameters
        }
        
        # Should handle gracefully with defaults
        result = await optimizer.optimize_study_design(minimal_requirements)
        assert isinstance(result, StudyDesignRecommendation)
        assert result.estimated_sample_size > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_in_power_integration(self, sample_study_requirements):
        """Test error recovery when power engine encounters issues."""
        optimizer = MLStudyDesignOptimizer(enable_advanced_power=True)
        
        # Use requirements that might cause power engine issues
        problematic_requirements = sample_study_requirements.copy()
        problematic_requirements["expected_effect_size"] = 0.0  # Zero effect size
        problematic_requirements["max_sample_size"] = 10  # Very small max
        
        result = await optimizer.optimize_study_design(problematic_requirements)
        
        # Should still produce a valid recommendation
        assert isinstance(result, StudyDesignRecommendation)
        # May fall back to simple methods
        assert result.optimization_parameters.get("optimization_success") is not None


if __name__ == "__main__":
    pytest.main([__file__])