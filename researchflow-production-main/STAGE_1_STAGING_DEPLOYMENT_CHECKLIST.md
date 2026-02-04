# 📋 Stage 1 Protocol Design Agent - Staging Deployment Checklist

## 🏗️ **DEPLOYMENT READINESS VERIFICATION**

### ✅ Pre-Deployment Requirements
- [ ] All Stage 1 implementation code committed and pushed (commit: cd47e2d)
- [ ] Test pass rate ≥ 75% (Current: 75% - 3/4 tests passing)
- [ ] Feature flag system operational (`ENABLE_NEW_STAGE_1`)
- [ ] PICO framework quality score ≥ 75/100 (Current: 75/100)
- [ ] Stages 2 & 3 integration validated
- [ ] Documentation complete and accessible

### ✅ Environment Setup
- [ ] Docker and Docker Compose installed
- [ ] Required API keys configured (OpenAI, Anthropic)
- [ ] Staging environment file created (`.env.staging`)
- [ ] Available ports confirmed (3000, 3002, 8001, 5434, 6381, 11435)
- [ ] Sufficient system resources (8GB+ RAM, 4+ CPU cores)

---

## 🚀 **STAGING DEPLOYMENT PROCESS**

### Phase 1: Environment Preparation
```bash
# 1. Clone/update repository
git pull origin main

# 2. Configure environment
cp .env.staging.example .env.staging
# Edit .env.staging with your API keys

# 3. Deploy staging environment
./scripts/staging-deploy.sh
```

**Validation Checkpoints:**
- [ ] All services healthy and running
- [ ] Frontend accessible at http://localhost:3000
- [ ] API responding at http://localhost:3002
- [ ] Feature flag `ENABLE_NEW_STAGE_1=true` confirmed
- [ ] Ollama model downloaded and ready

### Phase 2: Feature Flag Testing
```bash
# Test feature flag toggling
./scripts/staging-feature-toggle.sh

# Verify both states work:
# - ENABLE_NEW_STAGE_1=true  (Protocol Design Agent)
# - ENABLE_NEW_STAGE_1=false (Legacy Upload Stage)
```

**Validation Checkpoints:**
- [ ] Feature flag toggle successful
- [ ] Services restart correctly
- [ ] Stage implementation switches as expected
- [ ] No configuration conflicts

### Phase 3: PICO Pipeline Integration Testing
```bash
# Run comprehensive Stage 1 tests
./scripts/test-stage-1.sh
```

**Validation Checkpoints:**
- [ ] PICO framework extraction working
- [ ] Protocol generation producing quality outputs
- [ ] Stage 1→2→3 data flow validated
- [ ] Quality gates functioning properly
- [ ] Performance within acceptable ranges

### Phase 4: Performance & Load Testing
```bash
# Run load testing (3 concurrent jobs, 5 minutes)
./scripts/load-test-stage-1.sh 3 300

# Monitor system resources
docker stats
```

**Performance Targets:**
- [ ] Success rate ≥ 95%
- [ ] Average response time ≤ 60 seconds
- [ ] System resource usage stable
- [ ] No memory leaks detected
- [ ] Concurrent execution support validated

---

## 📊 **MONITORING & VALIDATION**

### Core Metrics Dashboard (Grafana: http://localhost:3003)
- [ ] Stage 1 execution metrics
- [ ] PICO extraction success rate
- [ ] Protocol generation quality scores
- [ ] System resource utilization
- [ ] Error rate tracking

### Key Performance Indicators (KPIs)
| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Test Pass Rate | ≥75% | 75% | ✅ |
| PICO Quality Score | ≥75/100 | 75/100 | ✅ |
| Feature Flag Toggle | <30s | TBD | ⏳ |
| Stage 1 Response Time | ≤60s | TBD | ⏳ |
| Pipeline Integration | 100% | TBD | ⏳ |

### User Acceptance Testing Scenarios
- [ ] **Scenario 1:** Simple research question → PICO extraction
- [ ] **Scenario 2:** Complex multi-arm study → Protocol generation
- [ ] **Scenario 3:** Feature flag toggle → Seamless transition
- [ ] **Scenario 4:** Stage 1→2→3 pipeline → End-to-end flow
- [ ] **Scenario 5:** Concurrent users → Performance validation

---

## 🔧 **TROUBLESHOOTING GUIDE**

### Common Issues & Solutions

**Issue: Services fail to start**
```bash
# Check Docker resources
docker system df
docker system prune -f

# Check logs
docker-compose -f docker-compose.staging.yml logs
```

**Issue: Feature flag not toggling**
```bash
# Manual restart
docker-compose -f docker-compose.staging.yml restart orchestrator worker

# Verify environment
cat .env.staging | grep ENABLE_NEW_STAGE_1
```

**Issue: Poor Stage 1 performance**
```bash
# Check Ollama model status
docker-compose -f docker-compose.staging.yml exec ollama ollama ps

# Monitor resource usage
docker stats --no-stream
```

**Issue: PICO extraction failing**
```bash
# Check AI provider connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check worker logs
docker-compose -f docker-compose.staging.yml logs worker | grep -i error
```

### Emergency Rollback
```bash
# Immediate rollback to legacy Stage 1
./scripts/staging-feature-toggle.sh disable

# Or complete environment reset
docker-compose -f docker-compose.staging.yml down --volumes
```

---

## 🎯 **SUCCESS CRITERIA**

### ✅ Staging Deployment Complete When:
- [ ] All services running and healthy
- [ ] Feature flag system operational
- [ ] Stage 1 tests passing (≥75% pass rate)
- [ ] PICO pipeline integration validated
- [ ] Performance targets met
- [ ] User acceptance testing completed
- [ ] Monitoring dashboards functional
- [ ] Team trained on staging environment

### 🚨 **Go/No-Go Decision Points**

**🟢 GO for Production Rollout:**
- All success criteria met
- No critical bugs identified
- Performance within targets
- Team confidence high

**🔴 NO-GO - Additional Work Required:**
- Test pass rate <75%
- Critical feature flag issues
- Performance below targets
- Major integration problems

---

## 📝 **STAGING DEPLOYMENT SIGN-OFF**

### Technical Validation
- [ ] **DevOps Engineer:** Environment deployed successfully
- [ ] **Backend Engineer:** Stage 1 agent functioning properly
- [ ] **Frontend Engineer:** UI integration validated
- [ ] **QA Engineer:** Test scenarios completed
- [ ] **Product Manager:** User acceptance criteria met

### Deployment Approval
- [ ] **Technical Lead:** Code quality and architecture approved
- [ ] **Product Owner:** Feature functionality validated
- [ ] **Engineering Manager:** Performance and reliability confirmed

**Staging Deployment Approved By:** `_________________` **Date:** `_________`

**Ready for Production Rollout:** `☐ Yes` `☐ No` `☐ Needs Review`

---

## 🔄 **NEXT PHASE: PRODUCTION ROLLOUT**

Once staging validation is complete, proceed to:
1. **Production Environment Setup**
2. **Gradual Feature Flag Rollout (5% → 25% → 50% → 100%)**
3. **A/B Testing vs Legacy Stage 1**
4. **Full Production Monitoring**
5. **Team Training & Documentation**

**Estimated Timeline:** 2-3 weeks after staging validation