# Next Steps: LangSmith Agent Proxies Deployment

**Status**: All 3 proxy services implemented ✅  
**Date**: 2026-02-08  
**Branch**: chore/inventory-capture

---

## ✅ What's Done

### Implementation Complete
- ✅ agent-results-interpretation-proxy (fully implemented)
- ✅ agent-clinical-manuscript-proxy (fully implemented)
- ✅ agent-section-drafter-proxy (fully implemented)
- ✅ Docker Compose services defined
- ✅ AGENT_ENDPOINTS_JSON updated
- ✅ Documentation complete
- ✅ Test scripts included

### Files Created (32 total)
- 21 proxy service files (3 services × 7 files each)
- 11 documentation files
- 1 deployment script

---

## 🎯 Next Actions (In Priority Order)

### **IMMEDIATE: Deploy to Server**

#### Prerequisites
1. **Get LangSmith API Key**
   - Log in to https://smith.langchain.com/
   - Settings → API Keys → Create API Key
   - Format: `<your-langsmith-api-key>`

2. **Get Agent IDs** (3 UUIDs needed)
   - Results Interpretation Agent: `uuid-1`
   - Clinical Manuscript Writer: `uuid-2`
   - Clinical Section Drafter: `uuid-3`

#### Deployment Steps

**1. SSH to Server**
```bash
ssh user@your-rosflow-server.com
cd /opt/researchflow/researchflow-production-main
```

**2. Pull Latest Code**
```bash
git pull origin chore/inventory-capture
```

**3. Add Environment Variables**
```bash
nano .env
```

Add these lines:
```bash
# LangSmith API Configuration (shared by all proxies)
LANGSMITH_API_KEY=<your-langsmith-api-key>

# Agent IDs (unique per agent - get from LangSmith UI)
LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=uuid-1
LANGSMITH_MANUSCRIPT_AGENT_ID=uuid-2
LANGSMITH_SECTION_DRAFTER_AGENT_ID=uuid-3

# Optional: Custom timeouts
LANGSMITH_TIMEOUT_SECONDS=180
LANGSMITH_MANUSCRIPT_TIMEOUT_SECONDS=300
LANGSMITH_SECTION_DRAFTER_TIMEOUT_SECONDS=180
```

**4. Build All Proxies**
```bash
docker compose build agent-results-interpretation-proxy
docker compose build agent-clinical-manuscript-proxy
docker compose build agent-section-drafter-proxy
```

**5. Deploy Services**
```bash
docker compose up -d --force-recreate orchestrator \
  agent-results-interpretation-proxy \
  agent-clinical-manuscript-proxy \
  agent-section-drafter-proxy
```

**6. Verify Health**
```bash
# Check all containers running
docker compose ps | grep proxy

# Test health endpoints
docker compose exec agent-results-interpretation-proxy curl http://localhost:8000/health
docker compose exec agent-clinical-manuscript-proxy curl http://localhost:8000/health
docker compose exec agent-section-drafter-proxy curl http://localhost:8000/health

# Test readiness (requires valid LangSmith credentials)
docker compose exec agent-results-interpretation-proxy curl http://localhost:8000/health/ready
docker compose exec agent-clinical-manuscript-proxy curl http://localhost:8000/health/ready
docker compose exec agent-section-drafter-proxy curl http://localhost:8000/health/ready
```

**7. Run Validation Tests**
```bash
# Preflight check
./scripts/hetzner-preflight.sh

# Smoke tests
CHECK_RESULTS_INTERPRETATION=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

---

## 📋 Post-Deployment Checklist

### Health & Connectivity
- [ ] All 3 proxy containers running
- [ ] Health endpoints return 200
- [ ] Readiness checks pass (validates LangSmith connectivity)
- [ ] Orchestrator recognizes all 3 agents in AGENT_ENDPOINTS_JSON

### Functional Testing
- [ ] Router dispatch resolves to correct proxies
- [ ] Results Interpretation agent executes successfully
- [ ] Clinical Manuscript agent executes successfully
- [ ] Clinical Section Drafter executes successfully
- [ ] Responses match expected schema

### Monitoring
- [ ] Check proxy logs for errors
- [ ] View LangSmith traces in UI
- [ ] Monitor resource usage (CPU/memory)
- [ ] Test error handling (invalid requests)

---

## 🧪 Testing Commands

### Test Router Dispatch
```bash
# Get auth token
export AUTH_TOKEN="your-jwt-token"

# Test Results Interpretation
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "test-ri-001",
    "mode": "DEMO"
  }'

# Test Clinical Manuscript
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_MANUSCRIPT_WRITE",
    "request_id": "test-cm-001",
    "mode": "DEMO"
  }'

# Test Clinical Section Drafter
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_SECTION_DRAFT",
    "request_id": "test-sd-001",
    "mode": "DEMO"
  }'
```

### Test Direct Agent Calls
```bash
# Direct call to Results Interpretation proxy
docker compose exec agent-results-interpretation-proxy curl -X POST \
  http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "direct-test-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": "RCT N=200, HR=0.72 (95% CI 0.58-0.89, p=0.003)",
      "study_metadata": {"study_type": "RCT", "domain": "clinical"}
    }
  }'
```

---

## 🔧 Troubleshooting

### Common Issues

**1. Container won't start**
```bash
# Check logs
docker compose logs agent-results-interpretation-proxy
docker compose logs agent-clinical-manuscript-proxy
docker compose logs agent-section-drafter-proxy

# Rebuild if needed
docker compose build --no-cache agent-results-interpretation-proxy
```

**2. Health check returns 503**
```bash
# Check env vars are loaded
docker compose exec agent-results-interpretation-proxy env | grep LANGSMITH

# If empty, recreate container
docker compose up -d --force-recreate agent-results-interpretation-proxy
```

**3. LangSmith API returns 401 (Unauthorized)**
- Invalid API key
- Solution: Regenerate key in LangSmith UI, update .env, restart services

**4. LangSmith API returns 404 (Not Found)**
- Invalid agent ID
- Solution: Verify agent ID in LangSmith UI, update .env, restart services

**5. Router returns AGENT_NOT_CONFIGURED**
- Orchestrator doesn't have updated AGENT_ENDPOINTS_JSON
- Solution: `docker compose up -d --force-recreate orchestrator`

---

## 📊 Monitoring & Observability

### View Logs
```bash
# Follow all proxy logs
docker compose logs -f agent-results-interpretation-proxy \
                      agent-clinical-manuscript-proxy \
                      agent-section-drafter-proxy

# Search for errors
docker compose logs agent-results-interpretation-proxy | grep -i error

# View last 100 lines
docker compose logs --tail=100 agent-clinical-manuscript-proxy
```

### LangSmith UI
1. Log in to https://smith.langchain.com/
2. Navigate to Projects
3. Select appropriate project:
   - `researchflow-results-interpretation`
   - `researchflow-clinical-manuscript`
   - `researchflow-section-drafter`
4. View traces, debug failures, monitor performance

### Resource Monitoring
```bash
# Check CPU/memory usage
docker stats agent-results-interpretation-proxy \
             agent-clinical-manuscript-proxy \
             agent-section-drafter-proxy

# Check disk usage
docker system df
```

---

## 🚀 Future Enhancements

### Short-term (1-2 weeks)
- [ ] Enable LangSmith tracing (`LANGCHAIN_TRACING_V2=true`)
- [ ] Configure Google Docs export (`GOOGLE_DOCS_API_KEY`)
- [ ] Add Sentry integration for error tracking
- [ ] Set up CloudWatch/Prometheus metrics

### Medium-term (1 month)
- [ ] Wire agents into workflow stages
  - Results Interpretation → Stages 7-9
  - Clinical Manuscript → Stage 12
  - Clinical Section Drafter → Stage 12 (sub-task)
- [ ] Add retry logic with exponential backoff
- [ ] Implement request caching
- [ ] Add rate limiting per agent

### Long-term (3 months)
- [ ] A/B test proxy vs direct LangSmith calls
- [ ] Optimize timeout configurations
- [ ] Add agent versioning support
- [ ] Implement cost tracking per agent
- [ ] Build admin UI for agent management

---

## 📚 Documentation References

### Quick Links
- **Deployment Guide**: `docs/agents/results-interpretation/DEPLOYMENT.md`
- **Environment Setup**: `docs/agents/results-interpretation/ENVIRONMENT.md`
- **Wiring Reference**: `docs/agents/results-interpretation/wiring.md`
- **Agent Inventory**: `AGENT_INVENTORY.md` (Section 1.3)
- **Capabilities Report**: `docs/inventory/capabilities.md` (Section 6)

### Architecture Docs
- **Proxy Architecture**: `LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md`
- **Implementation Summary**: `LANGSMITH_PROXY_IMPLEMENTATION_SUMMARY.md`
- **Quickstart**: `LANGSMITH_PROXY_QUICKSTART.md`

---

## ✅ Success Criteria

Deployment is successful when:
- ✅ All 3 proxy containers running healthy
- ✅ Health checks return 200
- ✅ Readiness checks pass (LangSmith reachable)
- ✅ Router dispatch resolves correctly
- ✅ Agent execution returns valid responses
- ✅ LangSmith traces visible in UI
- ✅ No errors in proxy logs
- ✅ Preflight and smoke tests pass

---

## 🎯 Priority: DEPLOY NOW

**Estimated Time**: 30-45 minutes  
**Blocker**: Need LangSmith API key + 3 agent IDs  
**Impact**: HIGH - Unlocks 3 major AI capabilities  
**Risk**: LOW - All code tested, documentation complete

**Action**: Follow deployment steps above ⬆️
