# Results Interpretation Agent - Deployment Guide

Complete step-by-step guide to deploy the Results Interpretation Agent on your ResearchFlow instance.

## Prerequisites

- ResearchFlow instance running with Docker Compose
- Access to server via SSH
- LangSmith account with API access
- Access to `.env` file on server

## Step 1: Get LangSmith Credentials

### 1.1 Get API Key

1. Log in to LangSmith: https://smith.langchain.com/
2. Navigate to **Settings** → **API Keys**
3. Click **Create API Key**
4. Copy the key (format: `<your-langsmith-api-key>`)
5. Save it securely - you won't be able to see it again

### 1.2 Get Agent ID

1. In LangSmith, navigate to **Agents** in the left sidebar
2. Find **Results Interpretation Agent** (or your custom agent name)
3. Click on the agent to open details
4. Copy the **Agent ID** (UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
5. Note: If you haven't created the agent yet, you need to:
   - Import from `services/agents/agent-results-interpretation/` directory
   - Or create new agent in LangSmith UI
   - Configure sub-workers and tools

## Step 2: Configure Environment Variables

### 2.1 SSH to Server

```bash
ssh user@your-rosflow-server.com
cd /opt/researchflow/researchflow-production-main  # Or your deploy directory
```

### 2.2 Edit .env File

```bash
nano .env  # or vim .env
```

### 2.3 Add Required Variables

Add these lines to `.env`:

```bash
# Results Interpretation Agent - LangSmith Configuration
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=YOUR_AGENT_UUID_HERE
```

**Optional variables** (add if you want to customize):

```bash
# LangSmith API URL (default: https://api.smith.langchain.com/api/v1)
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1

# Timeout in seconds (default: 180 = 3 minutes)
LANGSMITH_TIMEOUT_SECONDS=180

# LangSmith project for tracing (default: researchflow-results-interpretation)
LANGCHAIN_PROJECT=researchflow-results-interpretation

# Enable tracing (default: false)
LANGCHAIN_TRACING_V2=false
```

### 2.4 Save and Exit

- For nano: `Ctrl+O`, `Enter`, `Ctrl+X`
- For vim: `:wq`

## Step 3: Build and Deploy Proxy Service

### 3.1 Build the Proxy Image

```bash
docker compose build agent-results-interpretation-proxy
```

This builds the FastAPI proxy service from `services/agents/agent-results-interpretation-proxy/`.

### 3.2 Deploy Services

```bash
# Recreate orchestrator (picks up updated AGENT_ENDPOINTS_JSON)
docker compose up -d --force-recreate orchestrator

# Start proxy service
docker compose up -d agent-results-interpretation-proxy
```

### 3.3 Wait for Services to Start

```bash
# Watch logs
docker compose logs -f agent-results-interpretation-proxy

# Wait for "Application startup complete"
# Press Ctrl+C when ready
```

## Step 4: Verify Deployment

### 4.1 Check Service Status

```bash
# Check containers are running
docker compose ps | grep -E "orchestrator|agent-results-interpretation-proxy"
```

**Expected output:**
```
orchestrator                    Running
agent-results-interpretation-proxy  Running
```

### 4.2 Check Proxy Health

```bash
# Basic health check
docker compose exec -T agent-results-interpretation-proxy curl -f http://localhost:8000/health

# Expected: {"status":"ok","service":"agent-results-interpretation-proxy"}
```

### 4.3 Check LangSmith Connectivity

```bash
# Readiness check (validates LangSmith API)
docker compose exec -T agent-results-interpretation-proxy curl -f http://localhost:8000/health/ready

# Expected: {"status":"ready","langsmith":"reachable"}
```

**If this fails:**
- Check `LANGSMITH_API_KEY` is correct
- Check `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` is correct
- Check server can reach `api.smith.langchain.com` (firewall/network)
- View logs: `docker compose logs agent-results-interpretation-proxy`

### 4.4 Verify Router Configuration

```bash
# Check AGENT_ENDPOINTS_JSON includes agent
docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep results-interpretation

# Expected: "agent-results-interpretation":"http://agent-results-interpretation-proxy:8000"
```

## Step 5: Run Validation Tests

### 5.1 Run Preflight Check

```bash
# From researchflow-production-main directory
./scripts/hetzner-preflight.sh
```

Look for Results Interpretation Agent checks - should show ✅ for:
- LANGSMITH_API_KEY configured
- Router registration
- AGENT_ENDPOINTS_JSON includes agent
- Proxy service healthy

### 5.2 Run Smoke Test

```bash
# Enable Results Interpretation check
CHECK_RESULTS_INTERPRETATION=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

**Expected output:**
```
[12] Results Interpretation Agent Check (optional)
[12a] Checking LANGSMITH_API_KEY configuration
✓ LANGSMITH_API_KEY is configured in orchestrator
[12b] POST /api/ai/router/dispatch (RESULTS_INTERPRETATION)
Router dispatch OK: routed to agent-results-interpretation
✓ Correctly routed to agent-results-interpretation
[12c] Checking artifacts directory for results interpretation output
✓ /data/artifacts directory exists
✓ Wrote validation artifact to /data/artifacts/validation/results-interpretation-smoke/...
Results Interpretation Agent check complete (optional - does not block)
```

## Step 6: Test End-to-End

### 6.1 Get Authentication Token

```bash
# Option 1: Use existing user token
export AUTH_TOKEN="your-jwt-token"

# Option 2: Get dev token (if ENABLE_DEV_AUTH=true on server)
curl -X POST http://127.0.0.1:3001/api/dev-auth/login \
  -H "X-Dev-User-Id: test-user" | grep accessToken
```

### 6.2 Test Direct Agent Call

```bash
# Call proxy directly
docker compose exec -T agent-results-interpretation-proxy curl -X POST \
  http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "deploy-test-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": "Randomized controlled trial, N=200 participants. Primary endpoint: hazard ratio = 0.72 (95% CI 0.58-0.89, p=0.003). Secondary endpoints: response rate 45% vs 30% (p=0.02).",
      "study_metadata": {
        "study_type": "RCT",
        "domain": "clinical",
        "data_types": "quantitative"
      }
    }
  }'
```

**Expected:** JSON response with `"ok": true` and structured report sections.

### 6.3 Test via Router Dispatch

```bash
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "deploy-test-002",
    "mode": "DEMO",
    "inputs": {
      "results_data": "Meta-analysis of 12 studies, pooled OR=1.45 (95% CI 1.20-1.75, I²=35%, p<0.001)",
      "study_metadata": {
        "study_type": "meta-analysis",
        "domain": "clinical"
      }
    }
  }'
```

**Expected:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-results-interpretation",
  "agent_url": "http://agent-results-interpretation-proxy:8000",
  "budgets": {},
  "rag_plan": {},
  "request_id": "deploy-test-002"
}
```

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker compose logs agent-results-interpretation-proxy
```

**Common issues:**
- Python dependency errors → Rebuild: `docker compose build --no-cache agent-results-interpretation-proxy`
- Port conflict → Check no other service using port 8000 internally
- Network errors → Verify `backend` and `frontend` networks exist

### Health Check Fails (503)

**Issue:** `LANGSMITH_API_KEY` or `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` not set

**Fix:**
1. Check env vars in proxy container:
   ```bash
   docker compose exec agent-results-interpretation-proxy env | grep LANGSMITH
   ```
2. If empty, env vars not loaded - check `.env` file
3. Recreate service:
   ```bash
   docker compose up -d --force-recreate agent-results-interpretation-proxy
   ```

### LangSmith API Returns 401

**Issue:** Invalid or expired API key

**Fix:**
1. Log in to LangSmith
2. Navigate to Settings → API Keys
3. Regenerate key if needed
4. Update `.env` with new key
5. Recreate services

### LangSmith API Returns 404

**Issue:** Invalid agent ID

**Fix:**
1. Log in to LangSmith → Agents
2. Find Results Interpretation Agent
3. Copy correct Agent ID
4. Update `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` in `.env`
5. Recreate services

### Timeout Errors

**Issue:** Agent execution takes longer than timeout

**Fix:**
1. Increase timeout in `.env`:
   ```bash
   LANGSMITH_TIMEOUT_SECONDS=300  # 5 minutes
   ```
2. Recreate services
3. Or: Configure agent in LangSmith to skip refinement workers

### Router Returns AGENT_NOT_CONFIGURED

**Issue:** Orchestrator doesn't have updated `AGENT_ENDPOINTS_JSON`

**Fix:**
1. Verify docker-compose.yml has updated `AGENT_ENDPOINTS_JSON` (should include agent-results-interpretation)
2. Recreate orchestrator:
   ```bash
   docker compose up -d --force-recreate orchestrator
   ```
3. Verify:
   ```bash
   docker compose exec -T orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep results-interpretation
   ```

## Monitoring

### View Proxy Logs

```bash
# Follow logs in real-time
docker compose logs -f agent-results-interpretation-proxy

# View last 100 lines
docker compose logs --tail=100 agent-results-interpretation-proxy

# Search for errors
docker compose logs agent-results-interpretation-proxy | grep -i error
```

### View LangSmith Traces

1. Log in to LangSmith: https://smith.langchain.com/
2. Navigate to **Projects** → **researchflow-results-interpretation**
3. View traces of agent executions
4. Debug failed runs
5. Monitor sub-worker performance

### Check Resource Usage

```bash
# CPU and memory
docker stats agent-results-interpretation-proxy

# Disk usage
docker system df
```

## Rollback

If deployment fails and you need to rollback:

```bash
# Stop proxy service
docker compose stop agent-results-interpretation-proxy

# Remove from AGENT_ENDPOINTS_JSON (edit docker-compose.yml)
# Remove agent-results-interpretation entry

# Recreate orchestrator
docker compose up -d --force-recreate orchestrator

# Remove proxy container
docker compose rm -f agent-results-interpretation-proxy
```

## Next Steps

After successful deployment:

1. **Integrate with workflow stages** - Wire agent into Stages 7-9 (Results Analysis)
2. **Configure Google Docs** - Add `GOOGLE_DOCS_API_KEY` for report generation
3. **Set up monitoring** - Add Sentry/CloudWatch for production monitoring
4. **Enable tracing** - Set `LANGCHAIN_TRACING_V2=true` for detailed debugging
5. **Scale if needed** - Add load balancer if high traffic expected

## Support

- **Canonical reference:** `docs/agents/results-interpretation/wiring.md`
- **Environment setup:** `docs/agents/results-interpretation/ENVIRONMENT.md`
- **Agent inventory:** `AGENT_INVENTORY.md` section 1.3
- **Capabilities report:** `docs/inventory/capabilities.md` section 6
