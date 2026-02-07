# Evaluation Datasets

Curated golden datasets for ResearchFlow agent evaluation.

## Files

### `golden-extractions.jsonl`
**Agent:** `agent-stage2-extract`  
**Records:** 10  
**Purpose:** Test data extraction from clinical study abstracts

Test cases cover:
- Randomized controlled trials (RCTs)
- Meta-analyses and systematic reviews
- Cohort and observational studies
- Various clinical domains (cardiology, psychiatry, endocrinology, etc.)
- Positive, null, and conflicting results

**Source:** Hand-curated from public PubMed abstracts (no PHI)

### `golden-synthesis.jsonl`
**Agent:** `agent-stage2-synthesize`  
**Records:** 5  
**Purpose:** Test evidence synthesis and conclusion generation

Test cases cover:
- High-quality consistent evidence
- Conflicting evidence from different study designs
- Null results with effect modification
- Class effects across multiple trials
- Network meta-analyses

**Source:** Based on published systematic reviews and clinical guidelines

### `schemas/`
JSON Schema definitions for agent output validation. One schema per agent.

Base envelopes:
- `_base_envelope.json` - Standard agent response structure
- `_alt_envelope.json` - Alternative response structure (evidence-synth, lit-triage)

## JSONL Format

Each line is a complete JSON object:

```jsonl
{
  "id": "unique-id",
  "agent": "agent-name",
  "input": { /* agent-specific input */ },
  "expected_output": { /* ground truth output */ },
  "tags": ["tag1", "tag2"]
}
```

## Adding New Datasets

1. Create a new `.jsonl` file following the format above
2. Use synthetic or publicly available data only (NO PHI)
3. Include 5-20 records per dataset
4. Add diverse test cases covering edge cases
5. Document the dataset in this README
6. Update the corresponding agent's test suite

## Schema Development

Schemas are extracted from `CANONICAL_AGENT_TIERING_POLICY.md` and stored as standalone JSON Schema files. To update:

1. Edit the schema file in `schemas/`
2. Run `make eval-dry` to validate
3. Update agent implementation if needed

## Usage

```bash
# Validate a single agent against its dataset
python tests/eval/run_eval.py \
  --agent stage2-extract \
  --dataset tests/eval/datasets/golden-extractions.jsonl

# Schema-only validation (no LLM calls)
python tests/eval/run_eval.py --all --dry-run

# Full evaluation suite
make eval
```

## Maintenance

- Review datasets quarterly for relevance
- Update with new edge cases as bugs are discovered
- Keep datasets small and focused (5-20 records)
- Version control all changes via git
- No PHI, ever
