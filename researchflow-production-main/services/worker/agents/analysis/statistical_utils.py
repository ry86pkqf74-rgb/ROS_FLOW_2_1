"""
Statistical Utility Functions

Helper functions for statistical calculations including:
- Effect size calculations
- Confidence intervals
- APA formatting
- Data validation
- Pooled statistics

Linear Issues: ROS-XXX (Stage 7 - Statistical Analysis Agent)
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from scipy import stats
import logging

from .statistical_types import (
    TestType,
    EffectSize,
    ConfidenceInterval,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Validation
# =============================================================================

def validate_data(data: pd.Series, name: str = "variable") -> Tuple[bool, List[str]]:
    """
    Validate data for statistical analysis.
    
    Checks for:
    - Missing values
    - Infinite values
    - Sufficient sample size
    - Variance
    
    Args:
        data: Series to validate
        name: Variable name for error messages
    
    Returns:
        Tuple of (is_valid, warnings)
    """
    warnings = []
    is_valid = True
    
    # Check for missing values
    n_missing = data.isna().sum()
    if n_missing > 0:
        pct_missing = (n_missing / len(data)) * 100
        warnings.append(f"{name}: {n_missing} missing values ({pct_missing:.1f}%)")
        
        if pct_missing > 50:
            warnings.append(f"{name}: >50% missing - analysis may be unreliable")
            is_valid = False
    
    # Check for infinite values
    if np.isinf(data.dropna()).any():
        warnings.append(f"{name}: Contains infinite values")
        is_valid = False
    
    # Check sample size
    n_valid = data.notna().sum()
    if n_valid < 3:
        warnings.append(f"{name}: Insufficient sample size (n={n_valid})")
        is_valid = False
    
    # Check for variance
    if n_valid >= 2:
        variance = data.var()
        if variance == 0:
            warnings.append(f"{name}: Zero variance - all values identical")
            is_valid = False
    
    return is_valid, warnings


def check_equal_variance(group_a: pd.Series, group_b: pd.Series, alpha: float = 0.05) -> bool:
    """
    Check if two groups have equal variance using Levene's test.
    
    Args:
        group_a: First group
        group_b: Second group
        alpha: Significance level
    
    Returns:
        True if variances are equal (p > alpha)
    """
    try:
        # Remove missing values
        a_clean = group_a.dropna()
        b_clean = group_b.dropna()
        
        if len(a_clean) < 2 or len(b_clean) < 2:
            logger.warning("Insufficient data for Levene's test")
            return True  # Assume equal variance
        
        statistic, p_value = stats.levene(a_clean, b_clean)
        return p_value > alpha
        
    except Exception as e:
        logger.error(f"Levene's test failed: {e}")
        return True  # Conservative assumption


# =============================================================================
# Effect Size Calculations
# =============================================================================

def calculate_cohens_d(group_a: pd.Series, group_b: pd.Series) -> float:
    """
    Calculate Cohen's d effect size for two independent groups.
    
    Formula: d = (M1 - M2) / pooled_SD
    
    Args:
        group_a: First group values
        group_b: Second group values
    
    Returns:
        Cohen's d value
    
    References:
        Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences (2nd ed.).
    """
    # Remove missing values
    a = group_a.dropna()
    b = group_b.dropna()
    
    # Calculate means
    mean_a = a.mean()
    mean_b = b.mean()
    
    # Calculate pooled standard deviation
    n_a = len(a)
    n_b = len(b)
    var_a = a.var(ddof=1)
    var_b = b.var(ddof=1)
    
    pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    
    # Cohen's d
    d = (mean_a - mean_b) / pooled_std
    
    return d


def calculate_hedges_g(group_a: pd.Series, group_b: pd.Series) -> float:
    """
    Calculate Hedges' g (bias-corrected Cohen's d).
    
    Hedges' g corrects for small sample bias in Cohen's d.
    
    Args:
        group_a: First group values
        group_b: Second group values
    
    Returns:
        Hedges' g value
    """
    # Calculate Cohen's d
    d = calculate_cohens_d(group_a, group_b)
    
    # Bias correction factor
    n_a = group_a.dropna().count()
    n_b = group_b.dropna().count()
    n = n_a + n_b
    
    # Correction factor (approximation)
    correction = 1 - (3 / (4 * n - 9))
    
    g = d * correction
    
    return g


def calculate_eta_squared(groups: List[pd.Series]) -> float:
    """
    Calculate eta-squared effect size for ANOVA.
    
    Formula: η² = SS_between / SS_total
    
    Args:
        groups: List of group values
    
    Returns:
        Eta-squared value
    """
    # Combine all data
    all_data = pd.concat([g.dropna() for g in groups])
    grand_mean = all_data.mean()
    
    # Calculate SS_between
    ss_between = sum(
        len(g.dropna()) * (g.dropna().mean() - grand_mean) ** 2
        for g in groups
    )
    
    # Calculate SS_total
    ss_total = sum((all_data - grand_mean) ** 2)
    
    # Eta-squared
    if ss_total == 0:
        return 0.0
    
    eta_sq = ss_between / ss_total
    
    return eta_sq


def calculate_cramers_v(contingency_table: np.ndarray) -> float:
    """
    Calculate Cramér's V effect size for chi-square test.
    
    Args:
        contingency_table: 2D contingency table
    
    Returns:
        Cramér's V value (0 to 1)
    """
    chi2 = stats.chi2_contingency(contingency_table)[0]
    n = contingency_table.sum()
    min_dim = min(contingency_table.shape[0], contingency_table.shape[1]) - 1
    
    v = np.sqrt(chi2 / (n * min_dim))
    
    return v


# =============================================================================
# Confidence Intervals
# =============================================================================

def calculate_mean_ci(
    data: pd.Series,
    confidence: float = 0.95
) -> ConfidenceInterval:
    """
    Calculate confidence interval for the mean.
    
    Uses t-distribution for small samples.
    
    Args:
        data: Data series
        confidence: Confidence level (default 0.95)
    
    Returns:
        ConfidenceInterval object
    """
    clean_data = data.dropna()
    n = len(clean_data)
    
    if n < 2:
        raise ValueError("Need at least 2 observations for CI")
    
    mean = clean_data.mean()
    se = clean_data.sem()  # Standard error
    
    # t-critical value
    df = n - 1
    t_crit = stats.t.ppf((1 + confidence) / 2, df)
    
    # Margin of error
    margin = t_crit * se
    
    return ConfidenceInterval(
        point_estimate=mean,
        lower=mean - margin,
        upper=mean + margin,
        level=confidence
    )


def calculate_proportion_ci(
    successes: int,
    n: int,
    confidence: float = 0.95,
    method: str = "wilson"
) -> ConfidenceInterval:
    """
    Calculate confidence interval for a proportion.
    
    Args:
        successes: Number of successes
        n: Total sample size
        confidence: Confidence level
        method: "wilson" (default) or "wald"
    
    Returns:
        ConfidenceInterval object
    """
    p = successes / n
    
    if method == "wilson":
        # Wilson score interval (more accurate for small samples)
        z = stats.norm.ppf((1 + confidence) / 2)
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denominator
        margin = z * np.sqrt((p * (1 - p) / n + z**2 / (4 * n**2))) / denominator
        
        lower = center - margin
        upper = center + margin
    else:
        # Wald interval (simple but less accurate)
        z = stats.norm.ppf((1 + confidence) / 2)
        se = np.sqrt(p * (1 - p) / n)
        margin = z * se
        
        lower = p - margin
        upper = p + margin
    
    # Clip to [0, 1]
    lower = max(0, lower)
    upper = min(1, upper)
    
    return ConfidenceInterval(
        point_estimate=p,
        lower=lower,
        upper=upper,
        level=confidence
    )


# =============================================================================
# APA Formatting
# =============================================================================

def format_p_value(p: float) -> str:
    """
    Format p-value in APA style.
    
    Args:
        p: P-value
    
    Returns:
        Formatted string (e.g., "p < .001", "p = .042")
    """
    if p < 0.001:
        return "p < .001"
    else:
        return f"p = {p:.3f}".replace("0.", ".")


def format_statistic_apa(
    test_type: TestType,
    statistic: float,
    df: Optional[float],
    p_value: float
) -> str:
    """
    Format statistical result in APA style.
    
    Args:
        test_type: Type of test
        statistic: Test statistic
        df: Degrees of freedom
        p_value: P-value
    
    Returns:
        APA-formatted string
    """
    p_str = format_p_value(p_value)
    
    if test_type in [TestType.T_TEST_INDEPENDENT, TestType.T_TEST_PAIRED]:
        return f"t({df:.0f}) = {statistic:.2f}, {p_str}"
    
    elif test_type == TestType.ANOVA_ONEWAY:
        if isinstance(df, tuple):
            df1, df2 = df
            return f"F({df1:.0f}, {df2:.0f}) = {statistic:.2f}, {p_str}"
        else:
            return f"F = {statistic:.2f}, {p_str}"
    
    elif test_type == TestType.CHI_SQUARE:
        return f"χ²({df:.0f}) = {statistic:.2f}, {p_str}"
    
    else:
        return f"statistic = {statistic:.2f}, {p_str}"


def format_descriptive_table_apa(descriptive_stats: List) -> str:
    """
    Generate APA-style descriptive statistics table.
    
    Args:
        descriptive_stats: List of DescriptiveStats objects
    
    Returns:
        Formatted table string
    """
    if not descriptive_stats:
        return ""
    
    lines = []
    lines.append("Descriptive Statistics")
    lines.append("-" * 60)
    lines.append(f"{'Variable':<20} {'N':>6} {'M':>8} {'SD':>8} {'Range':>15}")
    lines.append("-" * 60)
    
    for stat in descriptive_stats:
        var_name = stat.variable_name[:20]
        if stat.group_name:
            var_name = f"{var_name} ({stat.group_name})"[:20]
        
        range_str = f"{stat.min_value:.1f}-{stat.max_value:.1f}"
        
        lines.append(
            f"{var_name:<20} {stat.n:>6} {stat.mean:>8.2f} {stat.std:>8.2f} {range_str:>15}"
        )
    
    lines.append("-" * 60)
    
    return "\n".join(lines)


# =============================================================================
# Pooled Statistics
# =============================================================================

def pooled_std(group_a: pd.Series, group_b: pd.Series) -> float:
    """
    Calculate pooled standard deviation for two groups.
    
    Args:
        group_a: First group
        group_b: Second group
    
    Returns:
        Pooled standard deviation
    """
    a = group_a.dropna()
    b = group_b.dropna()
    
    n_a = len(a)
    n_b = len(b)
    var_a = a.var(ddof=1)
    var_b = b.var(ddof=1)
    
    pooled = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    
    return pooled


def pooled_variance(groups: List[pd.Series]) -> float:
    """
    Calculate pooled variance across multiple groups.
    
    Args:
        groups: List of group series
    
    Returns:
        Pooled variance
    """
    total_n = 0
    weighted_var = 0
    
    for group in groups:
        clean = group.dropna()
        n = len(clean)
        if n > 1:
            var = clean.var(ddof=1)
            weighted_var += (n - 1) * var
            total_n += (n - 1)
    
    if total_n == 0:
        return 0.0
    
    return weighted_var / total_n


# =============================================================================
# Interpretation Helpers
# =============================================================================

def interpret_effect_size_magnitude(effect_size: float, metric: str = "cohens_d") -> str:
    """
    Interpret effect size magnitude using Cohen's conventions.
    
    Args:
        effect_size: Effect size value
        metric: Type of effect size ("cohens_d", "eta_squared", "cramers_v")
    
    Returns:
        Interpretation string ("negligible", "small", "medium", "large")
    """
    es_abs = abs(effect_size)
    
    if metric == "cohens_d":
        if es_abs < 0.2:
            return "negligible"
        elif es_abs < 0.5:
            return "small"
        elif es_abs < 0.8:
            return "medium"
        else:
            return "large"
    
    elif metric == "eta_squared":
        if es_abs < 0.01:
            return "negligible"
        elif es_abs < 0.06:
            return "small"
        elif es_abs < 0.14:
            return "medium"
        else:
            return "large"
    
    elif metric == "cramers_v":
        if es_abs < 0.1:
            return "negligible"
        elif es_abs < 0.3:
            return "small"
        elif es_abs < 0.5:
            return "medium"
        else:
            return "large"
    
    else:
        return "unknown"


def generate_interpretation(
    test_result: dict,
    effect_size: Optional[float] = None,
    alpha: float = 0.05
) -> str:
    """
    Generate human-readable interpretation of statistical results.
    
    Args:
        test_result: Dictionary with test results
        effect_size: Optional effect size value
        alpha: Significance level
    
    Returns:
        Natural language interpretation
    """
    p_value = test_result.get("p_value", 1.0)
    test_name = test_result.get("test_name", "test")
    
    # Significance interpretation
    if p_value < alpha:
        sig_text = f"statistically significant at α = {alpha}"
    else:
        sig_text = "not statistically significant"
    
    # Effect size interpretation
    if effect_size is not None:
        magnitude = interpret_effect_size_magnitude(effect_size)
        effect_text = f" with a {magnitude} effect size"
    else:
        effect_text = ""
    
    return f"The {test_name} was {sig_text}{effect_text}."
