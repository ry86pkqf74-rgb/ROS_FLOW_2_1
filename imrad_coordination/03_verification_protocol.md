# IMRaD Verification Protocol for Agents

## Verification Agent Role

The verification agent runs after each section generation to validate outputs before allowing the next gate to open.

## Verification Workflow

```
Section Generator Completes
    ↓
Verification Agent Invoked
    ↓
Run All Checks for Gate
    ↓
Compute Status: PASS / WARN / FAIL
    ↓
Log Results to Transparency Log
    ↓
If PASS → Open Next Gate
If WARN → Flag for Review, Allow Proceed
If FAIL → Block Next Gate, Require Regeneration
```

## Verification Checklist Structure

Each verification returns:
```python
{
    "gate_name": "GATE_1_ABSTRACT",
    "status": "PASS" | "WARN" | "FAIL",
    "checks": {
        "check_name": True | False,
        ...
    },
    "warnings": ["list", "of", "warnings"],
    "errors": ["list", "of", "blocking", "errors"],
    "timestamp": "2025-01-15T10:30:00Z",
    "verified_by": "verification_agent_v1"
}
```

## Critical vs Non-Critical Checks

### Critical (FAIL if False)
- Required fields present
- Word count minimums met
- No hallucination markers
- Data types correct
- Transparency log complete

### Non-Critical (WARN if False)
- Word count maximums exceeded (soft limit)
- Quality scores in acceptable range
- Optional fields missing
- Style preferences

## Section-Specific Verification Details

### Abstract Verification
**Critical Checks:**
- word_count >= 200
- all 4 sections present (Background, Methods, Results, Conclusions)
- quality_score >= 60
- transparency_log exists

**Non-Critical Checks:**
- word_count <= 400 (WARN if exceeded)
- quality_score >= 80 (WARN if below)
- keywords provided (WARN if missing)

### Methods Verification
**Critical Checks:**
- study_design described
- participants criteria defined
- outcomes specified
- statistical_plan present
- completeness_score >= 60

**Non-Critical Checks:**
- completeness_score >= 80 (WARN if below)
- CONSORT/STROBE items all checked (WARN if incomplete)
- randomization described for RCTs (WARN if missing)

### Results Verification
**Critical Checks:**
- at least 1 statistical statement
- primary outcome reported
- sample_size_analyzed stated
- word_count >= 400

**Non-Critical Checks:**
- at least 5 statistical statements (WARN if below)
- all tables/figures referenced (WARN if some missing)
- no interpretation language present (WARN if found)

### Discussion Verification
**Critical Checks:**
- limitations section present
- at least 1 literature citation
- conclusions present
- completeness_score >= 60

**Non-Critical Checks:**
- completeness_score >= 80 (WARN if below)
- at least 5 literature citations (WARN if below)
- future research mentioned (WARN if missing)
- no overstating language (WARN if found)

### Final Assembly Verification
**Critical Checks:**
- all required sections present
- all cross-references resolved
- bibliography generated
- no validation_errors with "error" severity

**Non-Critical Checks:**
- total word count 3000-8000 (WARN if outside)
- all warnings resolved (WARN if any remain)
- supplementary materials included (WARN if missing)

## Verification Agent Implementation

```python
class IMRaDVerificationAgent:
    def verify_gate(self, gate_name: str, output: Any, input_data: Any) -> dict:
        """Main verification entry point."""
        
        if gate_name == "GATE_0_DATA_PREPARATION":
            return self._verify_data_preparation(input_data)
        elif gate_name == "GATE_1_ABSTRACT":
            return self._verify_abstract(output, input_data)
        elif gate_name == "GATE_2_METHODS":
            return self._verify_methods(output, input_data)
        elif gate_name == "GATE_3_RESULTS":
            return self._verify_results(output, input_data)
        elif gate_name == "GATE_4_DISCUSSION":
            return self._verify_discussion(output, input_data)
        elif gate_name == "GATE_5_ASSEMBLY":
            return self._verify_assembly(output, input_data)
        else:
            raise ValueError(f"Unknown gate: {gate_name}")
    
    def _verify_data_preparation(self, data: dict) -> dict:
        checks = {}
        errors = []
        warnings = []
        
        # Research question
        if not data.get("research_question"):
            errors.append("Missing research_question")
            checks["research_question_present"] = False
        elif len(data["research_question"]) < 10:
            warnings.append("Research question very brief")
            checks["research_question_present"] = True
        else:
            checks["research_question_present"] = True
        
        # Study type
        valid_types = ["RCT", "cohort", "case_control", "cross_sectional", "systematic_review"]
        if data.get("study_type") not in valid_types:
            errors.append(f"Invalid study_type: {data.get('study_type')}")
            checks["study_type_valid"] = False
        else:
            checks["study_type_valid"] = True
        
        # Sample size
        try:
            n = int(data.get("sample_size", 0))
            if n <= 0:
                errors.append("Sample size must be > 0")
                checks["sample_size_valid"] = False
            else:
                checks["sample_size_valid"] = True
        except (ValueError, TypeError):
            errors.append("Sample size not numeric")
            checks["sample_size_valid"] = False
        
        # Key findings
        findings = data.get("key_findings", [])
        if not findings or len(findings) == 0:
            errors.append("No key findings provided")
            checks["key_findings_present"] = False
        else:
            checks["key_findings_present"] = True
        
        status = "PASS" if not errors else "FAIL"
        if warnings and status == "PASS":
            status = "WARN"
        
        return {
            "gate_name": "GATE_0_DATA_PREPARATION",
            "status": status,
            "checks": checks,
            "warnings": warnings,
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
```

## Error Recovery Strategies

### Strategy 1: Automatic Retry with Adjusted Parameters
- If quality_score < 60, retry with temperature -= 0.1
- If word_count too short, retry with explicit "expand" instruction
- Max 2 retries per section

### Strategy 2: Fallback to Template
- If generation fails after retries, use structured template
- Fill template with available data
- Mark as "TEMPLATE_FALLBACK" in transparency log

### Strategy 3: Human-in-Loop
- If FAIL after retries, escalate to human review
- Provide specific error context
- Allow manual override with justification

## Verification Logging

All verification results logged to:
- Database: `manuscript_verification_logs` table
- File: `.tmp/verification/{manuscript_id}/gate_{N}_verification.json`
- Transparency bundle: included in final manuscript metadata

## Gate Status Dashboard

Track gate progression:
```
GATE_0: ✓ PASSED (2025-01-15 10:00:00)
GATE_1: ✓ PASSED (2025-01-15 10:05:30)
GATE_2: ⚠ WARNING (2025-01-15 10:12:00) - completeness 72%
GATE_3: ⏳ PENDING
GATE_4: 🔒 BLOCKED (waiting for GATE_3)
GATE_5: 🔒 BLOCKED (waiting for GATE_4)
```
