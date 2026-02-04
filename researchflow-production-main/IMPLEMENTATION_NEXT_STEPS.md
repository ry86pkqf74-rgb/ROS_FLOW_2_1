# PROTOCOL DESIGN AGENT - IMPLEMENTATION NEXT STEPS

## COMPLETED ✅

1. **Shared PICO Module** - `services/worker/src/agents/common/pico.py`
   - PICOElements (Pydantic model matching TypeScript)
   - PICOValidator (validation, query generation, hypothesis templates)
   - PICOExtractor (LLM-based extraction from natural language)
   
2. **Directory Structure**
   - `services/worker/src/agents/protocol_design/`
   - `services/worker/src/agents/common/`
   - `tests/unit/agents/protocol_design/`

## TO IMPLEMENT 📋

### Priority 1: Core Agent (20 hours)

**File**: `services/worker/src/agents/protocol_design/agent.py`

```python
class ProtocolDesignAgent(LangGraphBaseAgent):
    """Stage 1: Protocol Design with PICO framework"""
    
    stage_id = 1
    stage_name = "Protocol Design"
    stages = [1]
    agent_id = 'protocol_design'
    
    # Nodes to implement:
    async def detect_entry_mode_node(self, state) -> Dict
    async def convert_quick_to_pico_node(self, state) -> Dict
    async def validate_pico_node(self, state) -> Dict
    async def generate_hypothesis_node(self, state) -> Dict
    async def detect_study_type_node(self, state) -> Dict
    async def generate_protocol_outline_node(self, state) -> Dict
    async def improve_node(self, state) -> Dict
```

**Key Implementation Details**:
- Use `PICOExtractor.extract_from_text()` for Quick Entry conversion
- Use `PICOValidator.validate()` for validation
- Generate hypotheses using `PICOValidator.to_hypothesis()`
- Detect study type from keywords (RCT, cohort, case-control, observational)
- Generate protocol outline with LLM (7 sections minimum)

### Priority 2: Integration Updates (8 hours)

**Update Stage 2 Literature** - `stage_02_literature.py`:
```python
# In execute():
stage1_output = context.get_prior_stage_output(1)
if stage1_output and 'pico_elements' in stage1_output:
    from ..agents.common.pico import PICOElements, PICOValidator
    pico = PICOElements(**stage1_output['pico_elements'])
    search_query = PICOValidator.to_search_query(pico)
```

**Update Stage 3 IRB** - `stage_03_irb.py`:
```python
# In _extract_irb_data():
stage1_output = context.get_prior_stage_output(1)
if stage1_output and 'pico_elements' in stage1_output:
    from ..agents.common.pico import PICOElements, PICOValidator
    pico = PICOElements(**stage1_output['pico_elements'])
    hypothesis = stage1_output.get('hypothesis') or PICOValidator.to_hypothesis(pico)
```

### Priority 3: Comprehensive Tests (12 hours)

**Unit Tests** - `tests/unit/agents/protocol_design/test_agent.py`:
- test_quick_entry_conversion
- test_pico_validation_passes
- test_pico_validation_fails_incomplete
- test_hypothesis_generation
- test_study_type_detection_rct
- test_study_type_detection_cohort
- test_protocol_outline_generation
- test_quality_gate_passes
- test_quality_gate_fails
- test_improvement_loop
- test_demo_vs_live_mode
- test_phi_protection

**PICO Module Tests** - `tests/unit/agents/common/test_pico.py`:
- test_pico_elements_validation
- test_pico_validator_complete
- test_pico_validator_incomplete
- test_pico_to_search_query
- test_pico_to_hypothesis_styles
- test_pico_quality_assessment
- test_pico_extractor_success
- test_pico_extractor_invalid_json

**Integration Tests** - `tests/integration/test_pico_pipeline.py`:
- test_stage1_to_stage2_pico_flow
- test_stage1_to_stage3_pico_flow
- test_full_stage1_2_3_pipeline

### Priority 4: Documentation (5 hours)

**ADR Document** - `docs/ADR-001-stage-1-refactor.md`:
```markdown
# ADR-001: Stage 1 Protocol Design Agent

## Status: Proposed

## Context
Stage 1 implementation fragmented across file upload, data prep, and hypothesis agents.
Frontend expects PICO-based protocol design.

## Decision
Create dedicated ProtocolDesignAgent for Stage 1 with PICO framework.

## Consequences
- Clear separation of concerns
- PICO flows through all stages
- Better alignment with frontend
- Migration effort required
```

**Migration Guide** - `docs/migrations/stage-1-migration.md`
**Developer Docs** - Update `docs/DEVELOPER.md` with Stage 1 details

## IMPLEMENTATION ORDER

1. ✅ Create shared PICO module (DONE)
2. 📋 Implement ProtocolDesignAgent core
3. 📋 Write unit tests for agent
4. 📋 Update Stage 2 integration
5. 📋 Update Stage 3 integration
6. 📋 Write integration tests
7. 📋 Create documentation
8. 📋 Deploy behind feature flag

## TESTING CHECKLIST

Run these after implementation:
```bash
# Unit tests
pytest tests/unit/agents/protocol_design/test_agent.py -v
pytest tests/unit/agents/common/test_pico.py -v

# Integration tests
pytest tests/integration/test_pico_pipeline.py -v

# Full workflow test
pytest tests/integration/test_full_workflow_pipeline.py::test_stages_1_to_3 -v
```

## FEATURE FLAG

Add to environment:
```bash
ENABLE_NEW_STAGE_1=false  # Start disabled
```

Update stage registry:
```python
# services/worker/src/workflow_engine/registry.py
if os.getenv('ENABLE_NEW_STAGE_1', 'false').lower() == 'true':
    STAGE_REGISTRY[1] = ProtocolDesignAgent
else:
    STAGE_REGISTRY[1] = UploadIntakeStage  # Legacy
```

## SUCCESS CRITERIA

- [ ] All unit tests pass (30+ tests)
- [ ] All integration tests pass (10+ tests)
- [ ] PICO flows from Stage 1 → 2
- [ ] PICO flows from Stage 1 → 3
- [ ] Quality gate validates protocol
- [ ] Improvement loop works
- [ ] PHI protection verified
- [ ] Documentation complete

## ROLLBACK PLAN

If issues arise:
1. Set `ENABLE_NEW_STAGE_1=false`
2. Restart worker service
3. Old Stage 1 (upload) resumes
4. Fix issues and redeploy

---

**Current Status**: Foundation complete. Ready for agent implementation.
**Next Action**: Implement `ProtocolDesignAgent.build_graph()` and core nodes.
