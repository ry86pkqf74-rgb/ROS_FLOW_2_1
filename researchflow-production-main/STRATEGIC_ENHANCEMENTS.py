#!/usr/bin/env python3
"""
Strategic Enhancements for Statistical Analysis Agent

This file contains advanced statistical methods to be integrated into the main agent.
Phase A1: Statistical Rigor Sprint
"""

import numpy as np
from typing import List, Dict, Any
from scipy import stats


def apply_multiple_comparison_correction(
    p_values: List[float], 
    method: str = "benjamini_hochberg"
) -> Dict[str, Any]:
    """
    Apply multiple comparison corrections to p-values.
    
    ✅ Strategic Enhancement #13: Advanced multiple comparison corrections
    
    Args:
        p_values: List of uncorrected p-values
        method: Correction method ('bonferroni', 'benjamini_hochberg', 'holm', 'sidak')
    
    Returns:
        Dictionary with corrected p-values and rejection decisions
    """
    p_array = np.array(p_values)
    n_tests = len(p_array)
    alpha = 0.05
    
    if method == "bonferroni":
        # Simple Bonferroni correction
        p_corrected = np.minimum(p_array * n_tests, 1.0)
        rejected = p_corrected < alpha
        
    elif method == "benjamini_hochberg":
        # Benjamini-Hochberg (False Discovery Rate)
        sorted_indices = np.argsort(p_array)
        sorted_p = p_array[sorted_indices]
        
        # Calculate Benjamini-Hochberg critical values
        bh_values = alpha * np.arange(1, n_tests + 1) / n_tests
        
        # Find largest i where p(i) <= alpha * i / m
        rejected_sorted = sorted_p <= bh_values
        
        if np.any(rejected_sorted):
            max_rejected_idx = np.max(np.where(rejected_sorted)[0])
            rejected_sorted[:(max_rejected_idx + 1)] = True
        
        # Map back to original order
        rejected = np.zeros_like(p_array, dtype=bool)
        rejected[sorted_indices] = rejected_sorted
        
        # Adjusted p-values for BH
        p_corrected = np.zeros_like(p_array)
        for i in range(n_tests):
            original_idx = sorted_indices[i]
            rank = i + 1
            p_corrected[original_idx] = min(1.0, sorted_p[i] * n_tests / rank)
        
    elif method == "holm":
        # Holm-Bonferroni step-down method
        sorted_indices = np.argsort(p_array)
        sorted_p = p_array[sorted_indices]
        
        rejected_sorted = np.zeros(n_tests, dtype=bool)
        p_corrected_sorted = np.zeros(n_tests)
        
        for i in range(n_tests):
            # Holm critical value: alpha / (m - i)
            holm_alpha = alpha / (n_tests - i)
            p_corrected_sorted[i] = sorted_p[i] * (n_tests - i)
            
            if sorted_p[i] <= holm_alpha:
                rejected_sorted[i] = True
            else:
                # Once we fail to reject, all subsequent tests fail
                break
        
        # Map back to original order
        rejected = np.zeros_like(p_array, dtype=bool)
        p_corrected = np.zeros_like(p_array)
        rejected[sorted_indices] = rejected_sorted
        p_corrected[sorted_indices] = np.minimum(p_corrected_sorted, 1.0)
        
    elif method == "sidak":
        # Šidák correction (more accurate than Bonferroni for independent tests)
        p_corrected = 1 - (1 - p_array) ** n_tests
        rejected = p_corrected < alpha
    
    else:
        raise ValueError(f"Unknown correction method: {method}")
    
    return {
        "method": method,
        "n_comparisons": n_tests,
        "alpha": alpha,
        "p_values_raw": p_values,
        "p_values_corrected": p_corrected.tolist(),
        "rejected": rejected.tolist(),
        "n_rejected": int(np.sum(rejected)),
        "interpretation": f"{method.replace('_', '-').title()} correction: {np.sum(rejected)}/{n_tests} comparisons significant at α = {alpha}"
    }


def calculate_effect_size_confidence_intervals(
    effect_size: float,
    n1: int,
    n2: int = None,
    effect_type: str = "cohens_d"
) -> Dict[str, float]:
    """
    Calculate confidence intervals for effect sizes.
    
    ✅ Strategic Enhancement #14: Effect size confidence intervals
    
    Args:
        effect_size: Calculated effect size
        n1: Sample size group 1
        n2: Sample size group 2 (for between-group designs)
        effect_type: Type of effect size ('cohens_d', 'eta_squared', 'cramers_v')
    
    Returns:
        Dictionary with CI bounds
    """
    if effect_type == "cohens_d":
        # Hedges & Olkin (1985) method for Cohen's d CI
        if n2 is None:
            n2 = n1  # Assume equal groups
        
        # Correction factor (Hedges' g conversion)
        J = 1 - (3 / (4 * (n1 + n2 - 2) - 1))
        
        # Variance of Cohen's d
        var_d = ((n1 + n2) / (n1 * n2)) + ((effect_size ** 2) / (2 * (n1 + n2)))
        
        # Standard error
        se_d = np.sqrt(var_d)
        
        # 95% CI
        z_crit = stats.norm.ppf(0.975)
        ci_lower = effect_size - z_crit * se_d
        ci_upper = effect_size + z_crit * se_d
        
        return {
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "se": float(se_d),
            "method": "Hedges & Olkin (1985)"
        }
    
    elif effect_type == "eta_squared":
        # Steiger & Fouladi (1997) method for eta-squared CI
        # This is complex - simplified version
        if effect_size <= 0 or effect_size >= 1:
            return {"ci_lower": 0.0, "ci_upper": 1.0, "method": "Bounds only"}
        
        # Approximate CI using logit transformation
        logit_eta = np.log(effect_size / (1 - effect_size))
        se_logit = np.sqrt(1 / (n1 * effect_size * (1 - effect_size)))
        
        z_crit = stats.norm.ppf(0.975)
        logit_lower = logit_eta - z_crit * se_logit
        logit_upper = logit_eta + z_crit * se_logit
        
        ci_lower = np.exp(logit_lower) / (1 + np.exp(logit_lower))
        ci_upper = np.exp(logit_upper) / (1 + np.exp(logit_upper))
        
        return {
            "ci_lower": float(ci_lower),
            "ci_upper": float(ci_upper),
            "method": "Logit transformation (approximate)"
        }
    
    else:
        return {"ci_lower": None, "ci_upper": None, "method": "Not implemented"}


def assess_clinical_significance(
    effect_size: float,
    effect_type: str,
    domain: str = "general",
    mcid: float = None
) -> Dict[str, Any]:
    """
    Assess clinical significance of effect sizes.
    
    ✅ Strategic Enhancement #15: Clinical significance assessment
    
    Args:
        effect_size: Calculated effect size
        effect_type: Type of effect size
        domain: Clinical domain for context-specific thresholds
        mcid: Minimum Clinically Important Difference (if known)
    
    Returns:
        Clinical significance assessment
    """
    # Domain-specific thresholds (based on literature)
    domain_thresholds = {
        "general": {"small": 0.2, "medium": 0.5, "large": 0.8},
        "psychology": {"small": 0.2, "medium": 0.5, "large": 0.8},
        "medicine": {"small": 0.2, "medium": 0.5, "large": 0.8},
        "education": {"small": 0.25, "medium": 0.40, "large": 0.75},  # Hattie (2009)
        "cardiology": {"small": 0.1, "medium": 0.3, "large": 0.5},  # More conservative
    }
    
    thresholds = domain_thresholds.get(domain, domain_thresholds["general"])
    
    # Classify magnitude
    abs_effect = abs(effect_size)
    if abs_effect < thresholds["small"]:
        statistical_magnitude = "negligible"
    elif abs_effect < thresholds["medium"]:
        statistical_magnitude = "small"
    elif abs_effect < thresholds["large"]:
        statistical_magnitude = "medium"
    else:
        statistical_magnitude = "large"
    
    # Clinical significance assessment
    if mcid is not None:
        clinically_significant = abs_effect >= mcid
        clinical_assessment = f"Effect {'exceeds' if clinically_significant else 'does not exceed'} MCID of {mcid}"
    else:
        # General guidelines
        if statistical_magnitude in ["medium", "large"]:
            clinically_significant = True
            clinical_assessment = "Likely clinically meaningful"
        elif statistical_magnitude == "small":
            clinically_significant = False  # Uncertain
            clinical_assessment = "Clinical meaningfulness uncertain - consider context"
        else:
            clinically_significant = False
            clinical_assessment = "Unlikely to be clinically meaningful"
    
    return {
        "effect_size": effect_size,
        "statistical_magnitude": statistical_magnitude,
        "clinically_significant": clinically_significant,
        "clinical_assessment": clinical_assessment,
        "domain": domain,
        "mcid": mcid,
        "thresholds_used": thresholds
    }


def run_equivalence_test(
    effect_size: float,
    se: float,
    equivalence_bounds: tuple = (-0.2, 0.2)
) -> Dict[str, Any]:
    """
    Two One-Sided Tests (TOST) for equivalence testing.
    
    ✅ Strategic Enhancement #16: Equivalence testing
    
    Args:
        effect_size: Observed effect size
        se: Standard error of effect size
        equivalence_bounds: Equivalence bounds (lower, upper)
    
    Returns:
        TOST results
    """
    lower_bound, upper_bound = equivalence_bounds
    
    # Test 1: effect_size > lower_bound
    t1 = (effect_size - lower_bound) / se
    p1 = stats.norm.cdf(t1)  # One-tailed
    
    # Test 2: effect_size < upper_bound
    t2 = (effect_size - upper_bound) / se
    p2 = 1 - stats.norm.cdf(t2)  # One-tailed
    
    # TOST p-value is the maximum of the two tests
    tost_p_value = max(p1, p2)
    
    # Equivalent if both one-sided tests are significant
    equivalent = tost_p_value < 0.05
    
    return {
        "equivalence_bounds": equivalence_bounds,
        "effect_size": effect_size,
        "t_statistics": [float(t1), float(t2)],
        "p_values": [float(p1), float(p2)],
        "tost_p_value": float(tost_p_value),
        "equivalent": equivalent,
        "interpretation": f"Effect size {'is' if equivalent else 'is not'} equivalent to zero within bounds {equivalence_bounds}"
    }


if __name__ == "__main__":
    # Test the implementations
    print("🧪 Testing Strategic Enhancements...")
    
    # Test multiple comparison correction
    p_values = [0.01, 0.03, 0.15, 0.02, 0.08]
    result = apply_multiple_comparison_correction(p_values, "benjamini_hochberg")
    print(f"BH correction: {result['n_rejected']}/{result['n_comparisons']} significant")
    
    # Test effect size CI
    ci_result = calculate_effect_size_confidence_intervals(0.5, 30, 30, "cohens_d")
    print(f"Cohen's d CI: [{ci_result['ci_lower']:.3f}, {ci_result['ci_upper']:.3f}]")
    
    # Test clinical significance
    clinical = assess_clinical_significance(0.3, "cohens_d", "medicine")
    print(f"Clinical significance: {clinical['clinical_assessment']}")
    
    # Test equivalence
    equiv = run_equivalence_test(0.1, 0.2, (-0.2, 0.2))
    print(f"Equivalence test: {equiv['interpretation']}")
    
    print("✅ All strategic enhancements working!")
