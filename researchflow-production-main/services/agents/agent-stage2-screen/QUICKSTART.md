# Agent Stage 2 Screen - Quick Start Guide

## 5-Minute Setup

### 1. Start the Service

```bash
cd researchflow-production-main/services/agents/agent-stage2-screen
pip install -r requirements.txt
uvicorn app.main:app --port 8000 --reload
```

### 2. Test Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

### 3. Run Test Screening

```bash
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d @test_request.json
```

Expected output:
- ✅ 1 paper included (RCT on metformin)
- ✅ 2 papers excluded (pediatric case report, below year threshold)
- ✅ 1 duplicate removed
- ✅ 1 paper excluded (no metformin keyword)

## Docker Quick Start

```bash
# Build from repo root
cd researchflow-production-main
docker build -t agent-stage2-screen:latest \
  -f services/agents/agent-stage2-screen/Dockerfile .

# Run
docker run -p 8000:8000 \
  -e GOVERNANCE_MODE=DEMO \
  agent-stage2-screen:latest

# Test
curl http://localhost:8000/health
```

## Docker Compose Quick Start

```bash
cd researchflow-production-main

# Start all services
docker-compose up -d agent-stage2-screen

# Check logs
docker-compose logs -f agent-stage2-screen

# Test
curl http://localhost:8000/health
```

## Common Use Cases

### Case 1: Screen Papers with Inclusion Criteria

```json
{
  "request_id": "case1",
  "task_type": "STAGE2_SCREEN",
  "inputs": {
    "papers": [...],
    "criteria": {
      "inclusion": ["diabetes", "cardiovascular"],
      "year_min": 2020
    }
  }
}
```

### Case 2: Exclude Specific Study Types

```json
{
  "request_id": "case2",
  "task_type": "STAGE2_SCREEN",
  "inputs": {
    "papers": [...],
    "criteria": {
      "study_types_excluded": ["case_report", "review"]
    }
  }
}
```

### Case 3: Strict RCT-Only Screening

```json
{
  "request_id": "case3",
  "task_type": "STAGE2_SCREEN",
  "inputs": {
    "papers": [...],
    "criteria": {
      "study_types_required": ["randomized_controlled_trial"],
      "require_abstract": true
    }
  }
}
```

## Troubleshooting

### Import Error
```bash
# Ensure you're in the correct directory
cd services/agents/agent-stage2-screen
python3 -c "from agent import schemas; print('OK')"
```

### Port Already in Use
```bash
# Use different port
uvicorn app.main:app --port 8001 --reload
```

### Docker Build Fails
```bash
# Build from repo root (not agent directory)
cd researchflow-production-main
docker build -f services/agents/agent-stage2-screen/Dockerfile .
```

## Testing Checklist

- [ ] Health endpoint returns 200
- [ ] Sync endpoint accepts test_request.json
- [ ] Response has included/excluded/duplicates arrays
- [ ] Deduplication removes duplicate papers
- [ ] Exclusion criteria work (pediatric excluded)
- [ ] Year range filtering works (2018 paper excluded)
- [ ] Study type classification works (RCT identified)

## Development Workflow

1. **Make changes** to agent/*.py files
2. **Restart** uvicorn (auto-reloads in --reload mode)
3. **Test** with curl or test_request.json
4. **Validate** contract compliance
5. **Commit** when tests pass

## Next Steps

- Read [README.md](README.md) for full API documentation
- Check [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) for design details
- Review [test_request.json](test_request.json) for example payloads
- Run contract checker: `python3 scripts/check-agent-contract.py`

## Support

- Check agent logs: `docker-compose logs agent-stage2-screen`
- Review structured logs for request_id tracking
- Test with simple 1-paper payload first
- Verify AI Bridge is available if using AI enhancement

## Performance Tips

- Use `use_ai: false` for fast deterministic screening (default)
- Batch papers in groups of 100-500 for optimal performance
- Deduplication runs in O(n) time
- Consider year range filters to reduce processing load
