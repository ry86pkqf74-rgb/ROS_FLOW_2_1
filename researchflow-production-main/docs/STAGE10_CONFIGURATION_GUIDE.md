# Stage 10 Configuration Guide

## Overview

Stage 10 supports two operational modes that can be selected via configuration. This guide covers all configuration options for both modes.

## Mode Selection

### Configuration Key
```python
config = {
    "stage_10_mode": "validation"  # or "gap_analysis"
}
```

- **"validation"** (default): Research validation checklist
- **"gap_analysis"**: Comprehensive AI-powered gap analysis

## Validation Mode Configuration

### Basic Configuration

```python
config = {
    "stage_10_mode": "validation",
    "validation": {
        "criteria": [
            {
                "id": "data_completeness",
                "name": "Data Completeness",
                "description": "Verify all required data fields are present",
                "category": "data_quality",
                "severity": "high"
            }
        ],
        "strict_mode": False,
        "fail_on_warning": False,
        "checklist_type": "CONSORT"
    }
}
```

### Configuration Options

#### `criteria` (List[Dict])
List of validation criteria to check.

**Criterion Structure:**
```python
{
    "id": str,              # Unique identifier
    "name": str,            # Human-readable name
    "description": str,     # What is being validated
    "category": str,        # Category: data_quality, methodology, documentation, reproducibility
    "severity": str         # Severity: critical, high, medium, low
}
```

**Default Criteria:**
- Data completeness
- Statistical validity
- Sample size adequacy
- Reproducibility
- Documentation completeness

#### `strict_mode` (bool, default: False)
If True, fails the stage when critical or high severity issues are found.

#### `fail_on_warning` (bool, default: False)
If True, fails the stage when any warnings are found.

#### `checklist_type` (str, default: "CONSORT")
Reporting guideline to check compliance against.
- `"CONSORT"`: Clinical trials
- `"STROBE"`: Observational studies
- `"PRISMA"`: Systematic reviews

### Output Structure

```json
{
  "validation_results": [
    {
      "criterion_id": "data_completeness",
      "criterion_name": "Data Completeness",
      "category": "data_quality",
      "severity": "high",
      "status": "passed",
      "message": "...",
      "details": {},
      "checked_at": "2024-01-01T00:00:00Z"
    }
  ],
  "checklist_status": {
    "items": [...],
    "total_criteria": 5,
    "checked_count": 5,
    "passed_count": 4,
    "failed_count": 1,
    "pending_count": 0,
    "completion_percentage": 100.0,
    "pass_rate": 80.0
  },
  "issues_found": {
    "critical": [],
    "high": [],
    "medium": [...],
    "low": [],
    "by_category": {}
  },
  "summary": {
    "total_criteria": 5,
    "checks_run": 5,
    "passed": 4,
    "failed": 1,
    "warnings": 0,
    "errors": 0,
    "skipped": 0,
    "critical_issues": 0,
    "high_issues": 0,
    "validation_passed": true
  }
}
```

## Gap Analysis Mode Configuration

### Basic Configuration

```python
config = {
    "stage_10_mode": "gap_analysis",
    "gap_analysis": {
        "enable_semantic_comparison": True,
        "gap_types": ["empirical", "methodological", "population", "temporal"],
        "min_literature_count": 10,
        "max_literature_papers": 50,
        "prioritization_method": "impact_feasibility_matrix",
        "generate_pico": True,
        "target_suggestions": 5,
        "quality_threshold": 0.80,
        "cache_embeddings": True,
        "max_iterations": 3,
        "timeout_seconds": 300
    },
    
    # Study context (required for gap analysis)
    "study_context": {
        "title": "Impact of Mindfulness on College Student Anxiety",
        "research_question": "Does MBSR reduce anxiety in college students?",
        "study_type": "Randomized Controlled Trial",
        "population": "College students aged 18-25 with moderate anxiety",
        "intervention": "8-week Mindfulness-Based Stress Reduction program",
        "outcome": "GAD-7 anxiety score reduction"
    }
}
```

### Configuration Options

#### `enable_semantic_comparison` (bool, default: True)
Use OpenAI embeddings for semantic similarity in literature comparison.
- **True**: More accurate, requires OPENAI_API_KEY
- **False**: Falls back to keyword matching

#### `gap_types` (List[str], default: all types)
Which gap dimensions to analyze:
- `"theoretical"`: Missing explanatory frameworks
- `"empirical"`: Lacking data or evidence
- `"methodological"`: Design limitations
- `"population"`: Underrepresented demographic groups
- `"temporal"`: Outdated evidence needing update
- `"geographic"`: Limited geographic settings

#### `min_literature_count` (int, default: 10)
Minimum number of papers required for gap analysis.

#### `max_literature_papers` (int, default: 50)
Maximum papers to analyze (for performance).

#### `prioritization_method` (str, default: "impact_feasibility_matrix")
Method for prioritizing gaps:
- `"impact_feasibility_matrix"`: 2x2 matrix (recommended)
- `"mcda"`: Multi-criteria decision analysis
- `"simple_scoring"`: Simple weighted sum

#### `generate_pico` (bool, default: True)
Generate PICO frameworks for research suggestions.

#### `target_suggestions` (int, default: 5)
Number of research suggestions to generate.

#### `quality_threshold` (float, default: 0.80)
Minimum quality score (0.0-1.0) for accepting results.

#### `cache_embeddings` (bool, default: True)
Cache literature embeddings to save API calls.

#### `max_iterations` (int, default: 3)
Maximum agent iterations for quality improvement.

#### `timeout_seconds` (int, default: 300)
Timeout for gap analysis execution.

### Study Context (Required)

```python
"study_context": {
    "title": str,                    # Required
    "research_question": str,        # Required
    "study_type": str,               # Optional: "RCT", "Cohort", "Meta-analysis", etc.
    "population": str,               # Optional but recommended
    "intervention": str,             # Optional (for intervention studies)
    "comparison": str,               # Optional
    "outcome": str,                  # Optional but recommended
    "setting": str,                  # Optional
    "timeframe": str                 # Optional
}
```

### Output Structure

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
      "gap": {
        "description": "...",
        "gap_type": "empirical",
        "evidence_level": "strong",
        "related_papers": [...],
        "impact_score": 4.5,
        "feasibility_score": 3.8
      },
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
      "target_population": "...",
      "expected_contribution": "...",
      "pico_framework": {
        "population": "...",
        "intervention": "...",
        "comparison": "...",
        "outcome": "..."
      },
      "impact_score": 4.2,
      "feasibility_score": 3.8,
      "priority_score": 8.0
    }
  ],
  "narrative": "...",
  "future_directions_section": "...",
  "summary": {
    "total_gaps_identified": 12,
    "high_priority_count": 3,
    "gap_diversity_score": 0.83,
    "literature_coverage": 0.92
  },
  "metadata": {
    "literature_count": 45,
    "findings_count": 8,
    "semantic_comparison_enabled": true,
    "anthropic_key_present": true,
    "openai_key_present": true
  }
}
```

## Environment Variables

### Required for Gap Analysis Mode

```bash
# Claude Sonnet 4 for planning and reasoning
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI for embeddings (if semantic comparison enabled)
OPENAI_API_KEY=sk-...
```

### Optional (Enhances Performance)

```bash
# Grok-2 for fast literature comparison
XAI_API_KEY=xai-...
XAI_BASE_URL=https://api.x.ai/v1

# Mercury for structured analysis
MERCURY_API_KEY=...
# OR
INCEPTION_API_KEY=...
MERCURY_BASE_URL=https://api.inceptionlabs.ai/v1
```

## Complete Examples

### Example 1: Validation Only (Fast)

```python
config = {
    "stage_10_mode": "validation",
    "validation": {
        "criteria": [
            {
                "id": "data_completeness",
                "name": "Data Completeness",
                "category": "data_quality",
                "severity": "high"
            },
            {
                "id": "statistical_validity",
                "name": "Statistical Validity",
                "category": "methodology",
                "severity": "high"
            }
        ],
        "strict_mode": True,
        "checklist_type": "CONSORT"
    }
}

result = await execute_workflow(
    job_id="validation-001",
    config=config,
    stage_ids=[10]
)
```

### Example 2: Gap Analysis with Minimal Config

```python
config = {
    "stage_10_mode": "gap_analysis",
    "study_context": {
        "title": "Mindfulness for Anxiety",
        "research_question": "Does MBSR reduce anxiety?"
    },
    "gap_analysis": {
        "target_suggestions": 3
    }
}

result = await execute_workflow(
    job_id="gap-001",
    config=config,
    stage_ids=[6, 7, 10]  # Needs literature and findings
)
```

### Example 3: Comprehensive Gap Analysis

```python
config = {
    "stage_10_mode": "gap_analysis",
    
    "study_context": {
        "title": "Impact of Mindfulness-Based Stress Reduction on Anxiety in College Students",
        "research_question": "Does an 8-week MBSR program reduce anxiety symptoms in college students?",
        "study_type": "Randomized Controlled Trial",
        "population": "College students aged 18-25 with moderate anxiety (GAD-7 > 10)",
        "intervention": "8-week Mindfulness-Based Stress Reduction program (2 hours/week)",
        "comparison": "Wait-list control group",
        "outcome": "GAD-7 anxiety score change from baseline to 8 weeks",
        "setting": "Large public university in northeastern United States",
        "timeframe": "September 2023 - May 2024"
    },
    
    "gap_analysis": {
        "enable_semantic_comparison": True,
        "gap_types": [
            "empirical",
            "methodological",
            "population",
            "temporal",
            "geographic"
        ],
        "min_literature_count": 15,
        "max_literature_papers": 40,
        "prioritization_method": "impact_feasibility_matrix",
        "generate_pico": True,
        "target_suggestions": 5,
        "quality_threshold": 0.85,
        "cache_embeddings": True,
        "max_iterations": 3,
        "timeout_seconds": 300
    }
}

result = await execute_workflow(
    job_id="comprehensive-gap-001",
    config=config,
    stage_ids=[1, 2, 6, 7, 10, 12],  # Full pipeline
    stop_on_failure=True
)

# Use in manuscript
gap_output = result["results"][10]["output"]
future_directions = gap_output["future_directions_section"]
high_priority_gaps = gap_output["prioritization_matrix"]["high_priority"]
```

### Example 4: Both Modes in Sequence

```python
# First run validation
validation_config = {
    "stage_10_mode": "validation",
    "validation": {
        "strict_mode": True,
        "checklist_type": "CONSORT"
    }
}

validation_result = await execute_workflow(
    job_id="dual-mode-001",
    config=validation_config,
    stage_ids=[10]
)

# If validation passes, run gap analysis
if validation_result["results"][10]["output"]["summary"]["validation_passed"]:
    gap_config = {
        "stage_10_mode": "gap_analysis",
        "study_context": {...},
        "gap_analysis": {...}
    }
    
    gap_result = await execute_workflow(
        job_id="dual-mode-001",
        config=gap_config,
        stage_ids=[6, 7, 10, 12]
    )
```

## Performance Tuning

### For Faster Execution

```python
"gap_analysis": {
    "enable_semantic_comparison": False,    # Use keyword matching
    "max_literature_papers": 20,            # Limit papers
    "target_suggestions": 3,                # Fewer suggestions
    "max_iterations": 1                     # Single pass
}
```

### For Higher Quality

```python
"gap_analysis": {
    "enable_semantic_comparison": True,     # Use embeddings
    "max_literature_papers": 50,            # More papers
    "target_suggestions": 5,                # More suggestions
    "quality_threshold": 0.85,              # Higher threshold
    "max_iterations": 5                     # More refinement
}
```

### For Cost Optimization

```python
"gap_analysis": {
    "cache_embeddings": True,               # Cache embeddings
    "max_literature_papers": 30,            # Balance size
    "max_iterations": 2                     # Limit iterations
}
```

## Artifacts Generated

### Validation Mode
- `validation_report.json`: Complete validation results

### Gap Analysis Mode
- `gap_analysis_report.json`: Complete gap analysis with all components

## Error Handling

### Common Errors

**ValidationError: Missing required fields**
```python
# Ensure study context has required fields
"study_context": {
    "title": "...",              # Required
    "research_question": "..."   # Required
}
```

**ImportError: GapAnalysisAgent not available**
```bash
# Install required packages
pip install langchain langchain-anthropic langchain-openai
```

**APIError: Missing ANTHROPIC_API_KEY**
```bash
# Set required API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

**ValueError: Insufficient literature**
```python
# Ensure Stage 6 ran and found papers
# Or reduce min_literature_count
"gap_analysis": {
    "min_literature_count": 5
}
```

## See Also

- [Integration Guide](STAGE10_INTEGRATION_GUIDE.md)
- [Gap Analysis Examples](../services/worker/agents/analysis/GAP_ANALYSIS_EXAMPLES.md)
- [Stage Implementation Status](STAGE_IMPLEMENTATION_STATUS.md)
