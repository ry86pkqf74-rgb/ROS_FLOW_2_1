# ResearchFlow Inventory – Capabilities Report

Generated from repo + (optional) `rosflow-inventory.zip` artifacts.  
Focus: dispatch auth, WORKER_SERVICE_TOKEN, and the 10 agent services.

---

## 1. POST /api/ai/router/dispatch – Who Sets `authenticated: false`?

**Component:** Orchestrator **service-auth** middleware.

- **File:** `services/orchestrator/src/middleware/service-auth.ts`
- **Registration:** Applied globally in `services/orchestrator/index.ts` (before security/rate-limit):
  ```ts
  app.use(serviceAuthMiddleware);  // line ~146
  ```
- **Behavior:** On every request it sets `req.auth = { authenticated: false, isServiceToken: false }` by default. Only for **allowlisted** routes and when the request carries the correct service token does it set `authenticated: true` and `isServiceToken: true`. The only allowlisted route is `POST /api/ai/router/dispatch`.

So **the component that sets `authenticated: false`** for `POST /api/ai/router/dispatch` is this same middleware when the request does **not** present a valid service token (or is not on the allowlist).

---

## 2. Header / Token Expected for Dispatch

- **Header name:** `Authorization`
- **Format:** `Bearer <token>` (e.g. `Authorization: Bearer <WORKER_SERVICE_TOKEN value>`)
- **Token source:** Env var `WORKER_SERVICE_TOKEN` in the **orchestrator** process.
- **Where added:** The **orchestrator’s** BullMQ stage worker (Node) adds it when calling dispatch from `services/orchestrator/src/services/workflow-stages/worker.ts`:
  - `getServiceToken()` reads `process.env.WORKER_SERVICE_TOKEN` (orchestrator env).
  - Requests are sent with `'Authorization': \`Bearer ${serviceToken}\`` (e.g. lines ~417, ~859).

So the exact header is **`Authorization: Bearer <WORKER_SERVICE_TOKEN>`**, and it is added by the orchestrator’s internal workflow worker, not by the Python worker.

---

## 3. WORKER_SERVICE_TOKEN in Compose and Container

- **Rendered compose:** In `docker-compose.yml`, the **orchestrator** service has:
  - `env_file: .env`
  - `environment: ... - WORKER_SERVICE_TOKEN=${WORKER_SERVICE_TOKEN}`
  So the variable is **present in the compose spec**; its value comes from the host `.env` at deploy time.
- **Container env:** The token is **not** written into any artifact by the inventory script (env capture is redacted). To confirm it is loaded at runtime on ROSflow2:
  - Run: `docker compose exec -T orchestrator sh -c 'echo ${WORKER_SERVICE_TOKEN:+SET}'`
  - If output is `SET`, the variable is present in the orchestrator container (value remains secret).

Preflight and smoke scripts already check this: `scripts/hetzner-preflight.sh` and `scripts/stagewise-smoke.sh` (step 1.5) verify that `WORKER_SERVICE_TOKEN` is set (in `.env` and/or in the orchestrator container).

---

## 4. The 10 Agent Services – What They Do and Depend On

Defined in `docker-compose.yml`; dispatch uses `AGENT_ENDPOINTS_JSON` in the orchestrator env to resolve agent URLs.

| # | Service name           | Purpose / role                                      | Main dependencies (env / services) |
|---|------------------------|------------------------------------------------------|------------------------------------|
| 1 | **agent-stage2-lit**   | Stage 2 literature review (tier selection, synthesis) | ChromaDB, Ollama (optional), Semantic Scholar, NCBI |
| 2 | **agent-stage2-screen**| Deduplication, inclusion/exclusion, study-type tagging | AI_BRIDGE_URL, WORKER_SERVICE_TOKEN (or AI_BRIDGE_TOKEN) |
| 3 | **agent-stage2-extract** | PICO, endpoints, sample size, key results from papers | AI_BRIDGE_URL, WORKER_SERVICE_TOKEN |
| 4 | **agent-lit-retrieval** | Deterministic literature retrieval (e.g. PubMed)   | NCBI_API_KEY, NCBI_EMAIL |
| 5 | **agent-rag-retrieve** | Chroma vector retrieval → GroundingPack            | ChromaDB URL + auth token, OpenAI (optional) |
| 6 | **agent-policy-review**| Governance & compliance                             | GOVERNANCE_MODE |
| 7 | **agent-rag-ingest**   | Chunk, embed, write to Chroma                       | ChromaDB URL + auth, OpenAI (optional) |
| 8 | **agent-verify**       | Claim verification vs GroundingPack                 | AI_BRIDGE_URL, GOVERNANCE_MODE |
| 9 | **agent-intro-writer** | Section writer (intro); uses AI Bridge + evidence refs | AI_BRIDGE_URL, GOVERNANCE_MODE |
| 10| **agent-methods-writer** | Section writer (methods)                           | AI_BRIDGE_URL, GOVERNANCE_MODE |

**Router task-type → agent mapping** (in `ai-router.ts` `TASK_TYPE_TO_AGENT`):  
`STAGE_2_LITERATURE_REVIEW` → agent-stage2-lit, `STAGE2_SCREEN` → agent-stage2-screen, `STAGE_2_EXTRACT` / `STAGE2_EXTRACT` → agent-stage2-extract, `STAGE2_SYNTHESIZE` → agent-stage2-synthesize, `LIT_RETRIEVAL` → agent-lit-retrieval, `POLICY_REVIEW` → agent-policy-review, `RAG_INGEST` → agent-rag-ingest, `RAG_RETRIEVE` → agent-rag-retrieve, `SECTION_WRITE_INTRO` → agent-intro-writer, `SECTION_WRITE_METHODS` → agent-methods-writer, `SECTION_WRITE_RESULTS` → agent-results-writer, `SECTION_WRITE_DISCUSSION` → agent-discussion-writer, `CLAIM_VERIFY` → agent-verify.

**Gap:** Compose defines **10** agent services. `AGENT_ENDPOINTS_JSON` in compose lists **11** URLs (includes `agent-stage2-synthesize`). There is **no** `agent-stage2-synthesize`, `agent-results-writer`, or `agent-discussion-writer` service in `docker-compose.yml`. So dispatch for `STAGE2_SYNTHESIZE`, `SECTION_WRITE_RESULTS`, or `SECTION_WRITE_DISCUSSION` will either hit a non-existent service (if synthesize URL is used) or fail with `AGENT_NOT_CONFIGURED` (if results/discussion are not in the JSON). See `docs/inventory/validation-gaps.md`.

---

## 5. Other Capabilities (Summary)

- **Orchestrator:** Express API; mounts `/api/ai/router` (ai-router), workflow stages (BullMQ), health, auth, RBAC, audit, etc. Service auth runs first so security/rate-limit can treat internal token calls correctly.
- **Worker (Python):** Stage execution, callbacks; does **not** call `/api/ai/router/dispatch` — the **orchestrator’s** Node BullMQ worker does.
- **Preflight:** `scripts/hetzner-preflight.sh` checks `.env`, `WORKER_SERVICE_TOKEN` length (≥32), and token presence in the orchestrator container.
- **Smoke:** `scripts/stagewise-smoke.sh` step 1.5 verifies `WORKER_SERVICE_TOKEN` before stage 2; fails with clear remediation if missing.

When `rosflow-inventory.zip` is available, compare `compose.rendered.yml` and `env.redacted.by-container.txt` to confirm which env vars (including `WORKER_SERVICE_TOKEN`) are present in each container and that agent endpoints in the rendered compose match the 10 services above.

---

## 6. LangSmith-Hosted Agents

These agents run their core logic on LangSmith cloud but are accessible via local proxy services.

| Agent name | Router task type(s) | Compose service | AGENT_ENDPOINTS_JSON | Status |
|------------|---------------------|-----------------|----------------------|--------|
| `agent-results-interpretation` | `RESULTS_INTERPRETATION`, `STATISTICAL_ANALYSIS` | ✅ `agent-results-interpretation-proxy` | ✅ Included | ✅ **DEPLOYED** |
| `agent-clinical-manuscript` | `CLINICAL_MANUSCRIPT_WRITE` | ❌ None | ❌ Not included | ❌ Dispatch fails: `AGENT_NOT_CONFIGURED` |
| `agent-clinical-section-drafter` | `CLINICAL_SECTION_DRAFT` | ❌ None | ❌ Not included | ❌ Dispatch fails: `AGENT_NOT_CONFIGURED` |

**Required for all three:** `LANGSMITH_API_KEY` in orchestrator env.

### Results Interpretation Agent Details (✅ **DEPLOYED**)

| Property | Value |
|----------|-------|
| Execution model | LangSmith cloud via local proxy |
| Proxy service | `agent-results-interpretation-proxy` |
| Proxy location | `services/agents/agent-results-interpretation-proxy/` |
| Internal URL | `http://agent-results-interpretation-proxy:8000` |
| Router task types | `RESULTS_INTERPRETATION`, `STATISTICAL_ANALYSIS` |
| Config (cloud agent) | `services/agents/agent-results-interpretation/config.json` |
| Sub-workers | 4 (Literature Research, Methodology Audit, Section Draft, Draft Refinement) |
| Domain skills | `clinical-trials`, `survey-analysis` |
| Required env | `LANGSMITH_API_KEY`, `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` |
| Optional env | `LANGSMITH_API_URL`, `LANGSMITH_TIMEOUT_SECONDS`, `GOOGLE_DOCS_API_KEY` |
| Health endpoints | ✅ `/health`, `/health/ready` |
| Networks | `backend` (orchestrator), `frontend` (LangSmith API) |
| Canonical doc | `docs/agents/results-interpretation/wiring.md` |
| Setup guide | `docs/agents/results-interpretation/ENVIRONMENT.md` |
| Validation | `CHECK_RESULTS_INTERPRETATION=1` in `stagewise-smoke.sh` |
| Status | ✅ Fully deployed and integrated |

### Clinical Manuscript Writer (❌ TODO)

**To enable:** Build proxy service similar to `agent-results-interpretation-proxy`.

### Clinical Section Drafter (❌ TODO)

**To enable:** Build proxy service similar to `agent-results-interpretation-proxy`.
