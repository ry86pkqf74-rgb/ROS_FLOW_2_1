"""
Unit tests for shared PICO module

Tests PICOElements, PICOValidator, and PICOExtractor functionality.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from typing import List

# Import the PICO classes
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "services" / "worker"))

from src.agents.common.pico import PICOElements, PICOValidator, PICOExtractor


class TestPICOElements:
    """Tests for PICOElements Pydantic model"""
    
    def test_valid_pico_creation(self):
        """Should create valid PICO elements"""
        pico = PICOElements(
            population="Adults aged 40-65 with Type 2 diabetes",
            intervention="Structured exercise program (150 min/week)",
            comparator="Standard care without exercise",
            outcomes=["HbA1c reduction", "Weight loss"],
            timeframe="12 months"
        )
        
        assert pico.population == "Adults aged 40-65 with Type 2 diabetes"
        assert len(pico.outcomes) == 2
        assert "HbA1c reduction" in pico.outcomes
    
    def test_invalid_pico_missing_fields(self):
        """Should raise error for missing required fields"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PICOElements(
                population="Adults",
                intervention="Exercise",
                # Missing comparator, outcomes, timeframe
            )
    
    def test_invalid_pico_short_population(self):
        """Should raise error for population < 3 chars"""
        with pytest.raises(Exception):
            PICOElements(
                population="AB",  # Too short
                intervention="Exercise",
                comparator="Control",
                outcomes=["Outcome1"],
                timeframe="6 months"
            )
    
    def test_pico_outcomes_validation(self):
        """Should validate outcomes list"""
        # Valid with multiple outcomes
        pico = PICOElements(
            population="Adults",
            intervention="Drug X",
            comparator="Placebo",
            outcomes=["Primary", "Secondary"],
            timeframe="1 year"
        )
        assert len(pico.outcomes) == 2
        
        # Should strip whitespace
        pico2 = PICOElements(
            population="Adults",
            intervention="Drug X",
            comparator="Placebo",
            outcomes=["  Primary  ", " Secondary "],
            timeframe="1 year"
        )
        assert pico2.outcomes == ["Primary", "Secondary"]


class TestPICOValidator:
    """Tests for PICOValidator utility class"""
    
    def test_validate_complete_pico(self):
        """Should validate complete PICO as valid"""
        pico = PICOElements(
            population="Adults aged 40-65 with Type 2 diabetes",
            intervention="Metformin 500mg twice daily",
            comparator="Placebo twice daily",
            outcomes=["HbA1c reduction", "Adverse events"],
            timeframe="24 weeks"
        )
        
        is_valid, errors = PICOValidator.validate(pico)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_incomplete_pico(self):
        """Should identify validation errors"""
        pico = PICOElements(
            population="AB",  # Too short but passes Pydantic min_length
            intervention="X",  # Too short
            comparator="Y",    # Too short
            outcomes=["A"],    # Too short
            timeframe="Z"      # Too short
        )
        
        is_valid, errors = PICOValidator.validate(pico)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_to_search_query_boolean(self):
        """Should generate Boolean search query"""
        pico = PICOElements(
            population="Adults with diabetes",
            intervention="Exercise program",
            comparator="Standard care",
            outcomes=["HbA1c", "Weight"],
            timeframe="12 months"
        )
        
        query = PICOValidator.to_search_query(pico, use_boolean=True)
        
        assert "(Adults with diabetes)" in query
        assert "AND (Exercise program)" in query
        assert "AND (Standard care)" in query
        assert "AND ((HbA1c) OR (Weight))" in query
    
    def test_to_search_query_simple(self):
        """Should generate simple concatenated query"""
        pico = PICOElements(
            population="Elderly patients",
            intervention="Drug A",
            comparator="Drug B",
            outcomes=["Survival"],
            timeframe="5 years"
        )
        
        query = PICOValidator.to_search_query(pico, use_boolean=False)
        
        assert "Elderly patients" in query
        assert "Drug A" in query
        assert "Drug B" in query
        assert "Survival" in query
    
    def test_to_hypothesis_comparative(self):
        """Should generate comparative hypothesis"""
        pico = PICOElements(
            population="Adults with hypertension",
            intervention="ACE inhibitor",
            comparator="Beta blocker",
            outcomes=["Blood pressure reduction"],
            timeframe="6 months"
        )
        
        hypothesis = PICOValidator.to_hypothesis(pico, style="comparative")
        
        assert "Adults with hypertension" in hypothesis
        assert "ACE inhibitor" in hypothesis
        assert "Beta blocker" in hypothesis
        assert "Blood pressure reduction" in hypothesis
        assert "6 months" in hypothesis
    
    def test_to_hypothesis_null(self):
        """Should generate null hypothesis"""
        pico = PICOElements(
            population="Cancer patients",
            intervention="Chemotherapy A",
            comparator="Chemotherapy B",
            outcomes=["Survival rate"],
            timeframe="2 years"
        )
        
        hypothesis = PICOValidator.to_hypothesis(pico, style="null")
        
        assert "no significant difference" in hypothesis
        assert "Survival rate" in hypothesis
    
    def test_to_hypothesis_alternative(self):
        """Should generate alternative hypothesis"""
        pico = PICOElements(
            population="Diabetic patients",
            intervention="New drug",
            comparator="Standard treatment",
            outcomes=["Glucose control"],
            timeframe="3 months"
        )
        
        hypothesis = PICOValidator.to_hypothesis(pico, style="alternative")
        
        assert "significant improvement" in hypothesis
        assert "Glucose control" in hypothesis
    
    def test_assess_quality_excellent(self):
        """Should assess high-quality PICO as excellent"""
        pico = PICOElements(
            population="Adults aged 40-65 with Type 2 diabetes mellitus and HbA1c > 7.5%",
            intervention="Structured aerobic exercise program (150 minutes per week, moderate intensity)",
            comparator="Standard diabetes care without structured exercise program",
            outcomes=["HbA1c reduction", "Body weight change", "Cardiovascular event rate"],
            timeframe="12 months follow-up"
        )
        
        quality = PICOValidator.assess_quality(pico)
        
        assert quality['score'] >= 70
        assert quality['quality_level'] in ['good', 'excellent']
        assert 'strengths' in quality
        assert len(quality['strengths']) > 0
    
    def test_assess_quality_poor(self):
        """Should assess low-quality PICO as poor"""
        pico = PICOElements(
            population="Patients",
            intervention="Treatment",
            comparator="Other",
            outcomes=["Results"],
            timeframe="Time"
        )
        
        quality = PICOValidator.assess_quality(pico)
        
        assert quality['score'] < 50
        assert quality['quality_level'] == 'poor'
        assert len(quality['recommendations']) > 0


class TestPICOExtractor:
    """Tests for PICOExtractor LLM-based extraction"""
    
    @pytest.mark.asyncio
    async def test_extract_from_text_success(self):
        """Should successfully extract PICO from text"""
        # Mock LLM bridge
        mock_bridge = AsyncMock()
        mock_bridge.invoke = AsyncMock(return_value={
            'content': json.dumps({
                'population': 'Adults with Type 2 diabetes',
                'intervention': 'Exercise program',
                'comparator': 'Standard care',
                'outcomes': ['HbA1c reduction', 'Weight loss'],
                'timeframe': '6 months'
            })
        })
        
        mock_state = {'governance_mode': 'DEMO'}
        
        text = "Study of exercise in diabetic adults over 6 months"
        
        pico = await PICOExtractor.extract_from_text(
            text=text,
            llm_bridge=mock_bridge,
            state=mock_state,
        )
        
        assert pico is not None
        assert isinstance(pico, PICOElements)
        assert 'diabetes' in pico.population.lower()
        assert len(pico.outcomes) == 2
    
    @pytest.mark.asyncio
    async def test_extract_from_text_with_markdown(self):
        """Should handle LLM response with markdown code blocks"""
        mock_bridge = AsyncMock()
        mock_bridge.invoke = AsyncMock(return_value={
            'content': '''```json
{
  "population": "Elderly patients",
  "intervention": "Drug A",
  "comparator": "Placebo",
  "outcomes": ["Survival"],
  "timeframe": "1 year"
}
```'''
        })
        
        mock_state = {'governance_mode': 'DEMO'}
        
        pico = await PICOExtractor.extract_from_text(
            text="Test study",
            llm_bridge=mock_bridge,
            state=mock_state,
        )
        
        assert pico is not None
        assert pico.population == "Elderly patients"
    
    @pytest.mark.asyncio
    async def test_extract_from_text_invalid_json(self):
        """Should handle invalid JSON from LLM"""
        mock_bridge = AsyncMock()
        mock_bridge.invoke = AsyncMock(return_value={
            'content': 'This is not JSON at all'
        })
        
        mock_state = {'governance_mode': 'DEMO'}
        
        pico = await PICOExtractor.extract_from_text(
            text="Test study",
            llm_bridge=mock_bridge,
            state=mock_state,
        )
        
        assert pico is None
    
    @pytest.mark.asyncio
    async def test_extract_from_text_missing_fields(self):
        """Should handle LLM response missing required fields"""
        mock_bridge = AsyncMock()
        mock_bridge.invoke = AsyncMock(return_value={
            'content': json.dumps({
                'population': 'Adults',
                'intervention': 'Treatment',
                # Missing comparator, outcomes, timeframe
            })
        })
        
        mock_state = {'governance_mode': 'DEMO'}
        
        pico = await PICOExtractor.extract_from_text(
            text="Test study",
            llm_bridge=mock_bridge,
            state=mock_state,
        )
        
        assert pico is None
    
    def test_extract_from_quick_entry(self):
        """Should structure Quick Entry fields for LLM"""
        context = PICOExtractor.extract_from_quick_entry(
            general_topic="Effects of exercise on diabetes",
            scope="Adult patients only",
            timeframe="12 months",
            exposures=["Aerobic exercise"],
            outcomes=["HbA1c", "Weight"]
        )
        
        assert context['general_topic'] == "Effects of exercise on diabetes"
        assert context['scope'] == "Adult patients only"
        assert context['timeframe'] == "12 months"
        assert 'exposures' in context
        assert 'outcomes' in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
