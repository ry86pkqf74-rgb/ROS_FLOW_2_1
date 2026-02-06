# E2E and contract tests

## Python contract tests

- **`test_api_endpoints.py`** – Orchestrator HTTP API contract (health, etc.). Uses `ORCHESTRATOR_URL` (default `http://localhost:3001`).
- **`test_agent_stream_contract.py`** – Agent stream contract: `POST /agents/run/stream` must emit exactly one terminal event with `request_id`, `task_type`, and final payload (`status`, `outputs`). Prevents regressions on “terminal event missing request_id”.

### Running the agent stream contract test locally

1. Start the agent (e.g. agent-stage2-lit):

   ```bash
   # From repo root (agent must be reachable on host; if using Docker, ensure
   # agent-stage2-lit has a port mapping, e.g. ports: ["8000:8000"], or run
   # the test from a container on the same network)
   docker compose up -d agent-stage2-lit
   ```

   Or run the agent process directly (e.g. from `services/agents/agent-stage2-lit`):

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

2. Run the test (default base URL `http://localhost:8000`):

   ```bash
   pytest tests/e2e/test_agent_stream_contract.py -v
   ```

   With a custom base URL:

   ```bash
   AGENT_STREAM_BASE_URL=http://localhost:8000 pytest tests/e2e/test_agent_stream_contract.py -v
   ```

   If the agent is not reachable, the test is skipped.

## Playwright E2E

See repo root `package.json` for `test:e2e` and Playwright configuration.
