# Results Interpretation Agent - Environment Variables

## Required Variables

Add these to your `.env` file to enable the Results Interpretation Agent:

```bash
# LangSmith API Configuration (REQUIRED)
LANGSMITH_API_KEY=<your-langsmith-api-key>

# Results Interpretation Agent ID (REQUIRED)
# Get this from LangSmith UI: https://smith.langchain.com/
# Navigate to: Agents → Results Interpretation Agent → Copy Agent ID
LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=YOUR_AGENT_UUID_HERE
```

## Optional Variables

```bash
# LangSmith API URL (default: https://api.smith.langchain.com/api/v1)
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1

# Timeout for agent execution (default: 180 seconds = 3 minutes)
LANGSMITH_TIMEOUT_SECONDS=180

# LangSmith project for tracing (default: researchflow-results-interpretation)
LANGCHAIN_PROJECT=researchflow-results-interpretation

# Enable LangSmith tracing (default: false)
LANGCHAIN_TRACING_V2=false

# Log level for proxy service (default: INFO)
AGENT_LOG_LEVEL=INFO
```

## How to Get Your LangSmith Agent ID

1. Log in to LangSmith: https://smith.langchain.com/
2. Navigate to **Agents** in the left sidebar
3. Find **Results Interpretation Agent** (or your custom agent name)
4. Click on the agent to open details
5. Copy the **Agent ID** (UUID format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
6. Add to `.env`: `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID=<copied-uuid>`

## Verification

After setting environment variables:

```bash
# Recreate the orchestrator and proxy services
docker compose up -d --force-recreate orchestrator agent-results-interpretation-proxy

# Check proxy health
docker compose exec agent-results-interpretation-proxy curl -f http://localhost:8000/health

# Check readiness (validates LangSmith connectivity)
docker compose exec agent-results-interpretation-proxy curl -f http://localhost:8000/health/ready

# Test dispatch via orchestrator
curl -X POST http://127.0.0.1:3001/api/ai/router/dispatch \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "RESULTS_INTERPRETATION",
    "request_id": "test-001",
    "mode": "DEMO",
    "inputs": {
      "results_data": "RCT N=200, HR=0.72 (95% CI 0.58-0.89, p=0.003)",
      "study_metadata": {
        "study_type": "RCT",
        "domain": "clinical"
      }
    }
  }'
```

## Troubleshooting

### Error: "LANGSMITH_API_KEY not configured"
- Ensure `LANGSMITH_API_KEY` is set in `.env`
- Restart services: `docker compose restart orchestrator agent-results-interpretation-proxy`

### Error: "Cannot reach LangSmith API"
- Check internet connectivity from Docker containers
- Verify `LANGSMITH_API_URL` is correct
- Check firewall rules

### Error: "LangSmith API error: 401"
- Invalid API key format or expired key
- Generate new key from LangSmith UI

### Error: "LangSmith API error: 404"
- Invalid `LANGSMITH_RESULTS_INTERPRETATION_AGENT_ID`
- Verify agent ID in LangSmith UI
- Ensure agent is deployed and active

### Timeout errors
- Increase `LANGSMITH_TIMEOUT_SECONDS` (e.g., to 300 for 5 minutes)
- Check LangSmith agent performance in UI
- Consider disabling refinement workers for faster responses
