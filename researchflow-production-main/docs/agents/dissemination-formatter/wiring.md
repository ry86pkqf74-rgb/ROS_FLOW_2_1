# Dissemination Formatter Agent - Wiring Documentation

**Date:** 2026-02-08  
**Branch:** feat/import-dissemination-formatter  
**Status:** ✅ **Wired for Production Deployment**

---

## Summary

The Dissemination Formatter agent converts academic manuscripts into journal-specific, submission-ready formats (LaTeX, Word, text). This LangSmith cloud-hosted agent is accessible via an HTTP proxy service and integrated with the orchestrator router.

---

## Architecture

### Execution Model: LangSmith Cloud via FastAPI Proxy ✅

```
User/UI Request
    ↓
Orchestrator (/api/ai/router/dispatch)
    ↓ [task_type: DISSEMINATION_FORMATTING]
TASK_TYPE_TO_AGENT mapping
    ↓ [resolves to: agent-dissemination-formatter]
    ↓ [agent URL: http://agent-dissemination-formatter-proxy:8000]
FastAPI Proxy (agent-dissemination-formatter-proxy)
    ↓ [transform ResearchFlow → LangSmith format]
LangSmith API (https://api.smith.langchain.com)
    ↓ [executes agent + 5 worker sub-agents]
    ↓ [returns formatted output + validation reports]
FastAPI Proxy
    ↓ [transform LangSmith → ResearchFlow format]
Response (JSON: formatted_manuscript, validation_report, references, cover_letter)
    ↓
Artifact Writer (optional: /data/artifacts/dissemination/)
    ↓
Return to caller
```

---

## Components

### 1. Proxy Service: `agent-dissemination-formatter-proxy`

**Location:** `services/agents/agent-dissemination-formatter-proxy/`

**Docker Service:** `agent-dissemination-formatter-proxy` (compose service)

**Endpoints:**
- `GET /health` - Health check
- `GET /health/ready` - LangSmith connectivity validation
- `POST /agents/run/sync` - Synchronous formatting
- `POST /agents/run/stream` - Streaming formatting (SSE)

**Container Details:**
- Port: 8000 (internal)
- Networks: backend (internal), frontend (LangSmith API access)
- Health check: `/health` every 30s
- Resources: 0.5 CPU / 512MB memory (max)

### 2. Agent Configuration: `agent-dissemination-formatter`

**Location:** `services/agents/agent-dissemination-formatter/`

**Type:** LangSmith custom agent (cloud-hosted, not containerized)

**Worker Sub-Agents:**
1. Journal Guidelines Researcher - Fetches journal formatting requirements
2. Manuscript Formatter - Performs IMRaD conversion and template application
3. Reference Verifier - Cross-checks bibliographic references
4. Cover Letter Drafter - Generates journal-specific cover letters
5. Reviewer Response Formatter - Formats revision responses

---

## Router Registration

### Task Type Mapping

**File:** `services/orchestrator/src/routes/ai-router.ts`

```typescript
const TASK_TYPE_TO_AGENT: Record<string, string> = {
  // ... other agents ...
  DISSEMINATION_FORMATTING: 'agent-dissemination-formatter',  // LangSmith-hosted dissemination formatter (Stage 19)
};
```

### Endpoint Registration

**Environment Variable:** `AGENT_ENDPOINTS_JSON`

```json
{
  "agent-dissemination-formatter": "http://agent-dissemination-formatter-proxy:8000"
}
```

---

## Environment Variables

### Required

```bash
# LangSmith API credentials
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID=<uuid-from-langsmith>
```

### Optional

```bash
# LangSmith configuration
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1
LANGSMITH_DISSEMINATION_FORMATTER_TIMEOUT_SECONDS=240  # 4 minutes

# Logging
LOG_LEVEL=INFO
AGENT_LOG_LEVEL=INFO

# LangChain tracing
LANGCHAIN_PROJECT=researchflow-dissemination-formatter
LANGCHAIN_TRACING_V2=false

# Worker tools (optional - enhances functionality)
TAVILY_API_KEY=tvly-...                # Web search for journal guidelines
GOOGLE_DOCS_API_KEY=...                # Google Docs integration
```

---

## Input/Output Schema

### Input (POST `/api/ai/router/dispatch`)

```json
{
  "task_type": "DISSEMINATION_FORMATTING",
  "request_id": "req-123",
  "mode": "DEMO",
  "inputs": {
    "manuscript_text": "# Introduction\n...",
    "target_journal": "Nature",
    "output_format": "latex",
    "citation_style": "numbered",
    "include_cover_letter": true,
    "verify_references": true
  }
}
```

### Output

```json
{
  "ok": true,
  "request_id": "req-123",
  "outputs": {
    "formatted_manuscript": "\\documentclass{article}...",
    "validation_report": {
      "compliance_checks": [...],
      "issues": [],
      "warnings": []
    },
    "reference_verification_report": {
      "total_references": 25,
      "verified": 24,
      "issues": [...]
    },
    "cover_letter": "Dear Editor,...",
    "google_doc_url": "https://docs.google.com/...",
    "langsmith_run_id": "abc-123"
  }
}
```

### Artifact Paths (Optional)

```
/data/artifacts/dissemination/
├── formatting/
│   ├── req-123/
│   │   ├── formatted.tex
│   │   ├── validation.json
│   │   └── references.json
│   └── manifest.json
```

---

## Deployment Steps

### On ROSflow2 (Hetzner)

```bash
# 1. Navigate to deployment directory
cd /opt/researchflow

# 2. Pull latest code (branch: feat/import-dissemination-formatter)
git fetch --all --prune
git checkout feat/import-dissemination-formatter
git pull --ff-only

# 3. Set environment variables
cat >> .env << 'ENV_EOF'
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID=<uuid-from-langsmith>
ENV_EOF

# 4. Build proxy service
docker compose build agent-dissemination-formatter-proxy

# 5. Start proxy
docker compose up -d agent-dissemination-formatter-proxy

# 6. Wait for healthy
sleep 15

# 7. Verify proxy health
docker compose ps agent-dissemination-formatter-proxy
docker compose exec agent-dissemination-formatter-proxy curl -f http://localhost:8000/health

# 8. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 9. Run preflight checks
./researchflow-production-main/scripts/hetzner-preflight.sh

# 10. Optional: Run smoke test
CHECK_DISSEMINATION_FORMATTER=1 DEV_AUTH=true ./researchflow-production-main/scripts/stagewise-smoke.sh
```

---

## Validation

### Preflight Checks (Mandatory)

**Script:** `scripts/hetzner-preflight.sh`

**Checks:**
- ✅ `LANGSMITH_API_KEY` present in orchestrator environment
- ✅ Task type `DISSEMINATION_FORMATTING` registered in ai-router.ts

**Expected Output:**
```
✓ Dissemination Formatter - LANGSMITH_API_KEY configured
✓ Dissemination Formatter Router - task type registered
```

### Smoke Test (Optional)

**Flag:** `CHECK_DISSEMINATION_FORMATTER=1`

**Script:** `scripts/stagewise-smoke.sh`

**Tests:**
- LANGSMITH_API_KEY configured
- LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID configured
- Router dispatch returns correct agent name
- Proxy container running and healthy
- Artifact directory structure created

**Run:**
```bash
CHECK_DISSEMINATION_FORMATTER=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

**Expected Output:**
```
[13] Dissemination Formatter Agent Check (optional - LangSmith-based)
[13a] Checking LANGSMITH_API_KEY and agent ID configuration
✓ LANGSMITH_API_KEY is configured in orchestrator
✓ LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID is configured in orchestrator
[13b] POST /api/ai/router/dispatch (DISSEMINATION_FORMATTING)
Router dispatch OK: response code 200
✓ Correctly routed to agent-dissemination-formatter
[13c] Checking proxy container health
✓ agent-dissemination-formatter-proxy container is running
✓ Proxy health endpoint responding
[13d] Checking artifacts directory structure
✓ /data/artifacts exists
✓ Wrote validation artifact to /data/artifacts/validation/dissemination-formatter-smoke/...
Dissemination Formatter Agent check complete (optional - does not block)
```

### Manual Test

```bash
# Get auth token
TOKEN="Bearer <your-jwt>"

# Test dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "DISSEMINATION_FORMATTING",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "manuscript_text": "# Introduction\nThis is a test manuscript...",
      "target_journal": "Nature",
      "output_format": "text",
      "citation_style": "numbered",
      "include_cover_letter": true,
      "verify_references": true
    }
  }'
```

**Expected Response:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-dissemination-formatter",
  "agent_url": "http://agent-dissemination-formatter-proxy:8000",
  "request_id": "test-001"
}
```

---

## Files Changed

### Created (6 files)

1. `services/agents/agent-dissemination-formatter-proxy/Dockerfile`
2. `services/agents/agent-dissemination-formatter-proxy/requirements.txt`
3. `services/agents/agent-dissemination-formatter-proxy/app/__init__.py`
4. `services/agents/agent-dissemination-formatter-proxy/app/config.py`
5. `services/agents/agent-dissemination-formatter-proxy/app/main.py`
6. `services/agents/agent-dissemination-formatter-proxy/README.md`

### Modified (3 files)

1. `services/orchestrator/src/routes/ai-router.ts` (+1 line)
   - Added `DISSEMINATION_FORMATTING` task type
2. `docker-compose.yml` (+32 lines)
   - Added `agent-dissemination-formatter-proxy` service
   - Updated `AGENT_ENDPOINTS_JSON` to include formatter
3. `scripts/hetzner-preflight.sh` (+21 lines)
   - Added Dissemination Formatter health checks
4. `scripts/stagewise-smoke.sh` (+119 lines)
   - Added optional formatter validation (CHECK_DISSEMINATION_FORMATTER=1)

### Enhanced (1 file)

5. `docs/agents/dissemination-formatter/wiring.md` (this file)
   - Complete wiring documentation

**Total Changes:** 9 files, ~200 lines added

---

## Troubleshooting

### Issue: 503 on /health/ready

**Cause:** `LANGSMITH_API_KEY` not set or LangSmith API unreachable

**Fix:**
```bash
echo "LANGSMITH_API_KEY=lsv2_pt_..." >> .env
docker compose up -d --force-recreate agent-dissemination-formatter-proxy orchestrator
```

### Issue: Routing failures

**Symptom:** `UNSUPPORTED_TASK_TYPE` error

**Fix:** Verify task type in ai-router.ts
```bash
docker compose exec orchestrator grep "DISSEMINATION_FORMATTING" /app/src/routes/ai-router.ts
```

### Issue: Proxy container not running

**Check:**
```bash
docker compose ps agent-dissemination-formatter-proxy
docker compose logs agent-dissemination-formatter-proxy
```

**Restart:**
```bash
docker compose up -d --force-recreate agent-dissemination-formatter-proxy
```

### Issue: Empty outputs

**Cause:** Invalid LangSmith agent ID or input schema mismatch

**Fix:**
1. Verify agent ID in LangSmith UI
2. Update `LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID` in .env
3. Check input schema matches agent expectations

---

## Related Documentation

- **Agent Config:** `services/agents/agent-dissemination-formatter/README.md`
- **Proxy README:** `services/agents/agent-dissemination-formatter-proxy/README.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`
- **Agent Prompts:** `services/agents/agent-dissemination-formatter/workers/*/AGENTS.md`
- **Proxy Architecture:** `LANGSMITH_PROXY_IMPLEMENTATION_SUMMARY.md` (if exists)

---

## Next Steps

### Immediate

1. ✅ **Proxy service created**
2. ✅ **Docker Compose wiring complete**
3. ✅ **Router registration complete**
4. ✅ **Validation hooks added**
5. ⏳ **Deploy to ROSflow2**
6. ⏳ **Run preflight validation**
7. ⏳ **Optional smoke test**

### Future Enhancements

1. Add retry logic for LangSmith API timeouts
2. Implement caching for journal guidelines
3. Add rate limiting for LangSmith API
4. Create integration test: Manuscript Writer → Dissemination Formatter
5. Add monitoring for formatting success rate

---

**Wiring Date:** 2026-02-08  
**Status:** ✅ **COMPLETE**  
**Branch:** feat/import-dissemination-formatter  
**Next Action:** Deploy to ROSflow2 and run validation
