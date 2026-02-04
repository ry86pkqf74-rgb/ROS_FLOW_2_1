"""Tests for MethodsGenerator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.generators.methods_generator import (
    MethodsGenerator,
    MethodsInput,
    MethodsOutput,
    MethodsTemplate,
    StudyType,
    create_methods_generator,
)


@pytest.fixture
def rct_input():
    return MethodsInput(
        study_type=StudyType.RCT,
        study_design="Parallel-group randomized controlled trial",
        setting="Outpatient diabetes clinics in three academic medical centers",
        participants={
            "inclusion": ["Adults 18-65 years", "Type 2 diabetes", "HbA1c 7.0-10.0%"],
            "exclusion": ["Pregnancy", "Severe comorbidities", "Unable to exercise"],
            "recruitment": "Clinic referrals and advertisements",
        },
        intervention="Supervised moderate-intensity exercise, 150 min/week for 12 weeks",
        comparator="Standard care with general lifestyle advice",
        outcomes={
            "primary": ["Change in HbA1c at 12 weeks"],
            "secondary": ["Fasting glucose", "BMI", "Quality of life (SF-36)"],
        },
        sample_size=200,
        sample_size_justification="80% power to detect 0.5% HbA1c difference, alpha=0.05",
        randomization={
            "method": "Computer-generated random sequence",
            "allocation": "1:1 ratio, stratified by baseline HbA1c",
            "blinding": "Outcome assessors blinded; participants unblinded due to intervention nature",
        },
        statistical_plan="ITT analysis, mixed-effects models for repeated measures, significance p<0.05",
        ethics_approval="Approved by Institutional Review Board (IRB-2024-001)",
        registration="ClinicalTrials.gov NCT12345678",
        data_collection="Electronic data capture using REDCap",
        follow_up_period="12 weeks with assessments at baseline, 6 weeks, and 12 weeks",
        missing_data_handling="Multiple imputation for missing outcomes",
    )


class TestMethodsGenerator:
    def test_init_default(self):
        gen = MethodsGenerator()
        assert gen.model_provider == "anthropic"

    def test_template_selection_rct(self):
        gen = MethodsGenerator()
        template = gen._get_template(StudyType.RCT)
        assert template == MethodsTemplate.CONSORT

    def test_template_selection_cohort(self):
        gen = MethodsGenerator()
        template = gen._get_template(StudyType.COHORT)
        assert template == MethodsTemplate.STROBE

    def test_compliance_check_consort(self):
        gen = MethodsGenerator()
        text = """
        Study Design: This was a randomized controlled trial.
        Eligibility: Adults with diabetes were eligible.
        Intervention: Exercise program was provided.
        Outcomes: Primary outcome was HbA1c change.
        Sample Size: We calculated sample size based on power analysis.
        Randomization: Participants were randomly assigned.
        Blinding: Outcome assessors were blinded.
        Statistical Methods: We used mixed-effects models.
        """
        compliance = gen._check_compliance(text, MethodsTemplate.CONSORT)
        assert compliance["trial_design"] is True
        assert compliance["eligibility_criteria"] is True
        assert compliance["randomization_described"] is True

    def test_completeness_calculation(self):
        gen = MethodsGenerator()
        compliance = {"item1": True, "item2": True, "item3": False, "item4": True}
        score = gen._calculate_completeness(compliance)
        assert score == 75.0

    @pytest.mark.asyncio
    async def test_generate_rct(self, rct_input):
        with patch.object(MethodsGenerator, "_init_llm"):
            gen = MethodsGenerator()
            gen.llm = MagicMock()
            gen.llm.__or__ = MagicMock(
                return_value=MagicMock(
                    ainvoke=AsyncMock(
                        return_value=MagicMock(
                            content=(
                                "Study Design: Randomized trial. Participants: Adults with diabetes eligible. "
                                "Intervention: Exercise. Outcomes: HbA1c. Sample size: 200. "
                                "Randomization: Computer random. Blinding: Assessors blinded. "
                                "Statistical methods: Mixed models."
                            )
                        )
                    )
                )
            )

            result = await gen.generate(rct_input)

            assert isinstance(result, MethodsOutput)
            assert result.template == MethodsTemplate.CONSORT
            assert result.completeness_score > 0

    def test_factory_function(self):
        gen = create_methods_generator()
        assert isinstance(gen, MethodsGenerator)
