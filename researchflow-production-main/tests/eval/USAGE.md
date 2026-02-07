# Evaluation Harness Usage Guide

## Quick Start

```bash
# Install dependencies
pip install -r tests/eval/requirements.txt

# Run schema validation only (P0 - no agents needed)
python tests/eval/run_eval.py --all --dry-run

# Or use the Makefile
make eval-dry
```

## Usage Modes

### 1. Schema-Only Validation (P0)

Validates agent response structures against JSON schemas. **No LLM calls, no running agents required.**

```bash
# All agents
python tests/eval/run_eval.py --all --dry-run

# Single agent
python tests/eval/run_eval.py --agent stage2-extract --dry-run

# With custom output directory
python tests/eval/run_eval.py --all --dry-run --output ./my-results/
```

**Use Case:** Fast validation during development, CI pre-merge checks, schema regression testing.

### 2. Dataset Evaluation (Dry-Run)

Evaluates against curated datasets using synthetic responses. **No LLM calls.**

```bash
# Single agent with dataset (dry-run)
python tests/eval/run_eval.py \
  --agent stage2-extract \
  --dataset tests/eval/datasets/golden-extractions.jsonl \
  --dry-run

# Synthesis agent
python tests/eval/run_eval.py \
  --agent stage2-synthesize \
  --dataset tests/eval/datasets/golden-synthesis.jsonl \
  --dry-run
```

**Use Case:** Testing dataset structure, validating metrics logic, offline development.

### 3. Full Dataset Evaluation (Live)

Evaluates against curated datasets with **real agent calls**. Requires agents running.

```bash
# ⚠️  Requires agents running and API keys
python tests/eval/run_eval.py \
  --agent stage2-extract \
  --dataset tests/eval/datasets/golden-extractions.jsonl

# Or use the Makefile (starts agents if configured)
make eval
```

**Use Case:** Nightly regression testing, pre-release validation, performance benchmarking.

### 4. Check Results

Validate previously saved results against thresholds.

```bash
# Check latest results
python tests/eval/run_eval.py --check-results tests/eval/results/

# In CI - exits non-zero on failures
python tests/eval/run_eval.py --check-results tests/eval/results/
echo $?  # 0 = pass, 1 = failure
```

**Use Case:** CI gating, trend analysis, regression detection.

## Command-Line Options

```
Options:
  -a, --agent TEXT      Agent name (with or without 'agent-' prefix)
  -d, --dataset PATH    Path to JSONL dataset file
  --all                 Run for all agents with schemas
  --dry-run             Schema-only validation (no LLM calls)
  -o, --output PATH     Output directory (default: tests/eval/results/)
  --check-results PATH  Validate existing results
  --help                Show help message
```

## Output Format

Results are written to timestamped JSON files:

```json
[
  {
    "id": "ext-001",
    "agent": "agent-stage2-extract",
    "groundedness_f1": 0.82,
    "schema_errors": [],
    "schema_error_count": 0,
    "latency_s": 2.5,
    "cost_usd": 0.0015,
    "passed": true
  }
]
```

### Result Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Test case identifier |
| `agent` | string | Agent name |
| `groundedness_f1` | float | Rouge-L F1 score vs expected output (0-1) |
| `schema_errors` | array | List of schema validation errors |
| `schema_error_count` | int | Number of schema errors |
| `latency_s` | float | Wall-clock time in seconds |
| `cost_usd` | float | Estimated cost based on token usage |
| `passed` | boolean | True if all thresholds passed |

## Makefile Targets

```bash
# Schema-only validation
make eval-dry

# Full evaluation (requires agents)
make eval

# Check latest results
make eval --check-results
```

## CI Integration

The eval harness integrates with GitHub Actions:

```yaml
# .github/workflows/eval-harness.yml
- name: Run schema validation
  run: make eval-dry

- name: Upload results
  uses: actions/upload-artifact@v4
  with:
    name: eval-results
    path: tests/eval/results/

- name: Gate on failures
  run: python tests/eval/run_eval.py --check-results tests/eval/results/
```

### CI Behavior

- **On PR:** Schema validation only (fast, no cost)
- **On merge to main:** Schema + extraction dataset (limited)
- **Nightly:** Full suite with all datasets
- **On workflow_dispatch:** Manual full run

### Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `EVAL_MODE` | `ci`, `local` | In CI mode, samples only 5 records per dataset |
| `EVAL_AGENT_BASE_URL` | URL | Base URL for agent HTTP endpoints (default: `http://localhost`) |
| `OPENAI_API_KEY` | string | Required for live agent calls |

## Metrics & Thresholds

### Schema Validity (P0)
- **Threshold:** 0 errors
- **Gate:** Hard fail on any schema error
- **Metric:** JSON Schema validation

### Groundedness (P1+)
- **Threshold:** F1 ≥ 0.70
- **Gate:** Warning below 0.70, fail below 0.50
- **Metric:** Rouge-L F1 score

### Latency
- **Thresholds:** 
  - NANO/MINI: ≤ 30s (p95)
  - STANDARD: ≤ 60s (p95)
  - FRONTIER: ≤ 120s (p95)
- **Gate:** Warning on breach, no hard fail
- **Metric:** Wall-clock time

### Cost
- **Threshold:** ≤ 1.2× baseline
- **Gate:** Warning on >20% regression
- **Metric:** Token usage × tier pricing

## Troubleshooting

### `ModuleNotFoundError: No module named 'tabulate'`
```bash
pip install -r tests/eval/requirements.txt
```

### `FileNotFoundError: Schema not found`
The agent may not have a schema defined. Check `tests/eval/datasets/schemas/` for available schemas.

### Schema validation fails unexpectedly
1. Check if the schema was recently updated
2. Verify agent response structure matches the schema
3. Run with `--dry-run` to test synthetic responses first

### Groundedness F1 is 0 in dry-run mode
This is expected. Dry-run uses synthetic responses with empty outputs. Use live mode for meaningful groundedness scores.

### Agents not responding
1. Verify agents are running: `docker ps`
2. Check agent ports match `AGENT_PORTS` in `harness.py`
3. Set `EVAL_AGENT_BASE_URL` if agents are not on localhost

## Development Workflow

```bash
# 1. Make changes to agent or schema
# 2. Run fast validation
make eval-dry

# 3. If schema-valid, test with dataset (dry-run)
python tests/eval/run_eval.py \
  --agent my-agent \
  --dataset tests/eval/datasets/my-dataset.jsonl \
  --dry-run

# 4. Start agents and run live
python tests/eval/run_eval.py \
  --agent my-agent \
  --dataset tests/eval/datasets/my-dataset.jsonl

# 5. Check results
python tests/eval/run_eval.py --check-results tests/eval/results/
```

## Adding New Agents

1. Create JSON Schema in `tests/eval/datasets/schemas/agent-name.json`
2. Add agent to `AGENT_PORTS` in `harness.py` (if needed)
3. Add tier to `AGENT_TIERS` in `metrics/cost.py`
4. Run schema validation: `make eval-dry`
5. Create golden dataset (optional)
6. Update CI workflow if new dataset added

## Adding New Datasets

See [datasets/README.md](datasets/README.md) for detailed instructions.

## Performance Tips

- Use `--dry-run` for fast iteration
- Use `EVAL_MODE=ci` to sample datasets (5 records)
- Run schema-only validation on every commit
- Run full evaluation nightly or on-demand
- Cache results artifacts in CI for 30 days

## Support

For issues or questions:
1. Check [EVAL_HARNESS_ROADMAP.md](../../EVAL_HARNESS_ROADMAP.md)
2. Review existing test results in `tests/eval/results/`
3. Check CI workflow runs for examples
4. Open an issue with eval logs and result JSON
