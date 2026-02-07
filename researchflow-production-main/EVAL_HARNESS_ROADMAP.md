# Evaluation Harness Roadmap — ResearchFlow Agents

> **Author:** Claude Opus 4.6 · **Date:** 2026-02-06  
> **Scope:** Minimal, practical harness for the three agent layers (LangGraph orchestration, TypeScript AI-agents, Python worker stages).

---

## 1 · What Exists Today

| Component | Location | Covers |
|-----------|----------|--------|
| **FAVES evaluator** | `services/worker/src/evaluators/faves_evaluator.py` | Fair / Appropriate / Valid / Effective / Safe — model-level compliance |
| **Dual metrics** | `services/worker/src/validation/dual_metrics_evaluator.py` | Numeric, date, text strict vs tolerant accuracy |
| **Dataset baselines** | `services/worker/src/validation/dataset_baselines.py` | Parquet fingerprint drift detection |
| **Prometheus counters** | `agents/utils/metrics.py` | Runtime latency, success/failure rates, circuit-breaker stats |
| **Governance tests** | `tests/governance/` | PHI redaction, RBAC, fail-closed |

**Gap:** No unified harness that exercises an agent end-to-end with a fixed dataset, records all four key metrics (groundedness, schema validity, latency, cost), and runs the same way locally and in CI.

---

## 2 · Datasets to Collect

Keep datasets small, deterministic, and version-controlled. Store under `tests/eval/datasets/`.

| Dataset | Format | Records | Source | Purpose |
|---------|--------|---------|--------|---------|
| **golden-extractions** | JSONL | 20–30 | Hand-curated from public PubMed abstracts (no PHI) | Ground-truth for `stage2-screen`, `stage2-extract` |
| **golden-synthesis** | JSONL | 10 | Published systematic-review conclusions | Ground-truth for `stage2-synthesize`, `verify` |
| **golden-manuscripts** | JSONL | 5 | Redacted IMRAD sections with expert annotations | Ground-truth for `methods-writer`, `discussion-writer` |
| **schema-corpus** | JSON | 1 per agent | Copied from `CANONICAL_AGENT_TIERING_POLICY.md` output schemas | Schema-validity reference |
| **cost-baseline** | JSON | 1 | Snapshot of token counts × tier pricing | Cost-regression reference |

### JSONL record shape (one line per case)

```jsonl
{"id": "ext-001", "agent": "stage2-extract", "input": { ... }, "expected_output": { ... }, "tags": ["cardiology","rct"]}
```

> **Rule:** Never include real PHI. Use synthetic or published-abstract data only.

---

## 3 · Metrics to Compute

### 3.1 Groundedness

| What | How | Threshold |
|------|-----|-----------|
| Claim-level recall against golden answer | Token-overlap F1 (BERTScore or Rouge-L) between `actual.output` and `expected.output` | F1 ≥ 0.70 |
| Hallucination flag | Any claim in output with no supporting span in the input context → `hallucination_count` | 0 |

Use the lightweight `rouge-score` PyPI package locally; swap in a model-graded check only if Rouge-L proves too noisy.

### 3.2 Schema Validity

| What | How | Threshold |
|------|-----|-----------|
| Output matches declared JSON Schema | `jsonschema.validate(actual, schema)` | 0 errors |
| Required fields populated | Check for `null` / empty string in required fields | 100 % |
| Confidence range | `0.0 ≤ confidence ≤ 1.0` | 100 % |

Schemas are already defined in the tiering policy — extract them into `tests/eval/datasets/schemas/` as standalone `.json` files.

### 3.3 Latency

| What | How | Threshold |
|------|-----|-----------|
| Wall-clock per agent call | `time.perf_counter()` around `agent.run()` | p95 ≤ 30 s (NANO/MINI), ≤ 120 s (FRONTIER) |
| Token throughput | `output_tokens / latency` | Track trend, no hard gate initially |

### 3.4 Cost

| What | How | Threshold |
|------|-----|-----------|
| Estimated cost per call | `(input_tokens × tier_input_rate) + (output_tokens × tier_output_rate)` | ≤ 1.2 × baseline per agent |
| Tier compliance | Agent used correct tier per policy | Must match canonical tier |

Token counts come from the LLM response metadata (`usage.prompt_tokens`, `usage.completion_tokens`).

---

## 4 · Harness Architecture

```
tests/eval/
├── conftest.py              # Pytest fixtures: load datasets, init agents
├── run_eval.py              # CLI entry point (click or argparse)
├── harness.py               # Core loop: run agent → collect metrics → write results
├── metrics/
│   ├── groundedness.py      # Rouge-L / BERTScore wrapper
│   ├── schema_validity.py   # jsonschema validation
│   ├── latency.py           # Wall-clock timing decorator
│   └── cost.py              # Token-count × tier-rate calculator
├── datasets/
│   ├── golden-extractions.jsonl
│   ├── golden-synthesis.jsonl
│   ├── golden-manuscripts.jsonl
│   └── schemas/             # One .json per agent output schema
├── results/                  # gitignored; CI uploads as artifact
│   └── eval_<timestamp>.json
└── README.md
```

### Core loop (pseudo-code)

```python
# harness.py
import json, time, pathlib
from metrics import groundedness, schema_validity, cost

def evaluate(agent_name: str, dataset_path: pathlib.Path, schema_path: pathlib.Path):
    results = []
    for case in _load_jsonl(dataset_path):
        t0 = time.perf_counter()
        actual = invoke_agent(agent_name, case["input"])   # calls real or stubbed agent
        latency_s = time.perf_counter() - t0

        results.append({
            "id":               case["id"],
            "agent":            agent_name,
            "groundedness_f1":  groundedness.rouge_l(actual["output"], case["expected_output"]),
            "schema_errors":    schema_validity.validate(actual, schema_path),
            "latency_s":        round(latency_s, 3),
            "cost_usd":         cost.estimate(actual["usage"], agent_name),
            "passed":           True,   # set False if any threshold breached
        })
    return results
```

---

## 5 · Running Locally vs in CI

### 5.1 Local (developer laptop)

```bash
# One agent, fast feedback
python tests/eval/run_eval.py --agent stage2-extract --dataset tests/eval/datasets/golden-extractions.jsonl

# All agents, full suite
python tests/eval/run_eval.py --all

# Dry-run (schema-validity only, no LLM calls — useful offline)
python tests/eval/run_eval.py --all --dry-run
```

**Dry-run mode** loads pre-recorded responses from `tests/eval/datasets/cached_responses/` so developers can iterate on metric logic without burning tokens.

### 5.2 CI (GitHub Actions)

```yaml
# .github/workflows/eval.yml
name: Agent Eval
on:
  pull_request:
    paths:
      - 'agents/**'
      - 'services/worker/src/agents/**'
      - 'packages/ai-agents/src/**'
      - 'tests/eval/**'
  schedule:
    - cron: '0 6 * * 1'   # weekly Monday 06:00 UTC

jobs:
  eval:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }

      - name: Install deps
        run: pip install -r tests/eval/requirements.txt

      - name: Run eval harness
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          EVAL_MODE: ci           # shorter dataset slice in CI
        run: python tests/eval/run_eval.py --all --output results/

      - name: Upload results artifact
        uses: actions/upload-artifact@v4
        with:
          name: eval-results-${{ github.sha }}
          path: results/

      - name: Gate — fail if thresholds breached
        run: python tests/eval/run_eval.py --check-results results/
```

**CI-specific behaviour:**
- `EVAL_MODE=ci` → harness samples 5 records per dataset (fast, cheap).
- `--check-results` reads the JSON output and exits non-zero if any metric breaches its threshold.
- Results artifact retained for 30 days for trend analysis.

---

## 6 · Phased Roll-Out

| Phase | Scope | Effort | Gate |
|-------|-------|--------|------|
| **P0 — Schema only** | `schema_validity` metric for all 10 canonical agents using existing schemas. No LLM calls needed. | 1 day | CI blocks on schema failures |
| **P1 — Extractions** | Add `golden-extractions.jsonl` (20 records). Wire `groundedness`, `latency`, `cost` for `stage2-screen` + `stage2-extract`. | 2–3 days | PR gate for extraction agents |
| **P2 — Synthesis & Verify** | Add `golden-synthesis.jsonl`. Cover `stage2-synthesize` + `verify`. | 2 days | PR gate for synthesis agents |
| **P3 — Manuscript writers** | Add `golden-manuscripts.jsonl`. Integrate FAVES scores alongside Rouge-L. | 3 days | Advisory (no hard block initially) |
| **P4 — Cost regression** | Baseline token-cost snapshot. CI alerts on > 20 % regression. | 0.5 day | CI warns on cost spike |

---

## 7 · Dependencies (pip)

```
# tests/eval/requirements.txt
jsonschema>=4.20
rouge-score>=0.1.2
click>=8.1
tabulate>=0.9       # pretty-print local results
```

No heavy ML dependencies. BERTScore can be added later behind a `--bert` flag if Rouge-L proves insufficient.

---

## 8 · Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **JSONL datasets, not a database** | Version-controllable, diff-able, no infrastructure |
| **Rouge-L before BERTScore** | Zero model download, fast, good-enough for extraction tasks |
| **Cached responses for dry-run** | Lets devs iterate on metrics offline; avoids token burn |
| **Separate `--check-results` step** | Decouple "run" from "gate" so CI can always upload artifacts even on failure |
| **No custom dashboard (yet)** | Use GitHub Actions artifact + `tabulate` CLI output until volume justifies a dashboard |
| **Schemas extracted from tiering policy** | Single source of truth; policy already defines them |

---

## 9 · Success Criteria

The harness is "done" when:

1. `python tests/eval/run_eval.py --all --dry-run` passes with zero schema errors.
2. CI workflow runs on every PR touching agent code, completes in < 10 min.
3. At least one golden dataset (extractions) is curated and producing groundedness scores.
4. Cost estimation tracks token usage per tier and flags > 20 % regressions.
5. A new contributor can run `make eval` and understand the output without reading this document.
