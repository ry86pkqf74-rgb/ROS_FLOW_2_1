"""
Statistical Analysis Type Definitions

Comprehensive type definitions for statistical analysis including:
- Study data structures
- Test types and results
- Effect sizes and confidence intervals
- Assumption checking
- Visualization specifications

Linear Issues: ROS-XXX (Stage 7 - Statistical Analysis Agent)
"""

from typing import List, Optional, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
import pandas as pd
import numpy as np


# =============================================================================
# Test Type Enumerations
# =============================================================================

class TestType(str, Enum):
    """
    Statistical test types supported by the agent.
    
    Covers common parametric and non-parametric tests used in clinical research.
    """
    # Two-sample tests
    T_TEST_INDEPENDENT = "t_test_independent"
    T_TEST_PAIRED = "t_test_paired"
    MANN_WHITNEY = "mann_whitney"
    WILCOXON = "wilcoxon"
    
    # Multi-group tests
    ANOVA_ONEWAY = "anova_oneway"
    ANOVA_REPEATED = "anova_repeated"
    KRUSKAL_WALLIS = "kruskal_wallis"
    FRIEDMAN = "friedman"
    
    # Categorical tests
    CHI_SQUARE = "chi_square"
    FISHER_EXACT = "fisher_exact"
    
    # Correlation tests
    CORRELATION_PEARSON = "correlation_pearson"
    CORRELATION_SPEARMAN = "correlation_spearman"
    
    # Regression (placeholder for future)
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"


class AssumptionType(str, Enum):
    """Types of statistical assumptions to check."""
    NORMALITY = "normality"
    HOMOGENEITY = "homogeneity"
    INDEPENDENCE = "independence"
    LINEARITY = "linearity"
    SPHERICITY = "sphericity"


class EffectSizeType(str, Enum):
    """Types of effect size measures."""
    COHENS_D = "cohens_d"
    HEDGES_G = "hedges_g"
    GLASS_DELTA = "glass_delta"
    ETA_SQUARED = "eta_squared"
    OMEGA_SQUARED = "omega_squared"
    CRAMERS_V = "cramers_v"
    COHENS_W = "cohens_w"
    PEARSON_R = "pearson_r"


# =============================================================================
# Input Data Structures
# =============================================================================

class StudyData(BaseModel):
    """
    Input data structure for statistical analysis.
    
    Represents the complete dataset with group assignments, outcomes,
    and optional covariates.
    """
    model_config = {"arbitrary_types_allowed": True}
    
    groups: Optional[List[str]] = Field(
        None,
        description="Group labels for each observation"
    )
    outcomes: Dict[str, List[float]] = Field(
        ...,
        description="Outcome variables as dict of variable_name -> values"
    )
    covariates: Optional[Dict[str, List[Union[float, str]]]] = Field(
        None,
        description="Optional covariates for adjustment"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Study metadata (design, type, etc.)"
    )
    
    @field_validator('outcomes')
    @classmethod
    def validate_outcomes(cls, v):
        """Ensure all outcome lists have same length."""
        if not v:
            raise ValueError("At least one outcome variable required")
        
        lengths = [len(values) for values in v.values()]
        if len(set(lengths)) > 1:
            raise ValueError("All outcome variables must have same length")
        
        return v
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for analysis."""
        df = pd.DataFrame(self.outcomes)
        
        if self.groups:
            df['__group__'] = self.groups
        
        if self.covariates:
            for name, values in self.covariates.items():
                df[name] = values
        
        return df
    
    def get_sample_size(self) -> int:
        """Get total sample size."""
        first_outcome = next(iter(self.outcomes.values()))
        return len(first_outcome)


# =============================================================================
# Descriptive Statistics
# =============================================================================

@dataclass
class DescriptiveStats:
    """
    Descriptive statistics for a variable or group.
    
    Includes central tendency, dispersion, and data quality metrics.
    """
    variable_name: str
    n: int
    missing: int
    mean: float
    median: float
    std: float
    min_value: float
    max_value: float
    q25: float  # 25th percentile
    q75: float  # 75th percentile
    iqr: float  # Interquartile range
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    
    # Group-specific stats (if applicable)
    group_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "variable": self.variable_name,
            "n": self.n,
            "missing": self.missing,
            "mean": round(self.mean, 3),
            "median": round(self.median, 3),
            "std": round(self.std, 3),
            "min": round(self.min_value, 3),
            "max": round(self.max_value, 3),
            "q25": round(self.q25, 3),
            "q75": round(self.q75, 3),
            "iqr": round(self.iqr, 3),
            "group": self.group_name,
        }
    
    def format_apa(self) -> str:
        """Format as APA-style M(SD) = X.XX(Y.YY)."""
        return f"M(SD) = {self.mean:.2f}({self.std:.2f})"


# =============================================================================
# Assumption Checking
# =============================================================================

@dataclass
class AssumptionCheckResult:
    """
    Results of statistical assumption checking.
    
    Includes test results, warnings, and remediation suggestions.
    """
    test_type: TestType
    
    # Assumption test results
    normality: Dict[str, Any] = field(default_factory=dict)
    homogeneity: Dict[str, Any] = field(default_factory=dict)
    independence: Dict[str, Any] = field(default_factory=dict)
    
    # Overall status
    passed: bool = False
    warnings: List[str] = field(default_factory=list)
    
    # NEW: Remediation suggestions (P0 enhancement)
    remediation_suggestions: List[str] = field(default_factory=list)
    alternative_tests: List[TestType] = field(default_factory=list)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
    
    def suggest_remediation(self, suggestion: str, alternative_test: Optional[TestType] = None) -> None:
        """Add a remediation suggestion."""
        self.remediation_suggestions.append(suggestion)
        if alternative_test:
            self.alternative_tests.append(alternative_test)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_type": self.test_type.value,
            "passed": self.passed,
            "normality": self.normality,
            "homogeneity": self.homogeneity,
            "independence": self.independence,
            "warnings": self.warnings,
            "remediation_suggestions": self.remediation_suggestions,
            "alternative_tests": [t.value for t in self.alternative_tests],
        }


# =============================================================================
# Hypothesis Test Results
# =============================================================================

@dataclass
class HypothesisTestResult:
    """
    Results from a hypothesis test.
    
    Includes test statistic, p-value, interpretation, and APA formatting.
    """
    test_name: str
    test_type: TestType
    statistic: float
    p_value: float
    df: Optional[Union[int, float]] = None  # Can be tuple for F-test
    
    # Interpretation
    significant: bool = False
    alpha: float = 0.05
    interpretation: str = ""
    
    # Confidence interval (if applicable)
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    ci_level: float = 0.95
    
    # Post-hoc tests (for multi-group comparisons)
    post_hoc: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Set significant flag based on p-value."""
        self.significant = self.p_value < self.alpha
    
    def format_apa(self) -> str:
        """
        Format result in APA style.
        
        Examples:
            t(48) = 2.34, p = .023
            F(2, 47) = 5.67, p < .001
            χ²(2) = 12.34, p = .002
        """
        # Format p-value
        if self.p_value < 0.001:
            p_str = "p < .001"
        else:
            p_str = f"p = {self.p_value:.3f}".replace("0.", ".")
        
        # Format based on test type
        if self.test_type in [TestType.T_TEST_INDEPENDENT, TestType.T_TEST_PAIRED]:
            return f"t({self.df}) = {self.statistic:.2f}, {p_str}"
        
        elif self.test_type == TestType.ANOVA_ONEWAY:
            df_between, df_within = self.df if isinstance(self.df, tuple) else (self.df, 0)
            return f"F({df_between}, {df_within}) = {self.statistic:.2f}, {p_str}"
        
        elif self.test_type == TestType.CHI_SQUARE:
            return f"χ²({self.df}) = {self.statistic:.2f}, {p_str}"
        
        elif self.test_type in [TestType.CORRELATION_PEARSON, TestType.CORRELATION_SPEARMAN]:
            return f"r({self.df}) = {self.statistic:.2f}, {p_str}"
        
        else:
            return f"statistic = {self.statistic:.2f}, {p_str}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "test_type": self.test_type.value,
            "statistic": round(self.statistic, 4),
            "p_value": round(self.p_value, 4),
            "df": self.df,
            "significant": self.significant,
            "alpha": self.alpha,
            "interpretation": self.interpretation,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "apa_format": self.format_apa(),
        }


# =============================================================================
# Effect Sizes
# =============================================================================

@dataclass
class EffectSize:
    """
    Effect size measures and interpretation.
    
    Includes multiple effect size metrics and Cohen's conventions.
    """
    # Common effect sizes
    cohens_d: Optional[float] = None
    hedges_g: Optional[float] = None
    glass_delta: Optional[float] = None
    
    # ANOVA effect sizes
    eta_squared: Optional[float] = None
    omega_squared: Optional[float] = None
    
    # Categorical effect sizes
    cramers_v: Optional[float] = None
    cohens_w: Optional[float] = None
    
    # Correlation
    r: Optional[float] = None
    r_squared: Optional[float] = None
    
    # Interpretation
    interpretation: str = ""
    magnitude: str = ""  # "small", "medium", "large"
    
    def interpret_cohens_d(self) -> str:
        """
        Interpret Cohen's d using conventional thresholds.
        
        Cohen (1988) conventions:
            Small: 0.2
            Medium: 0.5
            Large: 0.8
        """
        if self.cohens_d is None:
            return "N/A"
        
        d_abs = abs(self.cohens_d)
        
        if d_abs < 0.2:
            return "negligible"
        elif d_abs < 0.5:
            return "small"
        elif d_abs < 0.8:
            return "medium"
        else:
            return "large"
    
    def interpret_eta_squared(self) -> str:
        """
        Interpret eta-squared using conventional thresholds.
        
        Cohen (1988) conventions:
            Small: 0.01
            Medium: 0.06
            Large: 0.14
        """
        if self.eta_squared is None:
            return "N/A"
        
        if self.eta_squared < 0.01:
            return "negligible"
        elif self.eta_squared < 0.06:
            return "small"
        elif self.eta_squared < 0.14:
            return "medium"
        else:
            return "large"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {}
        
        if self.cohens_d is not None:
            result["cohens_d"] = round(self.cohens_d, 3)
            result["cohens_d_interpretation"] = self.interpret_cohens_d()
        
        if self.hedges_g is not None:
            result["hedges_g"] = round(self.hedges_g, 3)
        
        if self.eta_squared is not None:
            result["eta_squared"] = round(self.eta_squared, 3)
            result["eta_squared_interpretation"] = self.interpret_eta_squared()
        
        if self.r is not None:
            result["r"] = round(self.r, 3)
        
        if self.r_squared is not None:
            result["r_squared"] = round(self.r_squared, 3)
        
        result["interpretation"] = self.interpretation
        result["magnitude"] = self.magnitude
        
        return result


# =============================================================================
# Confidence Intervals
# =============================================================================

@dataclass
class ConfidenceInterval:
    """Confidence interval for a statistic."""
    point_estimate: float
    lower: float
    upper: float
    level: float = 0.95
    
    def format_apa(self) -> str:
        """Format as APA style: 95% CI [lower, upper]."""
        ci_pct = int(self.level * 100)
        return f"{ci_pct}% CI [{self.lower:.2f}, {self.upper:.2f}]"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "point_estimate": round(self.point_estimate, 3),
            "lower": round(self.lower, 3),
            "upper": round(self.upper, 3),
            "level": self.level,
            "apa_format": self.format_apa(),
        }


# =============================================================================
# Visualization Specifications (P0 Enhancement)
# =============================================================================

@dataclass
class FigureSpec:
    """
    Specification for statistical visualization.
    
    Does not render the figure, but provides all data needed for
    frontend rendering (Recharts, Plotly, etc.)
    """
    figure_type: str  # "boxplot", "histogram", "qq_plot", "scatter", "bar"
    title: str
    data: Dict[str, Any]
    style: str = "seaborn"  # "seaborn", "matplotlib", "plotly"
    caption: str = ""
    
    # Axis labels
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    
    # Additional options
    options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.figure_type,
            "title": self.title,
            "data": self.data,
            "style": self.style,
            "caption": self.caption,
            "x_label": self.x_label,
            "y_label": self.y_label,
            "options": self.options,
        }


# =============================================================================
# Complete Statistical Result
# =============================================================================

@dataclass
class StatisticalResult:
    """
    Complete result from statistical analysis.
    
    Aggregates descriptive stats, inferential tests, effect sizes,
    assumption checks, and visualizations.
    """
    # Core results
    descriptive: List[DescriptiveStats] = field(default_factory=list)
    inferential: Optional[HypothesisTestResult] = None
    effect_sizes: Optional[EffectSize] = None
    assumptions: Optional[AssumptionCheckResult] = None
    confidence_intervals: List[ConfidenceInterval] = field(default_factory=list)
    
    # Outputs
    tables: List[str] = field(default_factory=list)  # APA-formatted tables
    figure_specs: List[FigureSpec] = field(default_factory=list)  # Visualization specs
    
    # Metadata
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "descriptive": [d.to_dict() for d in self.descriptive],
            "inferential": self.inferential.to_dict() if self.inferential else None,
            "effect_sizes": self.effect_sizes.to_dict() if self.effect_sizes else None,
            "assumptions": self.assumptions.to_dict() if self.assumptions else None,
            "confidence_intervals": [ci.to_dict() for ci in self.confidence_intervals],
            "tables": self.tables,
            "figure_specs": [fig.to_dict() for fig in self.figure_specs],
            "timestamp": self.analysis_timestamp,
            "warnings": self.warnings,
        }
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)


# =============================================================================
# Power Analysis (Placeholder for P1 Enhancement)
# =============================================================================

@dataclass
class PowerAnalysisResult:
    """
    Statistical power analysis result.
    
    TODO: Implement using statsmodels.stats.power
    """
    test_type: TestType
    effect_size: float
    alpha: float
    power: float
    sample_size: int
    
    # Recommendation
    recommended_n: Optional[int] = None
    interpretation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_type": self.test_type.value,
            "effect_size": self.effect_size,
            "alpha": self.alpha,
            "power": self.power,
            "sample_size": self.sample_size,
            "recommended_n": self.recommended_n,
            "interpretation": self.interpretation,
        }
