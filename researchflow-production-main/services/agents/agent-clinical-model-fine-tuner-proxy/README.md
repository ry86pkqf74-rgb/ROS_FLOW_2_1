# Clinical Model Fine-Tuner Agent - LangSmith Proxy

## Overview

The Clinical Model Fine-Tuner Agent is a comprehensive lifecycle management assistant for fine-tuning language models on clinical and medical data with a strong focus on HIPAA compliance.

## Architecture

This service acts as a **proxy adapter** between ResearchFlow's orchestrator and the LangSmith cloud-hosted agent:

```
Orchestrator → agent-clinical-model-fine-tuner-proxy → LangSmith Cloud Agent
```

## Features

- **Data Preparation**: Synthetic clinical data generation with HIPAA compliance
- **HIPAA Compliance Auditing**: Mandatory compliance checks before fine-tuning
- **Multi-Provider Support**: OpenAI, Azure OpenAI, and self-hosted models
- **Prompt Engineering Assessment**: Evaluate if prompting alone can achieve goals
- **Evaluation & Regression Testing**: Comprehensive model evaluation with benchmark comparisons
- **Full Lifecycle Tracking**: Integration with Google Sheets, GitHub, Google Docs, and Slack

## Subagents

The main agent delegates to 6 specialized workers:

1. **Clinical_Data_Preparation_Worker** - Synthetic data schema design and generation
2. **Evaluation_Report_Worker** - Metrics analysis and provider comparison
3. **HIPAA_Compliance_Auditor_Worker** - PHI leak detection and compliance reporting
4. **Benchmark_Literature_Research_Worker** - Latest clinical NLP research and techniques
5. **Prompt_Engineering_Worker** - Clinical prompt optimization and fine-tuning necessity assessment
6. **Regression_Testing_Worker** - Model performance comparison against baselines

## Configuration

### Environment Variables

```bash
LANGSMITH_API_KEY=<your-langsmith-api-key>
LANGSMITH_AGENT_ID=<assistant-id-from-langsmith>
LANGSMITH_API_URL=https://api.smith.langchain.com/api/v1
LANGSMITH_TIMEOUT_SECONDS=600  # 10 minutes
LANGCHAIN_PROJECT=researchflow-clinical-model-fine-tuner
LOG_LEVEL=INFO
```

### Task Type

The agent is registered in the orchestrator with the task type:

```
CLINICAL_MODEL_FINE_TUNING
```

## LangSmith Configuration

The complete LangSmith agent configuration is stored in the `langsmith_config/` directory:

- `AGENTS.md` - Main agent instructions and workflow
- `config.json` - Agent metadata and settings
- `tools.json` - Tool configurations (Google Sheets, GitHub, Docs, Slack)
- `subagents/` - Instructions for all 6 specialized workers

## Request/Response Schema

### Request

```json
{
  "task_type": "CLINICAL_MODEL_FINE_TUNING",
  "request_id": "uuid",
  "inputs": {
    "clinical_domain": "cardiology",
    "target_task": "clinical_note_generation",
    "model_provider": "openai",
    "dataset_specifications": {
      "size": 1000,
      "format": "jsonl"
    },
    "evaluation_criteria": {
      "metrics": ["accuracy", "fluency", "clinical_accuracy"]
    },
    "compliance_requirements": ["HIPAA"],
    "fine_tune_config": {
      "epochs": 3,
      "learning_rate": 5e-5
    },
    "workflow_phase": "data_preparation"
  }
}
```

### Response

```json
{
  "ok": true,
  "request_id": "uuid",
  "outputs": {
    "synthetic_dataset": [...],
    "dataset_schema": {...},
    "dataset_metadata_url": "https://sheets.google.com/...",
    "compliance_report": {...},
    "audit_status": "passed",
    "compliance_doc_url": "https://docs.google.com/...",
    "fine_tune_job_id": "ft-xyz",
    "model_id": "ft:gpt-3.5:...",
    "training_metrics": {...},
    "evaluation_report": {...},
    "model_card_url": "https://docs.google.com/...",
    "github_issue_url": "https://github.com/.../issues/123",
    "tracking_sheet_url": "https://sheets.google.com/...",
    "workflow_status": "completed",
    "next_steps": [...]
  }
}
```

## Workflow Phases

The agent supports multiple workflow phases:

1. **prompt_engineering_assessment** - Evaluate if prompting alone suffices
2. **data_preparation** - Generate synthetic clinical datasets
3. **hipaa_audit** - Mandatory compliance validation
4. **fine_tuning** - Execute fine-tuning job with cost estimates
5. **evaluation** - Comprehensive model evaluation
6. **regression_testing** - Compare against baselines
7. **deployment** - Model card generation and documentation

## Health Checks

- `/health` - Basic liveness check
- `/health/ready` - Validates LangSmith API connectivity

## Endpoints

- `POST /agents/run/sync` - Synchronous execution
- `POST /agents/run/stream` - Server-Sent Events streaming

## Integration with ResearchFlow

This service is registered in `docker-compose.yml` as `agent-clinical-model-fine-tuner-proxy` and mapped in orchestrator's `AGENT_ENDPOINTS_JSON`:

```json
{
  "agent-clinical-model-fine-tuner-proxy": "http://agent-clinical-model-fine-tuner-proxy:8000"
}
```

Router mapping in `ai-router.ts`:

```typescript
CLINICAL_MODEL_FINE_TUNING: 'agent-clinical-model-fine-tuner-proxy'
```

## Deployment

```bash
# Build
docker compose build agent-clinical-model-fine-tuner-proxy

# Deploy
docker compose up -d agent-clinical-model-fine-tuner-proxy

# Verify
curl http://localhost:<port>/health
```

## Testing

```bash
curl -X POST http://localhost:<port>/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_MODEL_FINE_TUNING",
    "request_id": "test-123",
    "inputs": {
      "clinical_domain": "cardiology",
      "target_task": "note_generation",
      "workflow_phase": "data_preparation"
    }
  }'
```

## Monitoring

- LangSmith traces available at: `https://smith.langchain.com`
- Project: `researchflow-clinical-model-fine-tuner`
- All requests include `request_id` for traceability

## Compliance & Security

- **HIPAA Compliant**: Uses only synthetic data
- **Mandatory Auditing**: HIPAA audit must pass before fine-tuning
- **PHI Detection**: 18 HIPAA identifiers validated
- **Audit Trails**: Complete tracking via Google Docs and GitHub

## Support

For issues or questions:
- GitHub Issues for agent configuration
- LangSmith support for cloud agent issues
- See `langsmith_config/AGENTS.md` for complete workflow documentation
