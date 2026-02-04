"""
PICO Framework - Shared utilities for Population, Intervention, Comparator, Outcome

This module provides shared PICO functionality across all agents, ensuring
consistency with the TypeScript frontend types.

PICO Framework:
- Population: Who is being studied?
- Intervention: What is being applied/tested?
- Comparator: What is it being compared to?
- Outcomes: What are we measuring?
- Timeframe: Study duration/follow-up
"""

import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class PICOElements(BaseModel):
    """
    PICO framework elements (matches TypeScript PICOElements interface).
    
    This matches the schema in:
    - packages/core/types/topic-declaration.ts
    - services/orchestrator/src/services/topic-converter.ts
    """
    population: str = Field(..., min_length=3, description="Target population description")
    intervention: str = Field(..., min_length=2, description="Intervention or exposure of interest")
    comparator: str = Field(..., min_length=2, description="Comparison group")
    outcomes: List[str] = Field(..., min_items=1, description="Primary and secondary outcomes")
    timeframe: str = Field(..., min_length=2, description="Study timeframe")
    
    @validator('outcomes')
    def validate_outcomes_not_empty(cls, v):
        """Ensure outcomes list has at least one non-empty item"""
        if not v or all(not outcome.strip() for outcome in v):
            raise ValueError("At least one outcome must be specified")
        return [outcome.strip() for outcome in v if outcome.strip()]
    
    class Config:
        json_schema_extra = {
            "example": {
                "population": "Adults with Type 2 diabetes aged 40-65",
                "intervention": "Structured exercise program (150 min/week)",
                "comparator": "Standard care without structured exercise",
                "outcomes": ["HbA1c reduction", "Weight loss", "Cardiovascular events"],
                "timeframe": "12 months follow-up"
            }
        }


class PICOValidator:
    """Validate and normalize PICO elements"""
    
    @staticmethod
    def validate(pico: PICOElements) -> Tuple[bool, List[str]]:
        """
        Validate PICO completeness and quality.
        
        Args:
            pico: PICOElements to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Population validation
        if not pico.population or len(pico.population.strip()) < 3:
            errors.append("Population must be specified (minimum 3 characters)")
        
        # Intervention validation
        if not pico.intervention or len(pico.intervention.strip()) < 2:
            errors.append("Intervention/Exposure must be specified")
        
        # Comparator validation
        if not pico.comparator or len(pico.comparator.strip()) < 2:
            errors.append("Comparator must be specified")
        
        # Outcomes validation
        if not pico.outcomes or len(pico.outcomes) == 0:
            errors.append("At least one outcome must be specified")
        elif any(len(o.strip()) < 2 for o in pico.outcomes):
            errors.append("All outcomes must have at least 2 characters")
        
        # Timeframe validation
        if not pico.timeframe or len(pico.timeframe.strip()) < 2:
            errors.append("Timeframe must be specified")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def to_search_query(pico: PICOElements, use_boolean: bool = True) -> str:
        """
        Convert PICO to search query string.
        
        Args:
            pico: PICOElements to convert
            use_boolean: Whether to use Boolean operators (AND/OR)
            
        Returns:
            Search query string suitable for PubMed/Semantic Scholar
        """
        if use_boolean:
            parts = [
                f"({pico.population})",
                f"AND ({pico.intervention})",
                f"AND ({pico.comparator})",
            ]
            
            if pico.outcomes:
                outcomes_query = " OR ".join(f"({o})" for o in pico.outcomes)
                parts.append(f"AND ({outcomes_query})")
            
            return " ".join(parts)
        else:
            # Simple concatenation for basic search
            parts = [pico.population, pico.intervention, pico.comparator]
            parts.extend(pico.outcomes)
            return " ".join(parts)
    
    @staticmethod
    def to_hypothesis(pico: PICOElements, style: str = "comparative") -> str:
        """
        Generate hypothesis template from PICO.
        
        Args:
            pico: PICOElements to convert
            style: Hypothesis style ("comparative", "null", "alternative")
            
        Returns:
            Hypothesis statement
        """
        primary_outcome = pico.outcomes[0] if pico.outcomes else "outcomes"
        
        if style == "null":
            return (
                f"In {pico.population}, {pico.intervention} compared to "
                f"{pico.comparator} will show no significant difference in "
                f"{primary_outcome} over {pico.timeframe}."
            )
        elif style == "alternative":
            return (
                f"In {pico.population}, {pico.intervention} compared to "
                f"{pico.comparator} will result in significant improvement in "
                f"{primary_outcome} over {pico.timeframe}."
            )
        else:  # comparative (default)
            outcomes_str = ", ".join(pico.outcomes) if len(pico.outcomes) > 1 else primary_outcome
            return (
                f"In {pico.population}, {pico.intervention} compared to "
                f"{pico.comparator} will affect {outcomes_str} over {pico.timeframe}."
            )
    
    @staticmethod
    def assess_quality(pico: PICOElements) -> Dict[str, Any]:
        """
        Assess PICO quality and provide recommendations.
        
        Returns:
            Dictionary with quality score and recommendations
        """
        score = 0.0
        recommendations = []
        
        # Population specificity (0-25 points)
        pop_words = pico.population.split()
        if len(pop_words) >= 5:
            score += 25
        elif len(pop_words) >= 3:
            score += 20
            recommendations.append("Population description could be more specific")
        else:
            score += 10
            recommendations.append("Population description is too vague")
        
        # Intervention clarity (0-25 points)
        if any(term in pico.intervention.lower() for term in ['dose', 'duration', 'frequency', 'protocol']):
            score += 25
        elif len(pico.intervention.split()) >= 3:
            score += 20
            recommendations.append("Intervention could include dosage/duration details")
        else:
            score += 10
            recommendations.append("Intervention needs more detail (dose, duration, protocol)")
        
        # Comparator appropriateness (0-20 points)
        if any(term in pico.comparator.lower() for term in ['placebo', 'standard care', 'control', 'usual care']):
            score += 20
        else:
            score += 10
            recommendations.append("Comparator should be more specific (e.g., 'placebo', 'standard care')")
        
        # Outcomes measurability (0-20 points)
        measurable_terms = ['reduction', 'increase', 'change', 'rate', 'score', 'level', 'count']
        outcomes_measurable = sum(
            1 for outcome in pico.outcomes
            if any(term in outcome.lower() for term in measurable_terms)
        )
        score += (outcomes_measurable / len(pico.outcomes)) * 20
        if outcomes_measurable < len(pico.outcomes):
            recommendations.append("Some outcomes should be more measurable/quantifiable")
        
        # Timeframe specificity (0-10 points)
        if any(unit in pico.timeframe.lower() for unit in ['week', 'month', 'year', 'day']):
            score += 10
        else:
            score += 5
            recommendations.append("Timeframe should include specific units (weeks, months, years)")
        
        quality_level = "excellent" if score >= 85 else "good" if score >= 70 else "fair" if score >= 50 else "poor"
        
        return {
            "score": round(score, 1),
            "quality_level": quality_level,
            "recommendations": recommendations,
            "strengths": PICOValidator._identify_strengths(pico),
        }
    
    @staticmethod
    def _identify_strengths(pico: PICOElements) -> List[str]:
        """Identify strengths in PICO formulation"""
        strengths = []
        
        if len(pico.population.split()) >= 5:
            strengths.append("Well-defined population")
        
        if len(pico.outcomes) >= 3:
            strengths.append("Multiple outcomes specified")
        
        if 'placebo' in pico.comparator.lower() or 'standard care' in pico.comparator.lower():
            strengths.append("Appropriate comparator")
        
        if any(unit in pico.timeframe.lower() for unit in ['month', 'year']):
            strengths.append("Clear timeframe")
        
        return strengths


class PICOExtractor:
    """Extract PICO elements from natural language using LLM"""
    
    @staticmethod
    async def extract_from_text(
        text: str,
        llm_bridge: Any,
        state: Any,
        model_tier: str = 'STANDARD',
    ) -> Optional[PICOElements]:
        """
        Use LLM to extract PICO elements from natural language.
        
        Args:
            text: Natural language research description
            llm_bridge: AI Router bridge for LLM calls
            state: Agent state for context
            model_tier: Model tier to use for extraction
            
        Returns:
            PICOElements if extraction successful, None otherwise
        """
        prompt = f"""Extract PICO elements from this research description:

{text}

Return ONLY valid JSON with these exact keys:
{{
  "population": "Who is being studied? Include age, condition, setting",
  "intervention": "What is being tested or observed? Include details",
  "comparator": "What is it compared to? (control, placebo, alternative)",
  "outcomes": ["What are the measured endpoints? List all"],
  "timeframe": "Study duration or follow-up period"
}}

Guidelines:
- Be specific: Include relevant demographics, conditions, settings
- Be measurable: Outcomes should be quantifiable
- Be realistic: Timeframe should match study type
- Use clinical terminology where appropriate

Example:
{{
  "population": "Adults aged 40-65 with Type 2 diabetes and HbA1c > 7.5%",
  "intervention": "Structured aerobic exercise program (150 minutes/week)",
  "comparator": "Standard diabetes care without structured exercise",
  "outcomes": ["HbA1c reduction", "Body weight change", "Cardiovascular events"],
  "timeframe": "12 months follow-up"
}}

Now extract PICO from the text above and return ONLY the JSON:"""
        
        try:
            response = await llm_bridge.invoke(
                prompt=prompt,
                task_type='pico_extraction',
                model_tier=model_tier,
                governance_mode=state.get('governance_mode', 'DEMO'),
                stage_id=1,
            )
            
            content = response.get('content', '{}')
            
            # Try to extract JSON from markdown code blocks if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            data = json.loads(content)
            
            # Validate required fields
            if not all(key in data for key in ['population', 'intervention', 'comparator', 'outcomes', 'timeframe']):
                logger.error("LLM response missing required PICO fields")
                return None
            
            # Ensure outcomes is a list
            if isinstance(data['outcomes'], str):
                data['outcomes'] = [o.strip() for o in data['outcomes'].split(',')]
            
            pico = PICOElements(**data)
            logger.info(f"Successfully extracted PICO: {pico.population[:50]}...")
            return pico
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PICO JSON: {e}")
            logger.debug(f"Raw LLM response: {content}")
            return None
        except Exception as e:
            logger.error(f"PICO extraction failed: {e}", exc_info=True)
            return None
    
    @staticmethod
    def extract_from_quick_entry(
        general_topic: str,
        scope: Optional[str] = None,
        timeframe: Optional[str] = None,
        exposures: Optional[List[str]] = None,
        outcomes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Convert Quick Entry fields to PICO-like structure (for LLM processing).
        
        This creates a structured representation that can be refined by LLM.
        
        Args:
            general_topic: General research topic
            scope: Research scope/constraints
            timeframe: Study timeframe
            exposures: Exposures/interventions (optional)
            outcomes: Desired outcomes (optional)
            
        Returns:
            Dictionary suitable for LLM-based PICO extraction
        """
        context = {
            "general_topic": general_topic,
            "scope": scope or "Not specified",
            "timeframe": timeframe or "Not specified",
        }
        
        if exposures:
            context["exposures"] = exposures
        if outcomes:
            context["outcomes"] = outcomes
        
        return context
