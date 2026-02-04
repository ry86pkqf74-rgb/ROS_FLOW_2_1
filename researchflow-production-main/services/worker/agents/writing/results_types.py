"""
Type definitions for Results Interpretation Agent

Defines the data models and enums used for clinical results interpretation,
including findings, confidence levels, and limitation types.
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class ClinicalSignificanceLevel(str, Enum):
    """Levels of clinical significance beyond statistical significance."""
    HIGHLY_SIGNIFICANT = "highly_significant"
    CLINICALLY_SIGNIFICANT = "clinically_significant" 
    MINIMALLY_SIGNIFICANT = "minimally_significant"
    STATISTICALLY_ONLY = "statistically_only"
    NOT_SIGNIFICANT = "not_significant"


class ConfidenceLevel(str, Enum):
    """Confidence levels for findings and interpretations."""
    VERY_HIGH = "very_high"
    HIGH = "high" 
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


class LimitationType(str, Enum):
    """Types of study limitations."""
    SAMPLE_SIZE = "sample_size"
    STATISTICAL_POWER = "statistical_power"
    GENERALIZABILITY = "generalizability"
    MEASUREMENT = "measurement"
    DESIGN = "design"
    TEMPORAL = "temporal"
    SELECTION_BIAS = "selection_bias"
    MULTIPLE_COMPARISONS = "multiple_comparisons"
    CONFOUNDING = "confounding"
    ATTRITION = "attrition"


class EffectMagnitude(str, Enum):
    """Effect size magnitude categories."""
    NEGLIGIBLE = "negligible"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VERY_LARGE = "very_large"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class Finding:
    """Represents a single research finding with interpretation."""
    hypothesis: str
    statistical_result: str
    clinical_interpretation: str
    confidence_level: ConfidenceLevel
    clinical_significance: ClinicalSignificanceLevel
    effect_size: Optional[float] = None
    p_value: Optional[float] = None
    confidence_interval: Optional[tuple[float, float]] = None
    supporting_evidence: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "hypothesis": self.hypothesis,
            "statistical_result": self.statistical_result,
            "clinical_interpretation": self.clinical_interpretation,
            "confidence_level": self.confidence_level.value,
            "clinical_significance": self.clinical_significance.value,
            "effect_size": self.effect_size,
            "p_value": self.p_value,
            "confidence_interval": self.confidence_interval,
            "supporting_evidence": self.supporting_evidence,
            "limitations": self.limitations,
        }


@dataclass
class EffectInterpretation:
    """Interpretation of effect size in clinical terms."""
    effect_size: float
    magnitude: str
    direction: str
    description: str
    clinical_meaning: str
    number_needed_to_treat: Optional[float] = None
    minimal_important_difference_met: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "effect_size": self.effect_size,
            "magnitude": self.magnitude,
            "direction": self.direction,
            "description": self.description,
            "clinical_meaning": self.clinical_meaning,
            "number_needed_to_treat": self.number_needed_to_treat,
            "minimal_important_difference_met": self.minimal_important_difference_met,
        }


@dataclass
class Limitation:
    """Represents a study limitation with severity and recommendations."""
    type: LimitationType
    severity: str  # "low", "moderate", "severe"
    description: str
    impact_on_findings: str
    recommendation: str
    affects_generalizability: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "severity": self.severity,
            "description": self.description,
            "impact_on_findings": self.impact_on_findings,
            "recommendation": self.recommendation,
            "affects_generalizability": self.affects_generalizability,
        }


class ResultsInterpretationState(BaseModel):
    """
    Pydantic model for Results Interpretation Agent state.
    
    This represents the complete state passed through the interpretation workflow,
    including inputs from previous stages and generated outputs.
    """
    
    # Inputs
    study_id: str = Field(description="Unique study identifier")
    statistical_results: Dict[str, Any] = Field(description="Results from Stage 7 statistical analysis")
    visualizations: List[str] = Field(description="Visualization file paths from Stage 8")
    study_context: Dict[str, Any] = Field(description="Study protocol, hypotheses, and design context")
    
    # Outputs
    primary_findings: List[Finding] = Field(default_factory=list, description="Primary study findings")
    secondary_findings: List[Finding] = Field(default_factory=list, description="Secondary/exploratory findings")
    clinical_significance: str = Field(default="", description="Overall clinical significance assessment")
    effect_interpretations: Dict[str, str] = Field(default_factory=dict, description="Effect size interpretations")
    limitations_identified: List[str] = Field(default_factory=list, description="Study limitations")
    confidence_statements: List[str] = Field(default_factory=list, description="Confidence assessments")
    
    # Metadata
    interpretation_version: str = Field(default="1.0", description="Version of interpretation framework")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during interpretation")
    warnings: List[str] = Field(default_factory=list, description="Warnings about interpretation quality")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of interpretation")
    interpreted_by: str = Field(default="ResultsInterpretationAgent", description="Agent that performed interpretation")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            Finding: lambda f: f.to_dict(),
            EffectInterpretation: lambda e: e.to_dict(),
            Limitation: lambda l: l.to_dict(),
        }

    def add_primary_finding(
        self, 
        hypothesis: str,
        statistical_result: str, 
        clinical_interpretation: str,
        confidence: ConfidenceLevel,
        significance: ClinicalSignificanceLevel,
        **kwargs
    ) -> None:
        """Add a primary finding to the results."""
        finding = Finding(
            hypothesis=hypothesis,
            statistical_result=statistical_result,
            clinical_interpretation=clinical_interpretation,
            confidence_level=confidence,
            clinical_significance=significance,
            **kwargs
        )
        self.primary_findings.append(finding)

    def add_secondary_finding(
        self, 
        hypothesis: str,
        statistical_result: str, 
        clinical_interpretation: str,
        confidence: ConfidenceLevel,
        significance: ClinicalSignificanceLevel,
        **kwargs
    ) -> None:
        """Add a secondary finding to the results."""
        finding = Finding(
            hypothesis=hypothesis,
            statistical_result=statistical_result,
            clinical_interpretation=clinical_interpretation,
            confidence_level=confidence,
            clinical_significance=significance,
            **kwargs
        )
        self.secondary_findings.append(finding)

    def add_limitation(self, limitation: str, severity: str = "moderate") -> None:
        """Add a study limitation."""
        self.limitations_identified.append(f"[{severity.upper()}] {limitation}")

    def add_confidence_statement(self, statement: str) -> None:
        """Add a confidence statement."""
        self.confidence_statements.append(statement)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the interpretation results."""
        return {
            "study_id": self.study_id,
            "num_primary_findings": len(self.primary_findings),
            "num_secondary_findings": len(self.secondary_findings),
            "num_limitations": len(self.limitations_identified),
            "num_confidence_statements": len(self.confidence_statements),
            "has_clinical_significance": bool(self.clinical_significance),
            "has_effect_interpretations": bool(self.effect_interpretations),
            "num_errors": len(self.errors),
            "num_warnings": len(self.warnings),
            "interpretation_version": self.interpretation_version,
            "created_at": self.created_at,
        }

    def validate_completeness(self) -> List[str]:
        """Validate that the interpretation is complete."""
        issues = []
        
        if not self.primary_findings:
            issues.append("No primary findings identified")
        
        if not self.clinical_significance:
            issues.append("Clinical significance assessment missing")
        
        if not self.limitations_identified:
            issues.append("No limitations identified (unlikely for real study)")
        
        if not self.confidence_statements:
            issues.append("No confidence statements provided")
        
        if self.errors:
            issues.append(f"{len(self.errors)} errors present in interpretation")
        
        return issues


# =============================================================================
# Input/Output Types for External Interface
# =============================================================================

class InterpretationRequest(BaseModel):
    """Request for results interpretation."""
    study_id: str
    statistical_results: Dict[str, Any]
    visualizations: List[str] = Field(default_factory=list)
    study_context: Dict[str, Any] = Field(default_factory=dict)
    interpretation_options: Dict[str, Any] = Field(default_factory=dict)


class InterpretationResponse(BaseModel):
    """Response from results interpretation."""
    success: bool
    study_id: str
    interpretation_state: Optional[ResultsInterpretationState] = None
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    processing_time_ms: int
    
    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Clinical Context Types
# =============================================================================

class ClinicalBenchmark(BaseModel):
    """Clinical benchmarks for significance assessment."""
    minimal_clinically_important_difference: float
    large_effect_threshold: float = 0.8
    baseline_risk: Optional[float] = None
    cost_effectiveness_threshold: Optional[float] = None
    patient_acceptable_symptom_state: Optional[float] = None


class StudyDesignContext(BaseModel):
    """Study design context for interpretation."""
    study_type: str  # "rct", "cohort", "case_control", etc.
    randomization: bool = False
    blinding: str = "none"  # "none", "single", "double", "triple"
    sample_size: int
    follow_up_duration: Optional[str] = None
    primary_endpoints: List[str] = Field(default_factory=list)
    secondary_endpoints: List[str] = Field(default_factory=list)
    inclusion_criteria: List[str] = Field(default_factory=list)
    exclusion_criteria: List[str] = Field(default_factory=list)


class LiteratureComparison(BaseModel):
    """Comparison with existing literature."""
    prior_studies: List[Dict[str, Any]] = Field(default_factory=list)
    systematic_reviews: List[Dict[str, Any]] = Field(default_factory=list)
    clinical_guidelines: List[Dict[str, Any]] = Field(default_factory=list)
    comparison_summary: str = ""