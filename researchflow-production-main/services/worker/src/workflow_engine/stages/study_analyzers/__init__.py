"""
Enhanced Study Design Analyzers for Stage 6

This module provides advanced study design capabilities including:
- ML-enhanced study design selection and optimization
- Advanced statistical power analysis and sample size calculations
- Regulatory compliance validation for clinical trials
- Template-driven protocol generation
- Integration with PHI protection systems

Components:
- MLStudyDesignOptimizer: Evidence-based study design selection
- StatisticalPowerEngine: Advanced power analysis and sample sizing
- ProtocolGenerator: Template-driven protocol generation
- StudyComplianceValidator: Regulatory compliance validation
"""

# Core study analyzers
from .ml_study_optimizer import MLStudyDesignOptimizer, StudyDesignRecommendation
from .statistical_power_engine import (
    StatisticalPowerEngine, PowerAnalysisResult, SampleSizeCalculation,
    AdaptiveAnalysisResult, BayesianPowerResult, StatisticalTestType,
    AdaptiveDesignType, BayesianMethod
)
from .protocol_generator import ProtocolGenerator, ProtocolTemplate, ProtocolSection
from .compliance_validator import StudyComplianceValidator, ComplianceFramework, ComplianceResult

# Utility functions
def create_ml_study_optimizer(
    confidence_threshold: float = 0.8,
    enable_clinical_models: bool = True,
    literature_integration: bool = True
) -> MLStudyDesignOptimizer:
    """Create ML study design optimizer with default configuration."""
    return MLStudyDesignOptimizer(
        confidence_threshold=confidence_threshold,
        enable_clinical_models=enable_clinical_models,
        literature_integration=literature_integration
    )

def create_power_engine(
    default_power: float = 0.8,
    default_alpha: float = 0.05,
    enable_adaptive: bool = True
) -> StatisticalPowerEngine:
    """Create statistical power engine with default configuration."""
    return StatisticalPowerEngine(
        default_power=default_power,
        default_alpha=default_alpha,
        enable_adaptive=enable_adaptive
    )

def create_protocol_generator(
    template_version: str = "v1.0",
    enable_phi_integration: bool = True,
    regulatory_templates: bool = True
) -> ProtocolGenerator:
    """Create protocol generator with default configuration."""
    return ProtocolGenerator(
        template_version=template_version,
        enable_phi_integration=enable_phi_integration,
        regulatory_templates=regulatory_templates
    )

# Export all components
__all__ = [
    # Core analyzers
    "MLStudyDesignOptimizer",
    "StatisticalPowerEngine", 
    "ProtocolGenerator",
    "StudyComplianceValidator",
    
    # Data structures
    "StudyDesignRecommendation",
    "PowerAnalysisResult",
    "SampleSizeCalculation",
    "AdaptiveAnalysisResult",
    "BayesianPowerResult",
    "StatisticalTestType",
    "AdaptiveDesignType",
    "BayesianMethod",
    "ProtocolTemplate",
    "ProtocolSection",
    "ComplianceFramework",
    "ComplianceResult",
    
    # Factory functions
    "create_ml_study_optimizer",
    "create_power_engine",
    "create_protocol_generator",
]