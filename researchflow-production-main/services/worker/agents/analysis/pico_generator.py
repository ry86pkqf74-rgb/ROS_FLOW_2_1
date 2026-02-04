"""
PICO Framework Generator

Tools for generating PICO-based research questions including:
- PICO extraction from text
- Research question formulation
- PubMed query generation
- Study design recommendation
- Sample size estimation guidance

Linear Issues: ROS-XXX (Stage 10 - Gap Analysis Agent)
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from .gap_analysis_types import PICOFramework, Gap, ResearchSuggestion

logger = logging.getLogger(__name__)


# =============================================================================
# PICO Generator
# =============================================================================

class PICOGenerator:
    """
    Generate PICO frameworks for research questions.
    
    PICO components:
    - P: Population/Patient/Problem
    - I: Intervention/Exposure
    - C: Comparison/Control
    - O: Outcome
    """
    
    # Study design recommendations based on research type
    STUDY_DESIGNS = {
        "efficacy": ["Randomized Controlled Trial", "Crossover Trial"],
        "effectiveness": ["Pragmatic Trial", "Cluster RCT"],
        "etiology": ["Cohort Study", "Case-Control Study"],
        "diagnosis": ["Cross-sectional Study", "Diagnostic Accuracy Study"],
        "prognosis": ["Cohort Study", "Registry Study"],
        "prevalence": ["Cross-sectional Study", "Survey"],
        "harm": ["Cohort Study", "Case-Control Study"]
    }
    
    def generate_from_gap(
        self,
        gap: Gap,
        study_context: Optional[Dict] = None
    ) -> PICOFramework:
        """
        Generate PICO framework from a research gap.
        
        Args:
            gap: Gap object
            study_context: Optional context from current study
        
        Returns:
            PICOFramework object
        """
        # Extract components from gap description
        population = self._extract_population(gap, study_context)
        intervention = self._extract_intervention(gap, study_context)
        comparison = self._extract_comparison(gap, study_context)
        outcome = self._extract_outcome(gap, study_context)
        
        # Recommend study design
        study_type = self._recommend_study_design(gap)
        
        return PICOFramework(
            population=population,
            intervention=intervention,
            comparison=comparison,
            outcome=outcome,
            study_type=study_type
        )
    
    def generate_research_question(
        self,
        pico: PICOFramework,
        question_style: str = "standard"
    ) -> str:
        """
        Generate natural language research question from PICO.
        
        Args:
            pico: PICOFramework object
            question_style: "standard", "causal", "descriptive"
        
        Returns:
            Formatted research question
        """
        if question_style == "causal":
            return self._causal_question(pico)
        elif question_style == "descriptive":
            return self._descriptive_question(pico)
        else:
            return pico.format_research_question()
    
    def _causal_question(self, pico: PICOFramework) -> str:
        """Generate causal research question."""
        return (
            f"Does {pico.intervention} cause {pico.outcome} "
            f"in {pico.population} compared to {pico.comparison}?"
        )
    
    def _descriptive_question(self, pico: PICOFramework) -> str:
        """Generate descriptive research question."""
        return (
            f"What is the prevalence of {pico.outcome} "
            f"in {pico.population} exposed to {pico.intervention}?"
        )
    
    def _extract_population(
        self,
        gap: Gap,
        context: Optional[Dict]
    ) -> str:
        """Extract or infer population from gap."""
        # Check gap description
        desc_lower = gap.description.lower()
        
        # Common population patterns
        pop_patterns = [
            r'(?:among|in)\s+([^\.,]+(?:patients|adults|children|participants))',
            r'([^\s]+\s+population)',
        ]
        
        for pattern in pop_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                return match.group(1).strip()
        
        # Use context if available
        if context:
            return context.get("population", "target population")
        
        # Default based on gap type
        if gap.gap_type.value == "population":
            return "underrepresented population groups"
        
        return "relevant patient population"
    
    def _extract_intervention(
        self,
        gap: Gap,
        context: Optional[Dict]
    ) -> str:
        """Extract or infer intervention from gap."""
        desc_lower = gap.description.lower()
        
        # Intervention keywords
        int_patterns = [
            r'(?:effect of|impact of|role of)\s+([^\.,]+)',
            r'(?:treatment|therapy|intervention)\s+(?:with|using)\s+([^\.,]+)',
        ]
        
        for pattern in int_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                return match.group(1).strip()
        
        # Context fallback
        if context:
            return context.get("intervention", "intervention of interest")
        
        # Default based on gap type
        if gap.gap_type.value == "methodological":
            return "improved methodological approach"
        
        return "intervention under investigation"
    
    def _extract_comparison(
        self,
        gap: Gap,
        context: Optional[Dict]
    ) -> str:
        """Extract or infer comparison/control from gap."""
        desc_lower = gap.description.lower()
        
        # Look for comparison keywords
        if "compared to" in desc_lower or "versus" in desc_lower:
            comp_match = re.search(r'(?:compared to|versus|vs\.?)\s+([^\.,]+)', desc_lower)
            if comp_match:
                return comp_match.group(1).strip()
        
        # Context fallback
        if context:
            return context.get("comparison", "standard care")
        
        return "standard care or placebo"
    
    def _extract_outcome(
        self,
        gap: Gap,
        context: Optional[Dict]
    ) -> str:
        """Extract or infer outcome from gap."""
        desc_lower = gap.description.lower()
        
        # Outcome patterns
        out_patterns = [
            r'(?:effect on|impact on|change in)\s+([^\.,]+)',
            r'(?:outcome|endpoint|measure)\s+(?:of|is)\s+([^\.,]+)',
        ]
        
        for pattern in out_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                return match.group(1).strip()
        
        # Context fallback
        if context:
            return context.get("outcome", "primary outcome")
        
        return "clinical outcome of interest"
    
    def _recommend_study_design(self, gap: Gap) -> str:
        """
        Recommend appropriate study design based on gap characteristics.
        
        Args:
            gap: Gap object
        
        Returns:
            Study design recommendation
        """
        # Determine research type from gap
        desc_lower = gap.description.lower()
        
        if any(kw in desc_lower for kw in ["efficacy", "effectiveness", "treatment", "intervention"]):
            if gap.addressability.value == "feasible":
                return "Randomized Controlled Trial"
            else:
                return "Pragmatic Trial or Cohort Study"
        
        elif any(kw in desc_lower for kw in ["cause", "etiology", "risk factor"]):
            return "Prospective Cohort Study"
        
        elif any(kw in desc_lower for kw in ["prevalence", "frequency", "rate"]):
            return "Cross-sectional Study"
        
        elif any(kw in desc_lower for kw in ["prognosis", "outcome", "survival"]):
            return "Cohort Study with long-term follow-up"
        
        elif gap.gap_type.value == "methodological":
            return "Methodological Study or Validation Study"
        
        else:
            # Default to flexible design
            return "Mixed-methods or Multi-phase Study"


# =============================================================================
# Research Question Validator
# =============================================================================

class ResearchQuestionValidator:
    """
    Validate research questions for clarity and answerability.
    """
    
    REQUIRED_ELEMENTS = ["population", "intervention", "outcome"]
    
    @classmethod
    def validate_pico(cls, pico: PICOFramework) -> Tuple[bool, List[str]]:
        """
        Validate PICO framework completeness.
        
        Args:
            pico: PICOFramework object
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for required elements
        if not pico.population or len(pico.population) < 5:
            issues.append("Population not clearly defined")
        
        if not pico.intervention or len(pico.intervention) < 5:
            issues.append("Intervention not clearly defined")
        
        if not pico.outcome or len(pico.outcome) < 5:
            issues.append("Outcome not clearly defined")
        
        # Comparison is optional but recommended
        if not pico.comparison:
            issues.append("Comparison group not specified (optional but recommended)")
        
        # Check for vague terms
        vague_terms = ["various", "some", "certain", "different", "multiple"]
        for term in vague_terms:
            if term in pico.population.lower():
                issues.append(f"Population description uses vague term: '{term}'")
        
        is_valid = len([i for i in issues if "optional" not in i]) == 0
        
        return is_valid, issues
    
    @classmethod
    def validate_research_question(cls, question: str) -> Tuple[bool, List[str]]:
        """
        Validate research question quality.
        
        Args:
            question: Research question string
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check length
        if len(question) < 20:
            issues.append("Question too short; may lack specificity")
        elif len(question) > 300:
            issues.append("Question too long; consider simplifying")
        
        # Check if it's actually a question
        if not question.strip().endswith("?"):
            issues.append("Should end with question mark")
        
        # Check for question words
        question_words = ["what", "how", "does", "is", "are", "can", "will"]
        if not any(word in question.lower() for word in question_words):
            issues.append("Should start with a question word")
        
        # Check for vague terms
        vague_terms = ["better", "improve", "worse", "affect"]
        for term in vague_terms:
            if term in question.lower() and "how" not in question.lower():
                issues.append(f"Vague term '{term}' without specific measurement")
        
        is_valid = len(issues) == 0
        
        return is_valid, issues


# =============================================================================
# Sample Size Guidance
# =============================================================================

class SampleSizeGuide:
    """
    Provide sample size estimation guidance.
    
    Note: This is educational guidance, not a calculator.
    Researchers should consult a statistician for formal power analysis.
    """
    
    # Rule-of-thumb sample sizes by study type
    SAMPLE_SIZE_RULES = {
        "pilot_study": "12-30 participants per group",
        "rct_small_effect": "250-400 per group (80% power, d=0.3)",
        "rct_medium_effect": "65-100 per group (80% power, d=0.5)",
        "rct_large_effect": "25-35 per group (80% power, d=0.8)",
        "cohort_rare_outcome": "500-1000+ participants",
        "cohort_common_outcome": "100-300 participants",
        "cross_sectional": "200-500 participants",
        "qualitative": "12-30 participants (thematic saturation)"
    }
    
    @classmethod
    def provide_guidance(
        cls,
        study_design: str,
        expected_effect_size: Optional[str] = "medium"
    ) -> str:
        """
        Provide sample size guidance.
        
        Args:
            study_design: Type of study
            expected_effect_size: "small", "medium", or "large"
        
        Returns:
            Guidance text
        """
        design_lower = study_design.lower()
        
        if "rct" in design_lower or "randomized" in design_lower:
            if expected_effect_size == "small":
                size = cls.SAMPLE_SIZE_RULES["rct_small_effect"]
            elif expected_effect_size == "large":
                size = cls.SAMPLE_SIZE_RULES["rct_large_effect"]
            else:
                size = cls.SAMPLE_SIZE_RULES["rct_medium_effect"]
            
            return f"Recommended sample size: {size}. Consult statistician for formal power analysis."
        
        elif "cohort" in design_lower:
            return (
                f"Recommended sample size depends on outcome prevalence. "
                f"For common outcomes: {cls.SAMPLE_SIZE_RULES['cohort_common_outcome']}. "
                f"For rare outcomes: {cls.SAMPLE_SIZE_RULES['cohort_rare_outcome']}."
            )
        
        elif "cross-sectional" in design_lower:
            return f"Recommended sample size: {cls.SAMPLE_SIZE_RULES['cross_sectional']}"
        
        elif "qualitative" in design_lower:
            return f"Recommended sample size: {cls.SAMPLE_SIZE_RULES['qualitative']}"
        
        elif "pilot" in design_lower:
            return f"Recommended sample size: {cls.SAMPLE_SIZE_RULES['pilot_study']}"
        
        else:
            return "Sample size depends on specific research question. Consult a statistician."
