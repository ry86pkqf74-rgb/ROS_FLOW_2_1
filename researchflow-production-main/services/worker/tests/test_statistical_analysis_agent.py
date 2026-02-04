"""
Unit Tests for StatisticalAnalysisAgent

Comprehensive tests for statistical analysis functionality including:
- Descriptive statistics calculation
- Hypothesis testing (t-tests, ANOVA, non-parametric)
- Effect size calculations
- Assumption checking
- APA formatting
- Quality checks

Linear Issues: ROS-XXX (Stage 7 - Statistical Analysis Agent)
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.analysis.statistical_analysis_agent import (
    StatisticalAnalysisAgent,
    create_statistical_analysis_agent,
)
from agents.analysis.statistical_types import (
    StudyData,
    TestType,
    DescriptiveStats,
    HypothesisTestResult,
    EffectSize,
    AssumptionCheckResult,
    StatisticalResult,
)
from agents.analysis.statistical_utils import (
    calculate_cohens_d,
    calculate_hedges_g,
    calculate_eta_squared,
    interpret_effect_size_magnitude,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_two_group_data():
    """Sample data for two-group comparison."""
    np.random.seed(42)
    group_a = pd.Series(np.random.normal(5.0, 1.0, 30), name="group_a")
    group_b = pd.Series(np.random.normal(5.5, 1.0, 30), name="group_b")
    return group_a, group_b


@pytest.fixture
def sample_three_group_data():
    """Sample data for three-group comparison (ANOVA)."""
    np.random.seed(42)
    group_a = pd.Series(np.random.normal(5.0, 1.0, 20), name="group_a")
    group_b = pd.Series(np.random.normal(5.5, 1.0, 20), name="group_b")
    group_c = pd.Series(np.random.normal(6.0, 1.0, 20), name="group_c")
    return [group_a, group_b, group_c]


@pytest.fixture
def sample_study_data():
    """Sample StudyData object."""
    np.random.seed(42)
    return StudyData(
        groups=["treatment"] * 30 + ["control"] * 30,
        outcomes={
            "hba1c": list(np.random.normal(6.5, 0.8, 30)) + list(np.random.normal(7.2, 0.9, 30))
        },
        metadata={
            "study_title": "Test RCT",
            "study_design": "RCT",
            "research_id": "test_001"
        }
    )


# =============================================================================
# Descriptive Statistics Tests
# =============================================================================

class TestDescriptiveStatistics:
    """Tests for descriptive statistics calculation."""
    
    def test_calculate_single_descriptive(self, sample_two_group_data):
        """Test calculating descriptive stats for single group."""
        agent = StatisticalAnalysisAgent()
        group_a, _ = sample_two_group_data
        
        stats = agent._calculate_single_descriptive(group_a, "outcome", "Group A")
        
        assert stats.variable_name == "outcome"
        assert stats.group_name == "Group A"
        assert stats.n == 30
        assert stats.missing == 0
        assert 4.5 < stats.mean < 5.5  # Approximately 5.0
        assert 0.8 < stats.std < 1.2    # Approximately 1.0
    
    def test_calculate_descriptive_stats_grouped(self):
        """Test descriptive stats with grouping."""
        agent = StatisticalAnalysisAgent()
        
        df = pd.DataFrame({
            "outcome": [5, 6, 7, 8, 9, 10],
            "group": ["A", "A", "A", "B", "B", "B"]
        })
        
        stats_list = agent.calculate_descriptive_stats(df, "outcome", "group")
        
        assert len(stats_list) == 2
        assert stats_list[0].group_name in ["A", "B"]
        assert stats_list[1].group_name in ["A", "B"]
    
    def test_descriptive_stats_apa_format(self):
        """Test APA formatting of descriptive stats."""
        stats = DescriptiveStats(
            variable_name="test",
            n=30,
            missing=0,
            mean=5.23,
            median=5.1,
            std=1.15,
            min_value=3.0,
            max_value=7.5,
            q25=4.5,
            q75=6.0,
            iqr=1.5
        )
        
        apa = stats.format_apa()
        assert "M(SD)" in apa
        assert "5.23" in apa
        assert "1.15" in apa


# =============================================================================
# Hypothesis Testing Tests
# =============================================================================

class TestHypothesisTesting:
    """Tests for hypothesis testing methods."""
    
    def test_t_test_independent(self, sample_two_group_data):
        """Test independent t-test."""
        agent = StatisticalAnalysisAgent()
        group_a, group_b = sample_two_group_data
        
        result = agent._run_t_test_independent(group_a, group_b)
        
        assert result.test_type == TestType.T_TEST_INDEPENDENT
        assert result.p_value >= 0  # P-value should be valid
        assert result.df == 58  # 30 + 30 - 2
        assert result.ci_lower is not None
        assert result.ci_upper is not None
    
    def test_mann_whitney(self, sample_two_group_data):
        """Test Mann-Whitney U test."""
        agent = StatisticalAnalysisAgent()
        group_a, group_b = sample_two_group_data
        
        result = agent._run_mann_whitney(group_a, group_b)
        
        assert result.test_type == TestType.MANN_WHITNEY
        assert 0 <= result.p_value <= 1
    
    def test_anova_oneway(self, sample_three_group_data):
        """Test one-way ANOVA."""
        agent = StatisticalAnalysisAgent()
        groups = sample_three_group_data
        
        result = agent._run_anova_oneway(groups)
        
        assert result.test_type == TestType.ANOVA_ONEWAY
        assert isinstance(result.df, tuple)
        assert result.df[0] == 2  # k - 1 = 3 - 1
        assert result.df[1] == 57  # n - k = 60 - 3
    
    def test_kruskal_wallis(self, sample_three_group_data):
        """Test Kruskal-Wallis H test."""
        agent = StatisticalAnalysisAgent()
        groups = sample_three_group_data
        
        result = agent._run_kruskal_wallis(groups)
        
        assert result.test_type == TestType.KRUSKAL_WALLIS
        assert result.df == 2  # k - 1
    
    def test_apa_formatting(self, sample_two_group_data):
        """Test APA formatting of test results."""
        agent = StatisticalAnalysisAgent()
        group_a, group_b = sample_two_group_data
        
        result = agent._run_t_test_independent(group_a, group_b)
        apa_str = result.format_apa()
        
        assert "t(" in apa_str
        assert "p " in apa_str
        assert result.df in [int(s) for s in apa_str.split() if s.isdigit()]


# =============================================================================
# Effect Size Tests
# =============================================================================

class TestEffectSizes:
    """Tests for effect size calculations."""
    
    def test_cohens_d_calculation(self, sample_two_group_data):
        """Test Cohen's d calculation."""
        group_a, group_b = sample_two_group_data
        
        d = calculate_cohens_d(group_a, group_b)
        
        assert isinstance(d, float)
        assert -3 < d < 3  # Reasonable range for Cohen's d
    
    def test_hedges_g_calculation(self, sample_two_group_data):
        """Test Hedges' g calculation."""
        group_a, group_b = sample_two_group_data
        
        g = calculate_hedges_g(group_a, group_b)
        
        # Hedges' g should be slightly smaller than Cohen's d
        d = calculate_cohens_d(group_a, group_b)
        assert abs(g) < abs(d) + 0.1
    
    def test_eta_squared_calculation(self, sample_three_group_data):
        """Test eta-squared calculation."""
        groups = sample_three_group_data
        
        eta_sq = calculate_eta_squared(groups)
        
        assert 0 <= eta_sq <= 1  # Eta-squared is between 0 and 1
    
    def test_effect_size_interpretation(self):
        """Test effect size interpretation."""
        # Cohen's d
        assert interpret_effect_size_magnitude(0.1, "cohens_d") == "negligible"
        assert interpret_effect_size_magnitude(0.3, "cohens_d") == "small"
        assert interpret_effect_size_magnitude(0.6, "cohens_d") == "medium"
        assert interpret_effect_size_magnitude(0.9, "cohens_d") == "large"
        
        # Eta-squared
        assert interpret_effect_size_magnitude(0.005, "eta_squared") == "negligible"
        assert interpret_effect_size_magnitude(0.03, "eta_squared") == "small"
        assert interpret_effect_size_magnitude(0.10, "eta_squared") == "medium"
        assert interpret_effect_size_magnitude(0.20, "eta_squared") == "large"
    
    def test_calculate_effect_size_method(self, sample_two_group_data):
        """Test agent's calculate_effect_size method."""
        agent = StatisticalAnalysisAgent()
        group_a, group_b = sample_two_group_data
        
        effect_size = agent.calculate_effect_size([group_a, group_b], TestType.T_TEST_INDEPENDENT)
        
        assert effect_size.cohens_d is not None
        assert effect_size.hedges_g is not None
        assert effect_size.magnitude in ["negligible", "small", "medium", "large"]


# =============================================================================
# Assumption Checking Tests
# =============================================================================

class TestAssumptionChecking:
    """Tests for statistical assumption checking."""
    
    def test_check_normality(self):
        """Test normality checking."""
        agent = StatisticalAnalysisAgent()
        
        # Create normal data
        np.random.seed(42)
        df = pd.DataFrame({
            "outcome": np.random.normal(5, 1, 100),
            "group": ["A"] * 50 + ["B"] * 50
        })
        
        result = agent._check_normality(df, "outcome", "group")
        
        assert "tests" in result or "statistic" in result
        assert "passed" in result
    
    def test_check_homogeneity(self):
        """Test homogeneity of variance checking."""
        agent = StatisticalAnalysisAgent()
        
        np.random.seed(42)
        df = pd.DataFrame({
            "outcome": list(np.random.normal(5, 1, 50)) + list(np.random.normal(5, 1.5, 50)),
            "group": ["A"] * 50 + ["B"] * 50
        })
        
        result = agent._check_homogeneity(df, "outcome", "group")
        
        assert "test" in result or "note" in result
        assert "passed" in result
    
    def test_check_assumptions_with_remediation(self):
        """Test assumption checking with remediation suggestions."""
        agent = StatisticalAnalysisAgent()
        
        # Create non-normal data (uniform distribution)
        np.random.seed(42)
        df = pd.DataFrame({
            "outcome": np.random.uniform(0, 10, 100),
            "group": ["A"] * 50 + ["B"] * 50
        })
        
        result = agent.check_assumptions(df, TestType.T_TEST_INDEPENDENT, "group", "outcome")
        
        assert isinstance(result, AssumptionCheckResult)
        assert hasattr(result, "remediation_suggestions")
        assert hasattr(result, "alternative_tests")


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
class TestStatisticalAnalysisAgent:
    """Integration tests for StatisticalAnalysisAgent."""
    
    async def test_agent_initialization(self):
        """Test agent initializes correctly."""
        agent = StatisticalAnalysisAgent()
        
        assert agent.config.name == "StatisticalAnalysisAgent"
        assert 7 in agent.config.stages
        assert agent.config.phi_safe is True
        assert agent.config.quality_threshold == 0.85
    
    @patch('agents.analysis.statistical_analysis_agent.BaseAgent.run')
    async def test_execute_analysis(self, mock_run, sample_study_data):
        """Test executing complete analysis."""
        # Mock agent run result
        mock_run.return_value = MagicMock(
            success=True,
            result={
                "descriptive": [{
                    "variable": "hba1c",
                    "group": "treatment",
                    "n": 30,
                    "mean": 6.5,
                    "std": 0.8,
                    "median": 6.4,
                    "iqr": 1.0
                }],
                "inferential": {
                    "test_name": "Independent t-test",
                    "test_type": "t_test_independent",
                    "statistic": 3.45,
                    "p_value": 0.001,
                    "df": 58
                },
                "effect_sizes": {
                    "cohens_d": 0.89,
                    "interpretation": "large effect"
                },
                "assumptions": {
                    "passed": True
                }
            }
        )
        
        agent = StatisticalAnalysisAgent()
        result = await agent.execute(sample_study_data)
        
        assert isinstance(result, StatisticalResult)
        assert len(result.descriptive) > 0
        assert result.inferential is not None or mock_run.called
    
    def test_factory_function(self):
        """Test factory function creates agent."""
        agent = create_statistical_analysis_agent()
        
        assert isinstance(agent, StatisticalAnalysisAgent)
        assert agent.config.name == "StatisticalAnalysisAgent"


# =============================================================================
# Quality Check Tests
# =============================================================================

@pytest.mark.asyncio
class TestQualityChecks:
    """Tests for quality checking functionality."""
    
    async def test_quality_check_complete_analysis(self):
        """Test quality check with complete analysis."""
        agent = StatisticalAnalysisAgent()
        
        state = {
            "execution_result": {
                "descriptive": [{"variable": "test", "n": 30}],
                "assumptions": {
                    "normality": {"passed": True},
                    "homogeneity": {"passed": True}
                },
                "inferential": {
                    "test_name": "t-test",
                    "p_value": 0.01,
                    "statistic": 2.5,
                    "df": 28
                },
                "effect_sizes": {
                    "cohens_d": 0.5,
                    "interpretation": "medium effect"
                }
            }
        }
        
        result = await agent._check_quality(state)
        
        assert result.score >= 0.85  # Should pass threshold
        assert result.passed
    
    async def test_quality_check_missing_effect_size(self):
        """Test quality check fails when effect size missing."""
        agent = StatisticalAnalysisAgent()
        
        state = {
            "execution_result": {
                "descriptive": [{"variable": "test"}],
                "assumptions": {"passed": True},
                "inferential": {"p_value": 0.01, "statistic": 2.5, "df": 28},
                "effect_sizes": {}  # Missing effect size
            }
        }
        
        result = await agent._check_quality(state)
        
        assert result.criteria_scores.get("effect_size", 0) == 0
        assert "Effect size not calculated" in result.feedback


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
