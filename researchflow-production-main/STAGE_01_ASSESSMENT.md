# STAGE 01 PROTOCOL DESIGN AGENT - ASSESSMENT & IMPLEMENTATION PLAN

## EXECUTIVE SUMMARY

**CRITICAL FINDING**: No dedicated "ProtocolDesignAgent" exists. Stage 1 is fragmented across:
1. `stage_01_upload.py` - File validation only
2. `dataprep/agent.py` - Data extraction (Stages 1-5)
3. `stage_04_hypothesis.py` - PICO logic (misplaced)

**Frontend expects**: Stage 1 = Topic Declaration with PICO framework
**Backend provides**: Stage 1 = File upload validation

## ARCHITECTURE MISMATCH

Current confusion:
- Frontend: Stage01Hypothesis.tsx (hypothesis generation UI)
- Orchestrator: topic-converter.ts (PICO conversion)
- Worker Stage 1: File upload only
- Worker Stage 4: Has PICO logic but wrong stage number

## SOLUTION: NEW PROTOCOL DESIGN AGENT

### Implemented Components

✅ **Shared PICO Module** (`services/worker/src/agents/common/pico.py`)
- PICOElements (Pydantic model, matches TypeScript)
- PICOValidator (validation, search query generation)
- PICOExtractor (LLM-based extraction)

### To Be Implemented

📋 **ProtocolDesignAgent** (`services/worker/src/agents/protocol_design/agent.py`)

**Graph Structure**:
```
Entry → detect_entry_mode → [Quick Entry → convert_to_pico] OR [PICO → validate]
     → generate_hypothesis → detect_study_type → generate_protocol_outline
     → quality_gate → [human_review] → save_version → [improve loop] → END
```

**State Schema**:
```python
class ProtocolDesignState(AgentState):
    pico_elements: Optional[PICOElements]
    pico_valid: bool
    entry_mode: Literal['quick', 'pico']
    hypothesis: Optional[str]
    secondary_hypotheses: List[str]
    study_type: Optional[str]
    protocol_outline: Optional[Dict]
```

## INTEGRATION POINTS

### → Stage 2 (Literature)
PICO elements drive search query construction

### → Stage 3 (IRB)
PICO + hypothesis populate IRB protocol

### → Stage 6 (Data Upload)
Move file validation here (rename stage_01_upload.py)

## TESTING STRATEGY

**Unit Tests** (30+ tests needed):
- PICO extraction from Quick Entry
- PICO validation (complete/incomplete)
- Hypothesis generation
- Study type detection
- Protocol outline generation
- Quality gate evaluation
- Improvement loop

**Integration Tests** (10+ tests):
- Stage 1 → 2 (PICO → Literature)
- Stage 1 → 3 (PICO → IRB)
- Full Stage 1-3 pipeline

## QUALITY CRITERIA

Protocol Design Agent quality gate:
- `pico_valid`: True
- `hypothesis_present`: True
- `study_type_detected`: True
- `protocol_outline_complete`: True
- `min_secondary_hypotheses`: 2

## FILES CREATED

✅ `services/worker/src/agents/common/pico.py` - Shared PICO utilities
✅ `services/worker/src/agents/common/__init__.py` - Module exports
✅ `services/worker/src/agents/protocol_design/__init__.py` - Agent package

## FILES TO CREATE

📋 `services/worker/src/agents/protocol_design/agent.py` - Main LangGraph agent
📋 `tests/unit/agents/protocol_design/test_agent.py` - Comprehensive tests
📋 `tests/unit/agents/common/test_pico.py` - PICO module tests
📋 `tests/integration/test_pico_pipeline.py` - Stage 1→2→3 flow
📋 `docs/ADR-001-stage-1-refactor.md` - Architecture decision record

## NEXT STEPS

1. **Implement ProtocolDesignAgent** with full LangGraph structure
2. **Update Stage 2 & 3** to consume PICO from Stage 1
3. **Write comprehensive tests** (unit + integration)
4. **Update documentation** (ADR, migration guide)
5. **Deploy behind feature flag** for gradual rollout

## ESTIMATED EFFORT

- Core implementation: 20-25 hours
- Testing: 10-15 hours
- Documentation: 5-8 hours
- **Total: 35-48 hours**

## RISK MITIGATION

- Feature flag for gradual rollout
- Backward compatibility layer
- Comprehensive test coverage
- Clear rollback plan

## KEY BENEFITS

1. ✅ Aligns frontend/backend expectations
2. ✅ PICO flows through all stages
3. ✅ Clear separation of concerns
4. ✅ Improved testability
5. ✅ Better user experience

---

**Status**: Foundation laid with shared PICO module. Ready for ProtocolDesignAgent implementation.

**Contact**: See implementation details in this assessment document.
