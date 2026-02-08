# Dissemination Formatter - Next Steps

**Date:** 2026-02-08  
**PR:** #33 - https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1/pull/33  
**Branch:** feat/import-dissemination-formatter  
**Status:** ✅ Ready for Review & Deployment

---

## Current Status ✅

### All Wiring Complete
- ✅ Proxy service created (6 files)
- ✅ Docker Compose integrated
- ✅ Router task type registered
- ✅ Validation hooks added (preflight + smoke)
- ✅ Documentation complete
- ✅ Dockerfile validated (local build + health check ✓)
- ✅ All changes committed (4 commits)
- ✅ PR created and pushed

### Commits in PR
1. **66a1f0e** - Import agent from LangSmith
2. **f3d3153** - Wire for Hetzner deployment (proxy, compose, router, validation)
3. **093dc40** - Add PR checklist
4. **d7e6e5e** - Import Performance Optimizer (unrelated, already in branch)
5. **4c96098** - Fix Dockerfile COPY paths for docker-compose context

---

## Phase 1: PR Review & Approval

### What to Do Now

1. **Review PR on GitHub:** https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1/pull/33

2. **Request reviewers** (if not auto-assigned):
   - Tag team members familiar with LangSmith agents
   - Tag platform/DevOps team for docker-compose review
   - Tag someone familiar with orchestrator routing

3. **Answer reviewer questions:**
   - Dockerfile path fix (commit 4c96098)
   - Proxy pattern consistency with other LangSmith agents
   - Validation strategy (preflight + smoke)

4. **Address any requested changes:**
   - Make changes on this branch
   - Push updates (they'll auto-add to PR)

### Review Focus Areas

Reviewers should check:
- ✅ Proxy implementation follows established pattern
- ✅ Docker Compose service definition correct
- ✅ Router registration proper
- ✅ Validation hooks non-breaking
- ✅ Documentation complete
- ✅ No secrets committed
- ✅ Local build tested

---

## Phase 2: After PR Approval

### Option A: Merge to Main (Recommended)

```bash
# 1. Merge PR on GitHub (or via gh CLI)
gh pr merge 33 --squash --delete-branch

# 2. The branch will be deleted automatically
# 3. Proceed to Phase 3 (Deployment)
```

### Option B: Merge to Another Branch First

If you need to test on a staging branch first:

```bash
# 1. Checkout target branch
git checkout chore/inventory-capture

# 2. Merge this branch
git merge feat/import-dissemination-formatter

# 3. Push
git push origin chore/inventory-capture

# 4. Later: merge chore/inventory-capture to main
```

---

## Phase 3: Deployment to ROSflow2

### Prerequisites

**On your local machine:**
1. Get LangSmith Agent ID from https://smith.langchain.com/
   - Navigate to Dissemination Formatter agent
   - Copy the UUID from URL or settings
2. Have your LangSmith API key ready (lsv2_pt_...)

**Access to server:**
- SSH credentials for ROSflow2
- Sudo access (if needed)

### Deployment Steps

```bash
# 1. SSH to ROSflow2
ssh user@rosflow2

# 2. Navigate to deployment directory
cd /opt/researchflow

# 3. Pull latest code (assuming merged to main)
git fetch --all --prune
git checkout main
git pull --ff-only

# 4. Add environment variables
cat >> .env << 'ENV_EOF'

# Dissemination Formatter Agent (LangSmith)
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID=<uuid-from-langsmith>

# Optional: Enhance functionality
TAVILY_API_KEY=tvly-...
GOOGLE_DOCS_API_KEY=...
ENV_EOF

# 5. Build proxy service
cd researchflow-production-main
docker compose build agent-dissemination-formatter-proxy

# 6. Start proxy service
docker compose up -d agent-dissemination-formatter-proxy

# 7. Wait for healthy status
sleep 15

# 8. Verify proxy health
docker compose ps agent-dissemination-formatter-proxy
docker compose logs --tail=20 agent-dissemination-formatter-proxy

# 9. Test health endpoint
docker compose exec agent-dissemination-formatter-proxy curl -f http://localhost:8000/health
# Expected: {"status":"ok","service":"agent-dissemination-formatter-proxy"}

# 10. Restart orchestrator to load new routing
docker compose up -d --force-recreate orchestrator

# 11. Wait for orchestrator healthy
sleep 10

# 12. Verify orchestrator sees the proxy
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep dissemination
# Expected: "agent-dissemination-formatter":"http://agent-dissemination-formatter-proxy:8000"
```

---

## Phase 4: Validation

### Mandatory: Preflight Checks

```bash
cd /opt/researchflow/researchflow-production-main
./scripts/hetzner-preflight.sh
```

**Expected output:**
```
✓ Dissemination Formatter - LANGSMITH_API_KEY configured
✓ Dissemination Formatter Router - task type registered
```

**If checks fail:**
- Check .env file has LANGSMITH_API_KEY and LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID
- Restart orchestrator: `docker compose up -d --force-recreate orchestrator`
- Check logs: `docker compose logs orchestrator | tail -50`

### Optional: Smoke Test

```bash
CHECK_DISSEMINATION_FORMATTER=1 DEV_AUTH=true SKIP_ADMIN_CHECKS=1 \
  ./scripts/stagewise-smoke.sh
```

**Expected output:**
```
[13] Dissemination Formatter Agent Check (optional - LangSmith-based)
✓ LANGSMITH_API_KEY is configured
✓ LANGSMITH_DISSEMINATION_FORMATTER_AGENT_ID is configured
✓ Correctly routed to agent-dissemination-formatter
✓ agent-dissemination-formatter-proxy container is running
✓ Proxy health endpoint responding
✓ Wrote validation artifact
Dissemination Formatter Agent check complete
```

**If smoke test fails:**
- Check proxy container logs: `docker compose logs agent-dissemination-formatter-proxy`
- Verify LangSmith API key is valid
- Check agent ID matches your LangSmith configuration

### Manual: Direct Dispatch Test

```bash
# 1. Get auth token (if DEV_AUTH enabled)
TOKEN=$(curl -X POST http://localhost:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' | jq -r '.token')

# 2. Test dispatch
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "DISSEMINATION_FORMATTING",
    "request_id": "manual-test-001",
    "mode": "DEMO",
    "inputs": {
      "manuscript_text": "# Introduction\n\nThis is a test manuscript for validation.\n\n## Methods\n\nStandard methodology.\n\n## Results\n\nResults here.\n\n## Discussion\n\nConclusions here.\n\n## References\n\n1. Smith J. et al. Nature. 2024.",
      "target_journal": "Nature",
      "output_format": "text",
      "citation_style": "numbered",
      "include_cover_letter": false,
      "verify_references": false
    }
  }'
```

**Expected response:**
```json
{
  "dispatch_type": "agent",
  "agent_name": "agent-dissemination-formatter",
  "agent_url": "http://agent-dissemination-formatter-proxy:8000",
  "request_id": "manual-test-001"
}
```

---

## Phase 5: Monitor & Troubleshoot

### Check Container Health

```bash
# View running containers
docker compose ps | grep formatter

# Check logs
docker compose logs -f agent-dissemination-formatter-proxy

# Check health endpoint
curl http://localhost:3001/api/health
```

### Common Issues

#### Issue 1: Proxy container not starting

**Symptoms:**
- Container exits immediately
- `docker compose ps` shows "Exited (1)"

**Diagnosis:**
```bash
docker compose logs agent-dissemination-formatter-proxy
```

**Common causes:**
- Missing LANGSMITH_API_KEY or LANGSMITH_AGENT_ID
- Port 8000 already in use (unlikely with internal-only)
- Python dependency issue

**Fix:**
```bash
# Check environment
docker compose exec orchestrator env | grep LANGSMITH

# Restart proxy
docker compose up -d --force-recreate agent-dissemination-formatter-proxy
```

#### Issue 2: Router dispatch fails

**Symptoms:**
- 400 error: "UNSUPPORTED_TASK_TYPE"
- 500 error: "AGENT_ENDPOINTS_INVALID"

**Diagnosis:**
```bash
# Check if task type registered
docker compose exec orchestrator grep "DISSEMINATION_FORMATTING" /app/src/routes/ai-router.ts

# Check if agent in endpoints
docker compose exec orchestrator sh -c 'echo $AGENT_ENDPOINTS_JSON' | grep dissemination
```

**Fix:**
```bash
# Restart orchestrator to reload routing
docker compose up -d --force-recreate orchestrator
```

#### Issue 3: LangSmith API errors

**Symptoms:**
- Proxy returns 503 on /health/ready
- Agent execution fails with timeout or auth errors

**Diagnosis:**
```bash
# Test LangSmith connectivity from proxy
docker compose exec agent-dissemination-formatter-proxy \
  curl -f http://localhost:8000/health/ready
```

**Common causes:**
- Invalid LANGSMITH_API_KEY
- Wrong LANGSMITH_AGENT_ID
- LangSmith API down or rate-limited

**Fix:**
1. Verify API key: https://smith.langchain.com/settings
2. Verify agent ID: https://smith.langchain.com/ (check agent URL)
3. Update .env and restart proxy

---

## Phase 6: Integration Testing

### End-to-End Test

After deployment is stable, test the full flow:

```bash
# 1. Prepare test manuscript (save as test-manuscript.md)
cat > test-manuscript.md << 'MANUSCRIPT_EOF'
# Clinical Trial of Drug X for Disease Y

## Abstract
Background: Disease Y affects millions.
Methods: RCT with 200 patients.
Results: 60% improvement in primary endpoint.
Conclusion: Drug X is effective.

## Introduction
Disease Y is a major health concern...

## Methods
We conducted a randomized controlled trial...

## Results
Primary endpoint showed significant improvement...

## Discussion
Our findings demonstrate...

## References
1. Jones A, et al. Previous work. Lancet. 2023;401:1234-1240.
2. Smith B, et al. Related study. NEJM. 2022;386:567-578.
MANUSCRIPT_EOF

# 2. Get auth token
TOKEN=$(curl -X POST http://localhost:3001/api/dev-auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"dev","password":"dev"}' | jq -r '.token')

# 3. Call formatter
curl -X POST http://localhost:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"task_type\": \"DISSEMINATION_FORMATTING\",
    \"request_id\": \"e2e-test-$(date +%s)\",
    \"mode\": \"DEMO\",
    \"inputs\": {
      \"manuscript_text\": $(cat test-manuscript.md | jq -Rs .),
      \"target_journal\": \"PLOS ONE\",
      \"output_format\": \"text\",
      \"citation_style\": \"vancouver\",
      \"include_cover_letter\": true,
      \"verify_references\": true
    }
  }" | jq .

# 4. Check artifacts (if written)
ls -lh /data/artifacts/dissemination/formatting/
```

**Success criteria:**
- Response includes `formatted_manuscript`
- Response includes `validation_report` with compliance checks
- Response includes `reference_verification_report`
- Optional: `cover_letter` if requested
- No errors in logs

---

## Phase 7: Production Hardening (Optional)

### After Initial Deployment

1. **Monitor usage:**
   ```bash
   # Check proxy performance
   docker stats agent-dissemination-formatter-proxy
   
   # Check LangSmith usage in dashboard
   # Visit: https://smith.langchain.com/
   ```

2. **Add monitoring alerts:**
   - High memory usage (>400MB sustained)
   - Frequent 503 errors (LangSmith API issues)
   - Long response times (>4 minutes)

3. **Optimize if needed:**
   - Increase `LANGSMITH_TIMEOUT_SECONDS` if large manuscripts timeout
   - Add retry logic for transient LangSmith errors
   - Implement caching for journal guidelines

4. **Document costs:**
   - Track LangSmith API usage per month
   - Monitor TAVILY and Google Docs API calls
   - Document typical cost per manuscript formatting

---

## Phase 8: Integration with Stage 19 Workflow

### Current State

The agent is wired for **standalone invocation** via `/api/ai/router/dispatch`.

### Future: Integrate with Workflow Engine

**Goal:** Make Dissemination Formatter callable from Stage 19 of the 20-stage workflow.

**Steps:**
1. Update `services/worker/src/workflow_engine/stages/stage_19_dissemination.py`
2. Add dispatcher call to `agent-dissemination-formatter`
3. Wire input/output to/from previous stages
4. Add Stage 19 validation tests

**Reference:** See `stage_18_impact.py` or `stage_20_conference.py` for patterns

---

## Quick Reference Commands

### Check Status
```bash
# On ROSflow2
ssh user@rosflow2
cd /opt/researchflow/researchflow-production-main

# Service status
docker compose ps agent-dissemination-formatter-proxy

# Logs
docker compose logs --tail=50 agent-dissemination-formatter-proxy

# Health
curl http://localhost:3001/api/health
```

### Restart Service
```bash
docker compose up -d --force-recreate agent-dissemination-formatter-proxy
```

### Full Restart
```bash
docker compose down
docker compose up -d
```

### View All Agents
```bash
docker compose ps | grep agent-
```

---

## Success Metrics

### Deployment Success
- [ ] Proxy container running and healthy
- [ ] Preflight checks pass
- [ ] Router dispatch returns 200
- [ ] Health endpoints respond correctly
- [ ] No error logs after startup

### Operational Success
- [ ] First real manuscript formatted successfully
- [ ] Validation report accurate
- [ ] Reference verification works
- [ ] Cover letter generated (if requested)
- [ ] Response time <4 minutes for typical manuscript

### Integration Success
- [ ] Called from Stage 19 workflow
- [ ] Artifacts written to /data/artifacts/
- [ ] Output integrated with UI
- [ ] Error handling graceful

---

## Rollback Plan

If deployment causes issues:

```bash
# 1. Stop the proxy
docker compose stop agent-dissemination-formatter-proxy

# 2. Remove from AGENT_ENDPOINTS_JSON
# Edit .env or docker-compose.yml, remove agent-dissemination-formatter entry

# 3. Restart orchestrator
docker compose up -d --force-recreate orchestrator

# 4. Verify other agents still work
./scripts/hetzner-preflight.sh
```

**No data loss:** Formatter is stateless, only processes inputs to outputs.

---

## Documentation Links

### For Operators
- **Deployment Guide:** `docs/agents/dissemination-formatter/wiring.md`
- **Troubleshooting:** See "Phase 5: Monitor & Troubleshoot" above
- **Preflight Script:** `scripts/hetzner-preflight.sh`
- **Smoke Test:** `scripts/stagewise-smoke.sh` (CHECK_DISSEMINATION_FORMATTER=1)

### For Developers
- **Proxy Code:** `services/agents/agent-dissemination-formatter-proxy/`
- **Agent Config:** `services/agents/agent-dissemination-formatter/`
- **Router Integration:** `services/orchestrator/src/routes/ai-router.ts` (line 246)
- **API Contract:** `services/agents/agent-dissemination-formatter-proxy/README.md`

### For Reviewers
- **PR Checklist:** `PR_CHECKLIST_DISSEMINATION_FORMATTER.md`
- **Wiring Summary:** `DISSEMINATION_FORMATTER_WIRING_COMPLETE.md`
- **Architecture:** `LANGSMITH_AGENTS_PROXY_ARCHITECTURE.md` (if on branch)

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| PR Review | 1-2 days | Team availability |
| PR Approval | Same day | Reviewer approval |
| Merge | <5 min | Automated |
| Deployment | 15-30 min | Server access |
| Validation | 10-15 min | Preflight + smoke |
| First E2E Test | 30-60 min | Test manuscript ready |

**Total:** 2-3 days (mostly waiting for review)

---

## Contact & Support

### If You Encounter Issues

1. **Check logs first:**
   ```bash
   docker compose logs agent-dissemination-formatter-proxy
   docker compose logs orchestrator | grep -i dissemination
   ```

2. **Check LangSmith dashboard:**
   - https://smith.langchain.com/
   - Look for recent runs
   - Check for API errors

3. **Review documentation:**
   - `docs/agents/dissemination-formatter/wiring.md`
   - `services/agents/agent-dissemination-formatter-proxy/README.md`

4. **Rollback if needed** (see Rollback Plan above)

---

## Completion Checklist

### PR Phase
- [x] PR created (#33)
- [x] All commits pushed (4 commits)
- [x] Dockerfile validated (build + health ✓)
- [ ] Reviewers assigned
- [ ] PR approved
- [ ] PR merged

### Deployment Phase
- [ ] Environment variables added to .env
- [ ] Proxy service built
- [ ] Proxy service started
- [ ] Orchestrator restarted
- [ ] Preflight checks passed
- [ ] Smoke test passed (optional)

### Validation Phase
- [ ] Manual dispatch test passed
- [ ] First real manuscript formatted
- [ ] End-to-end test completed
- [ ] Documentation verified accurate
- [ ] Team trained on usage

---

**Current Phase:** ✅ PR Review (Phase 1)  
**Next Action:** Wait for PR approval, then deploy to ROSflow2  
**Estimated Time to Production:** 2-3 days

**PR Link:** https://github.com/ry86pkqf74-rgb/ROS_FLOW_2_1/pull/33
