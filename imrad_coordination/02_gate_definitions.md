# IMRaD Generation Gate Definitions

## Gate 0: DATA_PREPARATION

### Prerequisites (Must Pass)
- [ ] Research question defined (non-empty string, >10 chars)
- [ ] Study type specified (valid StudyType enum value)
- [ ] Population described (non-empty string)
- [ ] Sample size > 0
- [ ] At least one key finding provided
- [ ] Methods summary present
- [ ] Primary outcome defined

### Optional But Recommended
- Hypothesis provided
- Intervention/Comparator specified (for RCTs)
- Keywords list (for Abstract)
- Literature references indexed

### Pass Criteria
- **PASS**: All required fields present and valid
- **WARN**: Optional fields missing (can proceed with warnings)
- **FAIL**: Any required field missing or invalid

### Verification Agent Checks
1. `assert data.get("research_question") and len(data["research_question"]) > 10`
2. `assert data.get("study_type") in [e.value for e in StudyType]`
3. `assert data.get("sample_size") and int(data["sample_size"]) > 0`
4. `assert data.get("key_findings") and len(data["key_findings"]) > 0`
5. `assert data.get("primary_outcome") and len(data["primary_outcome"]) > 5`

---

## Gate 1: ABSTRACT_GENERATION

### Prerequisites (Must Pass)
- [x] Gate 0 PASSED
- [ ] Abstract generator initialized
- [ ] Word limit parameters defined

### Expected Outputs
- `abstract_text`: string, 200-400 words
- `abstract_sections`: dict with Background, Methods, Results, Conclusions
- `word_count`: int
- `quality_score`: float >= 70.0
- `transparency_log`: dict with model info

### Pass Criteria
- **PASS**: Word count in range, quality_score >= 70, all sections present
- **WARN**: Quality score 60-69 (manual review recommended)
- **FAIL**: Word count out of range, quality_score < 60, missing sections

### Verification Agent Checks
```python
def verify_abstract(output: AbstractOutput) -> dict:
    checks = {
        "word_count_in_range": 200 <= output.word_count <= 400,
        "quality_score_acceptable": output.quality_score >= 70.0,
        "sections_complete": all(s in output.sections for s in 
            ["Background", "Methods", "Results", "Conclusions"]),
        "transparency_logged": "model_name" in output.transparency_log,
        "no_hallucination_markers": not any(marker in output.text.lower() 
            for marker in ["[citation needed]", "tbd", "to be determined"]),
    }
    
    status = "PASS" if all(checks.values()) else "FAIL"
    return {"status": status, "checks": checks}
```

---

## Gate 2: METHODS_GENERATION

### Prerequisites (Must Pass)
- [x] Gate 0 PASSED
- [ ] Study design specified
- [ ] Participants criteria defined
- [ ] Outcomes structure provided
- [ ] Statistical plan present

### Expected Outputs
- `methods_text`: string, 800-2000 words
- `template`: MethodsTemplate (CONSORT/STROBE/etc)
- `compliance_items`: dict of checklist items
- `completeness_score`: float >= 70.0
- `sections`: dict with Study Design, Participants, Analysis, etc.

### Pass Criteria
- **PASS**: Completeness >= 70%, all required sections present, compliance items checked
- **WARN**: Completeness 60-69%, some compliance items missing
- **FAIL**: Completeness < 60%, missing critical sections

### Verification Agent Checks
```python
def verify_methods(output: MethodsOutput) -> dict:
    required_compliance = {
        "study_design", "participants", "outcomes_defined", "statistical_methods"
    }
    
    checks = {
        "completeness_acceptable": output.completeness_score >= 70.0,
        "word_count_reasonable": 800 <= output.word_count <= 2000,
        "required_compliance_met": all(
            output.compliance_items.get(item, False) 
            for item in required_compliance
        ),
        "sections_present": len(output.sections) >= 4,
        "template_appropriate": output.template.value != "standard" or 
            "Not specified" not in output.text,
    }
    
    status = "PASS" if all(checks.values()) else "FAIL"
    return {"status": status, "checks": checks}
```

---

## Gate 3: RESULTS_GENERATION

### Prerequisites (Must Pass)
- [x] Gate 2 PASSED (Methods complete)
- [ ] Primary results data available
- [ ] Sample size analyzed known
- [ ] At least one statistical result

### Expected Outputs
- `results_text`: string, 600-1500 words
- `table_references`: list of "Table N" strings
- `figure_references`: list of "Figure N" strings
- `statistical_statements`: list of p-values, CIs, effect sizes
- `sections`: dict with flow, outcomes, analyses

### Pass Criteria
- **PASS**: At least 3 statistical statements, references match input tables/figures
- **WARN**: Few statistical statements, some references missing
- **FAIL**: No statistical statements, no table/figure references, word count < 400

### Verification Agent Checks
```python
def verify_results(output: ResultsOutput, input_data: ResultsInput) -> dict:
    checks = {
        "has_statistical_statements": len(output.statistical_statements) >= 3,
        "references_tables": len(output.table_references) == len(input_data.tables),
        "references_figures": len(output.figure_references) == len(input_data.figures),
        "word_count_adequate": output.word_count >= 600,
        "no_interpretation": not any(
            phrase in output.text.lower() 
            for phrase in ["suggests that", "indicates that", "implies", "therefore"]
        ),
        "past_tense": output.text.count(" were ") + output.text.count(" was ") > 5,
    }
    
    status = "PASS" if all(checks.values()) else "FAIL"
    return {"status": status, "checks": checks}
```

---

## Gate 4: DISCUSSION_GENERATION

### Prerequisites (Must Pass)
- [x] Gate 1 PASSED (Abstract complete)
- [x] Gate 3 PASSED (Results complete)
- [ ] Key findings structured
- [ ] At least 2 literature references
- [ ] Limitations identified

### Expected Outputs
- `discussion_text`: string, 800-2000 words
- `literature_citations_used`: list of citations
- `completeness_score`: float >= 70.0
- `sections`: dict with Principal Findings, Literature, Limitations, etc.

### Pass Criteria
- **PASS**: Completeness >= 70%, limitations discussed, literature cited, conclusions present
- **WARN**: Completeness 60-69%, few citations, brief limitations
- **FAIL**: Completeness < 60%, no limitations, no literature synthesis

### Verification Agent Checks
```python
def verify_discussion(output: DiscussionOutput, input_data: DiscussionInput) -> dict:
    checks = {
        "completeness_acceptable": output.completeness_score >= 70.0,
        "limitations_discussed": "limitation" in output.text.lower(),
        "literature_synthesized": len(output.literature_citations_used) >= 2,
        "conclusions_present": "conclusion" in output.text.lower(),
        "word_count_adequate": 800 <= output.word_count <= 2000,
        "no_overstating": not any(
            phrase in output.text.lower() 
            for phrase in ["proves that", "definitively shows", "clearly demonstrates"]
        ),
        "future_research_mentioned": "future" in output.text.lower() or 
            "further research" in output.text.lower(),
    }
    
    status = "PASS" if all(checks.values()) else "FAIL"
    return {"status": status, "checks": checks}
```

---

## Gate 5: FINAL_ASSEMBLY

### Prerequisites (Must Pass)
- [x] Gate 1 PASSED (Abstract)
- [x] Gate 2 PASSED (Methods)
- [x] Gate 3 PASSED (Results)
- [x] Gate 4 PASSED (Discussion)
- [ ] All sections word counts within limits
- [ ] No section has quality_score < 60

### Expected Outputs
- `manuscript_bundle`: ManuscriptBundle with all sections
- `references`: List[ManuscriptReference] with bibliography
- `warnings`: list of non-blocking issues
- `validation_errors`: empty list (all errors must be resolved)

### Pass Criteria
- **PASS**: All sections present, references resolved, no validation errors
- **WARN**: Some warnings present (missing optional fields)
- **FAIL**: Any section missing, unresolved references, validation errors present

### Verification Agent Checks
```python
def verify_assembly(bundle: ManuscriptBundle, inputs: IMRaDAssembleInput) -> dict:
    expected_sections = {"title", "abstract", "methods", "results", "discussion", "references"}
    
    checks = {
        "all_sections_present": expected_sections.issubset(set(bundle.sections.keys())),
        "no_validation_errors": len(bundle.warnings) == 0 or 
            all("error" not in w.lower() for w in bundle.warnings),
        "references_resolved": len(bundle.references) > 0,
        "cross_references_resolved": not any(
            "[CITE:" in section.text or "[FIGURE:" in section.text 
            for section in bundle.sections.values()
        ),
        "total_word_count_reasonable": 3000 <= sum(
            s.word_count for s in bundle.sections.values()
        ) <= 8000,
        "citations_formatted": all(
            ref.title or ref.raw for ref in bundle.references
        ),
    }
    
    status = "PASS" if all(checks.values()) else "FAIL"
    return {"status": status, "checks": checks}
```
