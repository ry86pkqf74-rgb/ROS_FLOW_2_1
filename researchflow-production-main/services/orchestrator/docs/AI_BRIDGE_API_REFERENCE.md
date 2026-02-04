# AI Bridge API Reference

## Overview

The AI Bridge provides a clean interface for Python LangGraph agents to access the TypeScript AI Router. It handles authentication, routing, cost tracking, and compliance for all LLM interactions.

**Architecture**: `Python Worker → AI Bridge → AI Router → LLM Provider`

## Base URL

```
http://localhost:3001/api/ai-bridge
```

## Authentication

All endpoints require authentication. Include user context in requests:

```http
Authorization: Bearer <jwt-token>
```

## Endpoints

### Health Check

#### `GET /health`

Returns the health status of the AI Bridge and its dependencies.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-30T10:00:00.000Z",
  "bridge": {
    "version": "1.0.0",
    "uptime": 3600,
    "healthy": true
  },
  "dependencies": {
    "aiRouter": {
      "healthy": true,
      "latencyMs": 45
    }
  },
  "performance": {
    "totalLatencyMs": 50,
    "memoryUsage": {
      "rss": 134217728,
      "heapTotal": 67108864,
      "heapUsed": 45088768,
      "external": 2097152
    }
  },
  "features": {
    "streamingEnabled": true,
    "batchProcessingEnabled": true,
    "costTrackingEnabled": true,
    "auditLoggingEnabled": true,
    "phiComplianceEnabled": true,
    "rateLimitingEnabled": true
  }
}
```

### Capabilities

#### `GET /capabilities`

Returns bridge capabilities and supported features.

**Response**:
```json
{
  "version": "1.0.0",
  "endpoints": [
    { "path": "/invoke", "method": "POST", "description": "Single LLM invocation" },
    { "path": "/batch", "method": "POST", "description": "Batch LLM processing" },
    { "path": "/stream", "method": "POST", "description": "Streaming LLM responses" },
    { "path": "/health", "method": "GET", "description": "Health check" },
    { "path": "/capabilities", "method": "GET", "description": "Capabilities info" },
    { "path": "/metrics", "method": "GET", "description": "Prometheus metrics" }
  ],
  "features": {
    "modelTiers": ["ECONOMY", "STANDARD", "PREMIUM"],
    "governanceModes": ["DEMO", "LIVE"],
    "streamingEnabled": true,
    "batchProcessingEnabled": true,
    "costTrackingEnabled": true,
    "auditLoggingEnabled": true,
    "phiComplianceEnabled": true,
    "rateLimitingEnabled": true
  },
  "limits": {
    "maxBatchSize": 10,
    "maxTokens": 200000,
    "timeoutMs": 60000,
    "maxConcurrentRequests": 5,
    "rateLimitPerMinute": 100
  },
  "supportedTaskTypes": [
    {
      "type": "hypothesis_generation",
      "description": "Generate and refine research hypotheses",
      "recommendedTier": "STANDARD",
      "requiresPhiCompliance": false
    },
    {
      "type": "phi_redaction",
      "description": "Detect and redact protected health information",
      "recommendedTier": "PREMIUM",
      "requiresPhiCompliance": true
    }
    // ... more task types
  ]
}
```

### Single LLM Invocation

#### `POST /invoke`

Make a single LLM call through the AI Router.

**Request Body**:
```json
{
  "prompt": "Analyze this clinical data for potential PHI.",
  "options": {
    "taskType": "phi_redaction",
    "stageId": 5,
    "modelTier": "PREMIUM",
    "governanceMode": "LIVE",
    "requirePhiCompliance": true,
    "budgetLimit": 10.0,
    "maxTokens": 4000,
    "temperature": 0.7
  },
  "metadata": {
    "agentId": "irb-agent-001",
    "projectId": "project-123",
    "runId": "run-456",
    "threadId": "thread-789",
    "stageRange": [1, 20],
    "currentStage": 5
  }
}
```

**Response**:
```json
{
  "content": "Analysis complete. I've identified 3 potential PHI instances...",
  "usage": {
    "totalTokens": 1250,
    "promptTokens": 800,
    "completionTokens": 450
  },
  "cost": {
    "total": 0.0375,
    "input": 0.024,
    "output": 0.0135
  },
  "model": "claude-3-5-sonnet-20241022",
  "tier": "premium",
  "finishReason": "stop",
  "metadata": {
    "requestId": "bridge_1738231200000",
    "routingMethod": "ai_router",
    "bridgeVersion": "1.0.0"
  }
}
```

### Batch Processing

#### `POST /batch`

Process multiple prompts in a single request.

**Request Body**:
```json
{
  "prompts": [
    "Summarize this research paper.",
    "Extract key findings from the data.",
    "Generate hypothesis based on results."
  ],
  "options": {
    "taskType": "summarization",
    "modelTier": "STANDARD",
    "governanceMode": "DEMO"
  },
  "metadata": {
    "agentId": "manuscript-agent",
    "projectId": "project-123",
    "runId": "batch-run-456",
    "threadId": "thread-batch",
    "stageRange": [10, 15],
    "currentStage": 12
  }
}
```

**Response**:
```json
{
  "responses": [
    {
      "content": "Summary: This paper investigates...",
      "usage": { "totalTokens": 500, "promptTokens": 200, "completionTokens": 300 },
      "cost": { "total": 0.015, "input": 0.006, "output": 0.009 },
      "model": "claude-3-5-sonnet-20241022",
      "tier": "standard",
      "finishReason": "stop",
      "index": 0
    }
    // ... more responses
  ],
  "totalCost": 0.045,
  "averageLatency": 2300,
  "successCount": 3,
  "errorCount": 0,
  "metadata": {
    "requestId": "bridge_batch_1738231200000",
    "processingTimeMs": 6900,
    "bridgeVersion": "1.0.0"
  }
}
```

### Streaming

#### `POST /stream`

Stream LLM responses using Server-Sent Events.

**Request Body**: Same as `/invoke`

**Response**: Server-Sent Events stream

```
data: {"type":"status","status":"starting","tier":"premium","model":"claude-3-5-sonnet-20241022"}

data: {"type":"content","content":"Analysis ","index":0}

data: {"type":"content","content":"complete. ","index":1}

data: {"type":"complete","finalContent":"Analysis complete...","usage":{"totalTokens":1250},"cost":{"total":0.0375},"model":"claude-3-5-sonnet-20241022","tier":"premium","finishReason":"stop"}

data: [DONE]
```

### Metrics

#### `GET /metrics`

Returns Prometheus metrics for monitoring.

**Response**: Prometheus metrics format

```
# HELP ai_bridge_requests_total Total number of AI Bridge requests
# TYPE ai_bridge_requests_total counter
ai_bridge_requests_total{endpoint="invoke",status="200",model_tier="standard",task_type="hypothesis_generation"} 42

# HELP ai_bridge_request_duration_seconds AI Bridge request duration in seconds
# TYPE ai_bridge_request_duration_seconds histogram
ai_bridge_request_duration_seconds_bucket{endpoint="invoke",model_tier="standard",le="0.1"} 5
ai_bridge_request_duration_seconds_bucket{endpoint="invoke",model_tier="standard",le="0.5"} 25
# ...
```

## Error Codes

| Code | Error | Description |
|------|-------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request body or parameters |
| 401 | `AUTHENTICATION_REQUIRED` | Missing or invalid authentication |
| 402 | `BUDGET_EXCEEDED` | Daily budget limit exceeded |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests per minute |
| 500 | `LLM_CALL_FAILED` | LLM provider error |
| 503 | `SERVICE_UNAVAILABLE` | Circuit breaker open or service down |

## Python Integration

### Using the Bridge from Python

```python
import httpx
import asyncio

class AIBridge:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {auth_token}"}
        self.client = httpx.AsyncClient()
    
    async def invoke(self, prompt: str, task_type: str, **options):
        response = await self.client.post(
            f"{self.base_url}/api/ai-bridge/invoke",
            json={
                "prompt": prompt,
                "options": {"taskType": task_type, **options},
                "metadata": {
                    "agentId": "python-agent",
                    "projectId": "project-123",
                    "runId": f"run-{int(time.time())}",
                    "threadId": "thread-main",
                    "stageRange": [1, 10],
                    "currentStage": 1
                }
            },
            headers=self.headers
        )
        return response.json()

# Usage
bridge = AIBridge("http://localhost:3001", "your-jwt-token")
result = await bridge.invoke(
    "Generate research hypotheses for this dataset",
    "hypothesis_generation",
    modelTier="STANDARD"
)
```

### Streaming Example

```python
async def stream_response(prompt: str):
    async with httpx.stream(
        "POST",
        f"{base_url}/api/ai-bridge/stream",
        json={"prompt": prompt, "options": {"taskType": "data_analysis"}},
        headers=headers
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if data["type"] == "content":
                        print(data["content"], end="")
                    elif data["type"] == "complete":
                        print(f"\nTotal cost: ${data['cost']['total']:.4f}")
                except json.JSONDecodeError:
                    continue
```

## Rate Limiting

- **100 requests per minute** per user
- **$50 daily budget** per user (configurable)
- **10 prompts maximum** per batch request
- **200,000 tokens maximum** per request

Rate limits reset every minute. Budget limits reset daily at midnight UTC.

## Monitoring

The bridge provides comprehensive monitoring:

- **Prometheus metrics** at `/metrics`
- **Health checks** at `/health`
- **Audit logging** for all requests
- **Cost tracking** per user/agent
- **Performance metrics** (latency, throughput)
- **Error rate monitoring**

## Security

- **Authentication required** for all endpoints
- **PHI compliance** mode for sensitive data
- **Rate limiting** to prevent abuse
- **Circuit breaker** for resilience
- **Audit trail** for compliance
- **Budget controls** for cost management

## Troubleshooting

See [Troubleshooting Guide](./AI_BRIDGE_TROUBLESHOOTING.md) for common issues and solutions.