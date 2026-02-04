"""Tests for DiscussionGenerator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.generators.discussion_generator import (
    DiscussionGenerator,
    DiscussionInput,
    DiscussionOutput,
    DiscussionStyle,
    KeyFinding,
    LiteratureReference,
    Limitation,
    create_discussion_generator,
)


@pytest.fixture
def discussion_input():
    return DiscussionInput(
        study_type="randomized_controlled_trial",
        research_question="Does supervised exercise improve glycemic control in adults with type 2 diabetes?",
        hypothesis="Supervised moderate-intensity exercise reduces HbA1c compared with standard care.",
        key_findings=[
            KeyFinding(
                finding="Supervised exercise reduced HbA1c at 12 weeks compared with standard care",
                statistical_support="Mean difference -0.55% (95% CI [-0.80, -0.30], p < 0.001)",
                clinical_significance="A ~0.5% HbA1c reduction is clinically meaningful for risk reduction",
                comparison_to_literature="Consistent with prior exercise trials reporting modest HbA1c improvements",
            )
        ],
        literature_context=[
            LiteratureReference(
                citation="Smith et al., 2021",
                finding="Exercise interventions reduce HbA1c by ~0.4–0.6% in type 2 diabetes",
                agreement="supports",
            ),
            LiteratureReference(
                citation="Jones et al., 2019",
                finding="No significant HbA1c improvement with low-adherence exercise programs",
                agreement="contradicts",
            ),
        ],
        limitations=[
            Limitation(
                category="generalizability",
                description="Participants were recruited from academic centers and may not represent community settings",
                impact="moderate",
                mitigation="Future trials in diverse community clinics",
            )
        ],
        clinical_implications=["Supervised exercise programs may be integrated into outpatient diabetes care"],
        policy_implications=["Coverage for structured exercise programs may improve access"],
        future_research=["Evaluate longer-term sustainability and outcomes beyond 12 weeks"],
        strengths=["Randomized design with blinded outcome assessors"],
        unexpected_findings=["No change in quality-of-life scores despite improved glycemic control"],
    )


class TestDiscussionGenerator:
    def test_init_default(self):
        gen = DiscussionGenerator()
        assert gen.model_provider == "anthropic"

    def test_format_literature_groups(self):
        gen = DiscussionGenerator()
        text = gen._format_literature(
            [
                LiteratureReference(
                    citation="A, 2020", finding="Supports", agreement="supports"
                ),
                LiteratureReference(
                    citation="B, 2021", finding="Contradicts", agreement="contradicts"
                ),
            ]
        )
        assert "Supporting studies" in text
        assert "Contradicting studies" in text

    def test_completeness_scoring(self, discussion_input):
        gen = DiscussionGenerator()
        text = (
            "Principal findings: main finding. Comparison with literature: prior work. "
            "Limitations: limitation. Clinical implications: implication. Future research: future. "
            "Conclusions: conclusion. Smith et al., 2021. "
            + ("word " * 520)
        )
        score = gen._calculate_completeness(text, discussion_input)
        assert score > 80

    @pytest.mark.asyncio
    async def test_generate(self, discussion_input):
        with patch.object(DiscussionGenerator, "_init_llm"):
            gen = DiscussionGenerator()
            gen.llm = MagicMock()
            gen.llm.__or__ = MagicMock(
                return_value=MagicMock(
                    ainvoke=AsyncMock(
                        return_value=MagicMock(
                            content=(
                                "Principal Findings: ... Smith et al., 2021. "
                                "Comparison with Literature: ... Limitations: ... "
                                "Clinical Implications: ... Future Research: ... Conclusions: ... "
                                + ("word " * 520)
                            )
                        )
                    )
                )
            )

            result = await gen.generate(discussion_input)

            assert isinstance(result, DiscussionOutput)
            assert result.word_count > 0
            assert result.completeness_score >= 0
            assert "Smith et al., 2021" in result.literature_citations_used

    def test_factory_function(self):
        gen = create_discussion_generator()
        assert isinstance(gen, DiscussionGenerator)
