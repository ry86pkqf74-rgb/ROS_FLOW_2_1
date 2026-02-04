# 🚀 Stage 1 Protocol Design Agent - Staging Quick Start

## ⚡ **5-MINUTE STAGING DEPLOYMENT**

### Prerequisites Checklist
- [x] Docker and Docker Compose installed
- [x] 8GB+ RAM and 4+ CPU cores available  
- [x] Ports available: 3000, 3002, 8001, 5434, 6381, 11435
- [x] OpenAI API key (required for Stage 1 testing)

### 🏃‍♂️ **Rapid Deployment Steps**

```bash
# 1. Clone and configure environment (30 seconds)
git clone <repository-url>
cd researchflow
cp .env.staging.example .env.staging

# 2. Add your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" >> .env.staging

# 3. Deploy staging environment (3-4 minutes)
./scripts/staging-deploy.sh

# 4. Run Stage 1 tests (2 minutes)
./scripts/test-stage-1.sh
```

**Total Time: ~5-6 minutes to fully operational staging environment**

---

## 🧪 **IMMEDIATE VALIDATION TESTS**

### Test 1: Feature Flag Status (30 seconds)
```bash
# Check feature flag configuration
curl -s http://localhost:3002/api/feature-flags | jq '.["ENABLE_NEW_STAGE_1"]'
# Expected: true
```

### Test 2: Stage 1 PICO Extraction (2 minutes)
```bash
# Submit test research question
curl -X POST http://localhost:3002/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "stage_id": 1,
    "config": {
      "protocol_design": {
        "initial_message": "Does cognitive behavioral therapy reduce depression in adolescents compared to standard care?"
      }
    },
    "governance_mode": "DEMO"
  }'

# Get job_id from response, then check result:
curl http://localhost:3002/api/jobs/{job_id}/result | jq '.output.pico_elements'
```

### Test 3: Feature Flag Toggle (1 minute)  
```bash
# Toggle to legacy Stage 1
./scripts/staging-feature-toggle.sh disable

# Toggle back to new Stage 1
./scripts/staging-feature-toggle.sh enable
```

---

## 📊 **ACCESS POINTS & MONITORING**

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | User interface testing |
| **API** | http://localhost:3002 | Backend API access |
| **Grafana** | http://localhost:3003 | Performance monitoring |
| **Prometheus** | http://localhost:9090 | Metrics collection |

**Default Login:** `admin` / `staging123` (Grafana)

---

## 🔥 **COMMON QUICK FIXES**

### Issue: Services won't start
```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart with fresh state  
docker-compose -f docker-compose.staging.yml down --volumes
./scripts/staging-deploy.sh
```

### Issue: Stage 1 tests failing
```bash
# Check OpenAI API key
echo $OPENAI_API_KEY

# Restart worker service
docker-compose -f docker-compose.staging.yml restart worker

# Check logs
docker-compose -f docker-compose.staging.yml logs worker | tail -20
```

### Issue: Feature flag not working
```bash
# Manual toggle
export ENABLE_NEW_STAGE_1=true
docker-compose -f docker-compose.staging.yml restart orchestrator worker
```

---

## 🎯 **SUCCESS INDICATORS**

### ✅ **Green Light Indicators**
- All services showing "healthy" status
- Feature flag API responding with correct values
- Stage 1 tests completing with PICO elements extracted
- Frontend accessible and responsive
- Grafana showing metrics data

### ⚠️ **Yellow Light Indicators** 
- Some tests failing but core functionality works
- Slower than expected response times
- Feature flag toggle requires manual restart
- Monitoring data incomplete

### 🚨 **Red Light Indicators**
- Services failing to start
- No response from APIs
- OpenAI API key invalid/missing
- Complete test failure
- Docker resource exhaustion

---

## 📱 **DEMO WORKFLOW**

### Quick Demo Script (5 minutes)
1. **Open Frontend:** http://localhost:3000
2. **Create New Project:** Click "New Research Project"
3. **Enter Research Question:** 
   ```
   "Does early intervention with physical therapy reduce recovery time in ACL injuries compared to delayed treatment over 6 months?"
   ```
4. **Watch Stage 1 Execute:** Monitor PICO extraction in real-time
5. **Review Results:** Check extracted Population, Intervention, Comparator, Outcomes
6. **Verify Pipeline:** Confirm data flows to Stages 2 & 3
7. **Toggle Feature Flag:** Demonstrate A/B testing capability

### Expected Results
- **Population:** "ACL injury patients"
- **Intervention:** "Early physical therapy intervention"  
- **Comparator:** "Delayed treatment"
- **Outcomes:** ["Recovery time", "Functional outcomes"]
- **Quality Score:** ≥75/100

---

## 🛠️ **DEVELOPMENT MODE**

### Enable Hot Reloading
```bash
# Start with development overrides
docker-compose -f docker-compose.staging.yml \
  -f docker-compose.dev.override.yml up -d
```

### Debug Stage 1 Agent
```bash
# Access worker shell for debugging
docker-compose -f docker-compose.staging.yml exec worker bash

# View real-time logs
docker-compose -f docker-compose.staging.yml logs -f worker
```

### Manual Testing
```bash
# Test specific PICO extraction
python3 -c "
from services.worker.src.agents.protocol_design.agent import ProtocolDesignAgent
agent = ProtocolDesignAgent()
result = agent.extract_pico('your research question here')
print(result)
"
```

---

## 📞 **SUPPORT & ESCALATION**

### Self-Service Debugging
1. **Check logs:** `docker-compose logs [service]`
2. **Restart service:** `docker-compose restart [service]`
3. **Reset environment:** `./scripts/staging-deploy.sh`
4. **Run diagnostics:** `./scripts/test-stage-1.sh`

### Escalation Path
1. **Level 1:** Check troubleshooting section in deployment checklist
2. **Level 2:** Review GitHub issues and documentation
3. **Level 3:** Contact development team with logs and error details

### Useful Commands
```bash
# View all service status
docker-compose -f docker-compose.staging.yml ps

# Get service logs  
docker-compose -f docker-compose.staging.yml logs [service]

# Check resource usage
docker stats

# Clean slate restart
docker-compose -f docker-compose.staging.yml down --volumes
./scripts/staging-deploy.sh
```

---

## 🎊 **NEXT STEPS AFTER STAGING SUCCESS**

1. **Run Load Tests:** `./scripts/load-test-stage-1.sh`
2. **Performance Optimization:** Review Grafana dashboards
3. **User Acceptance Testing:** Invite team members to test
4. **Production Planning:** Review production rollout plan
5. **Team Training:** Schedule knowledge transfer sessions

---

**🚀 Happy testing! Your Stage 1 Protocol Design Agent staging environment is ready for validation! 🧬**

**Need help?** Check the full deployment checklist: `STAGE_1_STAGING_DEPLOYMENT_CHECKLIST.md`