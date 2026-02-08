# Hypothesis Refiner Agent Proxy

LangSmith cloud proxy for the Hypothesis Refiner agent.

## Overview

This service is a thin FastAPI proxy that adapts ResearchFlow's agent contract to LangSmith API calls. It enables hypothesis refinement operations using PICOT/SMART frameworks.

## Architecture

- **Proxy Type**: LangSmith cloud-hosted agent
- **Canonical AgentKey**: `agent-hypothesis-refiner-proxy`
- **TaskType**: `HYPOTHESIS_REFINEMENT`
- **Port**: 8000 (internal)

## Endpoints

### Health Checks
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (validates LangSmith connectivity)

### Agent Operations
- `POST /agents/run/sync` - Synchronous hypothesis refinement
- `POST /agents/run/stream` - Streaming hypothesis refinement (SSE)

## Environment Variables

Required:
- `LANGSMITH_API_KEY` - LangSmith API key
- `LANGSMITH_AGENT_ID` - LangSmith assistant ID for Hypothesis Refiner

Optional:
- `LANGSMITH_API_URL` - LangSmith API URL (default: https://api.smith.langchain.com/api/v1)
- `LANGSMITH_TIMEOUT_SECONDS` - Request timeout (default: 300)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LANGCHAIN_PROJECT` - LangChain project name (default: researchflow-hypothesis-refiner)
- `LANGCHAIN_TRACING_V2` - Enable LangChain tracing (default: false)

## Input Parameters

Supported input fields (all optional):
- `research_question` - Research question text
- `hypothesis` - Initial hypothesis (may be vague or well-formed)
- `context` - Additional context or background
- `constraints` - Study constraints or limitations
- `variables` - Variables to consider
- `population` - Target population (PICOT)
- `intervention` - Intervention (PICOT)
- `comparison` - Comparison group (PICOT)
- `outcomes` - Outcome measures (PICOT)
- `study_design` - Preferred study design
- `citations` - Existing literature citations
- `output_format` - Desired output format

## Output Structure

Standard response includes:
- `refined_hypotheses` - Array of refined PICOT-structured hypotheses
- `evidence_summary` - Supporting evidence synthesis
- `scoring_matrix` - Hypothesis scoring on feasibility, novelty, ethics
- `google_doc_url` - Link to detailed refinement report
- `recommendations` - Next steps and recommendations
- `metadata` - Additional metadata
- `langsmith_run_id` - LangSmith execution trace ID

## Security & Compliance

- **PHI-safe logging**: Never logs request/response bodies
- Only logs: `status_code`, `request_id`, `task_type`, `exception type`
- No secrets committed to repository

## Local Development

```bash
# Build the image
docker build -t agent-hypothesis-refiner-proxy -f services/agents/agent-hypothesis-refiner-proxy/Dockerfile .

# Run locally (requires env vars)
docker run -p 8000:8000 \
  -e LANGSMITH_API_KEY=$LANGSMITH_API_KEY \
  -e LANGSMITH_AGENT_ID=$LANGSMITH_HYPOTHESIS_REFINER_AGENT_ID \
  agent-hypothesis-refiner-proxy

# Health check
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

## Validation

See orchestrator validation scripts:
- `scripts/hetzner-preflight.sh` - Pre-deployment health validation
- `scripts/stagewise-smoke.sh` - Smoke test with fixture payload

## Documentation

For integration details, see:
- `docs/agents/agent-hypothesis-refiner-proxy/wiring.md`
- `AGENT_INVENTORY.md`
