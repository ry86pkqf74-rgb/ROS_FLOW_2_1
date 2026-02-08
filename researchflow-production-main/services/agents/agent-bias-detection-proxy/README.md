# Clinical Bias Detection Agent - LangSmith Proxy

This is a thin FastAPI proxy adapter that bridges ResearchFlow's agent contract with the LangSmith cloud-hosted Clinical Bias Detection Agent.

## Architecture

- **Service:** `agent-bias-detection-proxy`
- **Port:** 8000 (internal Docker network)
- **Execution:** LangSmith cloud via HTTP API
- **Status:** ✅ Operational

## Endpoints

### Health Check
```bash
GET /health
GET /health/ready  # Validates LangSmith connectivity
```

### Agent Execution
```bash
POST /agents/run/sync     # Synchronous execution
POST /agents/run/stream   # Streaming execution
```

## Request Schema

```json
{
  "task_type": "CLINICAL_BIAS_DETECTION",
  "request_id": "unique-id",
  "workflow_id": "workflow-id",
  "inputs": {
    "dataset_summary": "Dataset description with key statistics",
    "dataset_url": "https://docs.google.com/spreadsheets/...",
    "pasted_data": "CSV or tabular data as string",
    "sensitive_attributes": ["gender", "ethnicity", "age", "geography"],
    "outcome_variables": ["treatment_efficacy", "diagnosis_rate"],
    "sample_size": 1500,
    "few_shot_examples": [],
    "audit_spreadsheet_id": "existing-audit-sheet-id",
    "generate_report": true,
    "output_email": "recipient@example.com"
  }
}
```

## Response Schema

```json
{
  "ok": true,
  "request_id": "unique-id",
  "outputs": {
    "bias_verdict": "Biased | Unbiased",
    "bias_score": 6.5,
    "bias_flags": [{
      "type": "demographic",
      "severity": "high",
      "description": "...",
      "metrics": {}
    }],
    "mitigation_plan": {
      "strategies": [],
      "expected_effectiveness": 8.5
    },
    "compliance_risk": {
      "risk_level": "medium",
      "blocking_issues": []
    },
    "red_team_validation": {
      "robustness_score": 7.8,
      "challenges": []
    },
    "report_url": "https://docs.google.com/...",
    "audit_log_url": "https://docs.google.com/spreadsheets/...",
    "mitigated_data_url": "https://docs.google.com/spreadsheets/..."
  }
}
```

## Environment Variables

Required:
- `LANGSMITH_API_KEY` - LangSmith API authentication
- `LANGSMITH_AGENT_ID` - Assistant ID for Clinical Bias Detection Agent

Optional:
- `LANGSMITH_API_URL` - Default: `https://api.smith.langchain.com/api/v1`
- `LANGSMITH_TIMEOUT_SECONDS` - Default: 300 (5 minutes)
- `LANGCHAIN_PROJECT` - Default: `researchflow-bias-detection`
- `LANGCHAIN_TRACING_V2` - Default: `false`
- `LOG_LEVEL` - Default: `INFO`

## Deployment

The proxy is deployed as a Docker Compose service:

```yaml
agent-bias-detection-proxy:
  build:
    context: services/agents/agent-bias-detection-proxy
  environment:
    - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
    - LANGSMITH_AGENT_ID=${LANGSMITH_BIAS_DETECTION_AGENT_ID}
  networks:
    - researchflow
```

## Integration

The orchestrator routes `CLINICAL_BIAS_DETECTION` tasks to this proxy:

```json
{
  "agent-bias-detection": "http://agent-bias-detection-proxy:8000"
}
```

## Workflow Architecture

The agent follows a 6-phase workflow:

1. **Data Ingestion** - Parse dataset (Google Sheets / pasted data)
2. **Scan & Flag** - Delegate to Bias_Scanner worker
3. **Mitigation** - Delegate to Bias_Mitigator worker
4. **Validation** - Parallel execution of Compliance_Reviewer + Red_Team_Validator
5. **Report Generation** - Create Google Doc + optional email
6. **Audit Logging** - Log all analysis to persistent audit trail

## Sub-Workers

The LangSmith agent includes 5 specialized workers:

- **Bias_Scanner** - Deep bias scanning with metrics
- **Bias_Mitigator** - Mitigation strategy generation
- **Compliance_Reviewer** - Regulatory risk assessment (FDA, ICH, etc.)
- **Red_Team_Validator** - Adversarial stress-testing
- **Audit_Logger** - Persistent audit trail management

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Run bias detection
curl -X POST http://localhost:8000/agents/run/sync \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "CLINICAL_BIAS_DETECTION",
    "request_id": "test-123",
    "inputs": {
      "dataset_summary": "Clinical trial with 1000 participants...",
      "sensitive_attributes": ["gender", "age"],
      "outcome_variables": ["treatment_response"]
    }
  }'
```

## Monitoring

- Logs are written to stdout in JSON format
- LangSmith tracing can be enabled via `LANGCHAIN_TRACING_V2=true`
- Health checks verify LangSmith API connectivity

## Error Handling

The proxy handles:
- LangSmith API errors (4xx, 5xx)
- Network timeouts
- Invalid configurations
- Missing API keys

All errors return standard ResearchFlow error format:
```json
{
  "ok": false,
  "request_id": "...",
  "error": "Detailed error message"
}
```
