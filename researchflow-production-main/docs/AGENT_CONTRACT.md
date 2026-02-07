# Agent HTTP contract (unified envelope)

All FastAPI agents under `services/agents/` (template and concrete agents) use a single JSON envelope and shared types so the orchestrator can call any agent without drift.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe. JSON must include `status` (string). |
| GET | `/health/ready` | Readiness probe. JSON must include `status` (string). |
| POST | `/agents/run/sync` | Synchronous run. Request/response use the envelope below. |
| POST | `/agents/run/stream` | Streaming run (SSE). Request body same as sync; terminal event must match envelope shape. |

## Request envelope: `AgentRunRequest`

Same JSON body for both sync and stream:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `request_id` | string | yes | Trace id (non-empty). |
| `task_type` | string | yes | Agent task type (e.g. `LIT_RETRIEVAL`, `POLICY_REVIEW`). |
| `workflow_id` | string | no | Optional workflow id. |
| `stage_id` | string | no | Optional stage id. |
| `user_id` | string | no | Optional user id. |
| `mode` | string | no | e.g. `DEMO`, `LIVE` (default `DEMO`). |
| `risk_tier` | string | no | e.g. `NON_SENSITIVE`. |
| `domain_id` | string | no | e.g. `clinical`. |
| `inputs` | object | no | Task-specific inputs. |
| `budgets` | object | no | Optional token/time limits. |

## Response envelope: `AgentRunResponse`

**POST /agents/run/sync** always returns this JSON shape (success or business error). Do not return a different envelope for errors; use `status: "error"` and `error` instead.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | string | yes | `"ok"` or `"success"` for success; `"error"` for business failure. |
| `request_id` | string | yes | Echo of request id. |
| `outputs` | object | yes | Task results. May be `{}` when `status === "error"`. |
| `artifacts` | array of string | no | Optional artifact IDs/paths. |
| `provenance` | object | no | Optional provenance metadata. |
| `usage` | object | no | Optional token/duration usage. |
| `grounding` | GroundingPack | no | Optional citations/sources (see below). |
| `error` | AgentError | no | Set when `status === "error"`. |

## AgentError (when status is not ok)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | yes | Error code (e.g. `VALIDATION_ERROR`, `TASK_FAILED`). |
| `message` | string | yes | Human-readable message (no PHI). |
| `details` | object | no | Optional extra context. |

## GroundingPack schema

Shared structure for RAG/retrieval citations and sources. Optional on `AgentRunResponse`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sources` | array of object | no | Source documents or references. |
| `citations` | array of string | no | Citation keys or IDs. |
| `span_refs` | array of object | no | Optional span references into sources. |

## Conformance check

Run the contract checker (validates JSON keys and types for `/health`, `/health/ready`, and `/agents/run/sync` / stream):

```bash
cd researchflow-production-main
export AGENT_CONTRACT_TARGETS="http://localhost:8000=LIT_RETRIEVAL,http://localhost:8001=POLICY_REVIEW"
python3 scripts/check-agent-contract.py
```

Exit code 0 = all targets pass; 1 = at least one check failed. Start agents first (e.g. `uvicorn app.main:app --port 8000` in each agent directory).

## Pydantic models (template and agents)

Defined in each agent’s `agent/schemas.py` (aligned with this doc):

- `AgentRunRequest`
- `AgentRunResponse` (includes optional `grounding: GroundingPack`, `error: AgentError`)
- `AgentError`
- `GroundingPack`

See also: `services/agents/CONTRACT.md` for SSE/stream details and PHI-safe logging rules.
