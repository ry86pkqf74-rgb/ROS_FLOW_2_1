# LangSmith Proxy Agents - Deployment Guide

**Date:** 2026-02-08  
**Status:** Production Ready  
**Architecture:** HTTP Proxy Pattern

---

## Overview

Three ResearchFlow agents are hosted on LangSmith cloud and accessed via local FastAPI proxy services. This architecture provides:

- ✅ **Architectural consistency** - All agents are HTTP services
- ✅ **Health monitoring** - Standard `/health` and `/health/ready` endpoints
- ✅ **Local development** - Can mock LangSmith for testing
- ✅ **Retry/timeout management** - Handled in proxy layer
- ✅ **Request/response transformation** - ResearchFlow ↔ LangSmith format

---

## Proxy Services

| Agent | Proxy Service | Config Bundle | Task Type |
|-------|---------------|---------------|-----------|
| Results Interpretation | `agent-results-interpretation-proxy` | `services/agents/agent-results-interpretation/` | `RESULTS_INTERPRETATION` |
| Clinical Manuscript Writer | `agent-clinical-manuscript-proxy` | `services/agents/agent-clinical-manuscript/` | `CLINICAL_MANUSCRIPT_WRITE` |
| Clinical Section Drafter | `agent-section-drafter-proxy` | `agents/Clinical_Study_Section_Drafter/` | `CLINICAL_SECTION_DRAFT` |

---

## Architecture

```
┌─────────────┐
│ Orchestrator│
└──────┬──────┘
       │ HTTP POST /api/ai/router/dispatch
       │ {"task_type": "CLINICAL_MANUSCRIPT_WRITE", ...}
       ▼
┌─────────────────────────────────┐
│ agent-clinical-manuscript-proxy │ ◄── FastAPI proxy service
│ (Docker container)              │     (ResearchFlow contract)
└──────────┬──────────────────────┘
           │ HTTPS POST /assistants/{id}/invoke
           │ Transform: ResearchFlow → LangSmith format
           ▼
    ┌──────────────┐
    │ LangSmith API│ ◄── Cloud-hosted agent
    │ (External)   │     (Multi-agent execution)
    └──────────────┘
```

**Key Points:**
- Proxy runs in Docker on your infrastructure
- LangSmith agent runs on LangSmith cloud
- Proxy handles request/response transformation
- All communication is HTTPS with API key auth

---

## Prerequisites

### 1. LangSmith Account

You need:
- **API Key** - Get from https://smith.langchain.com/settings
  - Format: `lsv2_pt_...`
- **Agent IDs** - UUID for each agent (from LangSmith UI)
  - Results Interpretation: `<uuid>`
  - Clinical Manuscript Writer: `<uuid>`
  - Clinical Section Drafter: `<uuid>`

### 2. Environment Variables

Add to orchestrator `.env` file:

```bash
# LangSmith API key (shared by all proxies)
LANGSMITH_API_KEY=lsv2_pt_YOUR_KEY_HERE

# Agent IDs (unique per agent)
LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=uuid-from-langsmith
LANGSMITH_MANUSCRIPT_AGENT_ID=uuid-from-langsmith
LANGSMITH_SECTION_DRAFTER_AGENT_ID=uuid-from-langsmith

# Optional configuration
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1  # Default
LANGSMITH_TIMEOUT_SECONDS=180                              # Default (180-300)
LANGCHAIN_PROJECT=researchflow                             # LangSmith project name
LANGCHAIN_TRACING_V2=false                                 # Enable tracing (true/false)
```

### 3. Optional: Sub-Worker API Keys

Some LangSmith agents use external services:

```bash
# For literature search in sub-workers
TAVILY_API_KEY=tvly-...
EXA_API_KEY=exa_...

# For Google Docs output
GOOGLE_DOCS_API_KEY=...
```

---

## Deployment

### On ROSflow2 (Hetzner)

```bash
# 1. SSH to server
ssh user@rosflow2

# 2. Navigate to deployment directory
cd /opt/researchflow/researchflow-production-main

# 3. Pull latest code
git fetch origin
git checkout chore/inventory-capture
git pull

# 4. Update .env with LangSmith configuration
nano .env
# Add LANGSMITH_API_KEY and agent IDs (see Prerequisites)

# 5. Build proxy services
docker compose build agent-results-interpretation-proxy
docker compose build agent-clinical-manuscript-proxy
docker compose build agent-section-drafter-proxy

# 6. Start proxies
docker compose up -d agent-results-interpretation-proxy
docker compose up -d agent-clinical-manuscript-proxy
docker compose up -d agent-section-drafter-proxy

# 7. Verify health
sleep 15  # Wait for startup
docker compose ps | grep proxy
# All should be "Up (healthy)"

# 8. Test health endpoints
docker compose exec agent-clinical-manuscript-proxy curl -f http://localhost:8000/health
docker compose exec agent-section-drafter-proxy curl -f http://localhost:8000/health
# Expected: {"status": "ok"}

# 9. Test readiness (validates LangSmith connectivity)
docker compose exec agent-clinical-manuscript-proxy curl -f http://localhost:8000/health/ready
# Expected: {"status": "ready", "langsmith": "reachable"}
```

---

## Validation

### 1. Container Health

```bash
# Check all proxy containers are running and healthy
docker compose ps | grep proxy

# Expected output:
# researchflow-agent-results-interpretation-proxy   Up (healthy)
# researchflow-agent-clinical-manuscript-proxy      Up (healthy)
# researchflow-agent-section-drafter-proxy          Up (healthy)
```

### 2. Health Endpoints

```bash
# Test each proxy's health endpoint
for proxy in results-interpretation-proxy clinical-manuscript-proxy section-drafter-proxy; do
  echo "Testing agent-$proxy..."
  docker compose exec agent-$proxy curl -sf http://localhost:8000/health || echo "FAIL: $proxy"
done

# All should return {"status": "ok"}
```

### 3. LangSmith Connectivity

```bash
# Test readiness (validates LangSmith API is reachable)
docker compose exec agent-clinical-manuscript-proxy curl -f http://localhost:8000/health/ready

# Success: {"status": "ready", "langsmith": "reachable"}
# Failure: HTTP 503 - Check LANGSMITH_API_KEY is valid
```

### 4. Router Integration

```bash
# Verify proxies are registered in AGENT_ENDPOINTS_JSON
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq . | grep -E 'manuscript|section-drafter|results-interpretation'

# Expected:
# "agent-clinical-manuscript": "http://agent-clinical-manuscript-proxy:8000"
# "agent-clinical-section-drafter": "http://agent-section-drafter-proxy:8000"
# "agent-results-interpretation": "http://agent-results-interpretation-proxy:8000"
```

### 5. End-to-End Test

```bash
# Get auth token (replace with actual token)
TOKEN="Bearer your-jwt-token"

# Test Clinical Manuscript Writer dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_MANUSCRIPT_WRITE",
    "request_id": "test-manuscript-001",
    "mode": "DEMO",
    "inputs": {
      "study_data": {
        "title": "Test Study",
        "study_type": "RCT"
      }
    }
  }'

# Expected: 
# {
#   "dispatch_type": "agent",
#   "agent_name": "agent-clinical-manuscript",
#   "agent_url": "http://agent-clinical-manuscript-proxy:8000",
#   "request_id": "test-manuscript-001"
# }

# Test Clinical Section Drafter dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_SECTION_DRAFT",
    "request_id": "test-section-001",
    "mode": "DEMO",
    "inputs": {
      "section_type": "Results",
      "study_summary": "RCT of 100 patients"
    }
  }'
```

---

## Troubleshooting

### Problem: Container won't start

```bash
# Check logs
docker compose logs agent-clinical-manuscript-proxy

# Common issues:
# - Missing LANGSMITH_API_KEY: Add to .env
# - Invalid LANGSMITH_AGENT_ID: Verify UUID from LangSmith UI
# - Port conflict: Check if port 8000 is in use by another service
```

### Problem: Health check fails (503)

```bash
# Check /health/ready endpoint
docker compose exec agent-clinical-manuscript-proxy curl -v http://localhost:8000/health/ready

# Common issues:
# - LANGSMITH_API_KEY not set: Check environment variable
# - Invalid API key: Test key manually with curl
# - Network issue: Check if container can reach api.smith.langchain.com
```

**Test API key manually:**
```bash
curl -H "x-api-key: $LANGSMITH_API_KEY" \
  https://api.smith.langchain.com/api/v1/info
```

### Problem: Router dispatch fails

```bash
# Check AGENT_ENDPOINTS_JSON includes proxy
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq .

# Verify task type is registered in ai-router.ts
grep -n "CLINICAL_MANUSCRIPT_WRITE\|CLINICAL_SECTION_DRAFT" \
  services/orchestrator/src/routes/ai-router.ts

# If missing, restart orchestrator
docker compose up -d --force-recreate orchestrator
```

### Problem: Timeout errors

```bash
# Increase timeout for complex operations
# In .env:
LANGSMITH_TIMEOUT_SECONDS=600  # 10 minutes

# Restart proxy
docker compose up -d --force-recreate agent-clinical-manuscript-proxy
```

### Problem: LangSmith API errors (4xx/5xx)

```bash
# View proxy logs
docker compose logs --tail=50 agent-clinical-manuscript-proxy

# Check LangSmith dashboard
# https://smith.langchain.com/
# Look for failed runs, error messages

# Common issues:
# - 401/403: Invalid API key or agent ID
# - 429: Rate limit exceeded
# - 500: LangSmith service issue (check status page)
```

---

## Monitoring

### Health Check Script

Create `scripts/check-langsmith-proxies.sh`:

```bash
#!/bin/bash
# Check health of all LangSmith proxy services

PROXIES=(
  "agent-results-interpretation-proxy"
  "agent-clinical-manuscript-proxy"
  "agent-section-drafter-proxy"
)

for proxy in "${PROXIES[@]}"; do
  echo "Checking $proxy..."
  
  # Liveness check
  if docker compose exec "$proxy" curl -sf http://localhost:8000/health > /dev/null; then
    echo "  ✓ Health OK"
  else
    echo "  ✗ Health FAIL"
  fi
  
  # Readiness check
  if docker compose exec "$proxy" curl -sf http://localhost:8000/health/ready > /dev/null; then
    echo "  ✓ Ready OK (LangSmith reachable)"
  else
    echo "  ✗ Ready FAIL (LangSmith unreachable)"
  fi
  
  echo ""
done
```

### Grafana Dashboard

Create dashboard with:
- **Proxy health metrics** - Up/down status
- **Response times** - P50, P95, P99 latency
- **Error rates** - 4xx/5xx responses
- **LangSmith API usage** - Request count, costs

---

## Cost Management

### LangSmith API Costs

Each agent execution incurs:
- **LLM tokens** - GPT-4/Claude usage in main agent + sub-agents
- **Tool calls** - Tavily/Exa searches, Google Docs API
- **Trace storage** - If LANGCHAIN_TRACING_V2=true

**Estimate costs:**
- Results Interpretation: ~$0.10-0.50 per request
- Clinical Manuscript Writer: ~$1.00-3.00 per manuscript
- Clinical Section Drafter: ~$0.50-1.50 per section

**Monitor usage:**
- LangSmith dashboard: https://smith.langchain.com/settings/billing
- Filter by project: `LANGCHAIN_PROJECT=researchflow-*`

---

## Rollback

If proxies cause issues:

```bash
# 1. Stop proxy services
docker compose stop agent-clinical-manuscript-proxy
docker compose stop agent-section-drafter-proxy

# 2. Remove from AGENT_ENDPOINTS_JSON
nano .env
# Remove lines for:
# - "agent-clinical-manuscript":"http://agent-clinical-manuscript-proxy:8000"
# - "agent-clinical-section-drafter":"http://agent-section-drafter-proxy:8000"

# 3. Restart orchestrator
docker compose up -d --force-recreate orchestrator

# 4. Verify removed
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq .

# 5. Optional: Remove containers
docker compose rm -f agent-clinical-manuscript-proxy
docker compose rm -f agent-section-drafter-proxy
```

---

## Development Workflow

### Running Locally (Without Docker)

```bash
# 1. Navigate to proxy directory
cd services/agents/agent-clinical-manuscript-proxy

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_AGENT_ID="uuid-from-langsmith"

# 5. Run proxy
uvicorn app.main:app --reload --port 8000

# 6. Test in another terminal
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

### Testing with Mock LangSmith

```python
# tests/test_manuscript_proxy.py
import pytest
from unittest.mock import AsyncMock, patch
from httpx import Response

@pytest.mark.asyncio
async def test_manuscript_proxy_mock():
    """Test proxy with mocked LangSmith API"""
    
    # Mock LangSmith response
    mock_response = AsyncMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "output": {
            "manuscript_draft": "# Test Manuscript\n\nTest content",
            "google_doc_url": "https://docs.google.com/..."
        },
        "metadata": {"run_id": "test-run-id"}
    }
    
    with patch('httpx.AsyncClient.post', return_value=mock_response):
        response = await client.post("/agents/run/sync", json={
            "task_type": "CLINICAL_MANUSCRIPT_WRITE",
            "request_id": "test-001",
            "mode": "DEMO",
            "inputs": {"study_data": {}}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "manuscript_draft" in data["outputs"]
```

---

## Security Considerations

### API Key Protection

**DO NOT:**
- ❌ Commit API keys to git
- ❌ Log API keys in proxy logs
- ❌ Expose API keys in error messages
- ❌ Pass API keys in query parameters

**DO:**
- ✅ Store in `.env` file (git-ignored)
- ✅ Use environment variables only
- ✅ Rotate keys quarterly
- ✅ Use separate keys per environment (dev/staging/prod)

### Network Security

**Proxy services:**
- ✅ No external port exposure (internal Docker network only)
- ✅ Orchestrator authentication required
- ✅ HTTPS for all LangSmith API calls
- ✅ Rate limiting in orchestrator

---

## Performance Tuning

### Timeout Configuration

**Adjust based on agent complexity:**

```bash
# Results Interpretation (simpler)
LANGSMITH_TIMEOUT_SECONDS=180  # 3 minutes

# Clinical Section Drafter (moderate)
LANGSMITH_SECTION_DRAFTER_TIMEOUT_SECONDS=180  # 3 minutes

# Clinical Manuscript Writer (complex, multi-section)
LANGSMITH_MANUSCRIPT_TIMEOUT_SECONDS=300  # 5 minutes
```

### Resource Limits

```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '0.5'      # Proxy is lightweight (just HTTP forwarding)
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

### Connection Pooling

Proxies use `httpx.AsyncClient` with:
- Connection pooling (reuse TCP connections)
- Automatic retry on connection errors
- Keep-alive for persistent connections

---

## Monitoring & Observability

### Key Metrics

1. **Availability** - Proxy uptime, health check success rate
2. **Latency** - P50/P95/P99 response times
3. **Errors** - 4xx/5xx error rates
4. **LangSmith API** - Upstream errors, timeout rates
5. **Costs** - LangSmith API usage, token consumption

### Logs

```bash
# View proxy logs
docker compose logs -f agent-clinical-manuscript-proxy

# Expected log entries:
# INFO - Received request: req-123 (task_type=CLINICAL_MANUSCRIPT_WRITE)
# INFO - Calling LangSmith agent uuid
# INFO - LangSmith response received for req-123

# Error patterns:
# ERROR - LangSmith API error: 401 - Invalid API key
# ERROR - Network error calling LangSmith: Connection timeout
```

### Alerts

Set up alerts for:
- Proxy health check failures (3+ consecutive failures)
- LangSmith API errors (>5% error rate)
- High latency (P95 > 60 seconds)
- Container restarts (>2 per hour)

---

## FAQ

### Q: Do I need separate LangSmith accounts for each agent?

**A:** No. You can use one LangSmith API key for all agents. Each agent is identified by its unique `LANGSMITH_AGENT_ID`.

### Q: Can I run proxies without LangSmith API access?

**A:** For local dev, yes - mock the LangSmith API in tests. For production, no - the proxies require live LangSmith API access.

### Q: Why not call LangSmith directly from orchestrator?

**A:** Proxies provide:
- Architectural consistency (all agents are HTTP services)
- Health checks and monitoring
- Request/response transformation
- Retry logic and timeout management
- Testing with mocks

### Q: Can I migrate LangSmith agents to local execution?

**A:** Yes, but requires significant work:
1. Implement agent logic in Python/TypeScript
2. Replace LangSmith sub-agents with local workers
3. Handle tool execution locally
4. Test extensively (LangSmith provides orchestration)

For now, **proxy pattern is recommended** - it's simpler and leverages existing LangSmith investments.

### Q: How do I get LangSmith Agent IDs?

**A:** 
1. Go to https://smith.langchain.com/
2. Navigate to "Agents" section
3. Click on your agent
4. Copy the UUID from the URL or agent settings

---

## Related Documentation

- **Proxy Architecture:** `LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md`
- **Agent Inventory:** `AGENT_INVENTORY.md`
- **Docker Compose:** `docker-compose.yml` (services: `agent-*-proxy`)
- **AI Router:** `services/orchestrator/src/routes/ai-router.ts`

---

**Status:** ✅ **PRODUCTION READY**

All three LangSmith proxy services are containerized, documented, and ready for deployment.
