import pytest

from services.worker.src.generators.imrad_assembler import IMRaDAssembler, IMRaDAssembleInput


@pytest.mark.asyncio
async def test_imrad_assembler_smoke():
    assembler = IMRaDAssembler()
    inp = IMRaDAssembleInput(
        title="Test Manuscript",
        data={
            "research_question": "Does X improve Y?",
            "hypothesis": "X improves Y.",
            "study_type": "cohort",
            "population": "Adults",
            "intervention": "X",
            "comparator": "Standard",
            "primary_outcome": "Y",
            "key_findings": ["Y improved by 10%"],
            "sample_size": 100,
            "methods_summary": "We ran a cohort study.",
            # methods
            "study_design": "Retrospective cohort",
            "setting": "Single center",
            "participants": {"inclusion": "Adults", "exclusion": "None", "recruitment": "EHR"},
            "outcomes": {"primary": ["Y"], "secondary": []},
            "statistical_plan": "Regression",
            "ethics_approval": "IRB exempt",
            # results
            "sample_size_analyzed": 100,
            "primary_results": [
                {
                    "name": "Primary outcome",
                    "result_type": "primary_outcome",
                    "estimate": 1.23,
                    "ci_lower": 1.01,
                    "ci_upper": 1.50,
                    "p_value": 0.03,
                    "effect_size": 0.2,
                    "effect_size_type": "cohens_d",
                }
            ],
            "tables": [{"table_number": 1, "title": "Baseline", "description": "Baseline characteristics"}],
            "figures": [{"figure_number": 1, "title": "Effect", "description": "Effect plot", "figure_type": "forest_plot"}],
            # discussion
            "key_findings_structured": [
                {
                    "finding": "X was associated with improved Y",
                    "statistical_support": "OR 1.23, p=0.03",
                    "clinical_significance": "Potentially meaningful",
                }
            ],
            "literature_context": [{"citation": "Smith 2020", "finding": "Similar", "agreement": "supports"}],
            "limitations": [{"category": "design", "description": "Observational", "impact": "moderate"}],
            "clinical_implications": ["Consider X"],
            "references": {
                "smith2020": {"title": "Study", "authors": ["Smith"], "year": 2020, "journal": "J"}
            },
        },
        journal_style="JAMA",
        citation_style="Vancouver",
        include_supplementary=True,
    )

    bundle = await assembler.assemble(inp)
    assert bundle.manuscript_id
    assert bundle.version >= 1
    assert "abstract" in bundle.sections
    assert "methods" in bundle.sections
    assert "results" in bundle.sections
    assert "discussion" in bundle.sections
    assert "references" in bundle.sections
