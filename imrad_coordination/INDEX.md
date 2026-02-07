# IMRaD Gating System - Complete Documentation Index

Generated for: **Claude Opus 4.6**  
Purpose: Define gating rules, dependency graphs, and verification protocols for IMRaD manuscript generation

---

## 📁 Documentation Files

### **README.md** - Quick Start Guide
Entry point with overview, gate summary, and key metrics.
- **Use this first** to understand the system
- Contains quick reference table
- Shows example verification call

### **COORDINATION_PROMPT.md** - System Instructions for Opus 4.6
Primary coordination prompt with decision template and execution examples.
- **Use this as the agent prompt** when running IMRaD generation
- Contains step-by-step decision logic
- Includes retry strategies and escalation triggers
- Shows complete execution example

### **01_dependency_graph.md** - Dependency Tree & Execution Modes
Visual dependency graph showing gate relationships.
- Parallel execution opportunities (Abstract + Methods)
- Sequential dependencies (Results requires Methods)
- Three execution modes: Sequential, Parallel, Opportunistic

### **02_gate_definitions.md** - Detailed Gate Requirements
Comprehensive specifications for each gate (0-5).
- Prerequisites for each gate
- Expected outputs with types and ranges
- Pass/Warn/Fail criteria
- Python verification functions

### **03_verification_protocol.md** - Verification Agent Specs
How verification works and what to check.
- Verification workflow diagram
- Critical vs non-critical checks
- Implementation examples
- Error recovery strategies
- Logging and transparency

### **04_pass_fail_rules.md** - Decision Matrix & Logic
Specific pass/fail conditions for each gate.
- Quick reference matrix
- Detailed FAIL conditions (Python snippets)
- WARN conditions
- PASS conditions
- Decision flow diagram
- Retry logic
- Override mechanism

### **05_visual_diagram.txt** - Complete System Visualization
ASCII art diagram of entire gating system.
- All 6 gates with checks
- Decision logic flowchart
- Retry strategies
- Status icons reference

---

## 🎯 Quick Navigation by Use Case

### "I need to implement this system"
1. Start with **README.md** (overview)
2. Read **COORDINATION_PROMPT.md** (agent instructions)
3. Reference **02_gate_definitions.md** (implementation details)
4. Use **04_pass_fail_rules.md** (specific logic)

### "I need to understand dependencies"
1. **01_dependency_graph.md** (visual tree)
2. **02_gate_definitions.md** (prerequisites section)

### "I need to implement verification"
1. **03_verification_protocol.md** (verification agent)
2. **04_pass_fail_rules.md** (decision logic)
3. **02_gate_definitions.md** (verification functions)

### "I need to troubleshoot failures"
1. **04_pass_fail_rules.md** (failure conditions)
2. **03_verification_protocol.md** (recovery strategies)
3. **COORDINATION_PROMPT.md** (retry logic)

### "I need to visualize the system"
1. **05_visual_diagram.txt** (complete ASCII diagram)
2. **01_dependency_graph.md** (dependency tree)

---

## 📊 Gate Summary Table

| Gate | Name | Depends On | Min Words | Max Words | Critical Checks | Status Types |
|------|------|------------|-----------|-----------|-----------------|--------------|
| 0 | DATA_PREPARATION | None | N/A | N/A | 5 | PASS/WARN/FAIL |
| 1 | ABSTRACT | Gate 0 | 200 | 400 | 4 sections, quality>=60 | PASS/WARN/FAIL |
| 2 | METHODS | Gate 0 | 800 | 2000 | completeness>=60, CONSORT/STROBE | PASS/WARN/FAIL |
| 3 | RESULTS | Gate 2 | 600 | 1500 | ≥3 stats, tables/figs match | PASS/WARN/FAIL |
| 4 | DISCUSSION | Gates 1+3 | 800 | 2000 | limitations, ≥2 citations | PASS/WARN/FAIL |
| 5 | ASSEMBLY | Gates 1-4 | 3000 | 8000 | all sections, refs resolved | PASS/WARN/FAIL |

---

## 🔑 Key Concepts

### Gates
Quality control checkpoints that must be satisfied before proceeding to dependent sections.

### Status Values
- **PASS** ✓: All checks passed, next gate opens
- **WARN** ⚠: Non-critical issues, can proceed with logging
- **FAIL** ✗: Critical issues, requires retry or escalation

### Dependencies
- Gate 1 (Abstract) and Gate 2 (Methods) can run in **parallel**
- Gate 3 (Results) requires Gate 2 (Methods)
- Gate 4 (Discussion) requires Gates 1 (Abstract) + 3 (Results)
- Gate 5 (Assembly) requires all previous gates

### Retry Logic
- Max 2 retries per section
- Adjust parameters based on failure type
- Escalate to human after 2 failed retries

### Verification
Each gate has a verification function that:
1. Checks all requirements
2. Computes status (PASS/WARN/FAIL)
3. Returns structured result with checks, warnings, errors

---

## 🚀 Getting Started

```python
# 1. Initialize verification agent
verifier = IMRaDVerificationAgent()

# 2. Validate input data (Gate 0)
gate0_result = verifier.verify_gate("GATE_0_DATA_PREPARATION", input_data, None)
if gate0_result["status"] == "FAIL":
    raise ValueError(f"Input validation failed: {gate0_result['errors']}")

# 3. Generate and verify each section
for gate in ["GATE_1_ABSTRACT", "GATE_2_METHODS", "GATE_3_RESULTS", "GATE_4_DISCUSSION"]:
    output = generate_section(gate, input_data)
    result = verifier.verify_gate(gate, output, input_data)
    
    if result["status"] == "FAIL":
        output = retry_with_adjustments(gate, output, result["errors"])
        result = verifier.verify_gate(gate, output, input_data)
    
    if result["status"] == "FAIL":
        escalate_to_human(gate, result)
    
    log_verification_result(result)

# 4. Final assembly
bundle = assemble_manuscript(all_sections)
assembly_result = verifier.verify_gate("GATE_5_ASSEMBLY", bundle, input_data)

if assembly_result["status"] in ["PASS", "WARN"]:
    return bundle
else:
    raise ManuscriptAssemblyError(assembly_result["errors"])
```

---

## 📝 Document Metadata

- **Created**: 2025-01-15
- **Version**: 1.0
- **Target Model**: Claude Opus 4.6
- **Purpose**: IMRaD manuscript generation coordination
- **Status**: Production Ready

---

## 🔗 Cross-References

- Implementation: `researchflow-production-main/services/worker/src/generators/imrad_assembler.py`
- Abstract Generator: `researchflow-production-main/services/worker/src/generators/abstract_generator.py`
- Methods Generator: `researchflow-production-main/services/worker/src/generators/methods_generator.py`
- Results Generator: `researchflow-production-main/services/worker/src/generators/results_generator.py`
- Discussion Generator: `researchflow-production-main/services/worker/src/generators/discussion_generator.py`

---

**Next Steps**: 
1. Review COORDINATION_PROMPT.md for system instructions
2. Implement verification agent using gate definitions
3. Test with sample manuscript data
4. Monitor verification logs for quality metrics
