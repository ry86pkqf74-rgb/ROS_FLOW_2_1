# Results Interpretation Agent — Wiring Reference

**Canonical doc.** All other docs (AGENT_RESULTS_INTERPRETATION_BRIEFING.md,
WORKFLOW_INTEGRATION.md) are supplementary and defer to this file for deploy
and routing truth.

**Last verified:** 2026-02-08  
**Branch:** `chore/inventory-capture`
**Status:** ✅ **IMPLEMENTED** - Proxy service deployed

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
3. Router looks up agent name in `AGENT_ENDPOINTS_JSON` →
   `http://agent-results-interpretation-proxy:8000`.
4. Proxy service transforms request and forwards to LangSmith API.
5. LangSmith executes cloud-hosted agent and returns results.
6. Proxy transforms response to ResearchFlow format and returns.

---

## 3. Deployment (Hetzner / Docker Compose)

### Execution Model: **LangSmith Cloud via Local Proxy**

The core agent logic runs on **LangSmith cloud**, but ResearchFlow includes a
**local proxy service** (`agent-results-interpretation-proxy`) that:
- Adapts ResearchFlow agent contract to LangSmith API format
- Provides health checks and monitoring
- Handles authentication and error translation
- Maintains ResearchFlow's standard agent interface

| Property | Value |
|----------|-------|
| **Core Agent** | LangSmith cloud-hosted (no local container) |
| **Proxy Service** | `agent-results-interpretation-proxy` |
| Compose service | ✅ `agent-results-interpretation-proxy` |
| Image | Built from `services/agents/agent-results-interpretation-proxy/` |
| Internal port | 8000 |
| Published port | None (internal only) |
| Healthcheck | ✅ `/health`, `/health/ready` |
| Networks | `backend` (orchestrator), `frontend` (LangSmith API) |
| Volumes / `/data` | None (reports go to Google Docs) |

### Required Environment Variables

See [`ENVIRONMENT.md`](./ENVIRONMENT.md) for complete setup instructions.

**Required:**
- `LANGSMITH_API_KEY` - LangSmith API key (format: `<your-langsmith-api-key>`)
- `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` - Assistant UUID from LangSmith

**Optional:**
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `180` (3 minutes)
- `LANGCHAIN_PROJECT` - Default: `researchflow-results-interpretation`
- `LANGCHAIN_TRACING_V2` - Default: `false`

### Setup Instructions

1. **Get LangSmith credentials:**
   - Log in to https://smith.langchain.com/
   - Navigate to **Agents** → **Results Interpretation Agent**
   - Copy the **Agent ID** (UUID)
   - Generate an **API Key** if needed

2. **Add to `.env` file:**
   ```bash
   LANGSMITH_API_KEY=<your-langsmith-api-key>
   LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=YOUR_AGENT_UUID_HERE
   ```

3. **Deploy services:**
   ```bash
   docker compose build agent-results-interpretation-proxy
   docker compose up -d --force-recreate orchestrator agent-results-interpretation-proxy
   ```

4. **Verify:**
   ```bash
   # Check proxy health
   docker compose exec agent-results-interpretation-proxy curl -f http://localhost:8000/health
   
   # Check LangSmith connectivity
   docker compose exec agent-results-interpretation-proxy curl -f http://localhost:8000/health/ready
   ```

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
| Format | `<your-langsmith-api-key>` |
| Used by | `agent-results-interpretation-proxy` service |
| Agent ID | `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` (UUID) |

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

Preflight checks verify:

1. `LANGSMITH_API_KEY` is set in orchestrator
2. `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` is set in proxy
3. `RESULTS_INTERPRETATION` task type is registered in router
4. Proxy service is healthy and can reach LangSmith API
5. Agent is present in `AGENT_ENDPOINTS_JSON`

```bash
# Check proxy container is running
docker compose ps agent-results-interpretation-proxy

# Check proxy health
docker compose exec -T agent-results-interpretation-proxy curl -f http://localhost:8000/health

# Check LangSmith connectivity
docker compose exec -T agent-results-interpretation-proxy curl -f http://localhost:8000/health/ready

# Check LANGSMITH_API_KEY in orchestrator
docker compose exec -T orchestrator sh -c 'echo ${LANGSMITH_API_KEY:+SET}'
# Expected: SET

# Check agent in AGENT_ENDPOINTS_JSON
docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep results-interpretation
# Expected: "agent-results-interpretation":"http://agent-results-interpretation-proxy:8000"
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

1. **Proxy container not running** — Check:
   `docker compose ps agent-results-interpretation-proxy`
   Fix: `docker compose up -d agent-results-interpretation-proxy`

2. **`503 Service Unavailable` on /health/ready** —
   `LANGSMITH_API_KEY` or `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` not set.
   Check proxy logs: `docker compose logs agent-results-interpretation-proxy`
   Add missing vars to `.env` and recreate:
   `docker compose up -d --force-recreate agent-results-interpretation-proxy`

3. **`AGENT_NOT_CONFIGURED` on dispatch** — Agent not in `AGENT_ENDPOINTS_JSON`.
   This should not occur after deployment (it's now included).
   Verify: `docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep results-interpretation`
   Fix: Recreate orchestrator: `docker compose up -d --force-recreate orchestrator`

4. **`401 Unauthorized` from LangSmith** — Invalid or expired API key.
   Generate new key from https://smith.langchain.com/ → Settings → API Keys

5. **`404 Not Found` from LangSmith** — Invalid `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID`.
   Verify agent ID in LangSmith UI: Agents → Results Interpretation Agent

6. **Schema mismatch** — The agent expects `results_data` (string) and
   `study_metadata` (object).  Sending a flat string without metadata
   will still work but produces less specific interpretation.

7. **Google Docs API failure** — Agent uses `GOOGLE_DOCS_API_KEY` to
   create reports.  If not set, report creation fails but interpretation
   still returns in the response body.

8. **Timeout (> 3 min)** — Full pipeline with all 4 workers can take
   120-180s.  Increase `LANGSMITH_TIMEOUT_SECONDS` to 300 (5 minutes) or
   disable refinement workers in LangSmith agent config.

9. **Network errors** — Proxy needs `frontend` network for LangSmith API.
   Check: `docker network inspect researchflow-production-main_frontend`
   Ensure proxy is connected: should show `agent-results-interpretation-proxy`
