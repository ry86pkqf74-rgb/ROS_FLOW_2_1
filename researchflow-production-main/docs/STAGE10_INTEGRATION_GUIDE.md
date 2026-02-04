# Stage 10: Dual-Mode Integration Guide

## Overview

Stage 10 now supports **two operational modes**:

1. **Validation Mode** (Default): Research validation checklist
2. **Gap Analysis Mode** (Enhanced): Comprehensive gap analysis with AI agents

## Architecture

```
Stage 10
├── Validation Mode (stage_10_validation.py)
│   ├── Research validation checklist
│   ├── CONSORT/STROBE compliance
│   ├── Statistical reporting verification
│   └── Bias risk assessment
│
└── Gap Analysis Mode (stage_10_gap_analysis.py)
    ├── Literature comparison
    ├── Multi-dimensional gap identification
    ├── PICO framework generation
    ├── Prioritization matrix (Impact vs Feasibility)
    └── Manuscript-ready narrative generation
```

## Configuration

### Enable Gap Analysis Mode

```python
# In job configuration
config = {
    "stage_10_mode": "gap_analysis",  # or "validation" (default)
    "gap_analysis": {
        "enable_semantic_comparison": True,
        "gap_types": ["empirical", "methodological", "population", "temporal"],
        "min_literature_count": 10,
        "prioritization_method": "impact_feasibility_matrix",
        "generate_pico": True,
        "target_suggestions": 5
    }
}
```

### Required API Keys (Gap Analysis Mode)

```bash
# Primary (Required)
ANTHROPIC_API_KEY=sk-ant-...          # Claude Sonnet 4
OPENAI_API_KEY=sk-...                 # Embeddings

# Optional (Enhances functionality)
XAI_API_KEY=xai-...                   # Grok-2 for fast comparison
MERCURY_API_KEY=...                   # Structured analysis
```

## Usage Examples

### Example 1: Validation Mode (Default)

```python
from workflow_engine import execute_workflow

result = await execute_workflow(
    job_id="study-001",
    config={
        "stage_10_mode": "validation",
        "validation": {
            "criteria": [
                {
                    "id": "data_completeness",
                    "name": "Data Completeness Check",
                    "category": "data_quality",
                    "severity": "high"
                }
            ],
            "strict_mode": False
        }
    },
    stage_ids=[10]
)

print(result["results"][10]["output"]["checklist_status"])
```

### Example 2: Gap Analysis Mode

```python
from workflow_engine import execute_workflow

result = await execute_workflow(
    job_id="study-001",
    config={
        "stage_10_mode": "gap_analysis",
        "gap_analysis": {
            "enable_semantic_comparison": True,
            "gap_types": ["empirical", "methodological", "population"],
            "target_suggestions": 5
        }
    },
    stage_ids=[6, 7, 10],  # Literature → Stats → Gap Analysis
    stop_on_failure=True
)

# Access gap analysis results
gap_result = result["results"][10]["output"]
print(f"Gaps identified: {gap_result['summary']['total_gaps']}")
print(f"High priority: {gap_result['summary']['high_priority_count']}")
print(f"\nNarrative:\n{gap_result['narrative']}")
```

### Example 3: Full Pipeline with Gap Analysis

```python
from workflow_engine import execute_workflow

# Run complete pipeline with gap analysis
result = await execute_workflow(
    job_id="mindfulness-rct-001",
    config={
        # Stage 6: Literature Search
        "literature": {
            "query": "mindfulness anxiety college students",
            "databases": ["pubmed", "semantic_scholar"],
            "max_results": 50
        },
        
        # Stage 7: Statistical Analysis
        "statistical_analysis": {
            "outcome_variable": "anxiety_score",
            "treatment_variable": "mbsr_group",
            "covariates": ["baseline_anxiety", "age", "gender"]
        },
        
        # Stage 10: Gap Analysis
        "stage_10_mode": "gap_analysis",
        "gap_analysis": {
            "enable_semantic_comparison": True,
            "gap_types": ["empirical", "methodological", "population", "temporal"],
            "prioritization_method": "impact_feasibility_matrix",
            "target_suggestions": 5
        },
        
        # Stage 12: Manuscript Generation
        "manuscript": {
            "include_future_directions": True,
            "style": "apa7"
        }
    },
    stage_ids=[1, 2, 6, 7, 10, 12],
    stop_on_failure=True
)

# Stage 12 manuscript will include Future Directions from Stage 10
manuscript = result["results"][12]["output"]["manuscript"]
print(manuscript["future_directions_section"])
```

## Output Structure

### Validation Mode Output

```json
{
  "validation_results": [...],
  "checklist_status": {
    "items": [...],
    "total_criteria": 5,
    "passed_count": 4,
    "failed_count": 1,
    "completion_percentage": 100.0,
    "pass_rate": 80.0
  },
  "issues_found": {
    "critical": [],
    "high": [],
    "medium": [...]
  },
  "summary": {
    "validation_passed": true
  }
}
```

### Gap Analysis Mode Output

```json
{
  "comparisons": {
    "consistent_with": [...],
    "contradicts": [...],
    "novel_findings": [...],
    "extends": [...],
    "overall_similarity_score": 0.73
  },
  "gaps": {
    "knowledge": [...],
    "methodological": [...],
    "population": [...],
    "temporal": [...],
    "geographic": [...]
  },
  "prioritized_gaps": [
    {
      "gap": {...},
      "priority_score": 8.5,
      "priority_level": "high",
      "rationale": "...",
      "expected_impact": "..."
    }
  ],
  "prioritization_matrix": {
    "high_priority": [...],
    "strategic": [...],
    "quick_wins": [...],
    "low_priority": [...]
  },
  "research_suggestions": [
    {
      "research_question": "...",
      "study_design": "RCT",
      "pico_framework": {...},
      "priority_score": 8.2
    }
  ],
  "narrative": "...",
  "future_directions_section": "...",
  "summary": {
    "total_gaps_identified": 12,
    "high_priority_count": 3,
    "gap_diversity_score": 0.83,
    "literature_coverage": 0.92
  }
}
```

## Integration Points

### Input Requirements

**Validation Mode:**
- Stage 1-9 results (any prior stage)
- Validation criteria configuration

**Gap Analysis Mode:**
- Stage 6 output: `literature` (List[Paper])
- Stage 7 output: `findings` (List[Finding])
- Study metadata: title, research_question, population, etc.

### Output Consumers

Both modes produce artifacts for:
- **Stage 11**: Iteration & refinement
- **Stage 12**: Manuscript generation (Discussion & Future Directions)
- **Stage 13**: Internal review
- **Research Database**: Systematic review protocols

## Performance Comparison

| Metric | Validation Mode | Gap Analysis Mode |
|--------|----------------|-------------------|
| Execution Time | ~5-10 seconds | ~30-120 seconds |
| API Calls | 2-3 (optional) | 10-15 |
| API Cost | ~$0.01 | ~$0.13 |
| Output Size | ~5 KB | ~50 KB |
| Literature Required | No | Yes (10+ papers) |
| AI Required | No | Yes |

## Migration Path

### Step 1: Test Validation Mode
```bash
# Ensure existing validation mode works
python -m pytest tests/test_stage_10_validation.py -v
```

### Step 2: Configure API Keys
```bash
# For gap analysis mode
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

### Step 3: Test Gap Analysis Mode
```bash
# Run gap analysis tests
cd services/worker/agents/analysis
pytest test_gap_analysis_agent.py -v
```

### Step 4: Update Orchestrator Config
```python
# Add to default configuration
DEFAULT_STAGE_10_CONFIG = {
    "mode": "validation",  # Start with validation
    "enable_gap_analysis": False  # Enable when ready
}
```

### Step 5: Gradual Rollout
1. **Week 1**: Validation mode only (existing behavior)
2. **Week 2**: Gap analysis in DEMO mode (test with sample data)
3. **Week 3**: Gap analysis in STANDBY mode (manual approval)
4. **Week 4**: Gap analysis in LIVE mode (production)

## Troubleshooting

### Issue: Gap analysis returns empty results
**Causes:**
- Insufficient literature (<10 papers)
- Missing API keys
- Invalid study metadata

**Solutions:**
```python
# Check literature count
if len(literature) < 10:
    logger.warning("Gap analysis requires 10+ papers")
    
# Verify API keys
assert os.getenv("ANTHROPIC_API_KEY"), "Missing ANTHROPIC_API_KEY"
assert os.getenv("OPENAI_API_KEY"), "Missing OPENAI_API_KEY"
```

### Issue: Semantic comparison fails
**Cause:** OpenAI API key not set

**Solution:**
```python
# Fallback to keyword-based comparison
config["gap_analysis"]["enable_semantic_comparison"] = False
```

### Issue: Low quality scores
**Causes:**
- Vague study description
- Low-quality literature
- Insufficient findings

**Solutions:**
```python
# Improve study metadata
study_context = {
    "title": "Specific, descriptive title",
    "research_question": "Clear, answerable question",
    "population": "Well-defined population",
    "intervention": "Specific intervention",
    "outcome": "Measurable outcome"
}

# Increase iterations
config["gap_analysis"]["max_iterations"] = 5
```

## Best Practices

### 1. Choose the Right Mode

**Use Validation Mode when:**
- You need CONSORT/STROBE compliance checks
- You're validating methodology
- You don't have literature search results
- You want fast execution (<10 seconds)

**Use Gap Analysis Mode when:**
- You have comprehensive literature (10+ papers)
- You need future research directions
- You're writing Discussion/Future Directions sections
- You want prioritized research suggestions
- You have statistical findings to compare

### 2. Optimize API Usage

```python
# Cache literature embeddings
config["gap_analysis"]["cache_embeddings"] = True

# Limit literature for faster processing
config["gap_analysis"]["max_literature_papers"] = 30

# Use faster models for comparison
config["gap_analysis"]["comparison_model"] = "grok-2"
```

### 3. Quality Assurance

```python
# Set quality thresholds
config["gap_analysis"]["quality_threshold"] = 0.80
config["gap_analysis"]["min_gaps_required"] = 5
config["gap_analysis"]["require_pico_framework"] = True
```

## API Reference

### Configuration Schema

```python
class Stage10Config(BaseModel):
    mode: Literal["validation", "gap_analysis"] = "validation"
    
    # Validation mode settings
    validation: Optional[ValidationConfig] = None
    
    # Gap analysis mode settings
    gap_analysis: Optional[GapAnalysisConfig] = None

class GapAnalysisConfig(BaseModel):
    enable_semantic_comparison: bool = True
    gap_types: List[str] = ["empirical", "methodological", "population"]
    min_literature_count: int = 10
    max_literature_papers: int = 50
    prioritization_method: str = "impact_feasibility_matrix"
    generate_pico: bool = True
    target_suggestions: int = 5
    quality_threshold: float = 0.80
    cache_embeddings: bool = True
    max_iterations: int = 3
    timeout_seconds: int = 300
```

## Support

- **Documentation**: `docs/gap_analysis/`
- **Examples**: `services/worker/agents/analysis/GAP_ANALYSIS_EXAMPLES.md`
- **Tests**: `services/worker/agents/analysis/test_gap_analysis_agent.py`
- **Issues**: GitHub Issues

## See Also

- [Stage 10 Gap Analysis Implementation](../services/worker/agents/analysis/STAGE10_GAP_ANALYSIS_COMPLETE.md)
- [Gap Analysis README](../services/worker/agents/analysis/GAP_ANALYSIS_README.md)
- [Gap Analysis Examples](../services/worker/agents/analysis/GAP_ANALYSIS_EXAMPLES.md)
- [PICO Framework Guide](../services/worker/agents/analysis/pico_generator.py)
- [Prioritization Algorithms](../services/worker/agents/analysis/gap_prioritization.py)

---

**Status**: Ready for Integration  
**Version**: 1.0.0  
**Last Updated**: 2024
