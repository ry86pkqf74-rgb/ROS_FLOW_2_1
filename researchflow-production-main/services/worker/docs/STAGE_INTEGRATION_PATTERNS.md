# Stage Integration Patterns

This document outlines the patterns and best practices for data integration between workflow stages, with a focus on the Stage 1 → Stage 3 PICO elements integration pattern.

## Overview

The ResearchFlow workflow consists of 20 stages that process research data sequentially. Stages can access outputs from previous stages through:

1. **In-session integration**: `context.previous_results` (current job run)
2. **Cross-session integration**: `context.prior_stage_outputs` (from database/orchestrator)
3. **Cumulative data**: `context.cumulative_data` (aggregated project data)

## Stage 1 → Stage 3 PICO Integration

### Pattern: PICO Elements Flow

Stage 1 (Protocol Design Agent) generates PICO elements that Stage 3 (IRB Drafting Agent) uses for protocol generation.

```python
# Stage 1 Output Structure
{
    "pico_elements": {
        "population": "Adults aged 18-65 with diabetes",
        "intervention": "Continuous glucose monitoring",
        "comparator": "Standard glucose monitoring", 
        "outcomes": ["HbA1c reduction", "Quality of life scores"]
    },
    "primary_hypothesis": "CGM improves glycemic control...",
    "hypotheses": {
        "primary": "Primary hypothesis text",
        "secondary": ["Secondary hypothesis 1", "Secondary hypothesis 2"]
    }
}

# Stage 3 Integration Code
def _extract_hypothesis_from_stages(self, context: StageContext) -> Optional[str]:
    stage1_output = context.get_prior_stage_output(1) or {}
    
    # Primary hypothesis (preferred)
    if stage1_output.get("primary_hypothesis"):
        return stage1_output["primary_hypothesis"]
    
    # Fallback to hypotheses dict
    stage1_hypotheses = stage1_output.get("hypotheses", {})
    if stage1_hypotheses.get("primary"):
        return stage1_hypotheses["primary"]
    
    return None

def _extract_population_from_stages(self, context: StageContext) -> Optional[str]:
    stage1_output = context.get_prior_stage_output(1) or {}
    pico_elements = stage1_output.get("pico_elements", {})
    
    return pico_elements.get("population")

def _extract_variables_from_stage1(self) -> Optional[List[str]]:
    stage1_output = context.get_prior_stage_output(1) or {}
    pico_elements = stage1_output.get("pico_elements", {})
    outcomes = pico_elements.get("outcomes", [])
    
    if isinstance(outcomes, list) and len(outcomes) > 0:
        return outcomes
        
    return None
```

### Data Priority Hierarchy

1. **Explicit Configuration**: `context.config.get("irb")` 
2. **Root Configuration**: `context.config` direct fields
3. **Stage Integration**: Previous stage outputs via PICO elements
4. **Default Values**: Fallback defaults for required fields

```python
# Example priority hierarchy for population
population = (
    irb_config.get("population") or          # 1. IRB-specific config
    config.get("population") or              # 2. Root config
    self._extract_population_from_stages(context) or  # 3. Stage 1 PICO
    "Study participants"                     # 4. Default
)
```

## Governance Mode Integration

### DEMO Mode
- **Permissive**: Allows missing data with warnings
- **Defaults**: Fills missing fields with reasonable defaults
- **Logging**: Warns about applied defaults

```python
if missing_fields and context.governance_mode == "DEMO":
    warnings.append(f"Applied defaults for missing fields: {missing_fields}")
    # Apply defaults...
```

### LIVE Mode  
- **Strict**: Requires all mandatory fields
- **Validation**: Fails on missing/invalid data
- **Quality**: Enforces data quality standards

```python
elif missing_fields and context.governance_mode == "LIVE":
    raise IRBValidationError(
        message=f"Missing required fields: {missing_fields}",
        missing_fields=missing_fields,
        governance_mode=context.governance_mode
    )
```

## Cross-Session Data Flow

### Orchestrator Integration
For LIVE mode projects spanning multiple sessions:

```python
def get_prior_stage_output(self, stage_number: int) -> Optional[Dict[str, Any]]:
    # Check in-job results first
    if stage_number in self.previous_results:
        return self.previous_results[stage_number].output

    # Fall back to orchestrator-provided cumulative data  
    if stage_number in self.prior_stage_outputs:
        return self.prior_stage_outputs[stage_number].get("output_data", {})

    return None
```

### Cumulative Data Access
```python
# Access accumulated project data
research_domain = context.get_cumulative_value("research_domain")
total_completed = context.get_cumulative_value("total_stages_completed", 0)
```

## Data Validation Patterns

### Type Safety with Pydantic

```python
# Define validation schemas
class IRBProtocolRequest(BaseModel):
    study_title: str = Field(min_length=5, max_length=200)
    population: str = Field(min_length=5, max_length=500)
    variables: List[str] = Field(min_items=1)

# Validation with fallbacks
validation_result = validate_irb_config(
    config=context.config,
    previous_results=context.previous_results,
    governance_mode=context.governance_mode
)
```

### Error Handling Patterns

```python
try:
    irb_data = self._extract_irb_data(context)
except IRBValidationError as e:
    # Handle validation-specific errors
    logger.error(f"IRB validation failed: {e.message}")
    return self.create_stage_result(status="failed", errors=[e.message])
except ProcessingError as e:
    # Handle processing-specific errors  
    logger.error(f"Data processing failed: {e.message}")
    return self.create_stage_result(status="failed", errors=[e.message])
```

## Testing Integration Patterns

### Unit Tests for Stage Integration
```python
@pytest.fixture
def stage1_pico_output():
    return {
        "pico_elements": {
            "population": "Adults aged 18-65 with diabetes",
            "outcomes": ["HbA1c reduction", "Quality of life scores"]
        },
        "primary_hypothesis": "CGM improves glycemic control"
    }

def test_pico_elements_integration(self, context_with_stage1):
    agent = IRBDraftingAgent()
    # Test Stage 1 → Stage 3 data flow
    result = await agent.execute(context_with_stage1)
    # Verify PICO integration...
```

### Integration Tests Across Stages
```python
async def test_end_to_end_stage1_to_stage3():
    # Run Stage 1
    stage1_agent = DataIngestionAgent() 
    stage1_result = await stage1_agent.execute(stage1_context)
    
    # Pass Stage 1 output to Stage 3
    stage3_context.previous_results = {1: stage1_result}
    stage3_agent = IRBDraftingAgent()
    stage3_result = await stage3_agent.execute(stage3_context)
    
    # Verify data flow
    assert stage3_result.status == "completed"
```

## Best Practices

### 1. Defensive Data Access
Always check for data existence before access:
```python
stage1_output = context.get_prior_stage_output(1) or {}
pico_elements = stage1_output.get("pico_elements", {})
population = pico_elements.get("population")  # Safe access
```

### 2. Type Conversion and Validation
Handle different data types gracefully:
```python
# Convert string to list
if isinstance(variables_raw, str):
    variables = [v.strip() for v in variables_raw.split(",")]
elif isinstance(variables_raw, list):
    variables = variables_raw
else:
    variables = []
```

### 3. Meaningful Defaults
Provide context-appropriate defaults:
```python
# Context-aware defaults
if not irb_data.get("variables"):
    warnings.append("No variables specified, using PICO-derived defaults")
    irb_data["variables"] = ["Primary outcome", "Secondary outcomes"]
```

### 4. Comprehensive Logging
Log integration decisions for debugging:
```python
if stage1_hypothesis:
    logger.info(f"Using hypothesis from Stage 1: {stage1_hypothesis[:50]}...")
else:
    logger.warning("No hypothesis found in Stage 1, using config/default")
```

### 5. Graceful Degradation
Handle missing or malformed data gracefully:
```python
try:
    variables = pico_elements.get("outcomes", [])
    if not isinstance(variables, list):
        logger.warning(f"Invalid PICO outcomes type: {type(variables)}")
        variables = []
except Exception as e:
    logger.warning(f"Failed to extract PICO outcomes: {e}")
    variables = []
```

## Future Integration Patterns

### Stage 2 → Stage 3: Literature Context
```python
# Potential Stage 2 integration
def _extract_literature_context(self, context: StageContext):
    stage2_output = context.get_prior_stage_output(2) or {}
    return {
        "background_summary": stage2_output.get("background_summary"),
        "key_citations": stage2_output.get("key_citations", []),
        "research_gaps": stage2_output.get("research_gaps", [])
    }
```

### Stage 3 → Stage 6: Protocol to Analysis
```python
# IRB protocol informing analysis design
def _extract_irb_constraints(self, context: StageContext):
    stage3_output = context.get_prior_stage_output(3) or {}
    protocol = stage3_output.get("protocol", {})
    return {
        "approved_variables": protocol.get("variables", []),
        "risk_level": protocol.get("risk_level"),
        "analysis_constraints": protocol.get("analysis_constraints", [])
    }
```

## Common Integration Issues

### 1. Data Type Mismatches
- **Issue**: Stage 1 outputs list, Stage 3 expects string
- **Solution**: Type conversion with validation

### 2. Missing Optional Data
- **Issue**: Stage 1 incomplete but Stage 3 needs specific fields
- **Solution**: Graceful fallbacks with appropriate defaults

### 3. Governance Mode Conflicts
- **Issue**: DEMO mode allows incomplete data, LIVE mode requires complete data
- **Solution**: Mode-aware validation with different thresholds

### 4. Cross-Session Data Loss
- **Issue**: Stage 1 data not persisted between sessions
- **Solution**: Orchestrator cumulative data management

## Monitoring and Debugging

### Integration Metrics
- Track successful Stage 1 → Stage 3 integrations
- Monitor default application rates by governance mode
- Alert on high validation failure rates

### Debug Logging
```python
logger.debug(f"Stage integration summary: "
           f"Stage1_data={'present' if stage1_output else 'missing'}, "
           f"PICO_elements={len(pico_elements)}, "
           f"applied_defaults={applied_defaults}")
```

This pattern should be extended to other stage integrations as the workflow evolves.