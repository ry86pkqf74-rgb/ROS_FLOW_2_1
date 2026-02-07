# IMRaD Generation: Pass/Fail Rules & Decision Matrix

## Quick Reference Matrix

| Gate | Critical Failures | Automatic Failures | Warnings (Allow Proceed) |
|------|-------------------|-------------------|--------------------------|
| **0: Data Prep** | Missing research_question, Invalid study_type, sample_size <= 0 | No key_findings | Missing hypothesis, No keywords |
| **1: Abstract** | word_count < 200, Missing sections, quality_score < 60 | Hallucination markers present | word_count > 400, quality_score < 80 |
| **2: Methods** | completeness < 60, Missing study_design | No statistical_plan | completeness < 80, Missing CONSORT items |
| **3: Results** | No statistical statements, word_count < 400 | Missing primary outcome | < 5 statistical statements, Interpretation language |
| **4: Discussion** | No limitations, completeness < 60 | No conclusions, < 2 citations | completeness < 80, Overstating language |
| **5: Assembly** | Missing sections, Unresolved references | validation_errors present | Warnings present, word_count outside range |

## Detailed Pass/Fail Logic

### Gate 0: DATA_PREPARATION

#### FAIL Conditions (Block All Generation)
```python
FAIL if any([
    not data.get("research_question"),
    len(data.get("research_question", "")) < 10,
    data.get("study_type") not in VALID_STUDY_TYPES,
    int(data.get("sample_size", 0)) <= 0,
    not data.get("key_findings") or len(data["key_findings"]) == 0,
    not data.get("primary_outcome"),
])
```

#### WARN Conditions (Allow with Caution)
```python
WARN if any([
    not data.get("hypothesis"),
    not data.get("keywords") or len(data["keywords"]) == 0,
    not data.get("intervention") and data["study_type"] == "RCT",
    not data.get("literature_context"),
])
```

#### PASS Condition
```python
PASS if all required fields valid and no FAIL conditions
```

---

### Gate 1: ABSTRACT_GENERATION

#### FAIL Conditions (Require Regeneration)
```python
FAIL if any([
    output.word_count < 200,
    output.quality_score < 60.0,
    len(output.sections) < 4,
    not all(section in output.sections for section in 
        ["Background", "Methods", "Results", "Conclusions"]),
    "transparency_log" not in output.__dict__,
    any(marker in output.text.lower() for marker in 
        ["[citation needed]", "tbd", "to be determined", "not available"]),
])
```

#### WARN Conditions (Flag for Review)
```python
WARN if any([
    output.word_count > 400,
    output.quality_score < 80.0,
    not output.keywords or len(output.keywords) < 3,
    len(output.suggestions) > 3,
])
```

#### PASS Condition
```python
PASS if (
    200 <= output.word_count <= 400 and
    output.quality_score >= 70.0 and
    len(output.sections) == 4 and
    output.transparency_log.get("success") == True
)
```

---

### Gate 2: METHODS_GENERATION

#### FAIL Conditions
```python
FAIL if any([
    output.completeness_score < 60.0,
    output.word_count < 800,
    not output.compliance_items.get("study_design"),
    not output.compliance_items.get("participants"),
    not output.compliance_items.get("outcomes_defined"),
    not output.compliance_items.get("statistical_methods"),
    "study design" not in output.text.lower(),
])
```

#### WARN Conditions
```python
WARN if any([
    output.completeness_score < 80.0,
    output.word_count > 2000,
    sum(output.compliance_items.values()) / len(output.compliance_items) < 0.8,
    input_data.study_type == StudyType.RCT and not output.compliance_items.get("randomization_described"),
])
```

#### PASS Condition
```python
PASS if (
    output.completeness_score >= 70.0 and
    800 <= output.word_count <= 2000 and
    all(output.compliance_items.get(item) for item in 
        ["study_design", "participants", "outcomes_defined", "statistical_methods"])
)
```

---

### Gate 3: RESULTS_GENERATION

#### FAIL Conditions
```python
FAIL if any([
    len(output.statistical_statements) == 0,
    output.word_count < 400,
    "primary outcome" not in output.text.lower() and 
        "primary result" not in output.text.lower(),
    input_data.sample_size_analyzed not in output.text,
    len(output.table_references) == 0 and len(input_data.tables) > 0,
])
```

#### WARN Conditions
```python
WARN if any([
    len(output.statistical_statements) < 5,
    len(output.table_references) < len(input_data.tables),
    len(output.figure_references) < len(input_data.figures),
    any(phrase in output.text.lower() for phrase in 
        ["suggests that", "indicates that", "implies", "therefore"]),
])
```

#### PASS Condition
```python
PASS if (
    len(output.statistical_statements) >= 3 and
    output.word_count >= 600 and
    len(output.table_references) == len(input_data.tables) and
    len(output.figure_references) == len(input_data.figures)
)
```

---

### Gate 4: DISCUSSION_GENERATION

#### FAIL Conditions
```python
FAIL if any([
    output.completeness_score < 60.0,
    "limitation" not in output.text.lower(),
    len(output.literature_citations_used) < 2,
    "conclusion" not in output.text.lower(),
    output.word_count < 800,
])
```

#### WARN Conditions
```python
WARN if any([
    output.completeness_score < 80.0,
    len(output.literature_citations_used) < 5,
    "future research" not in output.text.lower() and 
        "further research" not in output.text.lower(),
    any(phrase in output.text.lower() for phrase in 
        ["proves that", "definitively shows", "clearly demonstrates"]),
    output.word_count > 2000,
])
```

#### PASS Condition
```python
PASS if (
    output.completeness_score >= 70.0 and
    800 <= output.word_count <= 2000 and
    len(output.literature_citations_used) >= 3 and
    "limitation" in output.text.lower() and
    "conclusion" in output.text.lower()
)
```

---

### Gate 5: FINAL_ASSEMBLY

#### FAIL Conditions
```python
expected_sections = {"title", "abstract", "methods", "results", "discussion", "references"}

FAIL if any([
    not expected_sections.issubset(set(bundle.sections.keys())),
    len(bundle.references) == 0,
    any("[CITE:" in section.text for section in bundle.sections.values()),
    any("[FIGURE:" in section.text for section in bundle.sections.values()),
    any("[TABLE:" in section.text for section in bundle.sections.values()),
    any("error" in warning.lower() for warning in bundle.warnings),
])
```

#### WARN Conditions
```python
WARN if any([
    len(bundle.warnings) > 0,
    sum(s.word_count for s in bundle.sections.values()) < 3000,
    sum(s.word_count for s in bundle.sections.values()) > 8000,
    not bundle.supplementary and input_data.include_supplementary,
])
```

#### PASS Condition
```python
PASS if (
    expected_sections.issubset(set(bundle.sections.keys())) and
    len(bundle.references) > 0 and
    not any("[CITE:" in s.text for s in bundle.sections.values()) and
    not any(e for e in bundle.warnings if "error" in e.lower())
)
```

## Decision Flow

```
┌─────────────────────┐
│  Run Gate Checks    │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Any FAIL?    │
    └──────┬───────┘
           │
     ┌─────┴─────┐
     │           │
    YES         NO
     │           │
     ▼           ▼
┌─────────┐  ┌──────────┐
│ FAIL    │  │ Any WARN?│
│ Status  │  └─────┬────┘
└────┬────┘        │
     │        ┌────┴────┐
     │        │         │
     │       YES       NO
     │        │         │
     │        ▼         ▼
     │   ┌────────┐  ┌──────┐
     │   │ WARN   │  │ PASS │
     │   │ Status │  │Status│
     │   └────────┘  └──────┘
     │
     ▼
┌──────────────────────┐
│ Block Next Gate      │
│ Require Regeneration │
└──────────────────────┘
     │
     ▼
┌──────────────────────┐
│ Retry (max 2 times)  │
└──────────────────────┘
     │
     ▼
┌──────────────────────┐
│ If still FAIL:       │
│ Escalate to Human    │
└──────────────────────┘
```

## Retry Logic

### Automatic Retry Conditions
1. **quality_score < 60**: Retry with temperature -= 0.1
2. **word_count too low**: Add "Please expand with more detail" to prompt
3. **word_count too high**: Add "Please be concise" to prompt
4. **Missing sections**: Add explicit section requirements to prompt

### Max Retries
- 2 retries per section
- After 2 failed retries → escalate to human review

### Escalation Triggers
```python
escalate_to_human = (
    retry_count >= 2 and status == "FAIL"
) or (
    manual_override_requested
) or (
    critical_data_quality_issue
)
```

## Override Mechanism

Authorized users can override FAIL → PASS with:
- Written justification (required)
- Risk acknowledgment (required)
- Approval signature (required)

Override logged to transparency bundle:
```json
{
    "gate": "GATE_2_METHODS",
    "original_status": "FAIL",
    "override_status": "PASS",
    "justification": "Methods section sufficient for pilot study",
    "approved_by": "PI_Name",
    "timestamp": "2025-01-15T14:30:00Z"
}
```

## Status Icons Reference

- ✓ PASS: All checks passed
- ⚠ WARN: Non-critical issues, can proceed
- ✗ FAIL: Critical issues, regeneration required
- ⏳ PENDING: Waiting for dependencies
- 🔒 BLOCKED: Dependencies not met
- 🔄 RETRYING: Automatic retry in progress
- 👤 ESCALATED: Human review required
