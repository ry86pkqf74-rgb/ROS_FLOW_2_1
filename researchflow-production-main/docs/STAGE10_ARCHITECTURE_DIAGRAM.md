# Stage 10 Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ResearchFlow Pipeline                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Stage 10                                 │
│                    Dual-Mode Operation                           │
│                                                                  │
│  ┌─────────────────────┐       ┌──────────────────────────┐   │
│  │  Validation Mode    │       │   Gap Analysis Mode      │   │
│  │    (Default)        │       │      (Enhanced)          │   │
│  └─────────────────────┘       └──────────────────────────┘   │
│           │                              │                       │
│           │                              │                       │
│           ▼                              ▼                       │
│  ┌─────────────────────┐       ┌──────────────────────────┐   │
│  │ ValidationAgent     │       │ GapAnalysisStageAgent    │   │
│  │ (Existing)          │       │ (New Integration)        │   │
│  └─────────────────────┘       └──────────────────────────┘   │
│           │                              │                       │
│           │                              ▼                       │
│           │                     ┌──────────────────────────┐   │
│           │                     │  GapAnalysisAgent        │   │
│           │                     │  (Core Implementation)   │   │
│           │                     └──────────────────────────┘   │
└───────────┼──────────────────────────────┼───────────────────────┘
            │                              │
            ▼                              ▼
┌─────────────────────┐       ┌──────────────────────────┐
│ Output (Validation) │       │  Output (Gap Analysis)   │
│  - Checklist Status │       │  - Prioritized Gaps      │
│  - Issues Found     │       │  - Research Suggestions  │
│  - Compliance       │       │  - PICO Frameworks       │
└─────────────────────┘       │  - Narrative             │
                               │  - Future Directions     │
                               └──────────────────────────┘
```

## Mode Selection Flow

```
┌─────────────────────┐
│  Job Configuration  │
│  config = {...}     │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ stage_10_mode│
    │ specified?   │
    └──┬───────┬───┘
       │       │
   No  │       │  Yes
       │       │
       ▼       ▼
    "validation"  Read mode value
       │           │
       │           ├─────► "validation"
       │           │
       │           └─────► "gap_analysis"
       │
       ▼
┌────────────────────────────────────────────┐
│           Validation Mode                  │
│  ┌──────────────────────────────────────┐ │
│  │ ValidationAgent                       │ │
│  │  - Check criteria                    │ │
│  │  - Generate checklist                │ │
│  │  - Report issues                     │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
                                         
                                         
┌────────────────────────────────────────────┐
│         Gap Analysis Mode                  │
│  ┌──────────────────────────────────────┐ │
│  │ GapAnalysisStageAgent                │ │
│  │  1. Extract study context            │ │
│  │  2. Extract Stage 6 literature       │ │
│  │  3. Extract Stage 7 findings         │ │
│  │  4. Call GapAnalysisAgent            │ │
│  │  5. Format output                    │ │
│  │  6. Generate artifacts               │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

## Gap Analysis Mode - Data Flow

```
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│   Stage 6     │      │   Stage 7     │      │    Config     │
│  Literature   │      │  Statistical  │      │     Study     │
│    Search     │      │   Analysis    │      │   Context     │
└───────┬───────┘      └───────┬───────┘      └───────┬───────┘
        │                      │                      │
        │  List[Paper]         │  List[Finding]       │  StudyContext
        │                      │                      │
        └──────────────────────┴──────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ GapAnalysisAgent    │
                    │                     │
                    │ Multi-Model AI:     │
                    │  - Claude Sonnet 4  │
                    │  - Grok-2          │
                    │  - Mercury         │
                    │  - OpenAI (embed)  │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │Literature│   │   Gap    │   │  PICO    │
        │Comparison│   │Identifi- │   │Framework │
        │          │   │ cation   │   │Generator │
        └─────┬────┘   └─────┬────┘   └─────┬────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Prioritization  │
                    │     Matrix      │
                    │ (Impact vs      │
                    │  Feasibility)   │
                    └────────┬────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │   Gap Analysis Result  │
                │   - Gaps               │
                │   - Suggestions        │
                │   - Narrative          │
                │   - Future Directions  │
                └────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Stage 12     │
                    │   Manuscript    │
                    │   Generation    │
                    └─────────────────┘
```

## Integration Adapter Architecture

```
┌────────────────────────────────────────────────────────┐
│          GapAnalysisStageAgent                         │
│          (Workflow Engine Adapter)                     │
│                                                        │
│  Inherits from: BaseStageAgent                        │
│  Registers as: Stage 10 (gap_analysis mode)           │
│                                                        │
│  ┌──────────────────────────────────────────────────┐│
│  │  execute(context: StageContext) -> StageResult   ││
│  │                                                   ││
│  │  1. Validate configuration                       ││
│  │     - Check API keys                             ││
│  │     - Verify study context                       ││
│  │                                                   ││
│  │  2. Extract inputs                               ││
│  │     ├─► _extract_study_context()                 ││
│  │     ├─► _extract_literature() (from Stage 6)     ││
│  │     └─► _extract_findings() (from Stage 7)       ││
│  │                                                   ││
│  │  3. Execute gap analysis                         ││
│  │     └─► gap_agent.execute()                      ││
│  │                                                   ││
│  │  4. Format output                                ││
│  │     └─► _format_gap_analysis_result()            ││
│  │                                                   ││
│  │  5. Generate artifacts                           ││
│  │     └─► _generate_artifacts()                    ││
│  │                                                   ││
│  │  6. Return StageResult                           ││
│  └──────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────┘
                         │
                         │ Wraps
                         ▼
┌────────────────────────────────────────────────────────┐
│             GapAnalysisAgent                           │
│             (Core Implementation)                      │
│                                                        │
│  Inherits from: BaseAgent                             │
│  Implements: LangGraph workflow                       │
│                                                        │
│  ┌──────────────────────────────────────────────────┐│
│  │  LangGraph Workflow                               ││
│  │                                                   ││
│  │  Plan → Retrieve → Execute → Reflect → Quality   ││
│  │                                                   ││
│  │  Components:                                      ││
│  │  - LiteratureComparator                          ││
│  │  - GapCategorizer                                ││
│  │  - GapPrioritizer                                ││
│  │  - PICOGenerator                                 ││
│  └──────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────┘
```

## Configuration Schema

```
StageConfig
    │
    ├─► stage_10_mode: str
    │   ├─► "validation" (default)
    │   └─► "gap_analysis" (new)
    │
    ├─► validation: ValidationConfig
    │   ├─► criteria: List[Criterion]
    │   ├─► strict_mode: bool
    │   └─► checklist_type: str
    │
    └─► gap_analysis: GapAnalysisConfig
        ├─► enable_semantic_comparison: bool
        ├─► gap_types: List[str]
        ├─► min_literature_count: int
        ├─► max_literature_papers: int
        ├─► prioritization_method: str
        ├─► generate_pico: bool
        ├─► target_suggestions: int
        ├─► quality_threshold: float
        ├─► cache_embeddings: bool
        ├─► max_iterations: int
        └─► timeout_seconds: int
```

## Output Structure Comparison

```
┌──────────────────────┐         ┌──────────────────────┐
│  Validation Output   │         │  Gap Analysis Output │
├──────────────────────┤         ├──────────────────────┤
│ validation_results   │         │ comparisons          │
│ checklist_status     │         │ gaps                 │
│ issues_found         │         │ prioritized_gaps     │
│ summary              │         │ prioritization_matrix│
│                      │         │ research_suggestions │
│ Size: ~5 KB          │         │ narrative            │
│ Time: ~5s            │         │ future_directions    │
│ Cost: $0             │         │ summary              │
│                      │         │                      │
│                      │         │ Size: ~50 KB         │
│                      │         │ Time: ~60s           │
│                      │         │ Cost: ~$0.13         │
└──────────────────────┘         └──────────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────────┐
│                  Production Environment                 │
│                                                        │
│  ┌──────────────┐        ┌──────────────┐            │
│  │  Validation  │        │    Gap       │            │
│  │    Mode      │        │  Analysis    │            │
│  │              │        │    Mode      │            │
│  │  Always      │        │  Conditional │            │
│  │  Available   │        │  (if API keys│            │
│  │              │        │   present)   │            │
│  └──────────────┘        └──────────────┘            │
│                                                        │
│  Environment Variables:                               │
│  - ANTHROPIC_API_KEY (optional for validation)        │
│  - OPENAI_API_KEY (optional for validation)           │
│                                                        │
│  Dependencies:                                         │
│  - langchain (optional for gap analysis)              │
│  - langchain-anthropic (optional for gap analysis)    │
│  - langchain-openai (optional for gap analysis)       │
└────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Dual-Mode Architecture
- **Decision**: Two separate stage implementations
- **Rationale**: Clean separation, backward compatibility
- **Impact**: Zero breaking changes for existing users

### 2. Opt-In Gap Analysis
- **Decision**: Validation mode is default
- **Rationale**: Gradual adoption, lower barriers
- **Impact**: Users can adopt at their own pace

### 3. Configuration-Based Selection
- **Decision**: Mode selected via config, not code
- **Rationale**: Flexible, runtime switching
- **Impact**: Same stage ID, different behaviors

### 4. Stage Registry Registration
- **Decision**: Both modes register as Stage 10
- **Rationale**: Maintain workflow position
- **Impact**: No changes to orchestrator

### 5. Input Extraction Pattern
- **Decision**: Adapter extracts from prior stages
- **Rationale**: Decouple agent from workflow
- **Impact**: Clean interfaces, testable

## Benefits of This Architecture

1. **Backward Compatible**: Existing workflows unaffected
2. **Flexible**: Choose mode per job
3. **Maintainable**: Clean separation of concerns
4. **Testable**: Each component independently testable
5. **Extensible**: Easy to add new modes or features
6. **Production-Ready**: Comprehensive error handling

---

**Last Updated**: 2024-02-03  
**Version**: 1.0.0
