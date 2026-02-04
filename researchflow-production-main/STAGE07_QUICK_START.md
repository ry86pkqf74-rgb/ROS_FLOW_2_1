# 🚀 Stage 7 Statistical Analysis - Quick Start

## TL;DR
Everything is ready except the API endpoint. Copy the code from the guide and you're done.

## ⚡ Super Quick Start (15 minutes)

### Step 1: Apply Migration (2 min)
```bash
psql -h localhost -U postgres -d researchflow_dev < migrations/018_stage07_statistical_analysis.sql
```

### Step 2: Create API Route (5 min)
```bash
# Create the file
touch services/orchestrator/routes/statistical-analysis.ts

# Copy the ENTIRE code from STAGE07_API_IMPLEMENTATION_GUIDE.md section "1. Create API Route File"
# Paste into services/orchestrator/routes/statistical-analysis.ts
```

### Step 3: Register Route (1 min)
```typescript
// In services/orchestrator/server.ts, add:
import statisticalAnalysisRoutes from './routes/statistical-analysis';
app.use('/api/statistical-analysis', statisticalAnalysisRoutes);
```

### Step 4: Test (7 min)
```bash
# Terminal 1: Start backend
cd services/orchestrator && npm run dev

# Terminal 2: Start worker
cd services/worker && python api_server.py

# Terminal 3: Start frontend
cd services/web && npm run dev

# Browser: Navigate to http://localhost:3000/stage/7
```

## 📊 What You Get

After these 15 minutes, users can:
- ✅ Configure statistical models in the UI
- ✅ Select variables for analysis
- ✅ Run t-tests, ANOVA, chi-square tests
- ✅ View results with p-values and effect sizes
- ✅ Check statistical assumptions
- ✅ Export results (JSON, CSV, HTML)
- ✅ Compare multiple models
- ✅ Store all results in database

## 🧪 Test It

```bash
# Quick API test
curl -X POST http://localhost:3000/api/statistical-analysis/research/test-123/stage/7/execute \
  -H "Content-Type: application/json" \
  -d '{
    "analysisName": "Quick Test",
    "testType": "t_test_independent",
    "dependentVariable": "outcome",
    "independentVariables": ["group"],
    "data": {
      "groups": [[10, 12, 14, 11, 13], [15, 17, 19, 16, 18]],
      "outcomes": [[10, 12, 14, 11, 13], [15, 17, 19, 16, 18]]
    }
  }'

# Should return:
# {
#   "success": true,
#   "analysisId": "uuid-here",
#   "results": { ... }
# }
```

## 📁 Files You Need

All files are ready:
- ✅ `migrations/018_stage07_statistical_analysis.sql` - Database
- ✅ `services/worker/agents/analysis/statistical_analysis_agent.py` - Backend
- ✅ `services/web/src/components/stages/Stage07StatisticalModeling.tsx` - Frontend
- ⏳ `services/orchestrator/routes/statistical-analysis.ts` - You create this (copy from guide)

## 🎯 Success Criteria

You'll know it's working when:
1. Migration runs without errors ✅
2. API responds to POST requests ✅
3. Frontend shows "Running analysis..." ✅
4. Results appear in the UI ✅
5. Database has records in `statistical_analysis_results` ✅

## 🐛 Troubleshooting

### Migration fails
```bash
# Check connection
psql -h localhost -U postgres -d researchflow_dev -c "SELECT 1;"

# Check if tables exist
psql -h localhost -U postgres -d researchflow_dev -c "\dt statistical*"
```

### API not responding
```bash
# Check orchestrator is running
curl http://localhost:3000/api/health

# Check worker is running
curl http://localhost:8000/health
```

### Frontend not connecting
- Check browser console for errors
- Verify API URL in network tab
- Check CORS settings in orchestrator

## 📚 Need More Details?

Comprehensive guides available:
- `STAGE07_COMPLETION_SUMMARY.md` - Full overview
- `STAGE07_API_IMPLEMENTATION_GUIDE.md` - Complete API code
- `STAGE07_MERCURY_ENHANCEMENTS.md` - Future enhancements
- `STAGE07_NEXT_STEPS_COMPLETE.md` - Detailed checklist

## 💡 Pro Tips

1. **Start Simple**: Test with t-test first, then try other tests
2. **Use Console**: Browser console shows helpful error messages
3. **Check Database**: Query `statistical_analysis_results` to see stored data
4. **Mock Data**: Use the test data in the API guide for quick testing

## ✨ That's It!

15 minutes to production-ready statistical analysis. Good luck! 🎉

---

**Questions?** Check the detailed guides or the existing agent documentation at:
- `services/worker/agents/analysis/STATISTICAL_ANALYSIS_README.md`
- `services/worker/agents/analysis/IMPLEMENTATION_SUMMARY.md`
