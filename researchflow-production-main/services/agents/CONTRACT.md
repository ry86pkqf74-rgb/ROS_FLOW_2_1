# Agent HTTP contract

Internal contract for agent services that the orchestrator calls. All agents must implement the same endpoints and shapes so the orchestrator can dispatch and parse responses without drift.

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

### Required fields by event type

- **started:** `data` JSON should include `request_id`, and preferably `task_type`.
- **progress:** `data` may include `percent`, `step`, etc. No strict shape.
- **complete / done / final:** Terminal event. `data` JSON **must** include:
  - `request_id` (string, non-empty)
  - Success indicator: `ok === true` or `status` in `["ok","success"]` or `success === true`
  - `outputs` (object) or `data` (object) — so the orchestrator can persist the result.

The orchestrator treats the last `complete`/`done`/`final` event (or end-of-stream) as the result payload.

## PHI-safe logging rules

- **Do:** Log only identifiers for tracing: `request_id`, `task_type`, `duration_ms`, status codes. No request or response bodies.
- **Do not:** Log `inputs`, `outputs`, or any user/content payloads. Do not log full event payloads or error bodies that might contain PHI.
- **Do not:** Include PHI in error messages or API response bodies (return IDs or codes only where needed).

## Compatibility notes

- The orchestrator expects the **terminal** SSE event to contain an **outputs-equivalent** (e.g. `outputs` or `data` object) so it can store the run result. Without it, stream results cannot be persisted.
- Conformance script: `scripts/check-agent-contract.py` validates sync and stream shapes against this contract (env: `AGENT_CONTRACT_URLS`).
