# Stage 10 Migration Guide

## Overview

This guide helps you migrate to or adopt the new **Stage 10 Gap Analysis Mode** while maintaining compatibility with existing **Validation Mode** workflows.

## Migration Paths

Choose the path that best fits your current setup:

1. **[Path A](#path-a-keep-validation-mode)**: Keep using validation mode only
2. **[Path B](#path-b-add-gap-analysis-gradually)**: Add gap analysis gradually alongside validation
3. **[Path C](#path-c-switch-to-gap-analysis)**: Switch entirely to gap analysis mode

---

## Path A: Keep Validation Mode

### When to Choose This Path
- You only need CONSORT/STROBE compliance checks
- You don't have literature search results
- You want fast execution (<10 seconds)
- You don't need AI-powered gap analysis

### Migration Steps

**✅ No changes required!**

The default Stage 10 mode is still validation. Your existing code will continue to work:

```python
# Your existing code - no changes needed
result = await execute_workflow(
    job_id="study-001",
    config={
        "validation": {
            "criteria": [...]
        }
    },
    stage_ids=[10]
)
```

### Optional: Make Mode Explicit

```python
# Explicitly specify validation mode (recommended for clarity)
config = {
    "stage_10_mode": "validation",  # Add this line
    "validation": {
        "criteria": [...]
    }
}
```

---

## Path B: Add Gap Analysis Gradually

### When to Choose This Path
- You want to try gap analysis without disrupting existing workflows
- You want to run both modes at different times
- You're testing gap analysis capabilities
- You have literature search (Stage 6) and statistical analysis (Stage 7) in place

### Migration Steps

#### Step 1: Install Dependencies (One-time)

```bash
# Gap analysis requires these packages
pip install langchain langchain-anthropic langchain-openai
```

#### Step 2: Set Up API Keys (One-time)

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Optional (enhances performance)
export XAI_API_KEY="xai-..."
export MERCURY_API_KEY="..."
```

#### Step 3: Create Two Configurations

**Config 1: Validation Mode (Existing)**
```python
validation_config = {
    "stage_10_mode": "validation",
    "validation": {
        "criteria": [...],
        "strict_mode": False
    }
}
```

**Config 2: Gap Analysis Mode (New)**
```python
gap_analysis_config = {
    "stage_10_mode": "gap_analysis",
    "study_context": {
        "title": "Your Study Title",
        "research_question": "Your Research Question",
        "population": "Your Population",
        "intervention": "Your Intervention",
        "outcome": "Your Outcome"
    },
    "gap_analysis": {
        "enable_semantic_comparison": True,
        "target_suggestions": 5,
        "min_literature_count": 10
    }
}
```

#### Step 4: Use Conditionally

```python
async def run_stage_10(job_id: str, mode: str = "validation"):
    """Run Stage 10 in specified mode."""
    
    if mode == "validation":
        config = validation_config
        stage_ids = [10]  # Just validation
    else:
        config = gap_analysis_config
        stage_ids = [6, 7, 10]  # Literature, stats, gap analysis
    
    result = await execute_workflow(
        job_id=job_id,
        config=config,
        stage_ids=stage_ids
    )
    
    return result

# Use validation for quick checks
validation_result = await run_stage_10("job-001", mode="validation")

# Use gap analysis for manuscript generation
gap_result = await run_stage_10("job-002", mode="gap_analysis")
```

#### Step 5: Test Gap Analysis

```python
# Start with a test job
test_config = {
    "stage_10_mode": "gap_analysis",
    "study_context": {
        "title": "Test Study",
        "research_question": "Test question?"
    },
    "gap_analysis": {
        "target_suggestions": 3,
        "min_literature_count": 5,  # Lower for testing
        "enable_semantic_comparison": False  # Faster for testing
    }
}

test_result = await execute_workflow(
    job_id="test-gap-001",
    config=test_config,
    stage_ids=[6, 7, 10],
    governance_mode="DEMO"
)

# Check if it worked
if test_result["results"][10]["status"] == "completed":
    print("✅ Gap analysis mode working!")
    print(f"Gaps found: {test_result['results'][10]['output']['summary']['total_gaps_identified']}")
else:
    print("❌ Gap analysis failed:")
    print(test_result["results"][10]["errors"])
```

#### Step 6: Integrate with Manuscript Generation

```python
# Run full pipeline with gap analysis
full_config = {
    "stage_10_mode": "gap_analysis",
    "study_context": {...},
    "gap_analysis": {...},
    "manuscript": {
        "include_future_directions": True  # Use gap analysis output
    }
}

result = await execute_workflow(
    job_id="manuscript-001",
    config=full_config,
    stage_ids=[1, 2, 6, 7, 10, 12],  # Through manuscript
    stop_on_failure=True
)

# Stage 12 will include Future Directions from Stage 10
manuscript = result["results"][12]["output"]["manuscript"]
future_directions = manuscript.get("future_directions_section", "")
```

---

## Path C: Switch to Gap Analysis

### When to Choose This Path
- You always run literature search and statistical analysis
- You need comprehensive gap identification
- You're generating manuscripts or grant proposals
- You want prioritized research suggestions

### Migration Steps

#### Step 1: Install Dependencies

```bash
pip install langchain langchain-anthropic langchain-openai
```

#### Step 2: Set Up API Keys

```bash
# Add to your .env or environment
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional
XAI_API_KEY=xai-...
MERCURY_API_KEY=...
```

#### Step 3: Update Configuration

**Before (Validation Only):**
```python
config = {
    "validation": {
        "criteria": [...]
    }
}
```

**After (Gap Analysis):**
```python
config = {
    "stage_10_mode": "gap_analysis",
    "study_context": {
        "title": "...",
        "research_question": "...",
        "study_type": "...",
        "population": "...",
        "intervention": "...",
        "outcome": "..."
    },
    "gap_analysis": {
        "enable_semantic_comparison": True,
        "gap_types": ["empirical", "methodological", "population", "temporal"],
        "target_suggestions": 5,
        "min_literature_count": 10
    }
}
```

#### Step 4: Update Workflow Stages

**Before:**
```python
stage_ids = [1, 2, 7, 10, 12]  # Skip literature search
```

**After:**
```python
stage_ids = [1, 2, 6, 7, 10, 12]  # Include Stage 6 (literature)
```

Gap analysis requires:
- **Stage 6**: Literature search (provides papers)
- **Stage 7**: Statistical analysis (provides findings)

#### Step 5: Update Output Handling

**Before:**
```python
# Access validation results
validation = result["results"][10]["output"]["validation_results"]
checklist = result["results"][10]["output"]["checklist_status"]
```

**After:**
```python
# Access gap analysis results
gaps = result["results"][10]["output"]["prioritized_gaps"]
suggestions = result["results"][10]["output"]["research_suggestions"]
narrative = result["results"][10]["output"]["narrative"]
future_directions = result["results"][10]["output"]["future_directions_section"]

# Use in downstream stages
high_priority = result["results"][10]["output"]["prioritization_matrix"]["high_priority"]
```

#### Step 6: Update Tests

**Before:**
```python
def test_stage_10():
    result = run_stage_10(config)
    assert "validation_results" in result.output
```

**After:**
```python
def test_stage_10():
    result = run_stage_10(gap_config)
    assert "prioritized_gaps" in result.output
    assert "research_suggestions" in result.output
    assert result.output["summary"]["total_gaps_identified"] > 0
```

---

## Hybrid Approach: Both Modes

### Use Case
Run validation first, then gap analysis if validation passes.

```python
async def run_stage_10_hybrid(job_id: str, config: dict):
    """Run validation first, then gap analysis if it passes."""
    
    # Step 1: Validation
    validation_config = {
        "stage_10_mode": "validation",
        "validation": config.get("validation", {})
    }
    
    validation_result = await execute_workflow(
        job_id=f"{job_id}-validation",
        config=validation_config,
        stage_ids=[10]
    )
    
    # Check if validation passed
    if not validation_result["results"][10]["output"]["summary"]["validation_passed"]:
        return {
            "status": "failed",
            "reason": "Validation failed",
            "validation_result": validation_result
        }
    
    # Step 2: Gap Analysis
    gap_config = {
        "stage_10_mode": "gap_analysis",
        "study_context": config["study_context"],
        "gap_analysis": config.get("gap_analysis", {})
    }
    
    gap_result = await execute_workflow(
        job_id=f"{job_id}-gaps",
        config=gap_config,
        stage_ids=[6, 7, 10]
    )
    
    return {
        "status": "completed",
        "validation_result": validation_result,
        "gap_analysis_result": gap_result
    }

# Usage
result = await run_stage_10_hybrid(
    "hybrid-001",
    config={
        "validation": {...},
        "study_context": {...},
        "gap_analysis": {...}
    }
)
```

---

## Configuration Comparison

| Feature | Validation Mode | Gap Analysis Mode |
|---------|----------------|-------------------|
| API Keys | None required | ANTHROPIC + OPENAI |
| Dependencies | Standard | langchain packages |
| Execution Time | ~5-10 seconds | ~30-120 seconds |
| Input Required | Any prior stage | Stage 6 + 7 results |
| Output | Checklist | Gaps + Suggestions |
| Use Case | Compliance | Research planning |

---

## Troubleshooting Migration

### Issue 1: "GapAnalysisAgent not available"

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install langchain langchain-anthropic langchain-openai
```

### Issue 2: "Missing ANTHROPIC_API_KEY"

**Cause:** API key not set

**Solution:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Or add to .env file
```

### Issue 3: "No literature found"

**Cause:** Stage 6 didn't run or returned no papers

**Solution:**
```python
# Ensure Stage 6 runs before Stage 10
stage_ids = [6, 7, 10]  # Not just [10]

# Or check Stage 6 config
config["literature"] = {
    "query": "your search terms",
    "databases": ["pubmed", "semantic_scholar"],
    "max_results": 50
}
```

### Issue 4: "Study context not found"

**Cause:** Missing study metadata

**Solution:**
```python
config["study_context"] = {
    "title": "Your Study Title",  # Required
    "research_question": "Your RQ",  # Required
    # Add other fields...
}
```

### Issue 5: Low quality scores

**Cause:** Insufficient or low-quality input data

**Solution:**
```python
# Improve input quality
config["gap_analysis"]["min_literature_count"] = 15
config["gap_analysis"]["max_iterations"] = 5

# Provide detailed study context
config["study_context"]["population"] = "Detailed population description"
config["study_context"]["intervention"] = "Specific intervention details"
```

---

## Rollback Plan

If you need to revert to validation-only mode:

```python
# Simple: Just set mode to validation
config["stage_10_mode"] = "validation"

# Or remove gap analysis config entirely
del config["gap_analysis"]
del config["study_context"]
```

Your validation workflows will continue to work as before.

---

## Migration Checklist

### Pre-Migration
- [ ] Review current Stage 10 usage
- [ ] Identify workflows that would benefit from gap analysis
- [ ] Check if Stage 6 (literature) and Stage 7 (stats) are available

### Migration
- [ ] Install dependencies (`pip install langchain...`)
- [ ] Set up API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- [ ] Test gap analysis in DEMO mode
- [ ] Update configuration for selected workflows
- [ ] Update output handling code
- [ ] Update tests

### Post-Migration
- [ ] Monitor API usage and costs
- [ ] Review gap analysis quality scores
- [ ] Collect feedback from users
- [ ] Optimize configuration based on results
- [ ] Document custom gap types or prioritization schemes

---

## Support Resources

- **Integration Guide**: [STAGE10_INTEGRATION_GUIDE.md](STAGE10_INTEGRATION_GUIDE.md)
- **Configuration Guide**: [STAGE10_CONFIGURATION_GUIDE.md](STAGE10_CONFIGURATION_GUIDE.md)
- **Examples**: [GAP_ANALYSIS_EXAMPLES.md](../services/worker/agents/analysis/GAP_ANALYSIS_EXAMPLES.md)
- **Tests**: [test_stage_10_integration.py](../services/worker/tests/test_stage_10_integration.py)

---

## Questions?

- **GitHub Issues**: Report issues or ask questions
- **Documentation**: Check the guides listed above
- **Email**: support@researchflow.ai

---

**Last Updated**: 2024  
**Version**: 1.0.0
