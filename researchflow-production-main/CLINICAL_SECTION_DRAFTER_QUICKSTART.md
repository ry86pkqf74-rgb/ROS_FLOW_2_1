# Clinical Study Section Drafter - Quick Reference

**Status:** ✅ Imported (2026-02-07)  
**Location:** `agents/Clinical_Study_Section_Drafter/`  
**Type:** LangSmith Multi-Agent System

---

## What It Does

Drafts publication-ready **Results** and **Discussion** sections for clinical studies with automatic reporting guideline compliance (CONSORT, STROBE, STARD, PRISMA, CARE).

---

## Quick Start

### 1. Basic Usage

```python
from agents.Clinical_Study_Section_Drafter import draft_section

draft = await draft_section(
    section_type="Results",  # or "Discussion"
    study_summary="[Study design, population, intervention, outcomes]",
    results_data={
        "primary_outcome": {
            "metric": "HbA1c reduction",
            "treatment": {"mean": -1.2, "std": 0.4, "n": 150},
            "control": {"mean": -0.3, "std": 0.5, "n": 150},
            "effect_size": -0.9,
            "ci_95": [-1.1, -0.7],
            "p_value": 0.001
        }
    },
    evidence_chunks=[...],  # From evidence synthesis
    key_hypotheses=["Primary hypothesis"],
    few_shot_examples=["Example passage from similar study..."]
)

print(draft['section_draft'])
```

### 2. Required Inputs

| Input | Description | Example |
|-------|-------------|---------|
| `section_type` | "Results" or "Discussion" | `"Results"` |
| `study_summary` | Study design summary | `"RCT of Drug X in 300 T2DM patients"` |
| `results_data` | Statistical outputs | `{"primary_outcome": {...}}` |
| `evidence_chunks` | Supporting evidence | From `agent-evidence-synthesis` |
| `key_hypotheses` | Hypotheses tested | `["Drug X reduces HbA1c"]` |
| `few_shot_examples` | Style examples | 2-3 example passages |

### 3. Output Structure

```json
{
  "section_draft": "## Results\n\n...",
  "guideline_compliance_report": {
    "guideline": "CONSORT",
    "items_addressed": ["13a", "17a"],
    "items_missing": ["14a"],
    "suggestions": [...]
  },
  "evidence_citations": [...],
  "audit_log": {...}
}
```

---

## Supported Study Types & Guidelines

| Study Type | Guideline | Key Elements |
|------------|-----------|--------------|
| **RCT** | CONSORT | Participant flow, effect sizes + CIs, harms |
| **Cohort/Case-Control** | STROBE | Descriptive data, adjusted estimates |
| **Diagnostic** | STARD | Test results, diagnostic accuracy + CIs |
| **Systematic Review** | PRISMA | Study selection, synthesis, GRADE |
| **Case Report** | CARE | Timeline, intervention, outcomes |

---

## Sub-Workers

### Clinical_Evidence_Researcher
- Searches PubMed, ClinicalTrials.gov, Cochrane
- Extracts comparable sections from published studies
- Validates claims against literature

### Reporting_Guideline_Checker
- Validates compliance against 5 major guidelines
- Identifies missing checklist items
- Provides actionable suggestions

---

## Integration Points

### A. Standalone Use
```bash
POST /agents/run/sync
# Provide all inputs manually
```

### B. Pipeline Integration
```python
# Evidence Synthesis → Section Drafter
synthesis = await agent_evidence_synthesis.synthesize(...)
draft = await clinical_section_drafter.draft(
    evidence_chunks=synthesis.evidence_chunks,
    ...
)
```

### C. Manuscript Assembly
```python
# Section Drafter → Clinical Manuscript Writer
sections = {}
for type in ['Results', 'Discussion']:
    sections[type] = await clinical_section_drafter.draft(...)
    
manuscript = await agent_clinical_manuscript.assemble(
    custom_sections=sections
)
```

---

## Environment Setup

```bash
# LangSmith
export LANGCHAIN_API_KEY=lsv2_pt_...
export LANGSMITH_PROJECT=ResearchFlow-Production

# External APIs (for sub-workers)
export TAVILY_API_KEY=tvly-...
export EXA_API_KEY=exa_...

# Optional: Google integration
export GOOGLE_DOCS_API_KEY=...
export GMAIL_API_KEY=...
```

---

## Common Patterns

### Pattern 1: RCT Results Section
```python
rct_draft = await draft_section(
    section_type='Results',
    study_summary='Double-blind RCT...',
    results_data={
        'primary_outcome': {...},
        'secondary_outcomes': [...],
        'adverse_events': [...]
    },
    ...
)
# Output: CONSORT-compliant Results section
```

### Pattern 2: Observational Study Discussion
```python
discussion = await draft_section(
    section_type='Discussion',
    study_summary='Retrospective cohort...',
    results_data={'adjusted_hr': 0.72, 'ci_95': [0.65, 0.80]},
    ...
)
# Output: STROBE-compliant Discussion section
```

### Pattern 3: Compliance Check Only
```python
from agents.Clinical_Study_Section_Drafter.subagents.Reporting_Guideline_Checker import check_compliance

audit = await check_compliance(
    draft_text=existing_results,
    section_type='Results',
    study_type='RCT'
)
# Output: Compliance report with missing items
```

---

## Quality Guarantees

✅ **Never fabricates statistics** - All numbers from `results_data`  
✅ **Evidence traceability** - Every claim linked to source  
✅ **Guideline compliance** - Automatic checklist validation  
✅ **Style matching** - Mirrors few-shot examples  
✅ **Audit logging** - Complete worker call history

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Missing required inputs | Check all 6 inputs provided |
| Guideline mismatch | Let agent auto-detect or verify `study_type` |
| Worker failures | Check API keys: TAVILY_API_KEY, EXA_API_KEY |
| Statistical format errors | Verify `results_data` schema |

---

## Related Agents

- **agent-evidence-synthesis**: Feeds evidence to this agent
- **agent-clinical-manuscript**: Consumes output for full manuscript
- **agent-lit-triage**: Upstream literature prioritization

---

## Files & Resources

```
agents/Clinical_Study_Section_Drafter/
├── AGENTS.md                        # Main prompt/instructions
├── config.json                      # Agent config
├── tools.json                       # Tool definitions
├── skills/
│   └── reporting-guidelines/        # Guideline knowledge
└── subagents/
    ├── Clinical_Evidence_Researcher/
    │   ├── AGENTS.md                # Literature search worker
    │   └── tools.json
    └── Reporting_Guideline_Checker/
        ├── AGENTS.md                # Compliance validator
        └── tools.json
```

---

## Next Steps

1. ✅ **Agent imported** - Files copied to `agents/`
2. ✅ **Inventory updated** - Added to AGENT_INVENTORY.md
3. ✅ **Documentation created** - Integration guide + quick reference
4. 🔄 **Test integration** - Run example drafts
5. 🔄 **Containerize** - Build Docker image (planned)
6. 🔄 **Connect to workflow** - Wire into Stage 8 (Writing)

---

**For detailed documentation:**  
👉 [CLINICAL_SECTION_DRAFTER_INTEGRATION.md](./CLINICAL_SECTION_DRAFTER_INTEGRATION.md)

**For agent instructions:**  
👉 [agents/Clinical_Study_Section_Drafter/AGENTS.md](./agents/Clinical_Study_Section_Drafter/AGENTS.md)
