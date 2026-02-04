# ResearchFlow LIVE Mode Deployment Guide

## Overview

This guide provides instructions for deploying ResearchFlow in **LIVE mode** with real data processing through the complete 20-stage workflow.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Node.js 20+ (for local development)
- Python 3.11+ (for local worker development)
- At least 16GB RAM and 50GB disk space
- Valid API keys for AI providers (OpenAI, Anthropic, or local Ollama)

## Governance Modes

ResearchFlow supports three governance modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **DEMO** | Offline fixtures only, no external APIs | Development, testing, demos |
| **STANDBY** | User review required before AI execution | Staged production, quality control |
| **LIVE** | Full AI execution with approval gates | Production with real data |

## LIVE Mode Configuration

### 1. Environment Setup

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

**Critical settings for LIVE mode:**

```bash
# Governance Mode - MUST be set to LIVE for production
GOVERNANCE_MODE=LIVE

# Database
POSTGRES_USER=researchflow_prod
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=researchflow_prod
DATABASE_URL=postgresql://researchflow_prod:<strong-password>@postgres:5432/researchflow_prod

# Redis
REDIS_PASSWORD=<strong-password>

# AI Providers (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_API_KEY=sk-ant-...

# PHI Protection (MUST be enabled for HIPAA compliance)
PHI_SCAN_ENABLED=true
PHI_FAIL_CLOSED=true

# Worker Configuration
WORKER_CALLBACK_URL=http://worker:8000
ORCHESTRATOR_URL=http://orchestrator:3001

# Optional: Local LLM (Ollama)
LOCAL_MODEL_ENABLED=true
LOCAL_MODEL_ENDPOINT=http://ollama:11434
LOCAL_MODEL_NAME=qwen2.5-coder:7b
```

### 2. Docker Compose Deployment

Start all services:

```bash
# Build and start services
docker-compose up -d --build

# Check service health
docker-compose ps

# View logs
docker-compose logs -f orchestrator worker
```

### 3. Verify Deployment

Run the validation script:

```bash
./scripts/validate-deployment.sh
```

This checks:
- ✓ All services are running and healthy
- ✓ GOVERNANCE_MODE=LIVE is configured
- ✓ Database schema is initialized
- ✓ All 20 workflow stages are registered
- ✓ AI providers are configured
- ✓ PHI scanning is enabled

### 4. Service URLs

After successful deployment:

| Service | URL | Purpose |
|---------|-----|---------|
| Web UI | http://localhost:5173 | Frontend application |
| Orchestrator API | http://localhost:3001 | Main API server |
| Worker (internal) | http://localhost:8000 | Background processing |
| Collab | ws://localhost:1234 | Real-time collaboration |
| Ollama | http://localhost:11434 | Local LLM (optional) |

## 20-Stage Workflow in LIVE Mode

### Stage Requirements

| Stage | Name | Requires Real Data | Mock Fallback Allowed |
|-------|------|-------------------|----------------------|
| 1 | Data Ingestion | ✓ | ✗ (LIVE mode) |
| 2 | Literature Review | ✓ | ✗ (LIVE mode) |
| 3 | IRB Compliance | - | ✓ (Form data) |
| 4 | Hypothesis Refinement | - | ✓ (AI generated) |
| 5 | PHI Scan | ✓ | ✗ (LIVE mode) |
| 6 | Study Design | - | ⚠ (Placeholder calculations) |
| 7 | Statistical Modeling | ✓ | ✗ (LIVE mode - enforced) |
| 8 | Data Validation | ✓ | ⚠ (Schema optional) |
| 9 | Interpretation | ✓ | ✗ (LIVE mode) |
| 10 | Validation Checklist | - | ✓ (Checklist data) |
| 11 | Analysis Iteration | ✓ | ✗ (LIVE mode) |
| 12 | Manuscript Drafting | ✓ | ✗ (LIVE mode) |
| 13 | Internal Review | ✓ | ✗ (LIVE mode) |
| 14 | Ethical Review | ✓ | ✗ (LIVE mode) |
| 15 | Artifact Bundling | ✓ | ✗ (LIVE mode) |
| 16 | Collaboration Handoff | ✓ | ⚠ (Comment threads) |
| 17 | Archiving | ✓ | ⚠ (Mock S3 URLs) |
| 18 | Impact Assessment | ✓ | ✗ (LIVE mode) |
| 19 | Dissemination | ✓ | ✗ (LIVE mode) |
| 20 | Conference Report | ✓ | ⚠ (Conference data) |

### Stage 7 Critical Validation

**Stage 7 (Statistical Modeling)** now enforces real data in LIVE mode:

```python
# In LIVE mode, mock data fallback is rejected
if context.governance_mode == "LIVE" and not used_real_analysis:
    raise StageExecutionError(
        "LIVE mode requires real data analysis. "
        "Dataset not available or analysis service unavailable."
    )
```

**Required for Stage 7:**
- Valid `dataset_pointer` (CSV, Parquet, Excel, or TSV file)
- Pandas available (`PANDAS_AVAILABLE=True`)
- AnalysisService available (`ANALYSIS_SERVICE_AVAILABLE=True`)

## Data Requirements

### Input Data Format

Supported formats for workflow execution:
- CSV (`.csv`)
- Parquet (`.parquet`)
- Excel (`.xlsx`, `.xls`)
- TSV (`.tsv`)

**Example dataset structure:**
```csv
patient_id,age,gender,diagnosis,treatment,outcome
P001,45,M,Diabetes,Metformin,Improved
P002,52,F,Hypertension,Lisinopril,Stable
...
```

### Dataset Location

Mount your dataset directory:

```yaml
# In docker-compose.yml
services:
  worker:
    volumes:
      - ./data:/data/datasets:ro  # Read-only dataset mount
```

Then reference in workflow execution:

```json
{
  "job_id": "workflow_001",
  "dataset_pointer": "/data/datasets/clinical_study.csv",
  "governance_mode": "LIVE",
  "config": {
    "model_type": "regression",
    "dependent_variable": "outcome",
    "independent_variables": ["age", "gender", "treatment"]
  }
}
```

## Executing a Workflow

### Via API

```bash
curl -X POST http://localhost:8000/api/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "workflow_2024_01",
    "governance_mode": "LIVE",
    "dataset_pointer": "/data/datasets/study.csv",
    "config": {
      "study_type": "observational",
      "model_type": "regression",
      "dependent_variable": "outcome",
      "independent_variables": ["age", "gender", "treatment"]
    },
    "stage_ids": [1, 2, 3, 4, 5, 6, 7],
    "stop_on_failure": true
  }'
```

### Response

```json
{
  "job_id": "workflow_2024_01",
  "stages_completed": [1, 2, 3, 4, 5, 6, 7],
  "stages_failed": [],
  "stages_skipped": [],
  "success": true,
  "results": {
    "1": {
      "stage_name": "Data Ingestion",
      "status": "completed",
      "duration_ms": 1234,
      "output": { ... }
    },
    ...
  }
}
```

## Monitoring

### Health Checks

```bash
# Orchestrator
curl http://localhost:3001/health

# Worker
curl http://localhost:8000/health

# Check governance mode
curl http://localhost:8000/health | jq '.governance_mode'
# Expected: "LIVE"
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f orchestrator

# Search for errors
docker-compose logs worker | grep -i error
```

### Metrics

Prometheus metrics are available at:
- Orchestrator: http://localhost:3001/metrics
- Worker: http://localhost:8000/metrics

## Security Considerations

### PHI Protection

In LIVE mode with PHI data:

1. **Enable PHI scanning:**
   ```bash
   PHI_SCAN_ENABLED=true
   PHI_FAIL_CLOSED=true
   ```

2. **PHI detection patterns** are auto-loaded from `packages/phi-engine/src/patterns/`

3. **Fail-closed behavior:** Operations are blocked if PHI scanner fails

4. **Audit logging:** All PHI-related operations are logged

### Network Security

Production deployment recommendations:

```yaml
# docker-compose.prod.yml
networks:
  frontend:
    driver: bridge
    # Public-facing (web, orchestrator API)
  backend:
    driver: bridge
    internal: true
    # Internal only (postgres, redis, worker)
```

- PostgreSQL: **NEVER** expose publicly (use internal network)
- Redis: **NEVER** expose publicly (use internal network)
- Worker: Internal service, no public port exposure

## Troubleshooting

### Stage 7 Fails with "LIVE mode requires real data"

**Cause:** No valid dataset or AnalysisService unavailable

**Solution:**
1. Verify dataset file exists and is accessible
2. Check file format (CSV, Parquet, Excel, TSV)
3. Ensure Pandas is installed in worker
4. Check worker logs: `docker-compose logs worker`

### Governance Mode Shows DEMO Instead of LIVE

**Cause:** Environment variable not set or database config overrides

**Solution:**
1. Check `.env` file: `GOVERNANCE_MODE=LIVE`
2. Restart services: `docker-compose restart`
3. Verify: `curl http://localhost:8000/health | jq '.governance_mode'`

### Worker Cannot Connect to Orchestrator

**Cause:** Network configuration or service not ready

**Solution:**
1. Check Docker networks: `docker network ls`
2. Verify service health: `docker-compose ps`
3. Check orchestrator logs: `docker-compose logs orchestrator`

## Maintenance

### Database Backups

```bash
# Backup
docker-compose exec postgres pg_dump -U ros ros > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T postgres psql -U ros ros < backup_20240203.sql
```

### Updating Services

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build

# Run migrations (if needed)
docker-compose exec orchestrator npm run db:migrate
```

## Production Deployment

For production, use `docker-compose.prod.yml`:

```bash
# Production build
docker-compose -f docker-compose.prod.yml up -d --build

# With monitoring
docker-compose -f docker-compose.prod.yml -f docker-compose.monitoring.yml up -d
```

Additional production considerations:
- Use managed PostgreSQL (AWS RDS, Azure Database)
- Use managed Redis (AWS ElastiCache, Azure Cache)
- Configure SSL/TLS certificates
- Set up log aggregation (ELK, Datadog)
- Configure monitoring and alerting
- Implement backup automation
- Use secrets management (Vault, AWS Secrets Manager)

## Support

- Documentation: `/docs`
- Issues: GitHub Issues
- API Docs: http://localhost:3001/docs (Orchestrator)
- Worker Docs: http://localhost:8000/docs (Worker)
