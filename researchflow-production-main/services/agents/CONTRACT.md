# Agent HTTP contract

Internal contract for agent services that the orchestrator calls. For the **unified JSON envelope**, **AgentRunResponse**, **AgentError**, and **GroundingPack** schema see [docs/AGENT_CONTRACT.md](../../docs/AGENT_CONTRACT.md). All agents must implement the same endpoints and shapes so the orchestrator can dispatch and parse responses without drift.

## Overview + endpoints

- **POST** `{base}/agents/run/sync` — Synchronous run. Request body: JSON. Response: JSON.
- **POST** `{base}/agents/run/stream` — Streaming run (SSE). Request body: same JSON. Response: `text/event-stream`.

Agents may reject unsupported `task_type` with a 4xx response and a contract-shaped error body (e.g. `request_id`, `ok: false`, `outputs`, `warnings`).

## Request schema

Same JSON body for both endpoints.

| Field        | Required | Type   | Description                    |
|-------------|----------|--------|--------------------------------|
| `request_id`| yes      | string | Trace id (non-empty)          |
| `task_type` | yes      | string | Agent task type               |
| `workflow_id` | no     | string | Optional workflow id          |
| `stage_id`  | no       | string | Optional stage id             |
| `user_id`   | no       | string | Optional user id              |
| `mode`      | no       | string | e.g. `DEMO`, `LIVE` (default `DEMO`) |
| `risk_tier` | no       | string | e.g. `NON_SENSITIVE`          |
| `domain_id` | no       | string | e.g. `clinical`               |
| `inputs`    | no       | object | Task-specific inputs         |
| `budgets`   | no       | object | Optional token/time limits    |

## Sync response shape

Response must be JSON with:

- **`request_id`** (string, non-empty) — echo of request.
- **`outputs`** (object) — task results. May be empty `{}` but must be present.
- **Success indicator** — one of:
  - **Canonical:** `status` (string) in `["ok", "success"]`, or
  - **Accepted:** `ok` (boolean) `=== true`.

Both styles are accepted for compatibility. Canonical preference: use `status: "ok"` and `outputs` so all agents align with `AgentRunResponse` (see template `agent/schemas.py`).

Optional but recommended: `artifacts`, `provenance`, `usage`, `warnings`.

## SSE format

- **Content-Type:** `text/event-stream`.
- **Framing:** One or more events. Each event has:
  - `event:` line (event type, e.g. `started`, `progress`, `final`, `complete`, `done`).
  - `data:` line(s) — UTF-8 JSON. Multiple `data:` lines are concatenated (newline-separated) into a single JSON value.
  - Empty line ends the event.

### Stream invariant: single terminal event

- **Exactly one terminal event per stream** — the **last** event in the stream is the terminal event.
- Every terminal event **must** include: `request_id`, `task_type`, `status`, a success indicator, and `outputs` or `data`.
- Do not emit a trailing event (e.g. a second `complete` without `request_id`) after the terminal event. Emit exactly one terminal event (e.g. `final`) with all required fields.

### Required fields by event type

- **started:** `data` JSON should include `request_id`, and preferably `task_type`.
- **progress:** `data` may include `percent`, `step`, etc. No strict shape.
- **complete / done / final:** Terminal event. `data` JSON **must** include:
  - `request_id` (string, non-empty)
  - `task_type` (string, non-empty)
  - `status` (string, e.g. `"ok"` or `"success"`)
  - Success indicator: `ok === true` or `status` in `["ok","success"]` or `success === true`
  - `outputs` (object) or `data` (object) — so the orchestrator can persist the result.

The conformance script treats the **last** SSE event as the terminal event and validates it has `request_id`, `task_type`, and `status`.

## PHI-safe logging rules

- **Do:** Log only identifiers for tracing: `request_id`, `task_type`, `duration_ms`, status codes. No request or response bodies.
- **Do not:** Log `inputs`, `outputs`, or any user/content payloads. Do not log full event payloads or error bodies that might contain PHI.
- **Do not:** Include PHI in error messages or API response bodies (return IDs or codes only where needed).

## Compatibility notes

- The orchestrator expects the **terminal** SSE event to contain an **outputs-equivalent** (e.g. `outputs` or `data` object) so it can store the run result. Without it, stream results cannot be persisted.
- Conformance script: `scripts/check-agent-contract.py` validates sync and stream shapes against this contract.

### Running the stream contract check locally

1. **Script (requires running agents):**
   ```bash
   cd researchflow-production-main
   export AGENT_CONTRACT_TARGETS="http://localhost:8000=LIT_RETRIEVAL,http://localhost:8001=POLICY_REVIEW"
   python3 scripts/check-agent-contract.py
   ```
   Start the agent(s) first (e.g. `uvicorn app.main:app --port 8000` in each agent directory). Exit code 0 = pass, 1 = fail.

2. **Unit test (agent-rag-retrieve):**
   ```bash
   cd researchflow-production-main/services/agents/agent-rag-retrieve
   pip install -r requirements.txt
   python3 -m pytest tests/test_contract.py -v
   ```
   Or include in `AGENT_CONTRACT_TARGETS` for the script:
   `AGENT_CONTRACT_TARGETS=...,http://agent-rag-retrieve:8000=RAG_RETRIEVE`

4. **Unit test (agent-lit-retrieval):**
   ```bash
   cd researchflow-production-main/services/agents/agent-lit-retrieval
   pip install -r requirements.txt
   python3 -m pytest tests/test_contract.py::test_stream_terminal_event_has_request_id_task_type_status -v
   ```
   This test fails if: the stream does not have exactly one terminal event, the last event is not terminal, or the terminal event is missing `request_id`, `task_type`, or `status`.
