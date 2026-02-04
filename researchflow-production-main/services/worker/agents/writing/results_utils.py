"""
Utility functions for Results Interpretation Agent

Contains helper functions for interpreting statistical results, assessing
clinical significance, and generating clinical narratives.
"""

import logging
import numpy as np
import re
from typing import Dict, Any, List, Optional, Tuple, Union
from scipy import stats
from datetime import datetime

try:
    from .results_types import (
        Finding, 
        EffectInterpretation, 
        ClinicalSignificanceLevel, 
        ConfidenceLevel,
        EffectMagnitude,
        LimitationType,
        Limitation
    )
except ImportError:
    # Fallback for direct execution
    from results_types import (
        Finding, 
        EffectInterpretation, 
        ClinicalSignificanceLevel, 
        ConfidenceLevel,
        EffectMagnitude,
        LimitationType,
        Limitation
    )

logger = logging.getLogger(__name__)


# =============================================================================
# P-value and Statistical Significance Interpretation
# =============================================================================

def interpret_p_value(p: float, context: str = "general") -> str:
    """
    Convert p-value to meaningful statement with appropriate caveats.
    
    Args:
        p: P-value from statistical test
        context: Clinical context for interpretation
    
    Returns:
        Human-readable interpretation of statistical significance
    """
    if p < 0.001:
        return f"The result was highly statistically significant (p < 0.001), providing strong evidence against the null hypothesis in the context of {context}."
    elif p < 0.01:
        return f"The result was statistically significant (p = {p:.3f}), providing good evidence against the null hypothesis in the context of {context}."
    elif p < 0.05:
        return f"The result was statistically significant (p = {p:.3f}), providing evidence against the null hypothesis in the context of {context}."
    elif p < 0.10:
        return f"The result approached statistical significance (p = {p:.3f}), suggesting a possible trend in {context} that warrants further investigation."
    else:
        return f"The result was not statistically significant (p = {p:.3f}), indicating insufficient evidence to reject the null hypothesis in the context of {context}."


def assess_statistical_power(
    effect_size: float, 
    sample_size: int, 
    alpha: float = 0.05,
    test_type: str = "t_test"
) -> Dict[str, Any]:
    """
    Assess statistical power for interpreting null results.
    
    Args:
        effect_size: Observed or expected effect size
        sample_size: Study sample size
        alpha: Significance level
        test_type: Type of statistical test
    
    Returns:
        Dictionary with power assessment
    """
    # Simple power calculation for t-tests
    if test_type == "t_test":
        # Approximate power calculation using Cohen's formula
        delta = effect_size * np.sqrt(sample_size / 2)
        df = sample_size - 2
        t_crit = stats.t.ppf(1 - alpha/2, df)
        
        # Approximate power using non-central t-distribution
        power = 1 - stats.nct.cdf(t_crit, df, delta) + stats.nct.cdf(-t_crit, df, delta)
        
        # Required sample size for 80% power
        n_80 = 2 * (stats.norm.ppf(0.8) + stats.norm.ppf(1 - alpha/2))**2 / (effect_size**2)
        
        interpretation = ""
        if power < 0.5:
            interpretation = "very low power - high risk of Type II error"
        elif power < 0.8:
            interpretation = "low to moderate power - substantial risk of Type II error"
        else:
            interpretation = "adequate power for detecting meaningful effects"
        
        return {
            "observed_power": float(power),
            "required_n_80_percent": int(np.ceil(n_80)),
            "interpretation": interpretation,
            "adequate_power": power >= 0.8
        }
    
    else:
        return {
            "observed_power": None,
            "interpretation": "Power calculation not available for this test type"
        }


# =============================================================================
# Clinical Significance Assessment
# =============================================================================

def assess_clinical_magnitude(
    effect_size: float, 
    mcid: float, 
    large_effect_threshold: float = 0.8
) -> str:
    """
    Assess clinical magnitude of effect size.
    
    Args:
        effect_size: Statistical effect size (Cohen's d, etc.)
        mcid: Minimal clinically important difference
        large_effect_threshold: Threshold for large effects
    
    Returns:
        Clinical magnitude category
    """
    abs_effect = abs(effect_size)
    
    if abs_effect >= large_effect_threshold:
        return "large"
    elif abs_effect >= mcid:
        return "moderate"
    elif abs_effect >= mcid * 0.5:
        return "small"
    else:
        return "negligible"


def calculate_nnt(effect_size: float, baseline_risk: float) -> Optional[float]:
    """
    Calculate Number Needed to Treat for clinical context.
    
    Assumes Cohen's d effect size and converts to ARR (Absolute Risk Reduction)
    using baseline risk and normal distribution assumptions.
    
    Args:
        effect_size: Cohen's d effect size
        baseline_risk: Baseline risk/probability of outcome (0-1)
    
    Returns:
        Number needed to treat, or None if calculation not applicable
    """
    if baseline_risk <= 0 or baseline_risk >= 1 or effect_size == 0:
        return None
    
    try:
        # Convert Cohen's d to probability difference
        # This is an approximation using normal distribution
        control_z = stats.norm.ppf(1 - baseline_risk)
        treatment_z = control_z + effect_size
        treatment_risk = 1 - stats.norm.cdf(treatment_z)
        
        # Absolute risk reduction
        arr = baseline_risk - treatment_risk
        
        if arr <= 0:
            return None
        
        nnt = 1 / arr
        return float(nnt) if nnt > 0 and nnt < 10000 else None
        
    except Exception as e:
        logger.warning(f"NNT calculation failed: {e}")
        return None


def calculate_nnh(effect_size: float, baseline_risk: float) -> Optional[float]:
    """
    Calculate Number Needed to Harm for adverse effects.
    
    Args:
        effect_size: Effect size (negative for harmful effects)
        baseline_risk: Baseline risk of adverse event
    
    Returns:
        Number needed to harm, or None if not applicable
    """
    if effect_size >= 0:
        return None
    
    nnt = calculate_nnt(abs(effect_size), baseline_risk)
    return nnt  # NNH uses same calculation as NNT for harmful effects


# =============================================================================
# Effect Size Interpretation
# =============================================================================

def interpret_cohens_d(d: float) -> Dict[str, Any]:
    """
    Interpret Cohen's d effect size.
    
    Args:
        d: Cohen's d value
    
    Returns:
        Dictionary with interpretation details
    """
    abs_d = abs(d)
    direction = "increase" if d > 0 else "decrease"
    
    if abs_d < 0.1:
        magnitude = EffectMagnitude.NEGLIGIBLE
        description = "negligible effect with minimal practical importance"
    elif abs_d < 0.2:
        magnitude = EffectMagnitude.SMALL
        description = "very small effect"
    elif abs_d < 0.5:
        magnitude = EffectMagnitude.SMALL
        description = "small effect"
    elif abs_d < 0.8:
        magnitude = EffectMagnitude.MEDIUM
        description = "medium effect with moderate practical importance"
    elif abs_d < 1.2:
        magnitude = EffectMagnitude.LARGE
        description = "large effect with substantial practical importance"
    else:
        magnitude = EffectMagnitude.VERY_LARGE
        description = "very large effect with major practical importance"
    
    # Convert to percentile difference
    percentile_diff = abs(stats.norm.cdf(d) - 0.5) * 2 * 100
    
    return {
        "magnitude": magnitude,
        "direction": direction,
        "description": description,
        "percentile_difference": f"{percentile_diff:.1f}%",
        "interpretation": f"A {magnitude.value} {direction} ({description}). This represents approximately a {percentile_diff:.1f} percentile point difference between groups."
    }


def interpret_odds_ratio(or_value: float, ci_lower: float, ci_upper: float) -> Dict[str, Any]:
    """
    Interpret odds ratio with confidence interval.
    
    Args:
        or_value: Odds ratio value
        ci_lower: Lower bound of 95% CI
        ci_upper: Upper bound of 95% CI
    
    Returns:
        Dictionary with interpretation details
    """
    if or_value == 1.0:
        return {
            "direction": "no effect",
            "magnitude": "none",
            "interpretation": "No association between variables (OR = 1.0)",
            "clinical_meaning": "The intervention has no effect on the odds of the outcome"
        }
    
    elif or_value > 1.0:
        # Increased odds
        if or_value < 1.2:
            magnitude = "very small increase"
        elif or_value < 1.5:
            magnitude = "small increase"
        elif or_value < 2.0:
            magnitude = "moderate increase"
        elif or_value < 3.0:
            magnitude = "large increase"
        else:
            magnitude = "very large increase"
        
        interpretation = f"The odds are {or_value:.2f} times higher (95% CI: {ci_lower:.2f}-{ci_upper:.2f})"
        clinical_meaning = f"The intervention results in a {magnitude} in the odds of the outcome"
        
    else:
        # Decreased odds
        inverse_or = 1 / or_value
        if inverse_or < 1.2:
            magnitude = "very small decrease"
        elif inverse_or < 1.5:
            magnitude = "small decrease" 
        elif inverse_or < 2.0:
            magnitude = "moderate decrease"
        elif inverse_or < 3.0:
            magnitude = "large decrease"
        else:
            magnitude = "very large decrease"
        
        interpretation = f"The odds are {inverse_or:.2f} times lower (95% CI: {1/ci_upper:.2f}-{1/ci_lower:.2f})"
        clinical_meaning = f"The intervention results in a {magnitude} in the odds of the outcome"
    
    return {
        "direction": "increase" if or_value > 1 else "decrease",
        "magnitude": magnitude,
        "interpretation": interpretation,
        "clinical_meaning": clinical_meaning
    }


def interpret_correlation(r: float, p_value: float) -> Dict[str, Any]:
    """
    Interpret correlation coefficient.
    
    Args:
        r: Correlation coefficient
        p_value: Statistical significance
    
    Returns:
        Dictionary with interpretation
    """
    abs_r = abs(r)
    direction = "positive" if r > 0 else "negative"
    
    if abs_r < 0.1:
        strength = "negligible"
    elif abs_r < 0.3:
        strength = "small"
    elif abs_r < 0.5:
        strength = "medium"
    elif abs_r < 0.7:
        strength = "large"
    else:
        strength = "very large"
    
    # Calculate shared variance
    r_squared = r ** 2
    
    significance = "statistically significant" if p_value < 0.05 else "not statistically significant"
    
    interpretation = f"A {strength} {direction} correlation (r = {r:.3f}, p = {p_value:.3f}) that is {significance}. Approximately {r_squared*100:.1f}% of the variance is shared between the variables."
    
    return {
        "strength": strength,
        "direction": direction,
        "r_squared": r_squared,
        "significance": significance,
        "interpretation": interpretation
    }


# =============================================================================
# Literature Comparison
# =============================================================================

def compare_to_literature(
    finding: Finding, 
    lit_results: List[Dict[str, Any]]
) -> str:
    """
    Compare finding to existing literature.
    
    Args:
        finding: Current study finding
        lit_results: List of literature results for comparison
    
    Returns:
        Comparison summary
    """
    if not lit_results:
        return "No comparable literature results available for comparison."
    
    # Extract effect sizes from literature
    lit_effects = []
    for result in lit_results:
        if "effect_size" in result and result["effect_size"] is not None:
            lit_effects.append(result["effect_size"])
    
    if not lit_effects or finding.effect_size is None:
        return "Insufficient data for quantitative comparison with literature."
    
    # Calculate literature statistics
    lit_mean = np.mean(lit_effects)
    lit_std = np.std(lit_effects) if len(lit_effects) > 1 else 0
    lit_min = np.min(lit_effects)
    lit_max = np.max(lit_effects)
    
    # Compare current finding
    current_effect = finding.effect_size
    
    # Determine where current finding falls in literature distribution
    if lit_std > 0:
        z_score = (current_effect - lit_mean) / lit_std
        if abs(z_score) < 0.5:
            comparison = "consistent with"
        elif z_score > 2:
            comparison = "substantially larger than"
        elif z_score < -2:
            comparison = "substantially smaller than" 
        elif z_score > 0.5:
            comparison = "larger than"
        else:
            comparison = "smaller than"
    else:
        if abs(current_effect - lit_mean) < 0.1:
            comparison = "very similar to"
        else:
            comparison = "different from"
    
    summary = f"The observed effect size ({current_effect:.3f}) is {comparison} the literature average ({lit_mean:.3f}, range: {lit_min:.3f} to {lit_max:.3f}, n = {len(lit_effects)} studies)."
    
    # Add context about consistency
    if len(lit_effects) >= 3:
        consistency_note = f" The literature shows {'high' if lit_std < 0.2 else 'moderate' if lit_std < 0.4 else 'low'} consistency (SD = {lit_std:.3f})."
        summary += consistency_note
    
    return summary


# =============================================================================
# Limitation Identification
# =============================================================================

def identify_statistical_limitations(statistical_results: Dict[str, Any]) -> List[Limitation]:
    """
    Identify statistical limitations from analysis results.
    
    Args:
        statistical_results: Results from statistical analysis
    
    Returns:
        List of identified statistical limitations
    """
    limitations = []
    
    # Check for multiple comparisons
    num_tests = len(statistical_results.get("secondary_outcomes", []))
    if num_tests > 5:
        limitations.append(Limitation(
            type=LimitationType.MULTIPLE_COMPARISONS,
            severity="moderate",
            description=f"Multiple secondary endpoints ({num_tests}) increase risk of Type I error",
            impact_on_findings="May inflate statistical significance of secondary outcomes",
            recommendation="Apply Bonferroni correction or focus on pre-specified primary endpoints",
            affects_generalizability=False
        ))
    
    # Check for assumption violations
    assumptions = statistical_results.get("assumptions", {})
    if assumptions.get("normality", {}).get("passed") is False:
        limitations.append(Limitation(
            type=LimitationType.STATISTICAL_POWER,
            severity="low",
            description="Normality assumption violated for parametric tests",
            impact_on_findings="May affect accuracy of p-values and confidence intervals",
            recommendation="Consider non-parametric alternatives or data transformation",
            affects_generalizability=False
        ))
    
    # Check for small sample size
    sample_info = statistical_results.get("sample_info", {})
    total_n = sample_info.get("total_n", 0)
    if total_n < 50:
        limitations.append(Limitation(
            type=LimitationType.SAMPLE_SIZE,
            severity="moderate",
            description=f"Small sample size (n={total_n}) limits statistical power",
            impact_on_findings="Increases risk of Type II error and reduces precision",
            recommendation="Interpret results cautiously; consider replication with larger sample",
            affects_generalizability=True
        ))
    
    # Check for effect size without confidence intervals
    primary_outcomes = statistical_results.get("primary_outcomes", [])
    missing_ci_count = sum(1 for outcome in primary_outcomes 
                          if "confidence_interval" not in outcome or 
                          outcome.get("confidence_interval") is None)
    
    if missing_ci_count > 0:
        limitations.append(Limitation(
            type=LimitationType.STATISTICAL_POWER,
            severity="low",
            description="Confidence intervals not provided for some effect sizes",
            impact_on_findings="Limits ability to assess precision of estimates",
            recommendation="Report confidence intervals for all effect sizes",
            affects_generalizability=False
        ))
    
    return limitations


def identify_design_limitations(study_context: Dict[str, Any]) -> List[Limitation]:
    """
    Identify study design limitations.
    
    Args:
        study_context: Study design and protocol information
    
    Returns:
        List of design-related limitations
    """
    limitations = []
    
    protocol = study_context.get("protocol", {})
    
    # Check study design
    study_type = protocol.get("study_design", "").lower()
    if "observational" in study_type or "cohort" in study_type:
        limitations.append(Limitation(
            type=LimitationType.DESIGN,
            severity="moderate",
            description="Observational design limits causal inference",
            impact_on_findings="Cannot establish causation, only association",
            recommendation="Consider randomized controlled trial for causal inference",
            affects_generalizability=True
        ))
    
    # Check randomization
    if not protocol.get("randomized", False) and "rct" not in study_type:
        limitations.append(Limitation(
            type=LimitationType.SELECTION_BIAS,
            severity="moderate",
            description="Non-randomized design increases risk of selection bias",
            impact_on_findings="Baseline differences may confound results",
            recommendation="Control for potential confounders in analysis",
            affects_generalizability=True
        ))
    
    # Check blinding
    blinding = protocol.get("blinding", "").lower()
    if "none" in blinding or not blinding:
        limitations.append(Limitation(
            type=LimitationType.DESIGN,
            severity="low",
            description="Lack of blinding may introduce bias",
            impact_on_findings="May affect outcome assessment and participant behavior",
            recommendation="Use objective outcomes when possible",
            affects_generalizability=False
        ))
    
    # Check follow-up duration
    follow_up = protocol.get("follow_up_duration", "").lower()
    if "week" in follow_up or "day" in follow_up:
        limitations.append(Limitation(
            type=LimitationType.TEMPORAL,
            severity="moderate",
            description="Short follow-up duration limits assessment of long-term effects",
            impact_on_findings="Cannot assess durability of treatment effects",
            recommendation="Consider longer follow-up studies",
            affects_generalizability=True
        ))
    
    return limitations


# =============================================================================
# Confidence Assessment
# =============================================================================

def generate_confidence_statement(finding: Finding, confidence: ConfidenceLevel) -> str:
    """
    Generate appropriate confidence statement for a finding.
    
    Args:
        finding: Research finding
        confidence: Assessed confidence level
    
    Returns:
        Confidence statement string
    """
    confidence_phrases = {
        ConfidenceLevel.VERY_HIGH: "very high confidence",
        ConfidenceLevel.HIGH: "high confidence", 
        ConfidenceLevel.MODERATE: "moderate confidence",
        ConfidenceLevel.LOW: "low confidence",
        ConfidenceLevel.VERY_LOW: "very low confidence"
    }
    
    phrase = confidence_phrases[confidence]
    
    # Customize based on finding characteristics
    if finding.p_value and finding.p_value < 0.001:
        statistical_strength = "strong statistical evidence"
    elif finding.p_value and finding.p_value < 0.01:
        statistical_strength = "good statistical evidence"
    elif finding.p_value and finding.p_value < 0.05:
        statistical_strength = "adequate statistical evidence"
    else:
        statistical_strength = "limited statistical evidence"
    
    # Include effect size context
    effect_context = ""
    if finding.effect_size:
        if abs(finding.effect_size) > 0.8:
            effect_context = " with a large effect size"
        elif abs(finding.effect_size) > 0.5:
            effect_context = " with a moderate effect size"
        else:
            effect_context = " with a small effect size"
    
    return f"We have {phrase} in this finding based on {statistical_strength}{effect_context}. {finding.clinical_interpretation}"


# =============================================================================
# Narrative Generation
# =============================================================================

def format_clinical_narrative(
    primary_findings: List[Finding],
    secondary_findings: List[Finding],
    clinical_significance: str,
    effect_interpretations: Dict[str, str],
    limitations: List[str],
    confidence_statements: List[str]
) -> str:
    """
    Format findings into coherent clinical narrative.
    
    Args:
        primary_findings: Primary study findings
        secondary_findings: Secondary findings  
        clinical_significance: Clinical significance assessment
        effect_interpretations: Effect size interpretations
        limitations: Study limitations
        confidence_statements: Confidence assessments
    
    Returns:
        Formatted clinical narrative
    """
    narrative_parts = []
    
    # Introduction
    narrative_parts.append("## Clinical Interpretation of Results\n")
    
    # Primary findings
    if primary_findings:
        narrative_parts.append("### Primary Findings\n")
        for i, finding in enumerate(primary_findings, 1):
            narrative_parts.append(f"**Finding {i}:** {finding.clinical_interpretation}")
            if finding.statistical_result:
                narrative_parts.append(f"(Statistical result: {finding.statistical_result})")
            narrative_parts.append("")
    
    # Clinical significance
    if clinical_significance:
        narrative_parts.append("### Clinical Significance\n")
        narrative_parts.append(clinical_significance)
        narrative_parts.append("")
    
    # Effect size interpretations
    if effect_interpretations:
        narrative_parts.append("### Effect Size Interpretations\n")
        for outcome, interpretation in effect_interpretations.items():
            narrative_parts.append(f"**{outcome}:** {interpretation}")
        narrative_parts.append("")
    
    # Secondary findings
    if secondary_findings:
        narrative_parts.append("### Secondary Findings\n")
        for finding in secondary_findings:
            narrative_parts.append(f"- {finding.clinical_interpretation}")
        narrative_parts.append("")
    
    # Limitations
    if limitations:
        narrative_parts.append("### Study Limitations\n")
        for limitation in limitations:
            narrative_parts.append(f"- {limitation}")
        narrative_parts.append("")
    
    # Confidence and conclusions
    if confidence_statements:
        narrative_parts.append("### Confidence in Findings\n")
        for statement in confidence_statements:
            narrative_parts.append(statement)
        narrative_parts.append("")
    
    return "\n".join(narrative_parts)


def generate_apa_summary(
    primary_findings: List[Finding],
    study_context: Dict[str, Any]
) -> str:
    """
    Generate APA-style results summary.
    
    Args:
        primary_findings: Primary study findings
        study_context: Study context information
    
    Returns:
        APA-formatted results summary
    """
    if not primary_findings:
        return "No primary findings to report."
    
    summary_parts = []
    
    # Extract study info
    n = study_context.get("sample_size", "N not specified")
    study_design = study_context.get("protocol", {}).get("study_design", "")
    
    summary_parts.append(f"In this {study_design} study (N = {n}), ")
    
    # Report primary findings
    for i, finding in enumerate(primary_findings):
        if i > 0:
            summary_parts.append(". Additionally, ")
        
        # Format statistical result
        if finding.statistical_result and finding.p_value:
            summary_parts.append(f"{finding.clinical_interpretation} ({finding.statistical_result}, p = {finding.p_value:.3f})")
        else:
            summary_parts.append(finding.clinical_interpretation)
        
        # Add effect size if available
        if finding.effect_size:
            summary_parts.append(f", d = {finding.effect_size:.2f}")
    
    summary_parts.append(".")
    
    return "".join(summary_parts)


# =============================================================================
# PHI Safety Functions
# =============================================================================

def scan_for_phi_in_interpretation(text: str) -> Dict[str, Any]:
    """
    Scan interpretation text for potential PHI.
    
    Args:
        text: Text to scan for PHI
    
    Returns:
        Dictionary with PHI scan results
    """
    phi_patterns = {
        "dates": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "mrn": r"\bmrn:?\s*\d+\b",
        "patient_id": r"\bpatient\s+id:?\s*\w+\b"
    }
    
    found_phi = {}
    total_matches = 0
    
    for phi_type, pattern in phi_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found_phi[phi_type] = matches
            total_matches += len(matches)
    
    return {
        "has_phi": total_matches > 0,
        "phi_types": list(found_phi.keys()),
        "total_matches": total_matches,
        "details": found_phi
    }


def redact_phi_from_interpretation(text: str) -> str:
    """
    Remove potential PHI from interpretation text.
    
    Args:
        text: Text to redact
    
    Returns:
        Redacted text
    """
    phi_patterns = {
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b": "[DATE REDACTED]",
        r"\b\d{3}-\d{2}-\d{4}\b": "[SSN REDACTED]",
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b": "[PHONE REDACTED]",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b": "[EMAIL REDACTED]",
        r"\bmrn:?\s*\d+\b": "[MRN REDACTED]",
        r"\bpatient\s+id:?\s*\w+\b": "[PATIENT ID REDACTED]"
    }
    
    redacted_text = text
    for pattern, replacement in phi_patterns.items():
        redacted_text = re.sub(pattern, replacement, redacted_text, flags=re.IGNORECASE)
    
    return redacted_text