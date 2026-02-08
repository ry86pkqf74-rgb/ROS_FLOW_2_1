# Results Interpretation Agent - Documentation Hub

Central documentation index for the Results Interpretation Agent.

## Quick Links

### Essential Docs (Start Here)

1. **[Deployment Guide](./DEPLOYMENT.md)** 📦 - Complete deployment walkthrough
2. **[Environment Variables](./ENVIRONMENT.md)** ⚙️ - Required configuration
3. **[Wiring Reference](./wiring.md)** 🔧 - Canonical technical reference

### Additional Resources

- **[Agent Inventory Entry](../../../AGENT_INVENTORY.md)** - Agent overview and status
- **[Capabilities Report](../../inventory/capabilities.md)** - LangSmith agents section
- **[Workflow Integration](../../../services/agents/agent-results-interpretation/WORKFLOW_INTEGRATION.md)** - Integration patterns

## What is the Results Interpretation Agent?

A LangSmith-hosted multi-agent system that interprets research results across multiple domains:
- Clinical trials
- Social science studies  
- Behavioral research
- Survey data

### Key Features

- **4-section structured reports:**
  - Findings narrative
  - Statistical assessment
  - Bias & limitations
  - Implications

- **4 sub-workers:**
  - Literature Research Worker
  - Methodology Audit Worker
  - Section Draft Worker
  - Draft Refinement Worker

- **Domain-specific skills:**
  - Clinical trials analysis
  - Survey methodology

- **Output formats:**
  - JSON structured report
  - Google Docs export

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      ResearchFlow                            │
│                                                               │
│  ┌──────────────┐         ┌────────────────────────────┐   │
│  │ Orchestrator │ ─────>  │ agent-results-             │   │
│  │              │         │ interpretation-proxy       │   │
│  │ /api/ai/     │         │                            │   │
│  │ router/      │         │ Port: 8000 (internal)      │   │
│  │ dispatch     │         │ Health: /health, /ready    │   │
│  └──────────────┘         └────────────┬───────────────┘   │
│                                         │                    │
└─────────────────────────────────────────┼────────────────────┘
                                          │ HTTPS
                                          │ auth: LANGSMITH_API_KEY
                                          │
                          ┌───────────────▼────────────────┐
                          │   LangSmith Cloud              │
                          │                                │
                          │  ┌──────────────────────────┐ │
                          │  │ Results Interpretation   │ │
                          │  │ Agent                    │ │
                          │  │                          │ │
                          │  │  Sub-workers:            │ │
                          │  │  - Literature Research   │ │
                          │  │  - Methodology Audit     │ │
                          │  │  - Section Draft         │ │
                          │  │  - Draft Refinement      │ │
                          │  └──────────────────────────┘ │
                          │                                │
                          └────────────────────────────────┘
```

## Deployment Status

| Component | Status | Notes |
|-----------|--------|-------|
| Router registration | ✅ Deployed | Task types: `RESULTS_INTERPRETATION`, `STATISTICAL_ANALYSIS` |
| Proxy service | ✅ Deployed | `agent-results-interpretation-proxy` |
| Docker Compose | ✅ Deployed | Service defined and configured |
| AGENT_ENDPOINTS_JSON | ✅ Deployed | Proxy URL registered |
| Health checks | ✅ Deployed | `/health`, `/health/ready` |
| Validation | ✅ Deployed | Preflight + smoke tests |
| LangSmith agent | ⚠️ Requires setup | Need API key + agent ID |

## Getting Started

### For Operators (Deploy to Server)

1. **Read:** [Deployment Guide](./DEPLOYMENT.md)
2. **Configure:** Get LangSmith credentials (API key + agent ID)
3. **Deploy:** Add env vars, build proxy, restart services
4. **Verify:** Run preflight + smoke tests
5. **Monitor:** Check LangSmith UI for traces

### For Developers (Local Development)

1. **Read:** [Environment Variables](./ENVIRONMENT.md)
2. **Setup:** Copy `.env.example`, add LangSmith credentials
3. **Run:** `docker compose up agent-results-interpretation-proxy`
4. **Test:** `curl http://localhost:8000/health`

### For Researchers (Use the Agent)

The agent is invoked automatically via workflow stages or can be called directly:

```bash
curl -X POST http://your-server:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "my-analysis-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": "Your statistical results here...",
      "study_metadata": {
        "study_type": "RCT",
        "domain": "clinical"
      }
    }
  }'
```

## Troubleshooting

### Quick Diagnostics

```bash
# Check proxy is running
docker compose ps agent-results-interpretation-proxy

# Check health
docker compose exec agent-results-interpretation-proxy curl http://localhost:8000/health

# Check LangSmith connectivity
docker compose exec agent-results-interpretation-proxy curl http://localhost:8000/health/ready

# View logs
docker compose logs agent-results-interpretation-proxy

# Check env vars
docker compose exec agent-results-interpretation-proxy env | grep LANGSMITH
```

### Common Issues

| Issue | Solution |
|-------|----------|
| 503 on /health/ready | Check LANGSMITH_API_KEY is set |
| 401 from LangSmith | Regenerate API key in LangSmith UI |
| 404 from LangSmith | Verify LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID |
| Timeout errors | Increase LANGSMITH_TIMEOUT_SECONDS |
| AGENT_NOT_CONFIGURED | Recreate orchestrator to load updated AGENT_ENDPOINTS_JSON |

Full troubleshooting: [Deployment Guide - Troubleshooting](./DEPLOYMENT.md#troubleshooting)

## Environment Variables Reference

### Required
- `LANGSMITH_API_KEY` - LangSmith API key
- `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID` - Agent UUID from LangSmith

### Optional
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: `180`
- `LANGCHAIN_PROJECT` - Default: `researchflow-results-interpretation`
- `LANGCHAIN_TRACING_V2` - Default: `false`
- `GOOGLE_DOCS_API_KEY` - For report export

Full reference: [Environment Variables](./ENVIRONMENT.md)

## API Reference

### Proxy Endpoints

- `GET /health` - Health check
- `GET /health/ready` - Readiness check (validates LangSmith)
- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - Streaming execution (SSE)

### Router Integration

- **Endpoint:** `POST /api/ai/router/dispatch`
- **Task types:** `RESULTS_INTERPRETATION`, `STATISTICAL_ANALYSIS`
- **Auth:** Requires `WORKER_SERVICE_TOKEN` or user JWT with `ANALYZE` permission

Full reference: [Wiring Reference](./wiring.md)

## Validation

### Preflight Checks
```bash
./scripts/hetzner-preflight.sh
```

Verifies:
- ✅ LANGSMITH_API_KEY configured
- ✅ LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID configured
- ✅ Router registration
- ✅ AGENT_ENDPOINTS_JSON includes agent
- ✅ Proxy service healthy
- ✅ LangSmith API reachable

### Smoke Tests
```bash
CHECK_RESULTS_INTERPRETATION=1 DEV_AUTH=true ./scripts/stagewise-smoke.sh
```

Tests:
- ✅ Router dispatch
- ✅ Agent execution
- ✅ Response format
- ✅ Artifact generation

## Contributing

When updating agent configuration or documentation:

1. **Update wiring.md first** - It's the canonical reference
2. **Update other docs to reference wiring.md** - Don't duplicate
3. **Test changes** - Run preflight + smoke tests
4. **Update inventory** - Keep AGENT_INVENTORY.md in sync
5. **Document** - Add notes to this README

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-08 | 1.0.0 | Initial implementation - proxy service deployed |
| 2026-02-08 | 0.1.0 | Agent imported from LangSmith, documentation only |

## Support & Resources

- **LangSmith UI:** https://smith.langchain.com/
- **Agent Builder Docs:** https://docs.smith.langchain.com/
- **ResearchFlow Docs:** `docs/README.md`
- **Issues:** Tag with `agent:results-interpretation`
