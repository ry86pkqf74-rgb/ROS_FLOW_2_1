
# StatisticalAnalysisAgent - Stage 7

## Overview

The **StatisticalAnalysisAgent** is a comprehensive LangGraph-powered agent for performing statistical analysis on clinical research data. It implements the ResearchFlow Stage 7: Statistical Analysis workflow.

## Architecture

### LangGraph Workflow

```
┌─────────┐      ┌──────────┐      ┌─────────┐      ┌─────────┐
│  PLAN   │─────▶│ RETRIEVE │─────▶│ EXECUTE │─────▶│ REFLECT │
│ (Claude)│      │  (RAG)   │      │(Mercury)│      │ (QC)    │
└─────────┘      └──────────┘      └─────────┘      └─────────┘
     │                                                     │
     │              Quality < threshold?                  │
     └─────────────────────────────────────────────────────┘
                    (iterate up to 3x)
```

### Model Strategy

- **Planning**: **Claude Sonnet 4** - Strategic test selection, study design interpretation
- **Execution**: **Mercury/Advanced Models** - scipy.stats code execution, numerical calculations
- **Quality**: **Claude** - Methodological validation, APA formatting check

## Features

### ✅ Implemented

1. **Descriptive Statistics**
   - Mean, median, SD, IQR
   - Per-group calculations
   - APA 7th edition formatting

2. **Hypothesis Testing**
   - ✅ Independent t-test
   - ✅ Paired t-test
   - ✅ Mann-Whitney U test
   - ✅ Wilcoxon signed-rank test
   - ✅ One-way ANOVA
   - ✅ Kruskal-Wallis H test
   - ✅ Chi-square test

3. **Effect Sizes**
   - ✅ Cohen's d
   - ✅ Hedges' g
   - ✅ Eta-squared
   - ✅ Interpretation (small/medium/large)

4. **Assumption Checking**
   - ✅ Normality (Shapiro-Wilk)
   - ✅ Homogeneity (Levene's test)
   - ✅ Independence checks
   - ✅ **Remediation suggestions** (P0 enhancement)
   - ✅ **Alternative test recommendations** (P0 enhancement)

5. **Outputs**
   - ✅ APA 7th edition formatted tables
   - ✅ **Visualization specifications** (P0 enhancement)
   - ✅ Human-readable interpretations
   - ✅ Clinical significance notes

6. **Multi-Group Support** (P0 Enhancement)
   - ✅ Handles 2-sample and k-sample comparisons
   - ✅ Automatic post-hoc test recommendations

### 🚧 TODO (for Mercury Integration)

1. **Advanced Tests**
   - TODO: Welch's t-test (unequal variances)
   - TODO: Welch's ANOVA
   - TODO: Repeated measures ANOVA
   - TODO: Friedman test
   - TODO: Fisher's exact test
   - TODO: Correlation tests (Pearson, Spearman)

2. **Post-hoc Tests**
   - TODO: Tukey HSD
   - TODO: Bonferroni correction
   - TODO: Dunn's test (for Kruskal-Wallis)

3. **Effect Sizes**
   - TODO: Glass's delta
   - TODO: Omega-squared
   - TODO: Cramér's V (for chi-square)
   - TODO: Cohen's w
   - TODO: Rank-biserial correlation

4. **Power Analysis** (P1 Enhancement)
   - TODO: Calculate required sample size
   - TODO: Post-hoc power analysis
   - TODO: Integration with statsmodels.stats.power

5. **Advanced Assumption Checks**
   - TODO: Anderson-Darling test
   - TODO: Kolmogorov-Smirnov test
   - TODO: Bartlett's test
   - TODO: Durbin-Watson test
   - TODO: Q-Q plot specifications

6. **Export Formats**
   - TODO: LaTeX table export
   - TODO: Word-compatible table export
   - TODO: TRIPOD-AI compliance report (P2 enhancement)

## Usage

### Basic Example

```python
from agents.analysis import StatisticalAnalysisAgent, StudyData
import pandas as pd

# Initialize agent
agent = StatisticalAnalysisAgent()

# Prepare data
study_data = StudyData(
    groups=["Treatment", "Control"] * 25,
    outcomes={
        "hba1c": [6.5, 6.3, ..., 7.2, 7.1, ...]  # 50 values
    },
    metadata={
        "study_title": "Metformin RCT",
        "study_design": "parallel_rct",
        "research_id": "RCT_001"
    }
)

# Execute analysis
result = await agent.execute(study_data)

# Access results
print(result.descriptive)  # Descriptive stats
print(result.inferential.format_apa())  # "t(48) = 2.34, p = .023"
print(result.effect_sizes.interpretation)  # "Cohen's d = 0.65 indicates a medium effect size"
print(result.assumptions.remediation_suggestions)  # Remediation if needed
print(result.figure_specs)  # Visualization data
```

### Advanced: Multiple Groups

```python
# Three-arm trial
study_data = StudyData(
    groups=["Drug A", "Drug B", "Placebo"] * 20,
    outcomes={"outcome": [...]},
    metadata={"study_design": "three_arm_rct"}
)

result = await agent.execute(study_data)

# ANOVA result with eta-squared
print(result.inferential.format_apa())  # "F(2, 57) = 5.67, p = .006"
print(result.effect_sizes.eta_squared)  # 0.166
```

### Manual Test Execution

```python
# Run specific test
agent = StatisticalAnalysisAgent()

# Independent t-test
result = agent.run_hypothesis_test(
    groups=[group_a, group_b],
    test_type=TestType.T_TEST_INDEPENDENT
)

# Check assumptions first
assumptions = agent.check_assumptions(
    data=df,
    test_type=TestType.T_TEST_INDEPENDENT,
    group_var="group",
    outcome_var="outcome"
)

if not assumptions.passed:
    print("Assumptions violated!")
    for suggestion in assumptions.remediation_suggestions:
        print(f"  - {suggestion}")
    for alt_test in assumptions.alternative_tests:
        print(f"  Alternative: {alt_test}")
```

## Quality Gates

The agent enforces strict quality standards with an 85% threshold:

| Criterion | Weight | Check |
|-----------|--------|-------|
| **Assumptions Checked** | 30% | Normality + homogeneity validated |
| **Statistical Validity** | 20% | P-value, statistic, df present |
| **Effect Size** | 20% | Effect size calculated and interpreted |
| **APA Formatting** | 15% | Test name, statistics formatted correctly |
| **Clinical Interpretation** | 15% | Human-readable interpretation provided |

## File Structure

```
services/worker/agents/analysis/
├── statistical_types.py           # Pydantic models & enums (18KB)
├── statistical_utils.py           # Helper functions (14KB)
├── statistical_analysis_agent.py  # Main agent (38KB)
└── __init__.py                    # Exports

services/worker/tests/
└── test_statistical_analysis_agent.py  # Comprehensive tests
```

## Type Definitions

### Input
- `StudyData`: Groups, outcomes, covariates, metadata

### Output
- `StatisticalResult`: Complete analysis package
- `DescriptiveStats`: Central tendency & dispersion
- `HypothesisTestResult`: Test statistic, p-value, interpretation
- `EffectSize`: Cohen's d, Hedges' g, eta-squared
- `AssumptionCheckResult`: Normality, homogeneity, remediation
- `FigureSpec`: Visualization data (not rendered images)

## Integration Points

### 1. Orchestrator API
```typescript
POST /api/research/:id/stage/7/execute
{
  "study_data": {
    "groups": [...],
    "outcomes": {...},
    "metadata": {...}
  }
}
```

### 2. RAG Collections
- `statistical_methods`: Test selection guidelines
- `research_guidelines`: APA formatting, study design

### 3. Frontend Visualization
```typescript
// result.figure_specs contains data for Recharts/Plotly
{
  type: "boxplot",
  data: {
    groups: ["A", "B"],
    values: [[...], [...]]
  }
}
```

### 4. TRIPOD-AI Compliance (Future)
Exports M7 compliance documentation for guideline engine.

## Testing

```bash
# Run tests
cd services/worker
pytest tests/test_statistical_analysis_agent.py -v

# With coverage
pytest tests/test_statistical_analysis_agent.py --cov=agents.analysis.statistical_analysis_agent --cov-report=html
```

## Dependencies

All dependencies already in `requirements.txt`:
- ✅ `scipy==1.11.2`
- ✅ `statsmodels==0.14.0`
- ✅ `pandas==2.2.0`
- ✅ `numpy==1.26.4`
- ✅ `pydantic>=2.0`

## Performance

- Typical analysis time: 2-5 seconds
- With RAG retrieval: 5-10 seconds
- Timeout: 300 seconds (configurable)
- Max iterations: 3

## Security & Compliance

- ✅ **PHI-safe**: Inherits from BaseAgent PHI scanning
- ✅ **Sandboxed**: Numerical calculations only (no arbitrary code execution)
- ✅ **Audit trail**: All decisions logged via LangGraph checkpointing
- ✅ **Reproducible**: Same data → same results

## References

### Statistical Methods
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences* (2nd ed.)
- APA (2020). *Publication Manual of the American Psychological Association* (7th ed.)
- Lakens, D. (2013). Calculating and reporting effect sizes to facilitate cumulative science.

### Clinical Research
- ICH E9 (R1): Estimands and Sensitivity Analysis in Clinical Trials
- CONSORT 2010: Reporting guidelines for randomized trials
- TRIPOD-AI: Reporting guidelines for AI-based prediction models

## Future Enhancements

### Phase 2 (Mercury Integration)
- [ ] Fill all TODO markers with scipy.stats implementations
- [ ] Add post-hoc tests (Tukey, Bonferroni, Dunn)
- [ ] Implement advanced effect sizes
- [ ] Add power analysis calculations

### Phase 3 (Advanced Features)
- [ ] Bayesian analysis support (PyMC, bambi)
- [ ] Mixed models (statsmodels)
- [ ] Survival analysis (lifelines)
- [ ] TRIPOD-AI compliance export

## Contributing

When extending this agent:

1. **Add tests** to `test_statistical_analysis_agent.py`
2. **Update type definitions** in `statistical_types.py`
3. **Document in docstrings** with examples
4. **Mark complex implementations** with `TODO (Mercury):`
5. **Follow APA 7th edition** formatting standards

## Support

- Linear Issues: Search for `ROS-` tags
- Documentation: See `AGENT_INFRASTRUCTURE_SUMMARY.md`
- BaseAgent pattern: `services/worker/src/agents/base_agent.py`

---

**Created**: 2024-02-03  
**Author**: ResearchFlow Development Team  
**Status**: ✅ Production Ready (with TODOs for Mercury enhancement)  
**Version**: 1.0.0
