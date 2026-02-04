# AI Bridge Troubleshooting Guide

## Common Issues and Solutions

### 1. Authentication Errors

#### Problem: `401 AUTHENTICATION_REQUIRED`
```json
{
  "error": "AUTHENTICATION_REQUIRED",
  "message": "Authentication required for AI Bridge access"
}
```

**Solutions:**
1. Verify JWT token is valid and not expired
2. Check token is included in `Authorization: Bearer <token>` header
3. Ensure user has proper permissions (ANALYZE role minimum)

#### Problem: `403 INSUFFICIENT_PERMISSIONS`
```json
{
  "error": "INSUFFICIENT_PERMISSIONS",
  "message": "User lacks required permissions"
}
```

**Solutions:**
1. Check user role assignments
2. Verify RBAC configuration
3. Ensure user has `ANALYZE` permission

### 2. Rate Limiting Issues

#### Problem: `429 RATE_LIMIT_EXCEEDED`
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please wait before retrying.",
  "retryAfter": 45
}
```

**Solutions:**
1. Implement exponential backoff in your client
2. Reduce request frequency
3. Use batch processing for multiple prompts
4. Check if multiple agents are using same user account

**Example Fix:**
```python
import asyncio
import time

async def with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                retry_after = int(e.response.headers.get('retry-after', 60))
                await asyncio.sleep(retry_after)
                continue
            raise
    raise Exception("Max retries exceeded")
```

### 3. Budget and Cost Issues

#### Problem: `402 BUDGET_EXCEEDED`
```json
{
  "error": "BUDGET_EXCEEDED",
  "message": "Daily budget limit exceeded. Please contact support.",
  "currentCost": 52.45,
  "budgetLimit": 50.0
}
```

**Solutions:**
1. Monitor daily usage with `/metrics` endpoint
2. Optimize prompts to reduce token usage
3. Use lower-cost tiers (ECONOMY vs PREMIUM)
4. Implement cost tracking in your agents
5. Request budget increase from admin

**Cost Optimization:**
```python
# Use economy tier for simple tasks
options = {
    "taskType": "summarization",
    "modelTier": "ECONOMY",  # Instead of PREMIUM
    "maxTokens": 1000       # Limit output length
}

# Monitor costs
response = await bridge.invoke(prompt, **options)
print(f"Cost: ${response['cost']['total']:.4f}")
```

### 4. Service Availability

#### Problem: `503 SERVICE_UNAVAILABLE`
```json
{
  "error": "SERVICE_UNAVAILABLE",
  "message": "Service temporarily unavailable. Please retry later.",
  "retryAfter": 30
}
```

**Causes:**
1. Circuit breaker is open (too many failures)
2. AI Router service is down
3. LLM provider outage
4. System overload

**Solutions:**
1. Check `/health` endpoint for service status
2. Wait for circuit breaker to reset (usually 1 minute)
3. Implement retry logic with exponential backoff
4. Use alternative task types if specific models are down

### 5. Validation Errors

#### Problem: `400 VALIDATION_ERROR`
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid request body",
  "details": {
    "fieldErrors": {
      "prompt": ["Required"],
      "options.taskType": ["Required"]
    }
  }
}
```

**Solutions:**
1. Verify all required fields are present
2. Check field types match schema
3. Validate enum values (e.g., taskType, modelTier)

**Valid Request Example:**
```python
valid_request = {
    "prompt": "Your prompt here",  # Required, non-empty string
    "options": {
        "taskType": "hypothesis_generation",  # Required, valid task type
        "modelTier": "STANDARD",              # Optional, valid tier
        "governanceMode": "DEMO",             # Optional, DEMO or LIVE
        "requirePhiCompliance": False,        # Optional, boolean
        "maxTokens": 4000,                    # Optional, positive number
        "temperature": 0.7                    # Optional, 0-2
    },
    "metadata": {  # Optional but recommended
        "agentId": "my-agent",
        "projectId": "project-123",
        "runId": "run-456",
        "threadId": "thread-789",
        "stageRange": [1, 10],
        "currentStage": 1
    }
}
```

### 6. Streaming Issues

#### Problem: Streaming connection drops or incomplete responses

**Symptoms:**
- Connection closes unexpectedly
- Missing `[DONE]` marker
- Partial responses

**Solutions:**
1. Implement proper SSE parsing:

```python
import json

async def parse_sse_stream(response):
    content = ""
    async for line in response.aiter_lines():
        if not line.startswith("data: "):
            continue
        
        data_str = line[6:]  # Remove "data: " prefix
        if data_str == "[DONE]":
            break
            
        try:
            data = json.loads(data_str)
            if data["type"] == "content":
                content += data["content"]
            elif data["type"] == "complete":
                return content, data["usage"], data["cost"]
        except json.JSONDecodeError:
            continue
    
    return content, None, None
```

2. Set appropriate timeouts:
```python
timeout = httpx.Timeout(60.0)  # 60 second timeout
```

3. Handle network interruptions with reconnection logic

### 7. Batch Processing Issues

#### Problem: `400 BATCH_SIZE_EXCEEDED`
```json
{
  "error": "BATCH_SIZE_EXCEEDED",
  "message": "Maximum batch size is 10 prompts",
  "received": 25,
  "maximum": 10
}
```

**Solutions:**
1. Split large batches into smaller chunks:

```python
def chunk_prompts(prompts, chunk_size=10):
    for i in range(0, len(prompts), chunk_size):
        yield prompts[i:i + chunk_size]

async def process_large_batch(prompts):
    all_responses = []
    for chunk in chunk_prompts(prompts):
        response = await bridge.batch(chunk, **options)
        all_responses.extend(response["responses"])
    return all_responses
```

### 8. Performance Issues

#### Problem: Slow response times

**Diagnosis:**
1. Check `/health` endpoint for latency metrics
2. Monitor `/metrics` for performance data
3. Verify task type and tier selection

**Optimizations:**
1. Use appropriate model tiers:
   - ECONOMY: For simple tasks (summarization, basic analysis)
   - STANDARD: For moderate complexity (hypothesis generation)
   - PREMIUM: For complex tasks (PHI detection, statistical analysis)

2. Optimize prompt length:
```python
# Bad: Very long prompt
prompt = "Analyze this dataset..." + very_long_data

# Good: Structured, focused prompt
prompt = f"""Analyze the following dataset for key patterns:
Dataset: {data_summary}
Focus: {analysis_type}
Output: {expected_format}"""
```

3. Use batch processing for multiple similar requests

### 9. Monitoring and Debugging

#### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor bridge responses
response = await bridge.invoke(prompt, task_type)
logger.debug(f"Bridge response: {response}")
logger.debug(f"Cost: ${response['cost']['total']:.4f}")
logger.debug(f"Tokens: {response['usage']['totalTokens']}")
```

#### Check Bridge Health

```python
async def check_bridge_health():
    response = await bridge.client.get(f"{bridge.base_url}/api/ai-bridge/health")
    health = response.json()
    
    if health["status"] != "healthy":
        logger.warning(f"Bridge health: {health['status']}")
        
    if not health["dependencies"]["aiRouter"]["healthy"]:
        logger.error("AI Router is down")
        
    return health["status"] == "healthy"
```

#### Monitor Metrics

```python
async def get_bridge_metrics():
    response = await bridge.client.get(f"{bridge.base_url}/api/ai-bridge/metrics")
    return response.text  # Prometheus format
```

### 10. Configuration Issues

#### Problem: Environment variables not set

**Check Required Variables:**
```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/db
JWT_SECRET=your-secret-key

# AI Bridge specific
AI_BRIDGE_ORCHESTRATOR_URL=http://localhost:3001
AI_BRIDGE_WORKER_URL=http://localhost:8000
AI_BRIDGE_PHI_COMPLIANCE=true

# Optional
AI_BRIDGE_MAX_BATCH_SIZE=10
AI_BRIDGE_DEFAULT_TIER=STANDARD
AI_BRIDGE_COST_LIMIT=100.0
```

#### Problem: Docker networking issues

**Solutions:**
1. Use service names in Docker Compose:
```yaml
services:
  orchestrator:
    environment:
      - AI_BRIDGE_ORCHESTRATOR_URL=http://orchestrator:3001
```

2. Check container connectivity:
```bash
docker exec -it worker curl http://orchestrator:3001/api/ai-bridge/health
```

## Getting Help

1. **Check Health**: Always start with `/health` endpoint
2. **Review Logs**: Check orchestrator logs for detailed errors
3. **Monitor Metrics**: Use `/metrics` for performance insights
4. **Test Connectivity**: Verify network connections between services
5. **Validate Environment**: Ensure all required variables are set

## Emergency Contacts

- **System Admin**: For budget increases and permission issues
- **DevOps Team**: For infrastructure and deployment issues  
- **AI Team**: For model tier and task type questions

## Performance Baselines

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Response Time | < 2s | > 5s |
| Success Rate | > 99% | < 95% |
| Cost per Request | < $0.05 | > $0.20 |
| Rate Limit Usage | < 80% | > 90% |