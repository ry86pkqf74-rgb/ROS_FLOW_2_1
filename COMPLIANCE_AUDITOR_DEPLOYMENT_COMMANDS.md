# Compliance Auditor Agent - Deployment Commands Reference

Quick reference for deploying the Compliance Auditor agent to production.

---

## Local Development

### 1. Apply Manual Edits

**File 1: docker-compose.yml**
```bash
# Add service definition after agent-bias-detection-proxy (line ~1545)
vim researchflow-production-main/docker-compose.yml
```

Add this service:
```yaml
  agent-compliance-auditor-proxy:
    build:
      context: .
      dockerfile: services/agents/agent-compliance-auditor-proxy/Dockerfile
    container_name: researchflow-agent-compliance-auditor-proxy
    restart: unless-stopped
    stop_grace_period: 30s
    environment:
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY:-}
      - LANGSMITH_AGENT_ID=${LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID:-}
      - LANGSMITH_API_URL=${LANGSMITH_API_URL:-https://api.smith.langchain.com/api/v1}
      - LANGSMITH_TIMEOUT_SECONDS=${LANGSMITH_COMPLIANCE_AUDITOR_TIMEOUT_SECONDS:-300}
      - LOG_LEVEL=${AGENT_LOG_LEVEL:-INFO}
      - LANGCHAIN_PROJECT=${LANGCHAIN_PROJECT:-researchflow-compliance-auditor}
      - LANGCHAIN_TRACING_V2=${LANGCHAIN_TRACING_V2:-false}
      - PYTHONUNBUFFERED=1
    expose:
      - "8000"
    networks:
      - backend
      - frontend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

**And update AGENT_ENDPOINTS_JSON** (line ~188, in orchestrator environment):
Add `"agent-compliance-auditor-proxy":"http://agent-compliance-auditor-proxy:8000"` before the closing `}`.

**File 2: ai-router.ts**
```bash
vim researchflow-production-main/services/orchestrator/src/routes/ai-router.ts
```

Add this line after `PERFORMANCE_OPTIMIZATION` (around line 181):
```typescript
  COMPLIANCE_AUDIT: 'agent-compliance-auditor-proxy',
```

### 2. Git Commit Sequence

```bash
cd researchflow-production-main

# Create feature branch
git checkout -b feat/wire-compliance-auditor

# Commit 1: Proxy service
git add services/agents/agent-compliance-auditor-proxy/
git commit -m "feat(agents): add Compliance Auditor proxy service

- Add FastAPI proxy for LangSmith-hosted Compliance Auditor agent
- Pattern-match agent-dissemination-formatter-proxy
- Support sync/stream execution modes
- 5-minute timeout for audits
- Env: LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID

Related: commit 3c19b64 (agent config import)"

# Commit 2: Compose + router wiring
git add docker-compose.yml services/orchestrator/src/routes/ai-router.ts
git commit -m "feat(agents): wire Compliance Auditor to core stack

- Add agent-compliance-auditor-proxy service to docker-compose.yml
- Register in AGENT_ENDPOINTS_JSON
- Add COMPLIANCE_AUDIT task type to ai-router.ts
- Networks: backend (internal) + frontend (LangSmith API)

Task type: COMPLIANCE_AUDIT → agent-compliance-auditor-proxy"

# Commit 3: Documentation
git add docs/agents/agent-compliance-auditor-proxy/
git commit -m "docs(agents): add Compliance Auditor wiring guide

- Comprehensive deployment steps for Hetzner
- Architecture diagram (orchestrator → proxy → LangSmith)
- Input/output schemas
- Validation procedures (preflight + smoke)
- Troubleshooting guide"
```

### 3. Push and Create PR

```bash
# Push branch
git push -u origin feat/wire-compliance-auditor

# Create PR (via gh CLI)
gh pr create \
  --title "feat: wire Compliance Auditor agent (LangSmith proxy)" \
  --body "Wires the Compliance Auditor agent into core stack deployment.

## Changes
- ✅ Add LangSmith proxy service (agent-compliance-auditor-proxy)
- ✅ Register in docker-compose.yml + AGENT_ENDPOINTS_JSON
- ✅ Add COMPLIANCE_AUDIT task type to ai-router.ts
- ✅ Preflight + smoke validation (dynamic via AGENT_ENDPOINTS_JSON)
- ✅ Comprehensive wiring documentation

## Testing
\`\`\`bash
./scripts/hetzner-preflight.sh
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
\`\`\`

## Dependencies
- Requires: \`LANGSMITH_API_KEY\`, \`LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID\`
- Related: commit 3c19b64 (agent config import)

## Deployment
Deploy to ROSflow2 following \`docs/agents/agent-compliance-auditor-proxy/wiring.md\`
"
```

---

## Production Deployment (ROSflow2 / Hetzner)

### Prerequisites

1. **Obtain LangSmith Agent ID:**
   - Log into LangSmith UI
   - Navigate to Assistants → Compliance Auditor
   - Copy the Assistant ID (UUID format)

2. **SSH Access to ROSflow2:**
   ```bash
   ssh user@rosflow2
   ```

### Deployment Sequence

```bash
# 1. Navigate to deployment directory
cd /opt/researchflow/researchflow-production-main

# 2. Pull latest code (after PR merge)
git fetch --all --prune
git checkout main
git pull --ff-only

# 3. Set environment variables
cat >> .env << 'ENV_EOF'
# Compliance Auditor Agent (LangSmith)
LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID=<uuid-from-langsmith>
ENV_EOF

# Verify LANGSMITH_API_KEY is already set
grep LANGSMITH_API_KEY .env || echo "WARNING: LANGSMITH_API_KEY not found!"

# 4. Build proxy service
docker compose build agent-compliance-auditor-proxy

# 5. Start proxy
docker compose up -d agent-compliance-auditor-proxy

# 6. Wait for healthy
sleep 15

# 7. Verify proxy health
docker compose ps agent-compliance-auditor-proxy
docker compose exec agent-compliance-auditor-proxy curl -f http://localhost:8000/health

# 8. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 9. Run preflight checks
./scripts/hetzner-preflight.sh

# 10. Optional: Run comprehensive smoke test
CHECK_ALL_AGENTS=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 ./scripts/stagewise-smoke.sh
```

### Validation

**Preflight Check:**
```bash
./scripts/hetzner-preflight.sh
```

Expected output:
```
✓ agent-compliance-auditor-proxy [Registry] http://agent-compliance-auditor-proxy:8000
✓ agent-compliance-auditor-proxy [Container] running
✓ agent-compliance-auditor-proxy [Health] responding
```

**Smoke Test:**
```bash
CHECK_ALL_AGENTS=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

Expected:
- Artifact written to `/data/artifacts/validation/agent-compliance-auditor-proxy/{timestamp}/summary.json`
- Router dispatch returns `agent-compliance-auditor-proxy`

**Manual Test:**
```bash
# Get auth token
TOKEN=$(docker compose exec -T orchestrator sh -c '
  curl -sS -X POST http://localhost:3001/api/dev-auth/login \
    -H "Content-Type: application/json" \
    -H "X-Dev-User-Id: test-admin" \
    | grep -o "\"accessToken\":\"[^\"]*\"" \
    | cut -d\" -f4
')

# Test dispatch
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "COMPLIANCE_AUDIT",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "log_source": "direct",
      "log_data": "test log entries...",
      "frameworks": ["HIPAA", "GDPR"]
    }
  }'
```

Expected response:
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-compliance-auditor-proxy",
  "agent_url": "http://agent-compliance-auditor-proxy:8000",
  "request_id": "test-001"
}
```

---

## Troubleshooting

### Issue: Container not starting

```bash
# Check logs
docker compose logs agent-compliance-auditor-proxy

# Common issues:
# - Missing LANGSMITH_API_KEY
# - Invalid LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID
# - Port 8000 already in use

# Fix and restart
docker compose up -d --force-recreate agent-compliance-auditor-proxy
```

### Issue: Health check failing

```bash
# Test health endpoint directly
docker compose exec agent-compliance-auditor-proxy curl -v http://localhost:8000/health

# Check LangSmith connectivity
docker compose exec agent-compliance-auditor-proxy curl -v http://localhost:8000/health/ready
```

### Issue: Routing failures

```bash
# Verify task type mapping
docker compose exec orchestrator grep "COMPLIANCE_AUDIT" /app/src/routes/ai-router.ts

# Verify AGENT_ENDPOINTS_JSON
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -m json.tool | grep compliance
```

### Issue: Preflight failing

```bash
# Check which validation failed
./scripts/hetzner-preflight.sh 2>&1 | grep "agent-compliance-auditor-proxy"

# Verify all mandatory keys present
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | python3 -c '
import json, sys
endpoints = json.load(sys.stdin)
print(f"Total agents: {len(endpoints)}")
if "agent-compliance-auditor-proxy" in endpoints:
    print("✓ agent-compliance-auditor-proxy found")
else:
    print("✗ agent-compliance-auditor-proxy MISSING")
'
```

---

## Rollback

If deployment fails, rollback to previous state:

```bash
# Stop new proxy
docker compose stop agent-compliance-auditor-proxy

# Revert to previous commit
git log --oneline -5
git reset --hard <previous-commit-sha>

# Restart orchestrator
docker compose up -d --force-recreate orchestrator

# Validate
./scripts/hetzner-preflight.sh
```

---

## Related Documentation

- **Wiring Guide:** `docs/agents/agent-compliance-auditor-proxy/wiring.md`
- **Proxy README:** `services/agents/agent-compliance-auditor-proxy/README.md`
- **Agent Config:** `services/agents/agent-compliance-auditor/AGENTS.md`
- **Preflight Script:** `scripts/hetzner-preflight.sh`
- **Smoke Script:** `scripts/stagewise-smoke.sh`

---

**Last Updated:** 2026-02-08  
**Deployment Target:** ROSflow2 (Hetzner)  
**Required Env Vars:** `LANGSMITH_API_KEY`, `LANGSMITH_COMPLIANCE_AUDITOR_AGENT_ID`
