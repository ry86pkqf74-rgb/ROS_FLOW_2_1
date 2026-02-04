"""Tests for ResultsGenerator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.generators.results_generator import (
    FigureReference,
    ResultType,
    ResultsGenerator,
    ResultsInput,
    ResultsOutput,
    StatisticalResult,
    StatFormatter,
    TableReference,
    create_results_generator,
)


class TestStatFormatter:
    def test_format_p_value_threshold(self):
        assert StatFormatter.format_p_value(0.0004) == "p < 0.001"

    def test_format_p_value_exact(self):
        assert StatFormatter.format_p_value(0.01234) == "p = 0.012"

    def test_format_ci(self):
        assert StatFormatter.format_ci(1.234, 5.678) == "95% CI [1.23, 5.68]"

    def test_format_effect_size_known(self):
        assert StatFormatter.format_effect_size(0.5, "cohens_d") == "d = 0.50"
        assert StatFormatter.format_effect_size(1.25, "or") == "OR = 1.25"

    def test_format_result_full(self):
        r = StatisticalResult(
            name="HbA1c change",
            result_type=ResultType.PRIMARY_OUTCOME,
            estimate=-0.55,
            ci_lower=-0.80,
            ci_upper=-0.30,
            p_value=0.0002,
            effect_size=0.62,
            effect_size_type="cohens_d",
            units="%",
        )
        s = StatFormatter.format_result(r)
        assert "-0.55 %" in s
        assert "95% CI" in s
        assert "p < 0.001" in s
        assert "d = 0.62" in s


@pytest.fixture
def results_input():
    return ResultsInput(
        study_type="randomized_controlled_trial",
        sample_size_analyzed=180,
        follow_up_completion=90.0,
        flow_data={
            "screened": 250,
            "excluded": 30,
            "randomized": 200,
            "intervention_allocated": 100,
            "control_allocated": 100,
            "analyzed_intervention": 90,
            "analyzed_control": 90,
        },
        primary_results=[
            StatisticalResult(
                name="Change in HbA1c at 12 weeks",
                result_type=ResultType.PRIMARY_OUTCOME,
                estimate=-0.55,
                ci_lower=-0.80,
                ci_upper=-0.30,
                p_value=0.0002,
                effect_size=0.62,
                effect_size_type="cohens_d",
                units="%",
                n_intervention=90,
                n_control=90,
            )
        ],
        secondary_results=[
            StatisticalResult(
                name="Change in BMI",
                result_type=ResultType.SECONDARY_OUTCOME,
                estimate=-1.2,
                ci_lower=-1.9,
                ci_upper=-0.5,
                p_value=0.002,
                units="kg/m^2",
            )
        ],
        adverse_events={"serious_adverse_events": 0, "any_adverse_event": 12},
        tables=[
            TableReference(
                table_number=1,
                title="Baseline characteristics",
                description="Baseline participant demographics and clinical measures",
            )
        ],
        figures=[
            FigureReference(
                figure_number=1,
                title="CONSORT flow diagram",
                description="Participant flow from screening to analysis",
                figure_type="flow_diagram",
            )
        ],
    )


class TestResultsGenerator:
    def test_init_default(self):
        gen = ResultsGenerator()
        assert gen.model_provider == "anthropic"

    def test_flow_diagram_text(self):
        gen = ResultsGenerator()
        text = gen._format_flow_diagram_text(
            {
                "screened": 100,
                "excluded": 10,
                "randomized": 90,
                "intervention_allocated": 45,
                "control_allocated": 45,
                "analyzed_intervention": 40,
                "analyzed_control": 42,
            }
        )
        assert "100 individuals were screened" in text
        assert "90 were randomized" in text
        assert "45 allocated to intervention" in text

    def test_extract_references(self):
        gen = ResultsGenerator()
        text = "Results are shown in Table 1 and Figure 2. See Table 1 for details."
        tables, figures = gen._extract_references(text)
        assert tables == ["Table 1"]
        assert figures == ["Figure 2"]

    def test_extract_statements(self):
        gen = ResultsGenerator()
        text = "The effect was significant, p = 0.012. The estimate was 95% CI [1.00, 2.00]."
        statements = gen._extract_statistical_statements(text)
        assert any("p = 0.012" in s for s in statements)
        assert any("95% CI" in s for s in statements)

    @pytest.mark.asyncio
    async def test_generate(self, results_input):
        with patch.object(ResultsGenerator, "_init_llm"):
            gen = ResultsGenerator()
            gen.llm = MagicMock()
            gen.llm.__or__ = MagicMock(
                return_value=MagicMock(
                    ainvoke=AsyncMock(
                        return_value=MagicMock(
                            content=(
                                "Participant Flow: As shown in Figure 1, 250 individuals were screened. "
                                "Primary Outcome: The primary outcome is summarized in Table 1 (p = 0.0002). "
                                "Secondary Outcome: BMI decreased (95% CI [1.00, 2.00])."
                            )
                        )
                    )
                )
            )

            result = await gen.generate(results_input)

            assert isinstance(result, ResultsOutput)
            assert result.word_count > 0
            assert "Table 1" in result.table_references
            assert "Figure 1" in result.figure_references
            assert len(result.statistical_statements) > 0

    def test_factory_function(self):
        gen = create_results_generator()
        assert isinstance(gen, ResultsGenerator)
