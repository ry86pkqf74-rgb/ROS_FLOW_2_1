# Evaluation Harness

Automated evaluation for ResearchFlow agents. See [EVAL_HARNESS_ROADMAP.md](../../EVAL_HARNESS_ROADMAP.md) for full design.

## Quick Start

```bash
# Install deps
pip install -r requirements.txt

# P0: Schema-only validation (no agents needed, no LLM calls)
python run_eval.py --all --dry-run

# Single agent with dataset
python run_eval.py --agent stage2-extract --dataset datasets/golden-extractions.jsonl

# Check saved results
python run_eval.py --check-results results/
```

## Structure

```
tests/eval/
├── run_eval.py          # CLI entry point
├── harness.py           # Core evaluation loop
├── conftest.py          # Pytest fixtures
├── metrics/
│   ├── schema_validity.py   # JSON Schema validation (P0)
│   ├── latency.py           # Wall-clock timing
│   ├── groundedness.py      # Rouge-L F1 scoring
│   └── cost.py              # Token cost estimation
├── datasets/
│   └── schemas/             # One .json per agent
└── results/                 # gitignored; CI uploads as artifact
```

## Phases

| Phase | What | Status |
|-------|------|--------|
| P0 — Schema only | Validate response shapes, no LLM | ✅ This PR |
| P1 — Extractions | Golden dataset + groundedness | 🔜 Next |
| P2 — Synthesis   | Cover synthesize + verify | Planned |
| P3 — Manuscripts | FAVES + Rouge-L for writers | Planned |
| P4 — Cost        | Baseline + regression alerts | Planned |
