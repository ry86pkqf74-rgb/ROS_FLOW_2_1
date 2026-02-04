# 🚀 Production-Ready Agent Infrastructure

This document describes the production-ready infrastructure components added to ResearchFlow agents.

## 📦 Components

### 1. **Secrets Management** (`utils/secrets_manager.py`)

Secure secret management with multiple backend support.

#### Features
- ✅ Environment variables (development)
- ✅ HashiCorp Vault (production)
- ✅ AWS Secrets Manager (cloud)
- ✅ Azure Key Vault (cloud)
- ✅ Automatic fallback to env vars
- ✅ Secret caching (5-minute TTL)
- ✅ Validation helpers

#### Usage

```python
from agents.utils import get_secrets_manager, get_secret

# Get secrets manager (singleton)
secrets = get_secrets_manager()

# Get secret with fallback
api_key = secrets.get_secret("OPENAI_API_KEY", default="fallback-key")

# Get required secret (raises if missing)
db_url = secrets.get_required_secret("DATABASE_URL")

# Validate multiple secrets
validation = secrets.validate_required_secrets([
    "COMPOSIO_API_KEY",
    "OPENAI_API_KEY",
    "DATABASE_URL"
])

if not all(validation.values()):
    print("Missing secrets:", [k for k, v in validation.items() if not v])
```

#### Configuration

```bash
# .env or environment
SECRET_BACKEND=env  # Options: env, vault, aws_secrets, azure_keyvault

# Vault
VAULT_URL=https://vault.example.com
VAULT_TOKEN=s.xxxxxxxxxx
VAULT_NAMESPACE=default

# AWS
AWS_REGION=us-east-1

# Azure
AZURE_VAULT_NAME=researchflow-vault

# Cache
SECRET_CACHE_TTL=300  # seconds
```

---

### 2. **AI Helper** (`utils/ai_helper.py`)

Integration with external AI services for task delegation.

#### Features
- ✅ OpenAI GPT-4 integration
- ✅ Anthropic Claude integration
- ✅ XAI Grok support
- ✅ Code generation assistance
- ✅ Error analysis
- ✅ Code review
- ✅ Documentation generation

#### Usage

```python
from agents.utils import get_ai_helper

ai = get_ai_helper()

# Ask OpenAI for help
response = await ai.ask_openai(
    prompt="Explain circuit breakers in distributed systems",
    model="gpt-4o"
)
print(response.content)

# Get code suggestions
code_help = await ai.get_code_suggestions(
    code_context="class MyAgent: pass",
    task="Add a method to validate inputs",
    language="python"
)

# Review code
review = await ai.review_code(
    code=my_code,
    language="python",
    focus_areas=["security", "performance"]
)
print(review["issues"])
print(review["suggestions"])

# Analyze error
analysis = await ai.analyze_error(
    error_message="ValueError: Invalid input",
    stack_trace=stack_trace,
    code_context=code_snippet
)
print(analysis["root_cause"])
print(analysis["suggested_fixes"])
```

---

### 3. **Environment Validator** (`utils/env_validator.py`)

Validates environment configuration at startup.

#### Features
- ✅ Required vs optional variables
- ✅ Type validation (URL, int, bool)
- ✅ Format validation (API keys, URLs)
- ✅ Custom validators
- ✅ Detailed error reporting
- ✅ JSON export

#### Usage

```python
from agents.utils import validate_startup_environment, EnvValidator, ValidationRule

# Quick startup validation
if not validate_startup_environment():
    sys.exit(1)

# Custom validation
validator = EnvValidator()
validator.add_rule(ValidationRule(
    name="DATABASE_URL",
    required=True,
    severity=ValidationSeverity.CRITICAL,
    validator=is_postgres_url,
    description="PostgreSQL connection URL",
    example="postgresql://user:pass@localhost:5432/db"
))

results = validator.validate_all()
if not validator.is_valid():
    validator.print_report()
    sys.exit(1)
```

#### Output Example

```
======================================================================
🔍 ENVIRONMENT VALIDATION REPORT
======================================================================

❌ CRITICAL FAILURES (1):
  ❌ COMPOSIO_API_KEY
     Required variable 'COMPOSIO_API_KEY' is not set
     Suggested: comp_xxxxxxxxxxxxxxxxxxxx

⚠️  WARNINGS (1):
  ⚠️  ANTHROPIC_API_KEY
     Optional variable 'ANTHROPIC_API_KEY' not set

======================================================================
Summary: 1 critical, 0 errors, 1 warnings

❌ VALIDATION FAILED - Fix issues above before starting
======================================================================
```

---

### 4. **Health Checks** (`utils/health_check.py`)

Comprehensive health monitoring system.

#### Features
- ✅ Component health checks
- ✅ Response time tracking
- ✅ Degraded state detection
- ✅ Critical vs non-critical components
- ✅ Docker health check integration
- ✅ FastAPI endpoint helper

#### Usage

```python
from agents.utils import get_agent_health_checker

# Get pre-configured checker
checker = get_agent_health_checker()

# Add custom check
async def check_my_service():
    # Return (is_healthy, message, details_dict)
    try:
        # Check service...
        return True, "Service is healthy", {"version": "1.0"}
    except Exception as e:
        return False, f"Service error: {e}", {}

checker.add_check("my_service", check_my_service, critical=True)

# Check all components
health = await checker.check_all()
print(f"Overall status: {health.status.value}")
print(f"Uptime: {health.uptime_seconds}s")

for component in health.components:
    print(f"{component.name}: {component.status.value} ({component.response_time_ms}ms)")
```

#### FastAPI Integration

```python
from fastapi import FastAPI
from agents.utils.health_check import create_health_endpoint

app = FastAPI()
health_check = create_health_endpoint()

@app.get("/health")
async def health():
    return await health_check()
```

#### Docker Compose Health Check

```yaml
services:
  agent:
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3001/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

### 5. **Structured Logging** (`utils/structured_logging.py`)

JSON-based structured logging for production.

#### Features
- ✅ JSON formatting
- ✅ Contextual information (correlation IDs, agent names)
- ✅ Performance metrics
- ✅ Log aggregation ready (ELK, Datadog, etc.)
- ✅ Execution time decorators

#### Usage

```python
from agents.utils import setup_structured_logging, get_logger, LogContext, log_execution_time

# Setup structured logging
setup_structured_logging(level="INFO", json_format=True)

# Get logger
logger = get_logger(__name__)

# Use context for tracing
with LogContext(
    agent_name="DesignOps",
    workflow_id="wf-123",
    correlation_id="req-456"
):
    logger.info("Processing task", extra={"task_id": "task-789"})

# Decorator for timing
@log_execution_time()
def process_data():
    # ...
    pass

# Async decorator
@log_async_execution_time()
async def fetch_data():
    # ...
    pass
```

#### Log Output (JSON)

```json
{
  "timestamp": "2025-01-30T12:00:00.000Z",
  "level": "INFO",
  "logger": "agents.design_ops",
  "message": "Processing task",
  "correlation_id": "req-456",
  "agent_name": "DesignOps",
  "workflow_id": "wf-123",
  "extra": {
    "task_id": "task-789"
  }
}
```

---

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install -r agents/requirements.txt

# Run all tests
pytest agents/tests/

# Run specific test file
pytest agents/tests/test_secrets_manager.py

# Run with coverage
pytest agents/tests/ --cov=agents --cov-report=html

# Run only unit tests (fast)
pytest agents/tests/ -m unit

# Run integration tests (requires services)
pytest agents/tests/ -m integration
```

### Test Categories

- **Unit tests**: Fast, no external dependencies
- **Integration tests**: Require external services (Vault, DB, etc.)

---

## 🔒 Security Best Practices

### 1. Never commit secrets

```bash
# .gitignore
.env
.env.local
.env.production
*.pem
*.key
```

### 2. Use secret backends in production

```bash
# Production
SECRET_BACKEND=vault
VAULT_URL=https://vault.prod.example.com
VAULT_TOKEN=<from-ci-cd>

# Development
SECRET_BACKEND=env
# Secrets in .env file (not committed)
```

### 3. Validate configuration at startup

```python
# In your main.py or agent initialization
from agents.utils import validate_startup_environment

if __name__ == "__main__":
    if not validate_startup_environment():
        sys.exit(1)
    
    # Start application...
```

---

## 📊 Monitoring Integration

### Datadog

```python
# Structured logs are automatically parsed by Datadog
setup_structured_logging(level="INFO", json_format=True)

# Use correlation IDs for request tracing
with LogContext(correlation_id=request_id):
    logger.info("Request processed", extra={"status": "success"})
```

### Prometheus Metrics

```python
from agents.utils.structured_logging import MetricsLogger

metrics = MetricsLogger()

# Record metrics
metrics.record_counter("agent.tasks.completed", 1, {"agent": "DesignOps"})
metrics.record_histogram("agent.task.duration_ms", 123.45, {"agent": "DesignOps"})
```

---

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] Run environment validation
- [ ] Run all tests
- [ ] Check health endpoints
- [ ] Verify secret backend connectivity
- [ ] Review logs for errors

### Docker Compose

```yaml
services:
  agent:
    environment:
      # Secrets
      - SECRET_BACKEND=vault
      - VAULT_URL=${VAULT_URL}
      - VAULT_TOKEN=${VAULT_TOKEN}
      
      # Logging
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      
      # Health checks
      - HEALTH_CHECK_ENABLED=true
    
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:3001/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 📚 Additional Resources

- [HashiCorp Vault Documentation](https://developer.hashicorp.com/vault/docs)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Azure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/)
- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Anthropic Claude API](https://docs.anthropic.com/)

---

## 🤝 Contributing

When adding new utilities:

1. Add tests in `agents/tests/`
2. Update `agents/utils/__init__.py`
3. Document in this file
4. Add usage examples
5. Update requirements.txt if needed

---

## 📝 License

Copyright © 2025 ResearchFlow. All rights reserved.
