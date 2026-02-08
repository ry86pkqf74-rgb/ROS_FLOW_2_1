# Resilience Architecture Advisor Proxy

FastAPI proxy service that adapts the ResearchFlow agent contract to LangSmith cloud API for the **Resilience Architecture Advisor** agent.

## Overview

The Resilience Architecture Advisor is an expert agent specializing in:
- Designing retry logic and fault-tolerant patterns for LangGraph applications
- Analyzing system resilience requirements
- Recommending best practices for error handling and recovery
- Reviewing architecture for robustness and reliability

## Architecture

This proxy service consists of three sub-agents:
1. **Architecture_Doc_Builder** - Creates documentation for resilience patterns
2. **PR_Resilience_Reviewer** - Reviews pull requests for resilience best practices
3. **Resilience_Research_Worker** - Researches industry best practices for fault tolerance

## Environment Variables

Required environment variables:

```bash
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_RESILIENCE_ARCHITECTURE_ADVISOR_AGENT_ID=your_agent_id
LANGSMITH_API_URL=https://api.smith.langchain.com/v1  # default
LANGSMITH_TIMEOUT_SECONDS=300  # default
```

## API Endpoints

### Health Check
- `GET /health` - Basic health status
- `GET /health/ready` - Readiness check with LangSmith API connectivity

### Agent Execution
- `POST /agents/run/sync` - Synchronous execution (waits for complete response)
- `POST /agents/run/stream` - Streaming execution (SSE)

### Request Format

```json
{
  "input": {
    "task": "Review our retry logic for database connections",
    "context": "We're using PostgreSQL with connection pooling..."
  },
  "config": {},
  "stream": false
}
```

## Docker Build

```bash
docker build -t agent-resilience-architecture-advisor-proxy .
docker run -p 8000:8000 --env-file .env agent-resilience-architecture-advisor-proxy
```

## Local Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Integration with ResearchFlow

This service is registered in:
- `docker-compose.yml` - Service definition
- `ai-router.ts` - Task type mapping (RESILIENCE_ARCHITECTURE)
- `task-contract.ts` - Input validation contract
- `AGENT_INVENTORY.md` - Fleet documentation

## Usage Example

```python
import requests

response = requests.post(
    "http://localhost:8000/agents/run/sync",
    json={
        "input": {
            "task": "Design retry strategy for API calls",
            "requirements": ["exponential backoff", "circuit breaker pattern"]
        }
    }
)

print(response.json()["output"])
```
