# Docker Model CLI Test and Agent Improvements

## Docker model CLI test (2026-02-05)

- **`docker model --help`** – Succeeds; CLI is available.
- **`docker model list`** – Succeeds (with Docker daemon access). Listed models: `devstral-small-2`, `ministral3-vllm`, `qwen3-coder`, `qwen3-embedding-vllm`.
- **`docker model run qwen3-coder "<prompt>"`** – Runs but **model load + inference can exceed 90s** (qwen3-coder ~16GB). For automation, use a longer timeout, run in background with `-d`, or use a smaller model (e.g. after `docker model pull ai/smollm2:360M-Q4_K_M`).

So the Docker model workflow (list, pull, run) is valid; `run` with a large model is slow for short-lived scripts.

## Improvements applied (aligned with code-review goals)

These were applied to **agent-lit-retrieval** as the kind of improvements a code-review model (e.g. qwen3-coder) would suggest:

1. **Request ID and duration in logs and response**
   - Log lines now include `request_id` and `duration_ms` for tracing (e.g. `LIT_RETRIEVAL completed request_id=... count=... duration_ms=...`).
   - Sync response `outputs` include `duration_ms`.

2. **Contract-shaped 400 response**
   - For invalid `task_type`, the handler returns HTTP 400 with a JSON body (under FastAPI’s `detail`) with `ok: false`, `request_id`, `task_type`, and `warnings`, so the orchestrator can parse errors consistently.

3. **Retrieval timeout**
   - `run_lit_retrieval(..., timeout_seconds=60)` (configurable via `LIT_RETRIEVAL_TIMEOUT_SECONDS`) wraps the PubMed call in `asyncio.wait_for`. On timeout, the agent returns empty papers and a warning instead of hanging.

4. **Contract test**
   - `test_sync_rejects_wrong_task_type` now asserts the 400 response has contract-shaped `detail` (e.g. `request_id`, `ok: false`).

## How to run tests

From the repo root or this directory, with dependencies installed (e.g. in a venv):

```bash
cd researchflow-production-main/services/agents/agent-lit-retrieval
pip install -r requirements.txt pytest
python -m pytest tests/ -v
```

## Using a Docker model for future improvements

To have a model generate more suggestions:

```bash
# Optional: pull a small model for faster runs
docker model pull ai/smollm2:360M-Q4_K_M

# Run with a prompt (allow 2–3 minutes for large models)
docker model run qwen3-coder "Review app/main.py and app/retrieval.py. Suggest 2 concrete code improvements with snippets."
```

Or run in the background and connect via OpenAI-compatible URL:

```bash
docker model run -d --openaiurl http://localhost:8080/v1 qwen3-coder
```
