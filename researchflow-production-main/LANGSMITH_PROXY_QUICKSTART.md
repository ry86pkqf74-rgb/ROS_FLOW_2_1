# LangSmith Proxy Agents - Quick Start

**3 agents. 5 minutes. Copy-paste deployment.**

---

## Step 1: Get Your LangSmith Credentials

1. Visit https://smith.langchain.com/settings
2. Copy your API key (format: `lsv2_pt_...`)
3. Find your agent UUIDs:
   - Results Interpretation Agent → copy UUID
   - Clinical Manuscript Writer Agent → copy UUID
   - Clinical Section Drafter Agent → copy UUID

---

## Step 2: Configure Environment

Add to `/opt/researchflow/.env`:

```bash
# LangSmith API key (shared)
LANGSMITH_API_KEY=lsv2_pt_YOUR_KEY_HERE

# Agent IDs (unique per agent)
LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=uuid-1
LANGSMITH_MANUSCRIPT_AGENT_ID=uuid-2
LANGSMITH_SECTION_DRAFTER_AGENT_ID=uuid-3
```

Update `AGENT_ENDPOINTS_JSON` in `.env` to include:

```bash
AGENT_ENDPOINTS_JSON='{"agent-stage2-lit":"http://agent-stage2-lit:8000","agent-stage2-screen":"http://agent-stage2-screen:8000","agent-stage2-extract":"http://agent-stage2-extract:8000","agent-stage2-synthesize":"http://agent-stage2-synthesize:8000","agent-lit-retrieval":"http://agent-lit-retrieval:8000","agent-lit-triage":"http://agent-lit-triage:8000","agent-policy-review":"http://agent-policy-review:8000","agent-rag-ingest":"http://agent-rag-ingest:8000","agent-rag-retrieve":"http://agent-rag-retrieve:8000","agent-verify":"http://agent-verify:8000","agent-intro-writer":"http://agent-intro-writer:8000","agent-methods-writer":"http://agent-methods-writer:8000","agent-evidence-synthesis":"http://agent-evidence-synthesis:8000","agent-results-interpretation":"http://agent-results-interpretation-proxy:8000","agent-clinical-manuscript":"http://agent-clinical-manuscript-proxy:8000","agent-clinical-section-drafter":"http://agent-section-drafter-proxy:8000"}'
```

---

## Step 3: Deploy Proxies

```bash
# Pull latest code
cd /opt/researchflow/researchflow-production-main
git pull origin chore/inventory-capture

# Build all three proxies
docker compose build agent-results-interpretation-proxy
docker compose build agent-clinical-manuscript-proxy
docker compose build agent-section-drafter-proxy

# Start proxies
docker compose up -d agent-results-interpretation-proxy
docker compose up -d agent-clinical-manuscript-proxy
docker compose up -d agent-section-drafter-proxy

# Restart orchestrator with new endpoints
docker compose up -d --force-recreate orchestrator
```

---

## Step 4: Verify

```bash
# Check all proxies are healthy
docker compose ps | grep proxy

# Test health endpoints
docker compose exec agent-results-interpretation-proxy curl -f http://localhost:8000/health
docker compose exec agent-clinical-manuscript-proxy curl -f http://localhost:8000/health
docker compose exec agent-section-drafter-proxy curl -f http://localhost:8000/health

# Test LangSmith connectivity
docker compose exec agent-clinical-manuscript-proxy curl -f http://localhost:8000/health/ready
# Expected: {"status": "ready", "langsmith": "reachable"}
```

---

## Step 5: Test Integration

```bash
# Get auth token (replace with actual token)
TOKEN="Bearer your-jwt-token"

# Test Results Interpretation
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"RESULTS_INTERPRETATION","request_id":"test-1","mode":"DEMO"}'

# Test Clinical Manuscript Writer
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"CLINICAL_MANUSCRIPT_WRITE","request_id":"test-2","mode":"DEMO"}'

# Test Clinical Section Drafter
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"task_type":"CLINICAL_SECTION_DRAFT","request_id":"test-3","mode":"DEMO"}'

# All should return:
# {"dispatch_type":"agent","agent_name":"agent-...","agent_url":"http://..."}
```

---

## Troubleshooting

### Proxy won't start

```bash
# Check logs
docker compose logs agent-clinical-manuscript-proxy

# Common fixes:
# - Missing LANGSMITH_API_KEY → Add to .env
# - Invalid agent ID → Verify UUID from LangSmith
# - Port conflict → Check docker compose ps
```

### Health check fails (503)

```bash
# Test API key manually
curl -H "x-api-key: $LANGSMITH_API_KEY" \
  https://api.smith.langchain.com/api/v1/info

# If this fails, your API key is invalid
```

### Router dispatch fails

```bash
# Verify AGENT_ENDPOINTS_JSON includes proxies
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | jq . | grep proxy

# If missing, update .env and restart orchestrator
docker compose up -d --force-recreate orchestrator
```

---

## Complete Deployment Script

Copy-paste this entire block:

```bash
#!/bin/bash
# Deploy all three LangSmith proxy services

set -e  # Exit on error

echo "📦 Building LangSmith proxy services..."
docker compose build agent-results-interpretation-proxy
docker compose build agent-clinical-manuscript-proxy
docker compose build agent-section-drafter-proxy

echo "🚀 Starting proxy services..."
docker compose up -d agent-results-interpretation-proxy
docker compose up -d agent-clinical-manuscript-proxy
docker compose up -d agent-section-drafter-proxy

echo "⏳ Waiting for services to start..."
sleep 15

echo "🔍 Checking health..."
PROXIES=(
  "agent-results-interpretation-proxy"
  "agent-clinical-manuscript-proxy"
  "agent-section-drafter-proxy"
)

for proxy in "${PROXIES[@]}"; do
  if docker compose exec "$proxy" curl -sf http://localhost:8000/health > /dev/null; then
    echo "  ✓ $proxy healthy"
  else
    echo "  ✗ $proxy FAILED"
    exit 1
  fi
done

echo "🔄 Restarting orchestrator..."
docker compose up -d --force-recreate orchestrator

echo ""
echo "✅ All LangSmith proxy services deployed successfully!"
echo ""
echo "Next steps:"
echo "  1. Test dispatch: curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch ..."
echo "  2. View logs: docker compose logs -f agent-clinical-manuscript-proxy"
echo "  3. Monitor in LangSmith: https://smith.langchain.com/"
```

Save as `scripts/deploy-langsmith-proxies.sh` and run:

```bash
chmod +x scripts/deploy-langsmith-proxies.sh
./scripts/deploy-langsmith-proxies.sh
```

---

## Need Help?

- **Full docs:** `docs/deployment/langsmith-proxy-deployment.md`
- **Architecture:** `LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md`
- **Agent inventory:** `AGENT_INVENTORY.md`
- **LangSmith dashboard:** https://smith.langchain.com/

---

**Time to deploy:** ~5 minutes  
**Difficulty:** Easy  
**Status:** Production Ready ✅
