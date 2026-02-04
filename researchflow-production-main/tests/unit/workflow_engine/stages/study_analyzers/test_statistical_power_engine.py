"""
Unit tests for Statistical Power Engine

Tests the comprehensive statistical power analysis and sample size calculation
functionality including multiple test types and advanced methodologies.

Author: Stage 6 Enhancement Team
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

# Import the module under test
from services.worker.src.workflow_engine.stages.study_analyzers.statistical_power_engine import (
    StatisticalPowerEngine,
    PowerAnalysisResult,
    SampleSizeCalculation,
    StatisticalTestType,
    EffectSizeType,
    PowerCalculator,
    AdaptiveDesignCalculator,
    BayesianPowerCalculator,
    AdaptiveAnalysisResult,
    BayesianPowerResult,
    AdaptiveDesignType,
    BayesianMethod
)


@pytest.fixture
def power_engine():
    """Create Statistical Power Engine instance."""
    return StatisticalPowerEngine(
        default_power=0.8,
        default_alpha=0.05,
        enable_adaptive=True
    )


@pytest.fixture
def power_calculator():
    """Create PowerCalculator instance."""
    return PowerCalculator()


class TestPowerCalculator:
    """Test cases for PowerCalculator class."""
    
    def test_initialization(self, power_calculator):
        """Test PowerCalculator initialization."""
        assert power_calculator.calculation_history == []
    
    def test_t_test_power_one_sample(self, power_calculator):
        """Test one-sample t-test power calculation."""
        power = power_calculator.calculate_t_test_power(
            n1=30,
            n2=None,
            effect_size=0.5,
            alpha=0.05,
            test_type=StatisticalTestType.ONE_SAMPLE_T_TEST
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.3  # Should have reasonable power
    
    def test_t_test_power_two_sample(self, power_calculator):
        """Test two-sample t-test power calculation."""
        power = power_calculator.calculate_t_test_power(
            n1=30,
            n2=30,
            effect_size=0.5,
            alpha=0.05,
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.4  # Should have reasonable power
    
    def test_t_test_power_paired(self, power_calculator):
        """Test paired t-test power calculation."""
        power = power_calculator.calculate_t_test_power(
            n1=30,
            n2=None,
            effect_size=0.5,
            alpha=0.05,
            test_type=StatisticalTestType.PAIRED_T_TEST
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.3
    
    def test_proportion_test_power_one_sample(self, power_calculator):
        """Test one-sample proportion test power calculation."""
        power = power_calculator.calculate_proportion_test_power(
            n=100,
            p1=0.5,  # Null hypothesis
            p2=0.7,  # Alternative
            alpha=0.05,
            test_type=StatisticalTestType.PROPORTION_ONE_SAMPLE
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.5  # Should have good power with large effect
    
    def test_proportion_test_power_two_sample(self, power_calculator):
        """Test two-sample proportion test power calculation."""
        power = power_calculator.calculate_proportion_test_power(
            n=200,  # Total sample size
            p1=0.4,
            p2=0.6,
            alpha=0.05,
            test_type=StatisticalTestType.PROPORTION_TWO_SAMPLE
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.4
    
    def test_anova_power_calculation(self, power_calculator):
        """Test one-way ANOVA power calculation."""
        group_sizes = [30, 30, 30]
        effect_size = 0.3  # Cohen's f
        
        power = power_calculator.calculate_anova_power(
            group_sizes=group_sizes,
            effect_size=effect_size,
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.3
    
    def test_chi_square_power_calculation(self, power_calculator):
        """Test chi-square test power calculation."""
        power = power_calculator.calculate_chi_square_power(
            n=200,
            effect_size=0.3,  # Cohen's w
            df=1,
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.4
    
    def test_power_increases_with_sample_size(self, power_calculator):
        """Test that power increases with sample size."""
        power_small = power_calculator.calculate_t_test_power(
            n1=20, n2=20, effect_size=0.5, alpha=0.05
        )
        power_large = power_calculator.calculate_t_test_power(
            n1=50, n2=50, effect_size=0.5, alpha=0.05
        )
        
        assert power_large > power_small
    
    def test_power_increases_with_effect_size(self, power_calculator):
        """Test that power increases with effect size."""
        power_small_effect = power_calculator.calculate_t_test_power(
            n1=30, n2=30, effect_size=0.2, alpha=0.05
        )
        power_large_effect = power_calculator.calculate_t_test_power(
            n1=30, n2=30, effect_size=0.8, alpha=0.05
        )
        
        assert power_large_effect > power_small_effect
    
    def test_correlation_power_calculation(self, power_calculator):
        """Test correlation power calculation."""
        power = power_calculator.calculate_correlation_power(
            n=50,
            effect_size=0.4,  # Medium correlation
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.3  # Should have reasonable power
    
    def test_regression_power_calculation(self, power_calculator):
        """Test multiple regression power calculation."""
        power = power_calculator.calculate_regression_power(
            n=100,
            effect_size=0.15,  # R² = 0.15
            num_predictors=3,
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.4
    
    def test_survival_logrank_power_calculation(self, power_calculator):
        """Test log-rank test power calculation."""
        power = power_calculator.calculate_survival_logrank_power(
            n1=50,
            n2=50,
            hazard_ratio=0.7,  # 30% risk reduction
            event_rate=0.6,
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.3
    
    def test_mann_whitney_power_calculation(self, power_calculator):
        """Test Mann-Whitney U test power calculation."""
        power = power_calculator.calculate_mann_whitney_power(
            n1=40,
            n2=40,
            effect_size=0.65,  # Probability of superiority
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.3
    
    def test_wilcoxon_signed_rank_power_calculation(self, power_calculator):
        """Test Wilcoxon signed-rank test power calculation."""
        power = power_calculator.calculate_wilcoxon_signed_rank_power(
            n=30,
            effect_size=0.65,  # Probability of positive difference
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.2
    
    def test_fisher_exact_power_calculation(self, power_calculator):
        """Test Fisher's exact test power calculation."""
        power = power_calculator.calculate_fisher_exact_power(
            n=60,
            p1=0.3,
            p2=0.6,
            alpha=0.05
        )
        
        assert 0.0 <= power <= 1.0
        assert power > 0.4  # Should have good power with large effect


class TestStatisticalPowerEngine:
    """Test cases for StatisticalPowerEngine class."""
    
    def test_initialization(self):
        """Test StatisticalPowerEngine initialization."""
        engine = StatisticalPowerEngine(
            default_power=0.9,
            default_alpha=0.01,
            enable_adaptive=False
        )
        
        assert engine.default_power == 0.9
        assert engine.default_alpha == 0.01
        assert engine.enable_adaptive is False
        assert engine.calculator is not None
    
    @pytest.mark.asyncio
    async def test_calculate_power_t_test(self, power_engine):
        """Test power calculation for t-test."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size=60,  # 30 per group
            effect_size=0.5,
            alpha=0.05
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.test_type == StatisticalTestType.TWO_SAMPLE_T_TEST
        assert 0.0 <= result.power <= 1.0
        assert result.alpha == 0.05
        assert result.effect_size == 0.5
        assert result.effect_size_type == EffectSizeType.COHEN_D
        assert result.sample_size_total == 60
    
    @pytest.mark.asyncio
    async def test_calculate_power_proportion_test(self, power_engine):
        """Test power calculation for proportion test."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.PROPORTION_TWO_SAMPLE,
            sample_size=200,
            effect_size=0.3,
            alpha=0.05,
            p1=0.4,
            p2=0.6
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.test_type == StatisticalTestType.PROPORTION_TWO_SAMPLE
        assert result.effect_size_type == EffectSizeType.COHEN_W
        assert result.sample_size_total == 200
    
    @pytest.mark.asyncio
    async def test_calculate_power_anova(self, power_engine):
        """Test power calculation for ANOVA."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.ONE_WAY_ANOVA,
            sample_size=[30, 30, 30],
            effect_size=0.25,
            alpha=0.05
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.test_type == StatisticalTestType.ONE_WAY_ANOVA
        assert result.effect_size_type == EffectSizeType.COHEN_F
        assert result.sample_size_total == 90
        assert result.sample_size_per_group == [30, 30, 30]
    
    @pytest.mark.asyncio
    async def test_calculate_power_chi_square(self, power_engine):
        """Test power calculation for chi-square test."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.CHI_SQUARE_INDEPENDENCE,
            sample_size=150,
            effect_size=0.3,
            alpha=0.05,
            df=1
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.test_type == StatisticalTestType.CHI_SQUARE_INDEPENDENCE
        assert result.effect_size_type == EffectSizeType.COHEN_W
    
    @pytest.mark.asyncio
    async def test_calculate_power_with_default_alpha(self, power_engine):
        """Test power calculation using default alpha."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size=60,
            effect_size=0.5
            # No alpha specified - should use default
        )
        
        assert result.alpha == power_engine.default_alpha
    
    @pytest.mark.asyncio
    async def test_calculate_power_unsupported_test(self, power_engine):
        """Test power calculation for unsupported test type."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.SURVIVAL_LOGRANK,  # Not implemented yet
            sample_size=100,
            effect_size=0.5
        )
        
        # Should handle gracefully
        assert isinstance(result, PowerAnalysisResult)
        assert len(result.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_calculate_sample_size_t_test(self, power_engine):
        """Test sample size calculation for t-test."""
        result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.8,
            effect_size=0.5,
            alpha=0.05
        )
        
        assert isinstance(result, SampleSizeCalculation)
        assert result.required_sample_size > 0
        assert result.target_power == 0.8
        assert result.test_type == StatisticalTestType.TWO_SAMPLE_T_TEST
        assert result.convergence_achieved is True
        assert len(result.sample_size_per_group) == 2  # Two groups
    
    @pytest.mark.asyncio
    async def test_calculate_sample_size_proportion_test(self, power_engine):
        """Test sample size calculation for proportion test."""
        result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.PROPORTION_TWO_SAMPLE,
            target_power=0.8,
            effect_size=0.3,
            alpha=0.05,
            p1=0.4,
            p2=0.6
        )
        
        assert isinstance(result, SampleSizeCalculation)
        assert result.required_sample_size > 0
        assert result.power_achieved >= 0.7  # Should achieve close to target
    
    @pytest.mark.asyncio
    async def test_calculate_sample_size_one_sample_test(self, power_engine):
        """Test sample size calculation for one-sample test."""
        result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.ONE_SAMPLE_T_TEST,
            target_power=0.8,
            effect_size=0.5,
            alpha=0.05
        )
        
        assert isinstance(result, SampleSizeCalculation)
        assert result.total_groups == 1
        assert len(result.sample_size_per_group) == 1
    
    @pytest.mark.asyncio
    async def test_sample_size_scales_with_power(self, power_engine):
        """Test that required sample size increases with target power."""
        result_low = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.7,
            effect_size=0.5
        )
        
        result_high = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.9,
            effect_size=0.5
        )
        
        assert result_high.required_sample_size > result_low.required_sample_size
    
    @pytest.mark.asyncio
    async def test_sample_size_scales_with_effect_size(self, power_engine):
        """Test that required sample size decreases with larger effect size."""
        result_small_effect = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.8,
            effect_size=0.2
        )
        
        result_large_effect = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.8,
            effect_size=0.8
        )
        
        assert result_small_effect.required_sample_size > result_large_effect.required_sample_size
    
    @pytest.mark.asyncio
    async def test_power_curve_generation(self, power_engine):
        """Test that power curve points are generated."""
        result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.8,
            effect_size=0.5
        )
        
        assert result.power_curve_points is not None
        assert len(result.power_curve_points) > 0
        
        # Check that curve points are reasonable
        for n, power in result.power_curve_points:
            assert n > 0
            assert 0.0 <= power <= 1.0


class TestDataStructures:
    """Test cases for data structure classes."""
    
    def test_power_analysis_result_to_dict(self):
        """Test PowerAnalysisResult to dictionary conversion."""
        result = PowerAnalysisResult(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            power=0.85,
            alpha=0.05,
            effect_size=0.5,
            effect_size_type=EffectSizeType.COHEN_D,
            sample_size_total=60,
            sample_size_per_group=[30, 30],
            warnings=["Test warning"],
            recommendations=["Test recommendation"]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["test_type"] == "two_sample_t"
        assert result_dict["power"] == 0.85
        assert result_dict["effect_size_type"] == "cohen_d"
        assert result_dict["sample_size_per_group"] == [30, 30]
        assert "Test warning" in result_dict["warnings"]
    
    def test_sample_size_calculation_to_dict(self):
        """Test SampleSizeCalculation to dictionary conversion."""
        result = SampleSizeCalculation(
            required_sample_size=128,
            power_achieved=0.81,
            target_power=0.8,
            alpha=0.05,
            effect_size=0.5,
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size_per_group=[64, 64],
            total_groups=2,
            allocation_ratio=[1.0, 1.0]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["required_sample_size"] == 128
        assert result_dict["power_achieved"] == 0.81
        assert result_dict["test_type"] == "two_sample_t"
        assert result_dict["total_groups"] == 2


class TestIntegration:
    """Integration tests for the complete power analysis workflow."""
    
    @pytest.mark.asyncio
    async def test_power_and_sample_size_consistency(self, power_engine):
        """Test consistency between power calculation and sample size calculation."""
        # Calculate required sample size for 80% power
        sample_size_result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            target_power=0.8,
            effect_size=0.5,
            alpha=0.05
        )
        
        # Calculate power with that sample size
        power_result = await power_engine.calculate_power(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size=sample_size_result.required_sample_size,
            effect_size=0.5,
            alpha=0.05
        )
        
        # Power should be close to target
        assert abs(power_result.power - 0.8) < 0.1
    
    @pytest.mark.asyncio
    async def test_multiple_test_types_workflow(self, power_engine):
        """Test workflow with multiple statistical test types."""
        test_configs = [
            (StatisticalTestType.ONE_SAMPLE_T_TEST, 0.5),
            (StatisticalTestType.TWO_SAMPLE_T_TEST, 0.5),
            (StatisticalTestType.PROPORTION_TWO_SAMPLE, 0.3),
            (StatisticalTestType.ONE_WAY_ANOVA, 0.25)
        ]
        
        results = []
        for test_type, effect_size in test_configs:
            kwargs = {}
            if test_type == StatisticalTestType.PROPORTION_TWO_SAMPLE:
                kwargs = {"p1": 0.4, "p2": 0.6}
            elif test_type == StatisticalTestType.ONE_WAY_ANOVA:
                kwargs = {"num_groups": 3}
            
            result = await power_engine.calculate_sample_size(
                test_type=test_type,
                target_power=0.8,
                effect_size=effect_size,
                **kwargs
            )
            results.append(result)
        
        # All calculations should succeed
        assert len(results) == 4
        for result in results:
            assert result.required_sample_size > 0
            assert result.convergence_achieved is True
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, power_engine):
        """Test error handling in complete workflow."""
        # Test with invalid parameters
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size=0,  # Invalid sample size
            effect_size=0.5
        )
        
        # Should handle gracefully
        assert isinstance(result, PowerAnalysisResult)
        assert result.power == 0.0  # Should return minimal result
    
    @pytest.mark.asyncio
    async def test_recommendations_generation(self, power_engine):
        """Test that appropriate recommendations are generated."""
        # Test low power scenario
        low_power_result = await power_engine.calculate_power(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size=20,  # Very small sample
            effect_size=0.2  # Small effect
        )
        
        assert len(low_power_result.recommendations) > 0
        assert len(low_power_result.warnings) > 0
        
        # Test high power scenario
        high_power_result = await power_engine.calculate_power(
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST,
            sample_size=1000,  # Very large sample
            effect_size=0.8  # Large effect
        )
        
        assert len(high_power_result.recommendations) > 0


class TestAdaptiveDesignCalculator:
    """Test cases for AdaptiveDesignCalculator."""
    
    @pytest.fixture
    def adaptive_calculator(self):
        """Create AdaptiveDesignCalculator instance."""
        return AdaptiveDesignCalculator()
    
    def test_initialization(self, adaptive_calculator):
        """Test AdaptiveDesignCalculator initialization."""
        assert adaptive_calculator.design_history == []
    
    def test_group_sequential_boundaries_obrien_fleming(self, adaptive_calculator):
        """Test O'Brien-Fleming boundary calculation."""
        information_fractions = [0.5, 1.0]
        efficacy_bounds, futility_bounds = adaptive_calculator.calculate_group_sequential_boundaries(
            alpha=0.05,
            information_fractions=information_fractions,
            spending_function="obrien_fleming"
        )
        
        assert len(efficacy_bounds) == 2
        assert len(futility_bounds) == 2
        assert efficacy_bounds[0] > efficacy_bounds[1]  # Earlier bound should be higher
        assert all(b > 0 for b in efficacy_bounds)
    
    def test_group_sequential_boundaries_pocock(self, adaptive_calculator):
        """Test Pocock boundary calculation."""
        information_fractions = [0.33, 0.67, 1.0]
        efficacy_bounds, futility_bounds = adaptive_calculator.calculate_group_sequential_boundaries(
            alpha=0.05,
            information_fractions=information_fractions,
            spending_function="pocock"
        )
        
        assert len(efficacy_bounds) == 3
        # Pocock boundaries should be approximately constant
        assert abs(efficacy_bounds[0] - efficacy_bounds[1]) < 0.1
    
    def test_conditional_power_calculation(self, adaptive_calculator):
        """Test conditional power calculation."""
        conditional_power = adaptive_calculator.calculate_conditional_power(
            interim_effect=0.5,
            interim_n=50,
            final_n=100,
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST
        )
        
        assert 0.0 <= conditional_power <= 1.0
        assert conditional_power > 0.3  # Should have reasonable power with effect
    
    def test_sample_size_reestimation(self, adaptive_calculator):
        """Test sample size reestimation."""
        reestimated_n = adaptive_calculator.calculate_sample_size_reestimation(
            interim_variance=4.0,  # Higher than planned
            planned_variance=1.0,
            original_n=100,
            target_power=0.8
        )
        
        assert reestimated_n > 100  # Should increase due to higher variance
        assert reestimated_n <= 300  # Should respect maximum bound
    
    def test_sample_size_reestimation_lower_variance(self, adaptive_calculator):
        """Test sample size reestimation with lower variance."""
        reestimated_n = adaptive_calculator.calculate_sample_size_reestimation(
            interim_variance=0.25,  # Lower than planned
            planned_variance=1.0,
            original_n=100,
            target_power=0.8
        )
        
        assert reestimated_n >= 50  # Should respect minimum bound
        assert reestimated_n < 100  # Should decrease due to lower variance


class TestBayesianPowerCalculator:
    """Test cases for BayesianPowerCalculator."""
    
    @pytest.fixture
    def bayesian_calculator(self):
        """Create BayesianPowerCalculator instance."""
        return BayesianPowerCalculator()
    
    def test_initialization(self, bayesian_calculator):
        """Test BayesianPowerCalculator initialization."""
        assert bayesian_calculator.prior_history == []
    
    def test_conjugate_prior_power(self, bayesian_calculator):
        """Test Bayesian power with conjugate prior."""
        result = bayesian_calculator.calculate_bayesian_power(
            n=100,
            effect_size=0.5,
            prior_mean=0.0,
            prior_variance=1.0,
            decision_threshold=0.95,
            method=BayesianMethod.CONJUGATE_PRIOR
        )
        
        assert isinstance(result, BayesianPowerResult)
        assert 0.0 <= result.posterior_power <= 1.0
        assert result.method == BayesianMethod.CONJUGATE_PRIOR
        assert len(result.credible_interval) == 2
        assert result.credible_interval[0] < result.credible_interval[1]
    
    def test_jeffrey_prior_power(self, bayesian_calculator):
        """Test Bayesian power with Jeffrey's prior."""
        result = bayesian_calculator.calculate_bayesian_power(
            n=50,
            effect_size=0.3,
            method=BayesianMethod.JEFFREY_PRIOR
        )
        
        assert isinstance(result, BayesianPowerResult)
        assert 0.0 <= result.posterior_power <= 1.0
        assert result.method == BayesianMethod.JEFFREY_PRIOR
    
    def test_posterior_probability_calculation(self, bayesian_calculator):
        """Test posterior probability calculation."""
        # Generate some mock data
        observed_data = np.array([0.5, 0.3, 0.7, 0.4, 0.6])
        
        prob = bayesian_calculator.calculate_posterior_probability(
            observed_data=observed_data,
            null_value=0.0,
            prior_mean=0.0,
            prior_variance=1.0
        )
        
        assert 0.0 <= prob <= 1.0
        assert prob > 0.5  # Should favor positive effect with positive data
    
    def test_bayesian_power_scales_with_sample_size(self, bayesian_calculator):
        """Test that Bayesian power increases with sample size."""
        result_small = bayesian_calculator.calculate_bayesian_power(
            n=20, effect_size=0.3, prior_mean=0.0, prior_variance=1.0
        )
        
        result_large = bayesian_calculator.calculate_bayesian_power(
            n=200, effect_size=0.3, prior_mean=0.0, prior_variance=1.0
        )
        
        assert result_large.posterior_power >= result_small.posterior_power


class TestAdaptiveAndBayesianIntegration:
    """Integration tests for adaptive and Bayesian methods in StatisticalPowerEngine."""
    
    @pytest.mark.asyncio
    async def test_design_group_sequential_study(self, power_engine):
        """Test group sequential design."""
        result = await power_engine.design_adaptive_study(
            design_type=AdaptiveDesignType.GROUP_SEQUENTIAL,
            initial_n=100,
            max_n=200,
            alpha=0.05,
            interim_fractions=[0.5, 1.0],
            spending_function="obrien_fleming"
        )
        
        assert isinstance(result, AdaptiveAnalysisResult)
        assert result.design_type == AdaptiveDesignType.GROUP_SEQUENTIAL
        assert result.initial_sample_size == 100
        assert result.maximum_sample_size == 200
        assert len(result.interim_analyses) == 2
        assert result.efficacy_boundaries is not None
        assert result.alpha_spending_function == "obrien_fleming"
        assert result.type_i_error_control is True
    
    @pytest.mark.asyncio
    async def test_design_sample_size_reestimation_study(self, power_engine):
        """Test sample size reestimation design."""
        result = await power_engine.design_adaptive_study(
            design_type=AdaptiveDesignType.SAMPLE_SIZE_REESTIMATION,
            initial_n=80,
            max_n=160
        )
        
        assert isinstance(result, AdaptiveAnalysisResult)
        assert result.design_type == AdaptiveDesignType.SAMPLE_SIZE_REESTIMATION
        assert result.expected_sample_size > 0
    
    @pytest.mark.asyncio
    async def test_bayesian_power_calculation(self, power_engine):
        """Test Bayesian power calculation through main engine."""
        prior_spec = {
            "mean": 0.0,
            "variance": 1.0
        }
        
        result = await power_engine.calculate_bayesian_power(
            sample_size=100,
            effect_size=0.4,
            prior_specification=prior_spec,
            method=BayesianMethod.CONJUGATE_PRIOR
        )
        
        assert isinstance(result, BayesianPowerResult)
        assert 0.0 <= result.posterior_power <= 1.0
        assert result.prior_specification == prior_spec
    
    @pytest.mark.asyncio
    async def test_conditional_power_calculation(self, power_engine):
        """Test conditional power calculation."""
        interim_data = {
            "effect_size": 0.3,
            "sample_size": 50
        }
        
        conditional_power = await power_engine.calculate_conditional_power(
            interim_data=interim_data,
            final_n=100,
            test_type=StatisticalTestType.TWO_SAMPLE_T_TEST
        )
        
        assert 0.0 <= conditional_power <= 1.0
    
    @pytest.mark.asyncio
    async def test_sample_size_reestimation_integration(self, power_engine):
        """Test sample size reestimation integration."""
        interim_data = {
            "variance": 2.0,
            "planned_variance": 1.0
        }
        
        reestimated_n = await power_engine.reestimate_sample_size(
            interim_data=interim_data,
            original_n=100,
            target_power=0.8
        )
        
        assert isinstance(reestimated_n, int)
        assert reestimated_n > 100  # Should increase due to higher variance
    
    @pytest.mark.asyncio
    async def test_adaptive_disabled_fallback(self):
        """Test behavior when adaptive designs are disabled."""
        engine = StatisticalPowerEngine(enable_adaptive=False)
        
        # Should handle gracefully when adaptive is disabled
        conditional_power = await engine.calculate_conditional_power(
            interim_data={"effect_size": 0.3, "sample_size": 50},
            final_n=100
        )
        
        assert conditional_power == 0.5  # Default fallback


class TestAdvancedStatisticalMethods:
    """Test cases for advanced statistical methods."""
    
    @pytest.mark.asyncio
    async def test_calculate_power_correlation(self, power_engine):
        """Test power calculation for correlation analysis."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.CORRELATION,
            sample_size=80,
            effect_size=0.35,  # Medium correlation
            alpha=0.05
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.test_type == StatisticalTestType.CORRELATION
        assert result.effect_size_type == EffectSizeType.PEARSON_R
        assert 0.0 <= result.power <= 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_power_survival(self, power_engine):
        """Test power calculation for survival analysis."""
        result = await power_engine.calculate_power(
            test_type=StatisticalTestType.SURVIVAL_LOGRANK,
            sample_size=[60, 60],
            effect_size=0.7,  # Hazard ratio
            alpha=0.05,
            event_rate=0.6
        )
        
        assert isinstance(result, PowerAnalysisResult)
        assert result.test_type == StatisticalTestType.SURVIVAL_LOGRANK
        assert result.effect_size_type == EffectSizeType.HAZARD_RATIO
        assert result.sample_size_per_group == [60, 60]
    
    @pytest.mark.asyncio
    async def test_advanced_sample_size_calculations(self, power_engine):
        """Test sample size calculations for advanced tests."""
        # Correlation analysis
        corr_result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.CORRELATION,
            target_power=0.8,
            effect_size=0.3  # Medium correlation
        )
        
        assert corr_result.required_sample_size > 0
        assert corr_result.total_groups == 1
        
        # Mann-Whitney test
        mw_result = await power_engine.calculate_sample_size(
            test_type=StatisticalTestType.MANN_WHITNEY,
            target_power=0.8,
            effect_size=0.65
        )
        
        assert mw_result.required_sample_size > 0
        assert mw_result.total_groups == 2


if __name__ == "__main__":
    pytest.main([__file__])