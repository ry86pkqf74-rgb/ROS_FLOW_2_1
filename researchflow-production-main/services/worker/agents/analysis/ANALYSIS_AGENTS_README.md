# ResearchFlow Analysis Agents - Complete Implementation

## Overview

The ResearchFlow analysis agents provide a comprehensive, LangGraph-powered workflow for systematic research analysis. This implementation covers Stages 6-12 of the research workflow with full PRISMA 2020 compliance.

### Agents Implemented

1. **LitSearchAgent** (Stage 6) - Automated literature search across PubMed, Semantic Scholar
2. **StatisticalAnalysisAgent** (Stage 7) - Comprehensive statistical analysis with assumption checking
3. **DataVisualizationAgent** (Stage 8) - Publication-quality figure generation
4. **MetaAnalysisAgent** (Stages 10-11) - Meta-analysis with heterogeneity & bias assessment
5. **PRISMAAgent** (Stage 12) - PRISMA 2020 compliant reporting
6. **AnalysisPipeline** - Orchestrates multi-stage workflows

---

## Architecture

### LangGraph Flow (All Agents)

```
┌─────────┐     ┌──────────┐     ┌─────────┐     ┌─────────┐
│  PLAN   │────>│ RETRIEVE │────>│ EXECUTE │────>│ REFLECT │
└─────────┘     └──────────┘     └─────────┘     └─────────┘
    │                                                   │
    │                                                   │
    └───────────────────< ITERATE (if needed) <────────┘
```

- **PLAN**: Claude Sonnet 4 analyzes task and creates execution strategy
- **RETRIEVE**: Fetch relevant guidelines from ChromaDB RAG
- **EXECUTE**: Perform analysis (statistical calculations, literature search, etc.)
- **REFLECT**: Quality check with iteration if quality threshold not met

---

## Quick Start

### 1. Literature Search

```python
from agents.analysis import create_lit_search_agent, StudyContext

agent = create_lit_search_agent()

context = StudyContext(
    title="Effect of Mindfulness on Anxiety",
    research_question="Does mindfulness reduce anxiety in adults?",
    keywords=["mindfulness", "anxiety", "meditation"],
    study_type="systematic_review",
    population="adults with anxiety disorders",
)

result = await agent.execute(context, max_results=50)

print(f"Found {len(result.papers)} papers")
for paper in result.papers[:5]:
    print(f"  - {paper.paper.title} (relevance: {paper.relevance_score:.2f})")
```

### 2. Statistical Analysis

```python
from agents.analysis import create_statistical_analysis_agent, StudyData
import pandas as pd

agent = create_statistical_analysis_agent()

data = StudyData(
    groups=["treatment", "control"],
    outcomes={"anxiety_score": [5.2, 7.8, 6.1, 8.9, 6.5, ...]},
    group_assignment=[0, 1, 0, 1, 0, ...],  # 0=treatment, 1=control
    metadata={"study_title": "Mindfulness RCT", "outcome_type": "continuous"},
)

result = await agent.execute(data)

print(f"Test: {result.inferential.test_name}")
print(f"p-value: {result.inferential.p_value:.4f}")
print(f"Effect size: {result.effect_sizes.cohens_d:.2f}")
print(result.inferential.format_apa())
```

### 3. Meta-Analysis

```python
from agents.analysis import create_meta_analysis_agent, StudyEffect, MetaAnalysisConfig

agent = create_meta_analysis_agent()

studies = [
    StudyEffect(
        study_id="study1",
        study_label="Smith 2020",
        effect_estimate=1.45,
        se=0.23,
        sample_size=100,
    ),
    StudyEffect(
        study_id="study2",
        study_label="Jones 2021",
        effect_estimate=1.89,
        se=0.31,
        sample_size=75,
    ),
    # ... more studies
]

config = MetaAnalysisConfig(
    effect_measure="OR",
    model_type="random_effects",
    test_publication_bias=True,
)

result = await agent.execute(studies, config)

print(result.format_result())
print(f"I² = {result.heterogeneity.i_squared:.1f}%")
print(f"Publication bias: {result.publication_bias.interpretation}")
```

### 4. PRISMA Report

```python
from agents.analysis import create_prisma_agent, PRISMAFlowchartData, SearchStrategy

agent = create_prisma_agent()

flowchart = PRISMAFlowchartData(
    records_identified_databases=1234,
    records_screened=890,
    reports_sought_retrieval=234,
    reports_assessed_eligibility=145,
    new_studies_included=42,
    total_studies_included=42,
    records_excluded=656,
    reports_excluded=103,
    exclusion_reasons={
        "Wrong population": 35,
        "No relevant outcome": 28,
        "Not RCT": 40,
    }
)

searches = [
    SearchStrategy(
        database="PubMed",
        search_date="2024-01-15",
        search_string='("mindfulness"[MeSH Terms]) AND "anxiety"[Title/Abstract]',
        results_count=567,
        filters_applied=["Humans", "English", "RCT"],
    ),
]

report = await agent.execute(
    flowchart_data=flowchart,
    search_strategies=searches,
    review_title="Mindfulness for Anxiety: A Systematic Review",
    authors=["Smith J", "Doe J"],
)

markdown = agent.generate_report_markdown(report)
html = agent.export_to_html(report)
```

### 5. Full Pipeline

```python
from agents.analysis import create_analysis_pipeline

pipeline = create_analysis_pipeline()

result = await pipeline.execute_full_workflow(
    research_id="anxiety_review_2024",
    study_context={
        "title": "Mindfulness for Anxiety",
        "authors": ["Smith J"],
        "keywords": ["mindfulness", "anxiety"],
    },
    statistical_data={
        "groups": ["treatment", "control"],
        "outcomes": {"anxiety": [...]},
    },
    meta_analysis_studies=[...],
    pipeline_config={
        "run_lit_search": True,
        "run_statistical_analysis": True,
        "run_meta_analysis": True,
        "run_prisma_report": True,
    }
)

print(f"Completed {len(result.stages_completed)} stages in {result.total_duration_ms}ms")
print(f"Generated {len(result.final_artifacts)} artifacts")
```

---

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
ORCHESTRATOR_URL=http://orchestrator:3001

# Optional
NCBI_API_KEY=...  # For PubMed searches
SEMANTIC_SCHOLAR_API_KEY=...  # For Semantic Scholar
OLLAMA_URL=http://localhost:11434  # For local models
```

### Agent Configuration

```python
from agents.base_agent import AgentConfig

config = AgentConfig(
    name="CustomAgent",
    description="Custom analysis agent",
    stages=[7],
    rag_collections=["statistical_methods"],
    max_iterations=3,  # Max retries if quality threshold not met
    quality_threshold=0.85,  # Quality score 0-1
    timeout_seconds=300,
    phi_safe=True,  # Enable PHI scanning
    model_provider="anthropic",  # anthropic, openai, local
    model_name="claude-sonnet-4-20250514",
)
```

---

## Quality Checks

### Statistical Analysis Quality Criteria

1. **Assumptions Checked** (30%) - Normality, homogeneity, independence
2. **Statistical Validity** (20%) - Complete test outputs (statistic, p-value, df)
3. **Effect Size** (20%) - Cohen's d, Hedges' g, or η²
4. **APA Formatting** (15%) - Proper statistical reporting
5. **Clinical Interpretation** (15%) - Meaningful interpretation

### Meta-Analysis Quality Criteria

1. **Heterogeneity Assessment** (30%) - I², τ², Q-test
2. **Publication Bias** (25%) - Egger's test, trim-and-fill
3. **Model Appropriateness** (20%) - Fixed vs. random effects
4. **Sensitivity Analysis** (15%) - Leave-one-out
5. **Interpretation** (10%) - Clinical context

### PRISMA Quality Criteria

1. **Flowchart Completeness** (25%) - All required fields
2. **Search Documentation** (25%) - ≥2 databases with full strategies
3. **Checklist Completion** (20%) - ≥85% of items reported
4. **Risk of Bias** (15%) - Systematic assessment
5. **Report Formatting** (15%) - Complete sections

---

## Testing

### Unit Tests

```bash
cd services/worker
pytest agents/analysis/tests/ -v
```

### Integration Tests

```bash
pytest agents/analysis/tests/test_pipeline_integration.py -v
```

### Example Test

```python
import pytest
from agents.analysis import create_meta_analysis_agent, StudyEffect, MetaAnalysisConfig

@pytest.mark.asyncio
async def test_meta_analysis_pooling():
    agent = create_meta_analysis_agent()
    
    studies = [
        StudyEffect(study_id="1", study_label="Study 1", effect_estimate=1.5, se=0.2),
        StudyEffect(study_id="2", study_label="Study 2", effect_estimate=1.8, se=0.3),
    ]
    
    config = MetaAnalysisConfig(effect_measure="OR")
    result = await agent.execute(studies, config)
    
    assert result.n_studies == 2
    assert result.pooled_effect > 0
    assert result.heterogeneity is not None
```

---

## Output Formats

### Statistical Analysis Result

```json
{
  "descriptive": [
    {"variable": "outcome", "group": "treatment", "n": 50, "mean": 5.2, "std": 1.1},
    {"variable": "outcome", "group": "control", "n": 48, "mean": 7.1, "std": 1.3}
  ],
  "inferential": {
    "test_name": "Independent t-test",
    "statistic": 2.34,
    "p_value": 0.023,
    "interpretation": "..."
  },
  "effect_sizes": {
    "cohens_d": 0.47,
    "magnitude": "medium"
  },
  "assumptions": {
    "normality": {"passed": true},
    "homogeneity": {"passed": true}
  }
}
```

### Meta-Analysis Result

```json
{
  "pooled_effect": 1.45,
  "ci_95": [1.12, 1.89],
  "p_value": 0.003,
  "heterogeneity": {
    "i_squared": 68.5,
    "tau_squared": 0.15,
    "interpretation": "Substantial heterogeneity"
  },
  "publication_bias": {
    "egger_p": 0.23,
    "interpretation": "No significant bias detected"
  },
  "forest_plot_data": {...},
  "funnel_plot_data": {...}
}
```

---

## References

### Statistical Methods
- Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences
- Field, A. (2018). Discovering Statistics Using IBM SPSS Statistics

### Meta-Analysis
- Borenstein, M. et al. (2009). Introduction to Meta-Analysis
- DerSimonian & Laird (1986). Meta-analysis in clinical trials

### PRISMA
- Page, M.J. et al. (2021). PRISMA 2020 Statement
- Cochrane Handbook for Systematic Reviews of Interventions v6.3

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'agents.base_agent'`
**Fix**: Ensure correct Python path: `sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))`

**Issue**: Quality check fails repeatedly
**Fix**: Review feedback in `QualityCheckResult.feedback` and adjust analysis parameters

**Issue**: RAG retrieval returns no results
**Fix**: Verify ChromaDB collections exist and orchestrator URL is correct

---

## Contributing

See `IMPLEMENTATION_PLAN.md` for architecture details and `COMPLETION_CHECKLIST.txt` for remaining work.

### Adding a New Agent

1. Extend `BaseAgent` class
2. Implement abstract methods: `_get_system_prompt`, `_get_planning_prompt`, `_get_execution_prompt`, `_parse_execution_result`, `_check_quality`
3. Add agent-specific methods for core functionality
4. Create type definitions in separate `*_types.py` file
5. Add factory function
6. Update `__init__.py` exports
7. Write tests

---

## License

MIT License - See LICENSE file for details

