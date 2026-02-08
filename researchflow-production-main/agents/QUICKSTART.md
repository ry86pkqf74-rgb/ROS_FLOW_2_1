# 🚀 Quick Start: Production-Ready Agents

Get started with ResearchFlow's production-ready agent infrastructure in 5 minutes.

## 📦 Installation

```bash
# Navigate to agents directory
cd agents

# Install dependencies
pip install -r requirements.txt

# For production backends (optional)
pip install hvac boto3 azure-keyvault-secrets azure-identity
```

---

## 🔧 Configuration

### 1. **Copy environment template**

```bash
cp .env.example .env
```

### 2. **Set required variables**

Edit `.env`:

```bash
# Required for agents
COMPOSIO_API_KEY=comp_your_key_here
OPENAI_API_KEY=sk-your_key_here

# Optional but recommended
ANTHROPIC_API_KEY=sk-ant-your_key_here
GITHUB_TOKEN=<your-github-token>
NOTION_API_KEY=secret_your_key_here

# Secret backend (default: env)
SECRET_BACKEND=env

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 🏃 Running Your First Agent

### Option A: Run Example Agent

```bash
# Run the production example
python -m agents.examples.production_agent_example
```

This demonstrates:
- ✅ Structured logging
- ✅ Environment validation
- ✅ Health checks
- ✅ AI helper integration
- ✅ Error analysis

### Option B: Use in Your Code

```python
#!/usr/bin/env python3
"""My Production Agent"""

import asyncio
from agents.utils import (
    setup_structured_logging,
    get_agent_logger,
    validate_startup_environment,
    get_ai_helper
)

# Setup
setup_structured_logging(level="INFO")
logger = get_agent_logger("MyAgent")

# Validate environment
if not validate_startup_environment():
    exit(1)

# Use AI helper
async def main():
    ai = get_ai_helper()
    response = await ai.ask_openai("Explain circuit breakers")
    logger.info(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest agents/tests/

# Run with coverage
pytest agents/tests/ --cov=agents --cov-report=html

# Run specific test file
pytest agents/tests/test_secrets_manager.py -v

# Run only fast unit tests
pytest agents/tests/ -m unit
```

---

## 🔍 Environment Validation

### Automatic Validation

Add to your agent startup:

```python
from agents.utils import validate_startup_environment

if not validate_startup_environment():
    sys.exit(1)
```

### Manual Validation

```bash
# Create validation script
python -c "
from agents.utils import validate_startup_environment
import sys
if not validate_startup_environment():
    sys.exit(1)
print('✅ Environment is valid!')
"
```

---

## 💚 Health Checks

### Add to Your Agent

```python
from agents.utils import get_agent_health_checker

checker = get_agent_health_checker()

# Check health
health = await checker.check_all()
print(f"Status: {health.status.value}")
```

### Add Custom Check

```python
async def check_my_service():
    try:
        # Check service...
        return True, "Service OK", {"version": "1.0"}
    except Exception as e:
        return False, f"Service error: {e}", {}

checker.add_check("my_service", check_my_service, critical=True)
```

### Docker Health Check

Add to `docker-compose.yml`:

```yaml
services:
  my_agent:
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3001/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 🔐 Secret Management

### Environment Variables (Development)

```python
from agents.utils import get_secret, get_required_secret

# Get with fallback
api_key = get_secret("OPENAI_API_KEY", default="sk-fallback")

# Get required (raises if missing)
db_url = get_required_secret("DATABASE_URL")

# Validate multiple
from agents.utils import validate_required_secrets
results = validate_required_secrets([
    "COMPOSIO_API_KEY",
    "OPENAI_API_KEY"
])
print(results)  # {"COMPOSIO_API_KEY": True, "OPENAI_API_KEY": False}
```

### HashiCorp Vault (Production)

```bash
# Set in .env
SECRET_BACKEND=vault
VAULT_URL=https://vault.example.com
VAULT_TOKEN=s.xxxxxxxxxx
```

Secrets will be automatically fetched from Vault with fallback to env vars.

---

## 🤖 AI Helper

### Code Generation

```python
from agents.utils import get_ai_helper

ai = get_ai_helper()

# Get code suggestions
response = await ai.get_code_suggestions(
    code_context="class MyClass: pass",
    task="Add a validate_email method",
    language="python"
)
print(response.content)
```

### Code Review

```python
review = await ai.review_code(
    code=my_code,
    language="python",
    focus_areas=["security", "performance"]
)

print("Issues:", review["issues"])
print("Suggestions:", review["suggestions"])
```

### Error Analysis

```python
try:
    # Some code...
    pass
except Exception as e:
    analysis = await ai.analyze_error(
        error_message=str(e),
        stack_trace=traceback.format_exc()
    )
    print("Root cause:", analysis["root_cause"])
    print("Fixes:", analysis["suggested_fixes"])
```

---

## 📊 Structured Logging

### Setup

```python
from agents.utils import setup_structured_logging, get_logger, LogContext

# Setup (once at startup)
setup_structured_logging(level="INFO", json_format=True)

# Get logger
logger = get_logger(__name__)

# Use context for tracing
with LogContext(
    agent_name="MyAgent",
    workflow_id="wf-123",
    correlation_id="req-456"
):
    logger.info("Processing", extra={"item_count": 10})
```

### Output (JSON)

```json
{
  "timestamp": "2025-01-30T12:00:00Z",
  "level": "INFO",
  "logger": "my_module",
  "message": "Processing",
  "agent_name": "MyAgent",
  "workflow_id": "wf-123",
  "correlation_id": "req-456",
  "extra": {
    "item_count": 10
  }
}
```

### Timing Decorators

```python
from agents.utils import log_execution_time, log_async_execution_time

@log_execution_time()
def sync_function():
    # Automatically logs execution time
    pass

@log_async_execution_time()
async def async_function():
    # Automatically logs execution time
    pass
```

---

## 🐳 Docker Integration

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY agents/requirements.txt .
RUN pip install -r requirements.txt

COPY agents/ .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:3001/health || exit 1

CMD ["python", "-m", "agents.run_agents"]
```

### docker-compose.yml

```yaml
services:
  agent:
    build:
      context: .
      dockerfile: agents/Dockerfile
    environment:
      - SECRET_BACKEND=env
      - COMPOSIO_API_KEY=${COMPOSIO_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3001/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
```

---

## 🚨 Troubleshooting

### Missing API Keys

```
❌ Required secret not found: OPENAI_API_KEY
```

**Solution**: Set the API key in `.env` or environment:
```bash
export OPENAI_API_KEY=sk-your_key_here
```

### Health Check Fails

```
❌ Service 'composio_api' is unhealthy
```

**Solution**: Check Composio API key configuration:
```bash
# Verify key is set
echo $COMPOSIO_API_KEY

# Test manually
curl -H "X-API-Key: $COMPOSIO_API_KEY" https://api.composio.dev/v1/status
```

### Tests Failing

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock pytest-cov

# Run with verbose output
pytest agents/tests/ -v

# Skip integration tests
pytest agents/tests/ -m "not integration"
```

### Import Errors

```
ImportError: No module named 'agents.utils'
```

**Solution**: Install package in editable mode:
```bash
pip install -e .
```

---

## 📚 Next Steps

1. **Read the full documentation**: [`PRODUCTION_READY.md`](./PRODUCTION_READY.md)
2. **Check out examples**: [`examples/production_agent_example.py`](./examples/production_agent_example.py)
3. **Review tests**: [`tests/`](./tests/)
4. **Configure for production**: Setup Vault/AWS Secrets Manager

---

## 🤝 Getting Help

- **Documentation**: See `PRODUCTION_READY.md` for detailed docs
- **Examples**: Check `examples/` directory
- **Tests**: Look at `tests/` for usage patterns
- **Issues**: Create a GitHub issue with logs and configuration

---

## ✅ Checklist for Production

- [ ] Environment validation passes
- [ ] All tests pass (`pytest agents/tests/`)
- [ ] Health checks configured
- [ ] Secret backend setup (Vault/AWS/Azure)
- [ ] Structured logging enabled
- [ ] Docker health checks configured
- [ ] Monitoring integrated (Datadog/Prometheus)
- [ ] Error alerting configured
- [ ] Documentation updated

---

**🎉 You're ready to build production-ready agents!**
