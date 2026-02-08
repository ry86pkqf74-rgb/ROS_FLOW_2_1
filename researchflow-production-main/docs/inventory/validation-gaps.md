# ResearchFlow Inventory – Validation Gaps

Tight, actionable gaps derived from repo (and optionally from `rosflow-inventory.zip`).

---

## 1. WORKER_SERVICE_TOKEN – Preflight / Smoke

- **Gap:** Preflight has two separate blocks that both check `WORKER_SERVICE_TOKEN` (“Environment Configuration” and “Worker Service Token”), which can be redundant and confusing.
- **Action:** Consider merging into a single “Worker service token (dispatch auth)” section: one pass/fail, one remediation block. Keep runtime check (orchestrator container) in the same section.

---

## 2. Agent Endpoints vs Compose Services

- **Gap:** `AGENT_ENDPOINTS_JSON` in `docker-compose.yml` includes `agent-stage2-synthesize`, but there is **no** `agent-stage2-synthesize` service defined in the same file. Dispatch for task type `STAGE2_SYNTHESIZE` will resolve to a URL that no container serves.
- **Action:** Either add an `agent-stage2-synthesize` service to compose and wire it, or remove `agent-stage2-synthesize` from `AGENT_ENDPOINTS_JSON` and remove/remap `STAGE2_SYNTHESIZE` in the router so it does not point at a missing agent.

---

## 3. Task Types Without Configured Agents

- **Gap:** Router maps `SECTION_WRITE_RESULTS` → `agent-results-writer` and `SECTION_WRITE_DISCUSSION` → `agent-discussion-writer`. Neither agent exists in `docker-compose.yml` nor in `AGENT_ENDPOINTS_JSON`. Dispatch for these task types returns 500 `AGENT_NOT_CONFIGURED`.
- **Action:** Either add `agent-results-writer` and `agent-discussion-writer` services and add them to `AGENT_ENDPOINTS_JSON`, or remove/remap these task types so they are not dispatched to non-existent agents.

---

## 4. Dispatch 403 vs 401

- **Gap:** Scripts and comments say “403 on POST /api/ai/router/dispatch if missing” token. The handler returns **401** when `!user` (no session and no valid service token). RBAC/security may return 403 in other cases. Clarifying which code path returns 403 would avoid confusion.
- **Action:** In `service-auth.ts` or the dispatch handler, document or log when 401 (missing/invalid auth) vs 403 (forbidden) is returned; align preflight/smoke messages with actual status codes.

---

## 5. Inventory Zip – Optional Checks When Available

- **Gap:** Without the zip, we cannot confirm that `WORKER_SERVICE_TOKEN` is present in the orchestrator container at runtime or that rendered compose matches the repo.
- **Action:** On ROSflow2, run `scripts/capture-rosflow-inventory.sh`, then re-run this inventory report using the zip. Confirm in `env.redacted.by-container.txt` that `WORKER_SERVICE_TOKEN=<redacted>` appears for the orchestrator, and in `compose.rendered.yml` that orchestrator env includes `WORKER_SERVICE_TOKEN` and that agent endpoints match the 10 (or 11) agents you intend to run.
