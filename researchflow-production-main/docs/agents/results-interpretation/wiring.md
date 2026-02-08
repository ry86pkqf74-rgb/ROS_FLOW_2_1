# Results Interpretation Agent — Wiring Reference

**Canonical doc.** All other docs (AGENT_RESULTS_INTERPRETATION_BRIEFING.md,
WORKFLOW_INTEGRATION.md) are supplementary and defer to this file for deploy
and routing truth.

**Last verified:** 2026-02-08  
**Branch:** `chore/inventory-capture`

---

## 1. What It Is / When It Runs

The **Results Interpretation Agent** is a LangSmith-hosted multi-agent system
that interprets research results across clinical, social-science, behavioural,
and survey domains.  It produces a structured 4-section report (Findings,
Statistical Assessment, Bias & Limitations, Implications), optionally enriched
by 4 sub-workers (Literature Research, Methodology Audit, Section Draft, Draft
Refinement), and saves the output to Google Docs.

| Attribute | Value |
|-----------|-------|
| Agent ID | `agent-results-interpretation` |
| Source | LangSmith Agent Builder |
| Config file | `services/agents/agent-results-interpretation/config.json` |
| Prompt file | `services/agents/agent-results-interpretation/AGENTS.md` |
| Tools | `services/agents/agent-results-interpretation/tools.json` |
| Sub-workers | 4 — in `subagents/` |
| Domain skills | `skills/clinical-trials/`, `skills/survey-analysis/` |

---

## 2. How It Is Invoked

### Router Task Types (ai-router.ts)

| Task type | Maps to agent name | Notes |
|-----------|--------------------|-------|
| `RESULTS_INTERPRETATION` | `agent-results-interpretation` | Primary |
| `STATISTICAL_ANALYSIS` | `agent-results-interpretation` | Alias |

Both are registered in
`services/orchestrator/src/routes/ai-router.ts` (lines 242-243).

### Workflow Stage

Not bound to a specific workflow stage today.  Planned for Stages 7-9
(Results Analysis → Synthesis → Refinement) but that wiring does not exist
yet.

### Current Invocation Path

1. Caller sends `POST /api/ai/router/dispatch` with
   `task_type: "RESULTS_INTERPRETATION"`.
2. Router resolves agent name → `agent-results-interpretation`.
3. Router looks up agent name in `AGENT_ENDPOINTS_JSON`.
4. **Gap:** `agent-results-interpretation` is **not** present in
   `AGENT_ENDPOINTS_JSON` today.  Dispatch returns
   `500 AGENT_NOT_CONFIGURED`.

To make dispatch succeed, add the agent to `AGENT_ENDPOINTS_JSON` in
the orchestrator `.env`.  Because this agent runs on LangSmith (not a local
container), the URL should point to a future LangSmith proxy endpoint or a
local adapter service.  Until that adapter is built, the agent can only be
invoked directly via the LangSmith API.

---

## 3. Deployment (Hetzner / Docker Compose)

### Execution Model: **LangSmith Cloud (not containerised)**

There is **no** Docker service, **no** Dockerfile, and **no** docker-compose
entry for this agent.  It follows the same pattern as:
- `agent-clinical-manuscript` (Clinical Manuscript Writer)
- `agent-clinical-section-drafter` (Clinical Section Drafter)

| Property | Value |
|----------|-------|
| Compose service | **None** |
| Image / `${IMAGE_TAG}` | N/A |
| Internal port | N/A |
| Published port | N/A |
| Healthcheck | N/A (cloud-hosted) |
| Volumes / `/data` | N/A |

### What Is Needed to Enable

1. **Option A — LangSmith direct:** Call the LangSmith API from a
   dedicated dispatcher in the orchestrator (see
   `WORKFLOW_INTEGRATION.md §2.2 LangSmith Bridge` for the planned
   design).
2. **Option B — Local adapter:** Create a thin FastAPI service that
   proxies to LangSmith, add it to `docker-compose.yml`, and register
   it in `AGENT_ENDPOINTS_JSON`.
3. **Option C — Full containerisation:** Reimplement agent logic locally
   with LangGraph, add Dockerfile + compose service.

None of these options are implemented today.

---

## 4. Auth

### Service-to-service (internal dispatch)

| Property | Value |
|----------|-------|
| Middleware | `requireAnalyzeOrServiceToken` (ai-router.ts line 21) |
| Header | `Authorization: Bearer <WORKER_SERVICE_TOKEN>` |
| Token env var | `WORKER_SERVICE_TOKEN` (orchestrator process) |
| When `isServiceToken` is true | Bypasses RBAC, proceeds to dispatch |

### User auth

| Property | Value |
|----------|-------|
| Required | Yes — `ANALYZE` permission (if not using service token) |
| JWT | Standard user JWT validated by auth middleware |

### LangSmith auth (cloud)

| Property | Value |
|----------|-------|
| Env var | `LANGSMITH_API_KEY` |
| Format | `lsv2_pt_...` |
| Used by | Future LangSmith dispatcher (not yet built) |

---

## 5. Inputs / Outputs

### Minimal Request (via router dispatch)

```json
{
  "task_type": "RESULTS_INTERPRETATION",
  "request_id": "smoke-ri-001",
  "mode": "DEMO",
  "inputs": {
    "results_data": "RCT N=200, primary endpoint HR=0.72 (95% CI 0.58-0.89, p=0.003)",
    "study_metadata": {
      "study_type": "RCT",
      "domain": "clinical",
      "data_types": "quantitative"
    }
  }
}
```

### Minimal Response (expected from LangSmith agent)

```json
{
  "report": {
    "study_overview": {
      "study_type": "RCT",
      "domain": "clinical",
      "data_types": "quantitative"
    },
    "findings": "300-500 word narrative ...",
    "statistical_assessment": "300-500 word narrative ...",
    "bias_limitations": "300-500 word narrative ...",
    "implications": "300-500 word narrative ...",
    "quality_scores": {
      "findings":  { "clarity": 9, "accuracy": 8, "bias": 9 },
      "statistical_assessment": { "clarity": 8, "accuracy": 9, "bias": 8 }
    },
    "confidence_rating": {
      "level": "Moderate",
      "rationale": "Adequate sample; borderline significance."
    }
  },
  "google_doc_url": "https://docs.google.com/document/d/...",
  "metadata": {
    "workers_used": ["section_draft", "draft_refinement"],
    "processing_time_ms": 45000
  }
}
```

### Artifact Outputs

No local artifacts.  Reports are saved to **Google Docs** by the agent
(via `google_docs_create_document` tool on LangSmith).  No `/data/artifacts/`
writes occur.

---

## 6. How to Validate

### Preflight (hetzner-preflight.sh)

Since the agent is cloud-hosted, preflight checks verify:

1. `LANGSMITH_API_KEY` is set in the orchestrator container.
2. `RESULTS_INTERPRETATION` task type is present in `ai-router.ts`.

```bash
# Check LANGSMITH_API_KEY
docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}'
# Expected: SET

# Check router registration
docker compose exec -T orchestrator grep -c "RESULTS_INTERPRETATION" \
  /app/src/routes/ai-router.ts
# Expected: 1 (or more)
```

### Smoke (stagewise-smoke.sh)

Enable with `CHECK_RESULTS_INTERPRETATION=1`:

```bash
CHECK_RESULTS_INTERPRETATION=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

The smoke check performs:

1. Verifies `LANGSMITH_API_KEY` is set in orchestrator.
2. Sends `POST /api/ai/router/dispatch` with
   `task_type: "RESULTS_INTERPRETATION"`.
3. Asserts HTTP 200 and `agent_name == "agent-results-interpretation"`.

**Note:** The smoke test does NOT call the LangSmith API directly (API key
must not be exposed in scripts).  Full end-to-end validation requires
running the LangSmith agent manually or through the planned dispatcher.

---

## 7. Common Failures + Where to Look

1. **`AGENT_NOT_CONFIGURED` on dispatch** — `agent-results-interpretation`
   is not in `AGENT_ENDPOINTS_JSON`.  This is the expected state until a
   LangSmith proxy/adapter is built.  Check with:
   `docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep results-interpretation`

2. **`LANGSMITH_API_KEY` not set** — LangSmith integration will fail.
   Add `LANGSMITH_API_KEY=lsv2_pt_...` to `.env` and recreate
   orchestrator.

3. **Schema mismatch** — The agent expects `results_data` (string) and
   `study_metadata` (object).  Sending a flat string without metadata
   will still work but produces less specific interpretation.

4. **Google Docs API failure** — Agent uses `GOOGLE_DOCS_API_KEY` to
   create reports.  If not set, report creation fails but interpretation
   still returns in the response body.

5. **Timeout (> 5 min)** — Full pipeline with all 4 workers can take
   120-180s.  If the dispatcher timeout is too low, set
   `skip_refinement: true` in the config to reduce processing time.
