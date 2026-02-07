# IMRaD Generation Gating System for Claude Opus 4.6

## Quick Start

This directory contains the coordination rules for IMRaD (Introduction, Methods, Results, and Discussion) manuscript generation with quality gates.

## Documents

1. **01_dependency_graph.md** - Visual dependency tree and execution modes
2. **02_gate_definitions.md** - Detailed requirements for each gate (0-5)
3. **03_verification_protocol.md** - How the verification agent checks each gate
4. **04_pass_fail_rules.md** - Specific pass/fail logic and decision matrix

## Gate Summary

- **Gate 0: DATA_PREPARATION** - Validates input data before any generation
- **Gate 1: ABSTRACT** - Generates 200-400 word structured abstract
- **Gate 2: METHODS** - Generates 800-2000 word methods with CONSORT/STROBE compliance
- **Gate 3: RESULTS** - Generates 600-1500 word results with statistical statements
- **Gate 4: DISCUSSION** - Generates 800-2000 word discussion with literature synthesis
- **Gate 5: ASSEMBLY** - Combines all sections into complete manuscript

## Status Values

- **PASS** ✓ - All checks passed, gate opens
- **WARN** ⚠ - Non-critical issues, can proceed with caution
- **FAIL** ✗ - Critical issues, requires regeneration or escalation

## Execution Flow

```
Data Prep → Abstract + Methods (parallel) → Results → Discussion → Assembly
     ↓           ↓           ↓                 ↓          ↓          ↓
  Verify    Verify      Verify            Verify     Verify     Verify
     ↓           ↓           ↓                 ↓          ↓          ↓
  PASS/WARN   PASS/WARN   PASS/WARN        PASS/WARN  PASS/WARN  PASS/WARN
     ↓           ↓           ↓                 ↓          ↓          ↓
  Next Gate   Next Gate   Next Gate        Next Gate  Next Gate  Complete
```

## For Opus 4.6

When generating IMRaD manuscripts:
1. **Check Gate 0 first** - Validate all input data
2. **Run generators sequentially or in parallel** (Abstract+Methods can be parallel)
3. **After each section, invoke verification agent** with specific gate checks
4. **Block next gate if FAIL** - Retry up to 2 times with adjusted parameters
5. **Escalate to human if still FAIL** after retries
6. **Allow WARN to proceed** but log warnings in transparency bundle
7. **Final assembly only runs if all sections PASS or WARN**

## Key Metrics

| Section | Min Words | Max Words | Min Quality Score | Critical Checks |
|---------|-----------|-----------|-------------------|-----------------|
| Abstract | 200 | 400 | 70 | 4 sections, no hallucinations |
| Methods | 800 | 2000 | 70 | CONSORT/STROBE items |
| Results | 600 | 1500 | N/A | ≥3 statistical statements |
| Discussion | 800 | 2000 | 70 | Limitations + citations |

## Example Verification Call

```python
verifier = IMRaDVerificationAgent()

# After abstract generation
result = verifier.verify_gate("GATE_1_ABSTRACT", abstract_output, input_data)

if result["status"] == "FAIL":
    # Retry with adjusted parameters
    retry_with_adjustments(abstract_generator, result["errors"])
elif result["status"] == "WARN":
    # Log warnings but proceed
    log_warnings(result["warnings"])
    open_next_gate("GATE_2_METHODS")
else:  # PASS
    open_next_gate("GATE_2_METHODS")
```

