"""
Statistical Power Engine for Advanced Power Analysis

This module provides comprehensive statistical power analysis and sample size 
calculation capabilities for clinical and research studies.

Key Features:
- Power analysis for multiple statistical test types
- Adaptive sample size recalculation
- Effect size estimation and validation
- Integration with ML Study Design Optimizer
- Bayesian and frequentist approaches

Author: Stage 6 Enhancement Team
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from enum import Enum
import numpy as np
from scipy import stats
from scipy.optimize import brentq, minimize_scalar
import asyncio

# Configure logging
logger = logging.getLogger(__name__)


class StatisticalTestType(Enum):
    """Supported statistical test types for power analysis."""
    ONE_SAMPLE_T_TEST = "one_sample_t"
    TWO_SAMPLE_T_TEST = "two_sample_t"
    PAIRED_T_TEST = "paired_t"
    ONE_WAY_ANOVA = "one_way_anova"
    CHI_SQUARE_INDEPENDENCE = "chi_square"
    CHI_SQUARE_GOODNESS = "chi_square_gof"
    FISHER_EXACT = "fisher_exact"
    PROPORTION_ONE_SAMPLE = "prop_one_sample"
    PROPORTION_TWO_SAMPLE = "prop_two_sample"
    CORRELATION = "correlation"
    REGRESSION = "regression"
    SURVIVAL_LOGRANK = "logrank"
    MANN_WHITNEY = "mann_whitney"
    WILCOXON_SIGNED_RANK = "wilcoxon"


class EffectSizeType(Enum):
    """Effect size measures for different test types."""
    COHEN_D = "cohen_d"
    HEDGE_G = "hedge_g"
    GLASS_DELTA = "glass_delta"
    ETA_SQUARED = "eta_squared"
    COHEN_F = "cohen_f"
    COHEN_W = "cohen_w"
    ODDS_RATIO = "odds_ratio"
    RISK_RATIO = "risk_ratio"
    HAZARD_RATIO = "hazard_ratio"
    PEARSON_R = "pearson_r"


@dataclass
class PowerAnalysisResult:
    """
    Comprehensive result structure for power analysis calculations.
    """
    test_type: StatisticalTestType
    power: float
    alpha: float
    effect_size: float
    effect_size_type: EffectSizeType
    sample_size_total: int
    
    # Detailed parameters
    sample_size_per_group: Optional[List[int]] = None
    degrees_of_freedom: Optional[int] = None
    critical_value: Optional[float] = None
    noncentrality_parameter: Optional[float] = None
    
    # Confidence intervals
    power_ci_lower: Optional[float] = None
    power_ci_upper: Optional[float] = None
    effect_size_ci_lower: Optional[float] = None
    effect_size_ci_upper: Optional[float] = None
    
    # Analysis details
    analysis_method: str = "frequentist"
    assumptions_met: bool = True
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "test_type": self.test_type.value,
            "power": self.power,
            "alpha": self.alpha,
            "effect_size": self.effect_size,
            "effect_size_type": self.effect_size_type.value,
            "sample_size_total": self.sample_size_total,
            "sample_size_per_group": self.sample_size_per_group,
            "degrees_of_freedom": self.degrees_of_freedom,
            "critical_value": self.critical_value,
            "noncentrality_parameter": self.noncentrality_parameter,
            "power_ci_lower": self.power_ci_lower,
            "power_ci_upper": self.power_ci_upper,
            "effect_size_ci_lower": self.effect_size_ci_lower,
            "effect_size_ci_upper": self.effect_size_ci_upper,
            "analysis_method": self.analysis_method,
            "assumptions_met": self.assumptions_met,
            "warnings": self.warnings,
            "recommendations": self.recommendations
        }


@dataclass
class SampleSizeCalculation:
    """
    Result structure for sample size calculations.
    """
    required_sample_size: int
    power_achieved: float
    target_power: float
    alpha: float
    effect_size: float
    test_type: StatisticalTestType
    
    # Calculation details
    calculation_method: str = "exact"
    iterations_used: Optional[int] = None
    convergence_achieved: bool = True
    
    # Sample size breakdown
    sample_size_per_group: Optional[List[int]] = None
    total_groups: int = 2
    allocation_ratio: List[float] = field(default_factory=lambda: [1.0, 1.0])
    
    # Sensitivity analysis
    sample_size_range: Optional[Dict[str, int]] = None
    power_curve_points: Optional[List[Tuple[int, float]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "required_sample_size": self.required_sample_size,
            "power_achieved": self.power_achieved,
            "target_power": self.target_power,
            "alpha": self.alpha,
            "effect_size": self.effect_size,
            "test_type": self.test_type.value,
            "calculation_method": self.calculation_method,
            "iterations_used": self.iterations_used,
            "convergence_achieved": self.convergence_achieved,
            "sample_size_per_group": self.sample_size_per_group,
            "total_groups": self.total_groups,
            "allocation_ratio": self.allocation_ratio,
            "sample_size_range": self.sample_size_range,
            "power_curve_points": self.power_curve_points
        }


class PowerCalculator:
    """
    Core calculator for statistical power and sample size calculations.
    """
    
    def __init__(self):
        self.calculation_history = []
        
    def calculate_t_test_power(self,
                             n1: int,
                             n2: Optional[int] = None,
                             effect_size: float = 0.5,
                             alpha: float = 0.05,
                             test_type: StatisticalTestType = StatisticalTestType.TWO_SAMPLE_T_TEST,
                             alternative: str = "two-sided") -> float:
        """
        Calculate power for t-tests.
        
        Args:
            n1: Sample size group 1
            n2: Sample size group 2 (None for one-sample)
            effect_size: Cohen's d effect size
            alpha: Significance level
            test_type: Type of t-test
            alternative: Direction of test
            
        Returns:
            Statistical power (0-1)
        """
        try:
            if test_type == StatisticalTestType.ONE_SAMPLE_T_TEST:
                # One-sample t-test
                df = n1 - 1
                ncp = effect_size * np.sqrt(n1)
                
            elif test_type == StatisticalTestType.TWO_SAMPLE_T_TEST:
                # Two-sample t-test (equal variances)
                if n2 is None:
                    n2 = n1
                df = n1 + n2 - 2
                pooled_se = np.sqrt(1/n1 + 1/n2)
                ncp = effect_size / pooled_se
                
            elif test_type == StatisticalTestType.PAIRED_T_TEST:
                # Paired t-test
                df = n1 - 1
                ncp = effect_size * np.sqrt(n1)
                
            else:
                raise ValueError(f"Unsupported t-test type: {test_type}")
            
            # Critical value
            if alternative == "two-sided":
                t_crit = stats.t.ppf(1 - alpha/2, df)
            else:
                t_crit = stats.t.ppf(1 - alpha, df)
            
            # Power calculation using non-central t-distribution
            if alternative == "two-sided":
                power = 1 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp)
            else:
                power = 1 - stats.nct.cdf(t_crit, df, ncp)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating t-test power: {str(e)}")
            return 0.0
    
    def calculate_proportion_test_power(self,
                                      n: int,
                                      p1: float,
                                      p2: Optional[float] = None,
                                      alpha: float = 0.05,
                                      test_type: StatisticalTestType = StatisticalTestType.PROPORTION_TWO_SAMPLE,
                                      alternative: str = "two-sided") -> float:
        """
        Calculate power for proportion tests.
        
        Args:
            n: Sample size (total for two-sample, single for one-sample)
            p1: Proportion in group 1 (or null hypothesis for one-sample)
            p2: Proportion in group 2 (or alternative for one-sample)
            alpha: Significance level
            test_type: Type of proportion test
            alternative: Direction of test
            
        Returns:
            Statistical power (0-1)
        """
        try:
            if test_type == StatisticalTestType.PROPORTION_ONE_SAMPLE:
                # One-sample proportion test
                p0 = p1  # Null hypothesis proportion
                p_alt = p2  # Alternative proportion
                
                se_null = np.sqrt(p0 * (1 - p0) / n)
                se_alt = np.sqrt(p_alt * (1 - p_alt) / n)
                
                if alternative == "two-sided":
                    z_crit = stats.norm.ppf(1 - alpha/2)
                    z_beta = (abs(p_alt - p0) - z_crit * se_null) / se_alt
                else:
                    z_crit = stats.norm.ppf(1 - alpha)
                    z_beta = ((p_alt - p0) - z_crit * se_null) / se_alt
                    
                power = stats.norm.cdf(z_beta)
                
            elif test_type == StatisticalTestType.PROPORTION_TWO_SAMPLE:
                # Two-sample proportion test (equal group sizes)
                n_per_group = n // 2
                
                p_pooled = (p1 + p2) / 2
                se_null = np.sqrt(2 * p_pooled * (1 - p_pooled) / n_per_group)
                se_alt = np.sqrt(p1 * (1 - p1) / n_per_group + p2 * (1 - p2) / n_per_group)
                
                if alternative == "two-sided":
                    z_crit = stats.norm.ppf(1 - alpha/2)
                else:
                    z_crit = stats.norm.ppf(1 - alpha)
                
                z_beta = (abs(p2 - p1) - z_crit * se_null) / se_alt
                power = stats.norm.cdf(z_beta)
                
            else:
                raise ValueError(f"Unsupported proportion test: {test_type}")
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating proportion test power: {str(e)}")
            return 0.0
    
    def calculate_anova_power(self,
                            group_sizes: List[int],
                            effect_size: float,
                            alpha: float = 0.05) -> float:
        """
        Calculate power for one-way ANOVA.
        
        Args:
            group_sizes: List of sample sizes for each group
            effect_size: Cohen's f effect size
            alpha: Significance level
            
        Returns:
            Statistical power (0-1)
        """
        try:
            k = len(group_sizes)  # Number of groups
            n_total = sum(group_sizes)
            
            # Degrees of freedom
            df_between = k - 1
            df_within = n_total - k
            
            # Non-centrality parameter
            ncp = effect_size**2 * n_total
            
            # Critical value from F-distribution
            f_crit = stats.f.ppf(1 - alpha, df_between, df_within)
            
            # Power using non-central F-distribution
            power = 1 - stats.ncf.cdf(f_crit, df_between, df_within, ncp)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating ANOVA power: {str(e)}")
            return 0.0
    
    def calculate_chi_square_power(self,
                                 n: int,
                                 effect_size: float,
                                 df: int,
                                 alpha: float = 0.05) -> float:
        """
        Calculate power for chi-square tests.
        
        Args:
            n: Total sample size
            effect_size: Cohen's w effect size
            df: Degrees of freedom
            alpha: Significance level
            
        Returns:
            Statistical power (0-1)
        """
        try:
            # Non-centrality parameter
            ncp = effect_size**2 * n
            
            # Critical value from chi-square distribution
            chi2_crit = stats.chi2.ppf(1 - alpha, df)
            
            # Power using non-central chi-square distribution
            power = 1 - stats.ncx2.cdf(chi2_crit, df, ncp)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating chi-square power: {str(e)}")
            return 0.0
    
    def calculate_correlation_power(self,
                                  n: int,
                                  effect_size: float,
                                  alpha: float = 0.05,
                                  alternative: str = "two-sided") -> float:
        """
        Calculate power for correlation analysis.
        
        Args:
            n: Sample size
            effect_size: Pearson correlation coefficient (r)
            alpha: Significance level
            alternative: Direction of test
            
        Returns:
            Statistical power (0-1)
        """
        try:
            # Fisher's z-transformation
            z_r = 0.5 * np.log((1 + effect_size) / (1 - effect_size))
            
            # Standard error
            se_z = 1 / np.sqrt(n - 3)
            
            # Critical value
            if alternative == "two-sided":
                z_crit = stats.norm.ppf(1 - alpha/2)
            else:
                z_crit = stats.norm.ppf(1 - alpha)
            
            # Power calculation
            z_beta = (abs(z_r) - z_crit * se_z) / se_z
            power = stats.norm.cdf(z_beta)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating correlation power: {str(e)}")
            return 0.0
    
    def calculate_regression_power(self,
                                 n: int,
                                 effect_size: float,
                                 num_predictors: int,
                                 alpha: float = 0.05) -> float:
        """
        Calculate power for multiple regression.
        
        Args:
            n: Sample size
            effect_size: Cohen's f² (R²/(1-R²))
            num_predictors: Number of predictor variables
            alpha: Significance level
            
        Returns:
            Statistical power (0-1)
        """
        try:
            # Degrees of freedom
            df_between = num_predictors
            df_within = n - num_predictors - 1
            
            if df_within <= 0:
                return 0.0
            
            # Non-centrality parameter
            ncp = effect_size * n
            
            # Critical F value
            f_crit = stats.f.ppf(1 - alpha, df_between, df_within)
            
            # Power using non-central F distribution
            power = 1 - stats.ncf.cdf(f_crit, df_between, df_within, ncp)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating regression power: {str(e)}")
            return 0.0
    
    def calculate_survival_logrank_power(self,
                                       n1: int,
                                       n2: int,
                                       hazard_ratio: float,
                                       event_rate: float = 0.5,
                                       alpha: float = 0.05,
                                       alternative: str = "two-sided") -> float:
        """
        Calculate power for log-rank test in survival analysis.
        
        Args:
            n1: Sample size group 1
            n2: Sample size group 2
            hazard_ratio: Hazard ratio (effect size)
            event_rate: Expected proportion of events
            alpha: Significance level
            alternative: Direction of test
            
        Returns:
            Statistical power (0-1)
        """
        try:
            n_total = n1 + n2
            expected_events = n_total * event_rate
            
            # Effective sample size for log-rank test
            n_eff = (4 * n1 * n2) / (n1 + n2)
            
            # Log hazard ratio
            log_hr = np.log(hazard_ratio)
            
            # Standard error
            se = np.sqrt(4 / expected_events)
            
            # Critical value
            if alternative == "two-sided":
                z_crit = stats.norm.ppf(1 - alpha/2)
            else:
                z_crit = stats.norm.ppf(1 - alpha)
            
            # Power calculation
            z_beta = (abs(log_hr) - z_crit * se) / se
            power = stats.norm.cdf(z_beta)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating log-rank power: {str(e)}")
            return 0.0
    
    def calculate_mann_whitney_power(self,
                                   n1: int,
                                   n2: int,
                                   effect_size: float,
                                   alpha: float = 0.05) -> float:
        """
        Calculate power for Mann-Whitney U test (Wilcoxon rank-sum).
        
        Uses normal approximation for large samples.
        
        Args:
            n1: Sample size group 1
            n2: Sample size group 2
            effect_size: Probability of superiority (P(X1 > X2))
            alpha: Significance level
            
        Returns:
            Statistical power (0-1)
        """
        try:
            n_total = n1 + n2
            
            # Expected value and variance for Mann-Whitney U
            mu_u = n1 * n2 / 2
            sigma_u = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
            
            # Effect size conversion to U statistic
            # effect_size = P(X1 > X2) = U / (n1 * n2)
            expected_u = effect_size * n1 * n2
            
            # Standard normal approximation
            z_score = abs(expected_u - mu_u) / sigma_u
            
            # Critical value
            z_crit = stats.norm.ppf(1 - alpha/2)  # Two-sided test
            
            # Power calculation
            power = 1 - stats.norm.cdf(z_crit - z_score)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating Mann-Whitney power: {str(e)}")
            return 0.0
    
    def calculate_wilcoxon_signed_rank_power(self,
                                           n: int,
                                           effect_size: float,
                                           alpha: float = 0.05) -> float:
        """
        Calculate power for Wilcoxon signed-rank test.
        
        Args:
            n: Number of paired observations
            effect_size: Probability that X > Y in paired comparison
            alpha: Significance level
            
        Returns:
            Statistical power (0-1)
        """
        try:
            # Expected value and variance for Wilcoxon signed-rank
            mu_w = n * (n + 1) / 4
            sigma_w = np.sqrt(n * (n + 1) * (2*n + 1) / 24)
            
            # Effect size conversion
            # Approximate relationship between effect size and test statistic
            expected_w = effect_size * n * (n + 1) / 2
            
            # Standard normal approximation
            z_score = abs(expected_w - mu_w) / sigma_w
            
            # Critical value
            z_crit = stats.norm.ppf(1 - alpha/2)  # Two-sided test
            
            # Power calculation
            power = 1 - stats.norm.cdf(z_crit - z_score)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating Wilcoxon signed-rank power: {str(e)}")
            return 0.0
    
    def calculate_fisher_exact_power(self,
                                   n: int,
                                   p1: float,
                                   p2: float,
                                   alpha: float = 0.05) -> float:
        """
        Calculate power for Fisher's exact test.
        
        Uses normal approximation for computational efficiency.
        
        Args:
            n: Total sample size (assumed equal groups)
            p1: Proportion in group 1
            p2: Proportion in group 2
            alpha: Significance level
            
        Returns:
            Statistical power (0-1)
        """
        try:
            n_per_group = n // 2
            
            # Use normal approximation (same as two-sample proportion test)
            # This is reasonable for moderate to large sample sizes
            
            p_pooled = (p1 + p2) / 2
            se_null = np.sqrt(2 * p_pooled * (1 - p_pooled) / n_per_group)
            se_alt = np.sqrt(p1 * (1 - p1) / n_per_group + p2 * (1 - p2) / n_per_group)
            
            z_crit = stats.norm.ppf(1 - alpha/2)
            z_beta = (abs(p2 - p1) - z_crit * se_null) / se_alt
            power = stats.norm.cdf(z_beta)
            
            return np.clip(power, 0.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating Fisher exact power: {str(e)}")
            return 0.0


class StatisticalPowerEngine:
    """
    Main Statistical Power Engine for comprehensive power analysis.
    
    Provides advanced statistical power analysis and sample size calculation
    capabilities with support for multiple test types and methodologies.
    """
    
    def __init__(self,
                 default_power: float = 0.8,
                 default_alpha: float = 0.05,
                 enable_adaptive: bool = True):
        self.default_power = default_power
        self.default_alpha = default_alpha
        self.enable_adaptive = enable_adaptive
        
        # Initialize calculators
        self.calculator = PowerCalculator()
        self.adaptive_calculator = AdaptiveDesignCalculator() if enable_adaptive else None
        self.bayesian_calculator = BayesianPowerCalculator()
        
        logger.info("Statistical Power Engine initialized")
    
    async def calculate_power(self,
                            test_type: StatisticalTestType,
                            sample_size: Union[int, List[int]],
                            effect_size: float,
                            alpha: float = None,
                            **kwargs) -> PowerAnalysisResult:
        """
        Calculate statistical power for a given test configuration.
        
        Args:
            test_type: Type of statistical test
            sample_size: Sample size(s)
            effect_size: Effect size measure
            alpha: Significance level
            **kwargs: Additional test-specific parameters
            
        Returns:
            PowerAnalysisResult with comprehensive analysis
        """
        try:
            if alpha is None:
                alpha = self.default_alpha
                
            logger.info(f"Calculating power for {test_type.value}")
            
            # Route to appropriate calculation method
            if test_type in [StatisticalTestType.ONE_SAMPLE_T_TEST, 
                           StatisticalTestType.TWO_SAMPLE_T_TEST,
                           StatisticalTestType.PAIRED_T_TEST]:
                power = await self._calculate_t_test_power(
                    test_type, sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_D
                
            elif test_type in [StatisticalTestType.PROPORTION_ONE_SAMPLE,
                             StatisticalTestType.PROPORTION_TWO_SAMPLE]:
                power = await self._calculate_proportion_power(
                    test_type, sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_W
                
            elif test_type == StatisticalTestType.ONE_WAY_ANOVA:
                power = await self._calculate_anova_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_F
                
            elif test_type in [StatisticalTestType.CHI_SQUARE_INDEPENDENCE,
                             StatisticalTestType.CHI_SQUARE_GOODNESS]:
                power = await self._calculate_chi_square_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_W
                
            elif test_type == StatisticalTestType.CORRELATION:
                power = await self._calculate_correlation_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.PEARSON_R
                
            elif test_type == StatisticalTestType.REGRESSION:
                power = await self._calculate_regression_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_F
                
            elif test_type == StatisticalTestType.SURVIVAL_LOGRANK:
                power = await self._calculate_survival_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.HAZARD_RATIO
                
            elif test_type == StatisticalTestType.MANN_WHITNEY:
                power = await self._calculate_mann_whitney_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_D  # Approximation
                
            elif test_type == StatisticalTestType.WILCOXON_SIGNED_RANK:
                power = await self._calculate_wilcoxon_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.COHEN_D  # Approximation
                
            elif test_type == StatisticalTestType.FISHER_EXACT:
                power = await self._calculate_fisher_exact_power(
                    sample_size, effect_size, alpha, **kwargs
                )
                effect_size_type = EffectSizeType.ODDS_RATIO
                
            else:
                raise NotImplementedError(f"Power calculation for {test_type.value} not yet implemented")
            
            # Calculate sample size details
            if isinstance(sample_size, int):
                total_sample_size = sample_size
                sample_size_per_group = None
            else:
                total_sample_size = sum(sample_size)
                sample_size_per_group = sample_size
            
            # Create result object
            result = PowerAnalysisResult(
                test_type=test_type,
                power=power,
                alpha=alpha,
                effect_size=effect_size,
                effect_size_type=effect_size_type,
                sample_size_total=total_sample_size,
                sample_size_per_group=sample_size_per_group,
                analysis_method="frequentist"
            )
            
            # Add recommendations
            await self._add_power_recommendations(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in power calculation: {str(e)}")
            return PowerAnalysisResult(
                test_type=test_type,
                power=0.0,
                alpha=alpha or self.default_alpha,
                effect_size=effect_size,
                effect_size_type=EffectSizeType.COHEN_D,
                sample_size_total=0,
                warnings=[f"Power calculation failed: {str(e)}"]
            )
    
    async def calculate_sample_size(self,
                                  test_type: StatisticalTestType,
                                  target_power: float,
                                  effect_size: float,
                                  alpha: float = None,
                                  max_n: int = 10000,
                                  **kwargs) -> SampleSizeCalculation:
        """
        Calculate required sample size for target power.
        
        Args:
            test_type: Type of statistical test
            target_power: Target statistical power (0-1)
            effect_size: Effect size measure
            alpha: Significance level
            max_n: Maximum sample size to consider
            **kwargs: Additional test-specific parameters
            
        Returns:
            SampleSizeCalculation with detailed results
        """
        try:
            if alpha is None:
                alpha = self.default_alpha
                
            logger.info(f"Calculating sample size for {test_type.value}, target power: {target_power}")
            
            # Define power function for optimization
            async def power_function(n: int) -> float:
                if isinstance(n, (list, np.ndarray)):
                    n = int(n[0]) if len(n) > 0 else 100
                n = max(1, int(n))
                
                result = await self.calculate_power(
                    test_type, n, effect_size, alpha, **kwargs
                )
                return result.power
            
            # Binary search for required sample size
            required_n = await self._optimize_sample_size(
                power_function, target_power, max_n
            )
            
            # Calculate achieved power with required sample size
            final_result = await self.calculate_power(
                test_type, required_n, effect_size, alpha, **kwargs
            )
            
            # Determine sample size per group
            if test_type in [StatisticalTestType.TWO_SAMPLE_T_TEST,
                           StatisticalTestType.PROPORTION_TWO_SAMPLE,
                           StatisticalTestType.MANN_WHITNEY,
                           StatisticalTestType.SURVIVAL_LOGRANK,
                           StatisticalTestType.FISHER_EXACT]:
                n_per_group = [required_n // 2, required_n // 2]
                total_groups = 2
                allocation_ratio = [1.0, 1.0]
            else:
                n_per_group = [required_n]
                total_groups = 1
                allocation_ratio = [1.0]
            
            # Create result
            result = SampleSizeCalculation(
                required_sample_size=required_n,
                power_achieved=final_result.power,
                target_power=target_power,
                alpha=alpha,
                effect_size=effect_size,
                test_type=test_type,
                calculation_method="binary_search",
                convergence_achieved=True,
                sample_size_per_group=n_per_group,
                total_groups=total_groups,
                allocation_ratio=allocation_ratio
            )
            
            # Generate power curve for sensitivity analysis
            await self._generate_power_curve(result, power_function)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sample size calculation: {str(e)}")
            return SampleSizeCalculation(
                required_sample_size=100,
                power_achieved=0.0,
                target_power=target_power,
                alpha=alpha or self.default_alpha,
                effect_size=effect_size,
                test_type=test_type,
                convergence_achieved=False
            )
    
    async def _calculate_t_test_power(self,
                                    test_type: StatisticalTestType,
                                    sample_size: Union[int, List[int]],
                                    effect_size: float,
                                    alpha: float,
                                    **kwargs) -> float:
        """Calculate power for t-tests."""
        if isinstance(sample_size, list):
            n1, n2 = sample_size[0], sample_size[1] if len(sample_size) > 1 else None
        else:
            n1, n2 = sample_size, sample_size // 2 if test_type == StatisticalTestType.TWO_SAMPLE_T_TEST else None
            
        return self.calculator.calculate_t_test_power(
            n1, n2, effect_size, alpha, test_type, 
            kwargs.get('alternative', 'two-sided')
        )
    
    async def _calculate_proportion_power(self,
                                        test_type: StatisticalTestType,
                                        sample_size: Union[int, List[int]],
                                        effect_size: float,
                                        alpha: float,
                                        **kwargs) -> float:
        """Calculate power for proportion tests."""
        if isinstance(sample_size, list):
            n = sum(sample_size)
        else:
            n = sample_size
            
        # Extract proportion parameters
        p1 = kwargs.get('p1', 0.5)
        p2 = kwargs.get('p2', 0.5 + effect_size)
        
        return self.calculator.calculate_proportion_test_power(
            n, p1, p2, alpha, test_type,
            kwargs.get('alternative', 'two-sided')
        )
    
    async def _calculate_anova_power(self,
                                   sample_size: Union[int, List[int]],
                                   effect_size: float,
                                   alpha: float,
                                   **kwargs) -> float:
        """Calculate power for ANOVA."""
        if isinstance(sample_size, list):
            group_sizes = sample_size
        else:
            num_groups = kwargs.get('num_groups', 3)
            group_sizes = [sample_size // num_groups] * num_groups
            
        return self.calculator.calculate_anova_power(group_sizes, effect_size, alpha)
    
    async def _calculate_chi_square_power(self,
                                        sample_size: Union[int, List[int]],
                                        effect_size: float,
                                        alpha: float,
                                        **kwargs) -> float:
        """Calculate power for chi-square tests."""
        if isinstance(sample_size, list):
            n = sum(sample_size)
        else:
            n = sample_size
            
        df = kwargs.get('df', 1)
        return self.calculator.calculate_chi_square_power(n, effect_size, df, alpha)
    
    async def _optimize_sample_size(self,
                                  power_function: Callable,
                                  target_power: float,
                                  max_n: int) -> int:
        """Optimize sample size using binary search."""
        try:
            # Binary search for required sample size
            low, high = 1, max_n
            best_n = max_n
            
            for _ in range(50):  # Max iterations
                mid = (low + high) // 2
                power = await power_function(mid)
                
                if power >= target_power:
                    best_n = mid
                    high = mid - 1
                else:
                    low = mid + 1
                    
                if low > high:
                    break
            
            return best_n
            
        except Exception as e:
            logger.error(f"Error in sample size optimization: {str(e)}")
            return max_n // 2
    
    async def _generate_power_curve(self,
                                  result: SampleSizeCalculation,
                                  power_function: Callable):
        """Generate power curve points for sensitivity analysis."""
        try:
            curve_points = []
            base_n = result.required_sample_size
            
            # Generate points around the required sample size
            test_sizes = [
                int(base_n * 0.5), int(base_n * 0.75), base_n,
                int(base_n * 1.25), int(base_n * 1.5)
            ]
            
            for n in test_sizes:
                if n > 0:
                    power = await power_function(n)
                    curve_points.append((n, power))
            
            result.power_curve_points = curve_points
            
        except Exception as e:
            logger.error(f"Error generating power curve: {str(e)}")
    
    async def _add_power_recommendations(self, result: PowerAnalysisResult):
        """Add recommendations based on power analysis results."""
        try:
            recommendations = []
            warnings = []
            
            # Power level recommendations
            if result.power < 0.7:
                warnings.append("Low statistical power detected")
                recommendations.append("Consider increasing sample size for adequate power")
            elif result.power < 0.8:
                recommendations.append("Power slightly below conventional threshold of 0.8")
            elif result.power > 0.95:
                recommendations.append("Very high power - consider if sample size can be reduced")
            
            # Effect size interpretation
            if result.effect_size_type == EffectSizeType.COHEN_D:
                if result.effect_size < 0.2:
                    recommendations.append("Small effect size detected - ensure clinical significance")
                elif result.effect_size > 0.8:
                    recommendations.append("Large effect size - verify assumptions")
            
            result.warnings.extend(warnings)
            result.recommendations.extend(recommendations)
            
        except Exception as e:
            logger.error(f"Error adding recommendations: {str(e)}")
    
    async def design_adaptive_study(self,
                                   design_type: AdaptiveDesignType,
                                   initial_n: int,
                                   max_n: int,
                                   alpha: float = 0.05,
                                   interim_fractions: List[float] = None,
                                   **kwargs) -> AdaptiveAnalysisResult:
        """
        Design an adaptive clinical trial.
        
        Args:
            design_type: Type of adaptive design
            initial_n: Initial sample size
            max_n: Maximum sample size
            alpha: Overall Type I error rate
            interim_fractions: Information fractions for interim analyses
            **kwargs: Additional design parameters
            
        Returns:
            AdaptiveAnalysisResult with design specifications
        """
        try:
            if not self.enable_adaptive or self.adaptive_calculator is None:
                raise ValueError("Adaptive designs not enabled")
                
            if interim_fractions is None:
                # Default to 50% and 100% information
                interim_fractions = [0.5, 1.0]
            
            # Calculate interim analysis sample sizes
            interim_analyses = [int(initial_n * frac) for frac in interim_fractions]
            
            if design_type == AdaptiveDesignType.GROUP_SEQUENTIAL:
                efficacy_bounds, futility_bounds = self.adaptive_calculator.calculate_group_sequential_boundaries(
                    alpha, interim_fractions, kwargs.get('spending_function', 'obrien_fleming')
                )
                
                result = AdaptiveAnalysisResult(
                    design_type=design_type,
                    initial_sample_size=initial_n,
                    maximum_sample_size=max_n,
                    interim_analyses=interim_analyses,
                    efficacy_boundaries=efficacy_bounds,
                    futility_boundaries=futility_bounds,
                    alpha_spending_function=kwargs.get('spending_function', 'obrien_fleming'),
                    information_fractions=interim_fractions,
                    type_i_error_control=True
                )
                
            elif design_type == AdaptiveDesignType.SAMPLE_SIZE_REESTIMATION:
                result = AdaptiveAnalysisResult(
                    design_type=design_type,
                    initial_sample_size=initial_n,
                    maximum_sample_size=max_n,
                    interim_analyses=interim_analyses,
                    information_fractions=interim_fractions
                )
                
            else:
                # Default adaptive design
                result = AdaptiveAnalysisResult(
                    design_type=design_type,
                    initial_sample_size=initial_n,
                    maximum_sample_size=max_n,
                    interim_analyses=interim_analyses,
                    information_fractions=interim_fractions
                )
            
            # Estimate expected sample size (simplified)
            result.expected_sample_size = (initial_n + max_n) / 2
            result.probability_early_stop = 0.3  # Placeholder estimate
            
            return result
            
        except Exception as e:
            logger.error(f"Error designing adaptive study: {str(e)}")
            return AdaptiveAnalysisResult(
                design_type=design_type,
                initial_sample_size=initial_n,
                maximum_sample_size=max_n,
                interim_analyses=[initial_n, max_n],
                type_i_error_control=False
            )
    
    async def calculate_bayesian_power(self,
                                     sample_size: int,
                                     effect_size: float,
                                     prior_specification: Dict[str, Any],
                                     method: BayesianMethod = BayesianMethod.CONJUGATE_PRIOR,
                                     **kwargs) -> BayesianPowerResult:
        """
        Calculate Bayesian predictive power.
        
        Args:
            sample_size: Planned sample size
            effect_size: Effect size for power calculation
            prior_specification: Prior distribution parameters
            method: Bayesian method to use
            **kwargs: Additional parameters
            
        Returns:
            BayesianPowerResult with posterior analysis
        """
        try:
            prior_mean = prior_specification.get('mean', 0.0)
            prior_variance = prior_specification.get('variance', 1.0)
            decision_threshold = kwargs.get('decision_threshold', 0.95)
            
            result = self.bayesian_calculator.calculate_bayesian_power(
                sample_size, effect_size, prior_mean, prior_variance, 
                decision_threshold, method
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in Bayesian power calculation: {str(e)}")
            return BayesianPowerResult(
                posterior_power=0.5,
                credible_interval=(0.0, 1.0),
                prior_specification=prior_specification,
                method=method
            )
    
    async def calculate_conditional_power(self,
                                        interim_data: Dict[str, Any],
                                        final_n: int,
                                        test_type: StatisticalTestType = StatisticalTestType.TWO_SAMPLE_T_TEST) -> float:
        """
        Calculate conditional power based on interim results.
        
        Args:
            interim_data: Interim analysis results
            final_n: Planned final sample size
            test_type: Type of statistical test
            
        Returns:
            Conditional power (0-1)
        """
        try:
            if not self.enable_adaptive or self.adaptive_calculator is None:
                return 0.5
                
            interim_effect = interim_data.get('effect_size', 0.0)
            interim_n = interim_data.get('sample_size', 0)
            
            conditional_power = self.adaptive_calculator.calculate_conditional_power(
                interim_effect, interim_n, final_n, test_type
            )
            
            return conditional_power
            
        except Exception as e:
            logger.error(f"Error calculating conditional power: {str(e)}")
            return 0.5
    
    async def reestimate_sample_size(self,
                                   interim_data: Dict[str, Any],
                                   original_n: int,
                                   target_power: float = 0.8) -> int:
        """
        Reestimate sample size based on interim data.
        
        Args:
            interim_data: Interim analysis results
            original_n: Original planned sample size
            target_power: Target power for reestimation
            
        Returns:
            Reestimated sample size
        """
        try:
            if not self.enable_adaptive or self.adaptive_calculator is None:
                return original_n
                
            interim_variance = interim_data.get('variance', 1.0)
            planned_variance = interim_data.get('planned_variance', 1.0)
            
            reestimated_n = self.adaptive_calculator.calculate_sample_size_reestimation(
                interim_variance, planned_variance, original_n, target_power
            )
            
            return reestimated_n
            
        except Exception as e:
            logger.error(f"Error in sample size reestimation: {str(e)}")
            return original_n
    
    async def _calculate_correlation_power(self,
                                         sample_size: Union[int, List[int]],
                                         effect_size: float,
                                         alpha: float,
                                         **kwargs) -> float:
        """Calculate power for correlation analysis."""
        if isinstance(sample_size, list):
            n = sum(sample_size)
        else:
            n = sample_size
            
        return self.calculator.calculate_correlation_power(
            n, effect_size, alpha, kwargs.get('alternative', 'two-sided')
        )
    
    async def _calculate_regression_power(self,
                                        sample_size: Union[int, List[int]],
                                        effect_size: float,
                                        alpha: float,
                                        **kwargs) -> float:
        """Calculate power for multiple regression."""
        if isinstance(sample_size, list):
            n = sum(sample_size)
        else:
            n = sample_size
            
        num_predictors = kwargs.get('num_predictors', 1)
        return self.calculator.calculate_regression_power(
            n, effect_size, num_predictors, alpha
        )
    
    async def _calculate_survival_power(self,
                                      sample_size: Union[int, List[int]],
                                      effect_size: float,
                                      alpha: float,
                                      **kwargs) -> float:
        """Calculate power for log-rank survival test."""
        if isinstance(sample_size, list):
            n1, n2 = sample_size[0], sample_size[1] if len(sample_size) > 1 else sample_size[0]
        else:
            n1, n2 = sample_size // 2, sample_size // 2
            
        event_rate = kwargs.get('event_rate', 0.5)
        return self.calculator.calculate_survival_logrank_power(
            n1, n2, effect_size, event_rate, alpha, kwargs.get('alternative', 'two-sided')
        )
    
    async def _calculate_mann_whitney_power(self,
                                          sample_size: Union[int, List[int]],
                                          effect_size: float,
                                          alpha: float,
                                          **kwargs) -> float:
        """Calculate power for Mann-Whitney U test."""
        if isinstance(sample_size, list):
            n1, n2 = sample_size[0], sample_size[1] if len(sample_size) > 1 else sample_size[0]
        else:
            n1, n2 = sample_size // 2, sample_size // 2
            
        return self.calculator.calculate_mann_whitney_power(n1, n2, effect_size, alpha)
    
    async def _calculate_wilcoxon_power(self,
                                      sample_size: Union[int, List[int]],
                                      effect_size: float,
                                      alpha: float,
                                      **kwargs) -> float:
        """Calculate power for Wilcoxon signed-rank test."""
        if isinstance(sample_size, list):
            n = sample_size[0]
        else:
            n = sample_size
            
        return self.calculator.calculate_wilcoxon_signed_rank_power(n, effect_size, alpha)
    
    async def _calculate_fisher_exact_power(self,
                                          sample_size: Union[int, List[int]],
                                          effect_size: float,
                                          alpha: float,
                                          **kwargs) -> float:
        """Calculate power for Fisher's exact test."""
        if isinstance(sample_size, list):
            n = sum(sample_size)
        else:
            n = sample_size
            
        # Convert effect size to proportions
        p1 = kwargs.get('p1', 0.5)
        p2 = kwargs.get('p2', 0.5 + effect_size)
        
        return self.calculator.calculate_fisher_exact_power(n, p1, p2, alpha)