"""
Meta-Analysis Type Definitions

Type definitions for meta-analysis including:
- Effect measures and models
- Heterogeneity assessments
- Publication bias detection
- Sensitivity analysis

Linear Issues: ROS-XXX (Stage 10-11 - Meta-Analysis Agent)
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enumerations
# =============================================================================

class EffectMeasure(str, Enum):
    """Types of effect measures for meta-analysis."""
    ODDS_RATIO = "OR"  # Odds ratio
    RISK_RATIO = "RR"  # Relative risk / risk ratio
    RISK_DIFFERENCE = "RD"  # Risk difference
    MEAN_DIFFERENCE = "MD"  # Mean difference
    STANDARDIZED_MEAN_DIFFERENCE = "SMD"  # Standardized mean difference (Hedges' g)
    HAZARD_RATIO = "HR"  # Hazard ratio (survival data)
    RATE_RATIO = "IRR"  # Incidence rate ratio


class ModelType(str, Enum):
    """Statistical models for pooling."""
    FIXED_EFFECT = "fixed"  # Fixed-effect model (Mantel-Haenszel, inverse variance)
    RANDOM_EFFECTS = "random"  # Random-effects model (DerSimonian-Laird)
    RANDOM_EFFECTS_REML = "random_reml"  # REML estimator
    RANDOM_EFFECTS_HKSJ = "random_hksj"  # Hartung-Knapp-Sidik-Jonkman


class HeterogeneityTest(str, Enum):
    """Tests for heterogeneity."""
    COCHRAN_Q = "cochran_q"
    I_SQUARED = "i_squared"
    TAU_SQUARED = "tau_squared"
    H_STATISTIC = "h_statistic"


class PublicationBiasTest(str, Enum):
    """Tests for publication bias."""
    EGGER = "egger"  # Egger's regression test
    BEGG = "begg"  # Begg-Mazumdar rank correlation
    TRIM_AND_FILL = "trim_and_fill"  # Trim-and-fill method


# =============================================================================
# Input Data Structures
# =============================================================================

class StudyEffect(BaseModel):
    """Individual study effect size data."""
    study_id: str = Field(..., description="Unique study identifier")
    study_label: str = Field(..., description="Study label for display (Author Year)")
    
    # Effect estimate
    effect_estimate: float = Field(..., description="Point estimate (OR, RR, MD, etc.)")
    se: Optional[float] = Field(None, description="Standard error")
    ci_lower: Optional[float] = Field(None, description="Lower 95% CI")
    ci_upper: Optional[float] = Field(None, description="Upper 95% CI")
    
    # Alternative: raw data for binary outcomes
    n_intervention: Optional[int] = Field(None, description="Sample size in intervention group")
    n_control: Optional[int] = Field(None, description="Sample size in control group")
    events_intervention: Optional[int] = Field(None, description="Events in intervention")
    events_control: Optional[int] = Field(None, description="Events in control")
    
    # Alternative: continuous data
    mean_intervention: Optional[float] = None
    sd_intervention: Optional[float] = None
    mean_control: Optional[float] = None
    sd_control: Optional[float] = None
    
    # Study characteristics
    year: Optional[int] = None
    sample_size: Optional[int] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Weighting (calculated)
    weight: Optional[float] = Field(None, description="Study weight in meta-analysis")


class MetaAnalysisConfig(BaseModel):
    """Configuration for meta-analysis."""
    effect_measure: EffectMeasure = Field(..., description="Type of effect measure")
    model_type: ModelType = Field(default=ModelType.RANDOM_EFFECTS, description="Pooling model")
    
    # Heterogeneity settings
    tau_method: str = Field(default="DL", description="Tau estimation method (DL, REML, PM)")
    confidence_level: float = Field(default=0.95, ge=0.0, le=1.0)
    
    # Subgroup/sensitivity settings
    subgroup_variable: Optional[str] = Field(None, description="Variable for subgroup analysis")
    exclude_studies: List[str] = Field(default_factory=list, description="Study IDs to exclude")
    
    # Publication bias settings
    test_publication_bias: bool = Field(default=True)
    trim_and_fill: bool = Field(default=True, description="Apply trim-and-fill method")


# =============================================================================
# Result Structures
# =============================================================================

@dataclass
class HeterogeneityResult:
    """Results of heterogeneity assessment."""
    cochran_q: float
    cochran_q_p: float
    df: int
    
    i_squared: float  # 0-100%
    i_squared_ci_lower: float
    i_squared_ci_upper: float
    
    tau_squared: float  # Between-study variance
    tau: float  # Between-study SD
    
    h_statistic: float
    
    interpretation: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cochran_q": round(self.cochran_q, 3),
            "cochran_q_p": round(self.cochran_q_p, 4),
            "df": self.df,
            "i_squared": round(self.i_squared, 1),
            "i_squared_ci": [round(self.i_squared_ci_lower, 1), round(self.i_squared_ci_upper, 1)],
            "tau_squared": round(self.tau_squared, 4),
            "tau": round(self.tau, 4),
            "h_statistic": round(self.h_statistic, 3),
            "interpretation": self.interpretation,
        }


@dataclass
class PublicationBiasResult:
    """Results of publication bias assessment."""
    test_name: str
    statistic: float
    p_value: float
    
    # Trim-and-fill results
    trim_and_fill_k0: Optional[int] = None  # Number of missing studies imputed
    trim_and_fill_estimate: Optional[float] = None
    trim_and_fill_ci_lower: Optional[float] = None
    trim_and_fill_ci_upper: Optional[float] = None
    
    interpretation: str
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "test_name": self.test_name,
            "statistic": round(self.statistic, 3),
            "p_value": round(self.p_value, 4),
            "interpretation": self.interpretation,
        }
        
        if self.trim_and_fill_k0 is not None:
            result["trim_and_fill"] = {
                "missing_studies": self.trim_and_fill_k0,
                "adjusted_estimate": round(self.trim_and_fill_estimate, 3) if self.trim_and_fill_estimate else None,
                "adjusted_ci": [
                    round(self.trim_and_fill_ci_lower, 3) if self.trim_and_fill_ci_lower else None,
                    round(self.trim_and_fill_ci_upper, 3) if self.trim_and_fill_ci_upper else None,
                ]
            }
        
        return result


@dataclass
class SubgroupResult:
    """Results of subgroup analysis."""
    subgroup_name: str
    n_studies: int
    pooled_effect: float
    ci_lower: float
    ci_upper: float
    i_squared: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subgroup": self.subgroup_name,
            "n_studies": self.n_studies,
            "pooled_effect": round(self.pooled_effect, 3),
            "ci_95": [round(self.ci_lower, 3), round(self.ci_upper, 3)],
            "i_squared": round(self.i_squared, 1),
        }


@dataclass
class SensitivityAnalysisResult:
    """Results of leave-one-out sensitivity analysis."""
    excluded_study_id: str
    pooled_effect: float
    ci_lower: float
    ci_upper: float
    i_squared: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "excluded_study": self.excluded_study_id,
            "pooled_effect": round(self.pooled_effect, 3),
            "ci_95": [round(self.ci_lower, 3), round(self.ci_upper, 3)],
            "i_squared": round(self.i_squared, 1),
        }


@dataclass
class MetaAnalysisResult:
    """Complete meta-analysis result."""
    # Configuration
    effect_measure: EffectMeasure
    model_type: ModelType
    n_studies: int
    total_n: int
    
    # Pooled effect
    pooled_effect: float
    ci_lower: float
    ci_upper: float
    p_value: float
    z_score: float
    
    # Study weights
    study_weights: Dict[str, float] = field(default_factory=dict)
    
    # Heterogeneity
    heterogeneity: Optional[HeterogeneityResult] = None
    
    # Publication bias
    publication_bias: Optional[PublicationBiasResult] = None
    
    # Subgroup analysis
    subgroups: List[SubgroupResult] = field(default_factory=list)
    
    # Sensitivity analysis
    sensitivity: List[SensitivityAnalysisResult] = field(default_factory=list)
    
    # Visualization specs
    forest_plot_data: Optional[Dict[str, Any]] = None
    funnel_plot_data: Optional[Dict[str, Any]] = None
    
    # Interpretation
    summary: str = ""
    warnings: List[str] = field(default_factory=list)
    
    # Metadata
    analysis_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def format_result(self) -> str:
        """Format result for reporting."""
        measure_name = {
            EffectMeasure.ODDS_RATIO: "OR",
            EffectMeasure.RISK_RATIO: "RR",
            EffectMeasure.MEAN_DIFFERENCE: "MD",
            EffectMeasure.STANDARDIZED_MEAN_DIFFERENCE: "SMD",
        }.get(self.effect_measure, str(self.effect_measure))
        
        model_name = "random-effects" if "random" in self.model_type.value else "fixed-effect"
        
        # Format p-value
        if self.p_value < 0.001:
            p_str = "p < 0.001"
        else:
            p_str = f"p = {self.p_value:.3f}"
        
        result_text = (
            f"Meta-analysis of {self.n_studies} studies (n = {self.total_n}) using {model_name} model: "
            f"{measure_name} = {self.pooled_effect:.2f} (95% CI [{self.ci_lower:.2f}, {self.ci_upper:.2f}]), "
            f"z = {self.z_score:.2f}, {p_str}."
        )
        
        if self.heterogeneity:
            result_text += (
                f" Heterogeneity: I² = {self.heterogeneity.i_squared:.1f}%, "
                f"τ² = {self.heterogeneity.tau_squared:.3f}, "
                f"χ² = {self.heterogeneity.cochran_q:.2f} (p = {self.heterogeneity.cochran_q_p:.3f})."
            )
        
        return result_text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "effect_measure": self.effect_measure.value,
            "model_type": self.model_type.value,
            "n_studies": self.n_studies,
            "total_n": self.total_n,
            "pooled_effect": round(self.pooled_effect, 3),
            "ci_95": [round(self.ci_lower, 3), round(self.ci_upper, 3)],
            "p_value": round(self.p_value, 4),
            "z_score": round(self.z_score, 3),
            "heterogeneity": self.heterogeneity.to_dict() if self.heterogeneity else None,
            "publication_bias": self.publication_bias.to_dict() if self.publication_bias else None,
            "subgroups": [s.to_dict() for s in self.subgroups],
            "sensitivity": [s.to_dict() for s in self.sensitivity],
            "summary": self.summary,
            "formatted_result": self.format_result(),
            "warnings": self.warnings,
            "timestamp": self.analysis_timestamp,
        }
