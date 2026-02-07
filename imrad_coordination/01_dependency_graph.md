# IMRaD Generation Dependency Graph

## Visual Dependency Tree

```
START
  │
  ├─► DATA_PREPARATION (Gate 0)
  │     ├─► Protocol Data Validated
  │     ├─► Statistical Results Available
  │     ├─► Literature References Indexed
  │     └─► Research Question Defined
  │
  ├─► ABSTRACT_GENERATION (Gate 1)
  │     ├─ Depends: DATA_PREPARATION ✓
  │     ├─ Produces: Abstract text
  │     ├─ Produces: Keywords list
  │     └─ Produces: Word count verification
  │
  ├─► METHODS_GENERATION (Gate 2)
  │     ├─ Depends: DATA_PREPARATION ✓
  │     ├─ Depends: ABSTRACT_GENERATION (optional)
  │     ├─ Produces: Methods text
  │     ├─ Produces: CONSORT/STROBE checklist
  │     └─ Produces: Compliance score
  │
  ├─► RESULTS_GENERATION (Gate 3)
  │     ├─ Depends: DATA_PREPARATION ✓
  │     ├─ Depends: METHODS_GENERATION ✓
  │     ├─ Produces: Results text
  │     ├─ Produces: Table/Figure references
  │     └─ Produces: Statistical statements
  │
  ├─► DISCUSSION_GENERATION (Gate 4)
  │     ├─ Depends: RESULTS_GENERATION ✓
  │     ├─ Depends: ABSTRACT_GENERATION ✓
  │     ├─ Depends: Literature context
  │     ├─ Produces: Discussion text
  │     ├─ Produces: Citation list
  │     └─ Produces: Completeness score
  │
  └─► FINAL_ASSEMBLY (Gate 5)
        ├─ Depends: All sections ✓
        ├─ Produces: Complete manuscript
        ├─ Produces: Bibliography
        ├─ Produces: Cross-references resolved
        └─ Produces: Validation report
```

## Execution Modes

### Mode 1: Sequential (Safe)
- Abstract → Methods → Results → Discussion → Assembly
- Each gate waits for previous completion + verification

### Mode 2: Parallel (Methods + Abstract)
- Abstract + Methods can run in parallel (both depend on DATA_PREPARATION only)
- Results waits for Methods
- Discussion waits for Results + Abstract

### Mode 3: Opportunistic
- Start all sections with available data
- Gate system prevents assembly until all verified
