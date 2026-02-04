"""Tests for AbstractGenerator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.generators.abstract_generator import (
    AbstractGenerator,
    AbstractInput,
    AbstractOutput,
    AbstractStyle,
    create_abstract_generator,
)


@pytest.fixture
def sample_input():
    return AbstractInput(
        research_question="Does exercise reduce HbA1c in Type 2 diabetes patients?",
        hypothesis="Regular exercise will reduce HbA1c by at least 0.5%",
        study_type="Randomized Controlled Trial",
        population="Adults 18-65 with Type 2 diabetes, HbA1c 7.0-10.0%",
        intervention="150 minutes moderate exercise per week for 12 weeks",
        comparator="Standard care without exercise intervention",
        primary_outcome="Change in HbA1c at 12 weeks",
        key_findings=[
            "Mean HbA1c reduction of 0.7% in intervention group",
            "No significant adverse events",
            "85% adherence rate",
        ],
        sample_size=200,
        methods_summary="Parallel-group RCT with 1:1 randomization, intention-to-treat analysis",
        keywords=["diabetes", "exercise", "HbA1c", "RCT"],
    )


class TestAbstractGenerator:
    def test_init_anthropic(self):
        gen = AbstractGenerator(model_provider="anthropic")
        assert gen.model_provider == "anthropic"
        assert gen.llm is not None

    def test_init_openai(self):
        gen = AbstractGenerator(model_provider="openai", model_name="gpt-4")
        assert gen.model_provider == "openai"

    def test_invalid_provider(self):
        with pytest.raises(ValueError):
            AbstractGenerator(model_provider="invalid")

    def test_word_limits(self):
        gen = AbstractGenerator()
        limits = gen._get_word_limits(AbstractStyle.STRUCTURED)
        assert limits == (200, 350)

    def test_custom_word_limits(self):
        gen = AbstractGenerator(word_limit=(100, 200))
        limits = gen._get_word_limits(AbstractStyle.STRUCTURED)
        assert limits == (100, 200)

    @pytest.mark.asyncio
    async def test_generate_structured(self, sample_input):
        with patch.object(AbstractGenerator, "_init_llm"):
            gen = AbstractGenerator()
            gen.llm = MagicMock()
            gen.llm.__or__ = MagicMock(
                return_value=MagicMock(
                    ainvoke=AsyncMock(
                        return_value=MagicMock(
                            content=(
                                "Background: Test background. "
                                "Methods: Test methods. "
                                "Results: Test results with 200 participants. "
                                "Conclusions: Test conclusions."
                            )
                        )
                    )
                )
            )

            result = await gen.generate(sample_input, AbstractStyle.STRUCTURED)

            assert isinstance(result, AbstractOutput)
            assert result.style == AbstractStyle.STRUCTURED
            assert result.word_count > 0
            assert result.transparency_log["model_provider"] == "anthropic"

    def test_quality_score_calculation(self, sample_input):
        gen = AbstractGenerator()
        abstract = (
            "This is a test abstract mentioning Change in HbA1c at 12 weeks "
            "and 200 participants."
        )
        score = gen._calculate_quality_score(abstract, sample_input)
        assert 0 <= score <= 100

    def test_factory_function(self):
        gen = create_abstract_generator(model_provider="anthropic")
        assert isinstance(gen, AbstractGenerator)
