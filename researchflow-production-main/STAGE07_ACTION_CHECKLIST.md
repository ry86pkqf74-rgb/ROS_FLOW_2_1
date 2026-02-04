# ✅ Stage 7 Statistical Analysis - Action Checklist

**Use this checklist to complete the deployment**

---

## Phase 1: Deployment (15 minutes)

### Step 1: Commit Changes
```bash
□ git status                                    # Review changes
□ git add migrations/018_stage07_statistical_analysis.sql
□ git add STAGE07_*.md SESSION_SUMMARY_*.md
□ git commit -m "feat(stage7): add statistical analysis migration and docs"
□ git push origin main
```

### Step 2: Rebuild Docker Images
```bash
□ docker-compose build worker orchestrator      # ~5-10 minutes
□ docker-compose up -d                          # Restart services
□ docker-compose ps                             # Verify running
```

### Step 3: Verify Deployment
```bash
□ curl http://localhost:8000/api/analysis/statistical/health
  # Should show: "status": "healthy", "agent_loaded": true

□ docker exec researchflow-production-postgres-1 \
    psql -U ros -d ros -c "\dt statistical*"
  # Should show 11 tables

□ docker-compose logs worker | grep "Statistical analysis"
  # Should show: "Statistical analysis router registered"
```

---

## Phase 2: Integration Testing (30 minutes)

### Test 1: Worker Health
```bash
□ curl http://localhost:8000/api/analysis/statistical/health
□ Verify response shows agent_loaded: true
```

### Test 2: List Capabilities
```bash
□ curl http://localhost:8000/api/analysis/statistical/capabilities
□ Verify 7 test types are listed
```

### Test 3: Run Simple Analysis
```bash
□ Create test_data.json with sample data
□ curl -X POST http://localhost:8000/api/analysis/statistical \
    -H "Content-Type: application/json" \
    -d @test_data.json
□ Verify response contains descriptive stats, test results, effect sizes
```

### Test 4: Verify Database Storage
```bash
□ docker exec researchflow-production-postgres-1 \
    psql -U ros -d ros -c "SELECT COUNT(*) FROM statistical_analysis_results;"
□ Should show at least 1 record after test
```

### Test 5: Full Stack Test (Orchestrator)
```bash
□ curl -X POST http://localhost:3001/api/research/test-001/stage/7/execute \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer TOKEN" \
    -d '{...}'
□ Verify complete workflow works
```

---

## Phase 3: Frontend Development (4-6 hours)

### Component Creation
```bash
□ Create services/web/src/components/stages/Stage07StatisticalAnalysis.tsx
□ Add model configuration form
□ Add variable selection interface
□ Add results display area
□ Add visualization rendering
□ Add export functionality
```

### Integration
```bash
□ Register component in stage navigation
□ Connect to API endpoints
□ Test data flow
□ Add error handling
```

---

## Phase 4: Documentation (1 hour)

### User Documentation
```bash
□ Add usage guide for researchers
□ Document test selection process
□ Explain interpretation of results
□ Add APA formatting examples
```

### Developer Documentation
```bash
□ Update API documentation
□ Add example requests/responses
□ Document database schema
□ Create troubleshooting guide
```

---

## Quick Status Check

Run this to see overall status:

```bash
echo "=== STAGE 7 STATUS CHECK ==="
echo ""
echo "1. Database Tables:"
docker exec researchflow-production-postgres-1 \
  psql -U ros -d ros -c "\dt statistical*" | wc -l
echo "   (Should be > 10)"
echo ""
echo "2. Worker Health:"
curl -s http://localhost:8000/api/analysis/statistical/health | \
  python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"   Status: {d.get('status')}, Agent: {d.get('agent_loaded')}\")"
echo ""
echo "3. Services Running:"
docker-compose ps | grep -E "worker|orchestrator" | wc -l
echo "   (Should be 2)"
```

---

## Troubleshooting

### If "agent_loaded": false
```bash
□ Check worker logs: docker-compose logs worker | tail -50
□ Verify import: docker exec researchflow-production-worker-1 \
    python -c "from agents.analysis import StatisticalAnalysisAgent; print('OK')"
□ Rebuild: docker-compose build --no-cache worker
```

### If routes not found
```bash
□ Check route registration: docker-compose logs worker | grep router
□ Rebuild images: docker-compose build
□ Restart: docker-compose up -d
```

### If database errors
```bash
□ Verify tables: docker exec researchflow-production-postgres-1 \
    psql -U ros -d ros -c "\dt"
□ Re-run migration if needed
□ Check foreign key constraints
```

---

## Success Criteria

✅ All phases complete when:
- [ ] Docker images rebuilt and running
- [ ] Health endpoint shows agent_loaded: true
- [ ] Can execute statistical analysis via API
- [ ] Results are stored in database
- [ ] Frontend component displays results
- [ ] End-to-end workflow tested
- [ ] Documentation updated

---

**Current Phase**: Phase 1 - Deployment  
**Next Phase**: Phase 2 - Integration Testing  
**ETA to Complete**: 6-8 hours total

**Created**: 2024-02-04
