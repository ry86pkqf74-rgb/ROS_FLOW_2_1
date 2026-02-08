# Release Guardian Agent - Quick Start Guide

## Installation

The Release Guardian Agent is already installed. Import it:

```python
from services.worker.src.agents.release_guardian import ReleaseGuardianAgent
```

## Basic Usage

### 1. Create Agent Instance

```python
from services.worker.src.agents.release_guardian import ReleaseGuardianAgent

agent = ReleaseGuardianAgent()
```

### 2. Prepare Release Context

```python
import os

context = {
    # GitHub Configuration
    "github_token": os.getenv("GITHUB_TOKEN"),
    "repo_owner": "researchflow",
    "repo_name": "main",
    "branch": "main",

    # Evidence Pack
    "evidence_pack_path": "/releases/v2.0.0",

    # Rollback Plan
    "rollback_plan": {
        "steps": [
            "Scale down new deployment",
            "Restore database snapshot",
            "Update load balancer"
        ],
        "estimated_duration_minutes": 15,
        "contact": "oncall@researchflow.io"
    },
    "rollback_tested": True,

    # Monitoring
    "monitoring_dashboard_url": "https://grafana.researchflow.io/d/prod",
    "alerting_rules": {
        "error_rate": {"threshold": "5%"},
        "latency_p99": {"threshold": "500ms"},
        "memory_usage": {"threshold": "80%"},
        "database_connection_pool": {"threshold": "90%"}
    },
    "metrics_configured": [
        "cpu_usage",
        "memory_usage",
        "error_rate",
        "latency"
    ],

    # Deployment
    "deployment_mode": "LIVE",
    "target": "prod-us-east-1"
}
```

### 3. Run Evaluation

```python
result = await agent.run(
    release_id="v2.0.0",
    release_context=context
)
```

### 4. Check Results

```python
if result.deployment_approved:
    print(f"✓ Approved! Gates passed: {result.gates_passed}")
    print(f"  All systems ready for deployment")
else:
    print(f"✗ Blocked! Gates failed: {result.gates_failed}")
    for action in result.actions_taken:
        print(f"  Action: {action.action_name}")
        print(f"    Message: {action.message}")

print(f"\nEvaluation took: {result.duration_seconds:.1f}s")
```

## Common Scenarios

### Scenario 1: DEMO Deployment (Low Risk)

```python
context_demo = {
    "github_token": os.getenv("GITHUB_TOKEN"),
    "repo_owner": "researchflow",
    "repo_name": "main",
    "branch": "develop",  # Non-production branch
    "evidence_pack_path": "/releases/v2.0.0-rc1",
    "monitoring_dashboard_url": "https://grafana.researchflow.io/d/demo",
    "alerting_rules": {"error_rate": {}},
    "metrics_configured": ["error_rate"],
    "deployment_mode": "DEMO"
}

result = await agent.run("v2.0.0-rc1", context_demo)
```

### Scenario 2: LIVE Deployment (High Risk)

```python
context_live = {
    "github_token": os.getenv("GITHUB_TOKEN"),
    "repo_owner": "researchflow",
    "repo_name": "main",
    "branch": "main",
    "commit_sha": "a1b2c3d4...",
    "evidence_pack_path": "/releases/v2.0.0",
    "expected_hash": "sha256:abcd1234...",

    # LIVE-specific requirements
    "faves_assessment": {
        "assessment_date": "2026-01-30",
        "risk_level": "low",
        "approval_status": "APPROVED"
    },

    "rollback_plan": {
        "steps": [
            "Scale down new version",
            "Restore snapshot from t-5min",
            "Update routing back to v1.9.9",
            "Verify health checks pass",
            "Monitor error rate for 5min"
        ],
        "estimated_duration_minutes": 20,
        "contact": "oncall@researchflow.io"
    },
    "rollback_tested": True,

    "monitoring_dashboard_url": "https://grafana.researchflow.io/d/prod",
    "alerting_rules": {
        "error_rate": {"threshold": "5%"},
        "latency_p99": {"threshold": "500ms"},
        "memory_usage": {"threshold": "80%"},
        "database_connection_pool": {"threshold": "90%"}
    },
    "metrics_configured": [
        "cpu_usage", "memory_usage", "error_rate", "latency"
    ],

    "deployment_mode": "LIVE",
    "target": "prod-us-east-1",
    "stakeholder_emails": ["qa@researchflow.io", "eng-lead@researchflow.io"]
}

result = await agent.run("v2.0.0", context_live)
```

### Scenario 3: Handling Blocks

```python
result = await agent.run("v2.0.0", context)

if not result.deployment_approved:
    print(f"Deployment blocked: {result.gates_failed}")

    # Check what actions were taken
    for action in result.actions_taken:
        if action.action_name == "BLOCK_DEPLOYMENT":
            print(f"Reason: {action.details}")
            print(f"Gates blocked on:")
            for gate in action.details.get("gates", []):
                print(f"  - {gate}")

        elif action.action_name == "REQUEST_SIGNOFF":
            print(f"Signoffs requested for:")
            for signoff in action.details.get("signoffs", []):
                print(f"  - {signoff}")
```

## Gate Quick Reference

| Gate | Purpose | Required | DEMO | LIVE |
|------|---------|----------|------|------|
| **CI Status** | GitHub Actions pass | Yes | Yes | Yes |
| **Evidence Pack** | Hash recorded | Yes | Yes | Yes |
| **FAVES** | Compliance verified | No | No | Yes |
| **Rollback** | Plan tested | Yes | Optional | Yes |
| **Monitoring** | Dashboard ready | Yes | Yes | Yes |

## Configuration Reference

### Minimal Configuration (DEMO)

```python
{
    "github_token": "<your-github-token>",
    "repo_owner": "researchflow",
    "repo_name": "main",
    "branch": "develop",
    "evidence_pack_path": "/releases/v2.0.0-rc1",
    "monitoring_dashboard_url": "https://grafana...",
    "alerting_rules": {},
    "metrics_configured": []
}
```

### Full Configuration (LIVE)

```python
{
    # GitHub
    "github_token": "<your-github-token>",
    "repo_owner": "researchflow",
    "repo_name": "main",
    "branch": "main",
    "commit_sha": "a1b2c3d4...",

    # Evidence
    "evidence_pack_path": "/releases/v2.0.0",
    "expected_hash": "sha256:...",

    # FAVES (LIVE only)
    "faves_assessment": {
        "assessment_date": "2026-01-30",
        "risk_level": "low",
        "approval_status": "APPROVED"
    },

    # Rollback
    "rollback_plan": {
        "steps": [...],
        "estimated_duration_minutes": 20,
        "contact": "oncall@researchflow.io"
    },
    "rollback_tested": True,

    # Monitoring
    "monitoring_dashboard_url": "https://grafana.researchflow.io/d/prod",
    "alerting_rules": {
        "error_rate": {"threshold": "5%"},
        "latency_p99": {"threshold": "500ms"},
        "memory_usage": {"threshold": "80%"},
        "database_connection_pool": {"threshold": "90%"}
    },
    "metrics_configured": [
        "cpu_usage", "memory_usage", "error_rate", "latency"
    ],

    # Deployment
    "deployment_mode": "LIVE",
    "target": "prod-us-east-1",
    "stakeholder_emails": [...]
}
```

## Result Interpretation

### Approved Deployment

```
✓ deployment_approved: True
✓ gates_failed: 0
✓ gates_passed: 5
→ Action: ApproveDeployment executed
```

**Next Step:** Proceed with deployment

### Blocked Deployment (Critical)

```
✗ deployment_approved: False
✗ gates_failed: 2 (ci_status, monitoring)
→ Action: BlockDeployment executed
→ Reason: "Critical gates failed: ci_status, monitoring"
```

**Next Step:** Fix failing gates, retry

### Manual Review Needed

```
? deployment_approved: False (but not blocked)
✗ gates_failed: 1 (faves)
→ Action: RequestSignoff executed
→ Signoffs requested for: faves
```

**Next Step:** Wait for stakeholder signoff, or override

## Troubleshooting

### GitHub Token Issues

```python
# Error: "No checks found" or API errors
# Solution: Verify token and permissions
context["github_token"] = os.getenv("GITHUB_TOKEN")
# Token needs: repo, workflow scopes
```

### Missing Context Fields

```python
# Error: "No evidence pack path provided"
# Solution: Add required field
context["evidence_pack_path"] = "/path/to/evidence"
```

### Monitoring Configuration

```python
# Error: "Missing required alerting rules"
# Solution: Add all required alert types
context["alerting_rules"] = {
    "error_rate": {},
    "latency_p99": {},
    "memory_usage": {},
    "database_connection_pool": {}
}
```

## Environment Variables

Required:
```bash
export GITHUB_TOKEN="<your-github-token>"
export OPENAI_API_KEY="sk-..."
```

Optional:
```bash
export RELEASE_GUARDIAN_LOG_LEVEL="INFO"
export RELEASE_GUARDIAN_TIMEOUT="300"
```

## Performance Tips

1. **Gate Evaluation Parallelization** (future feature)
   - Currently gates run sequentially
   - Parallel execution coming in Phase 2

2. **Caching**
   - CI results cached per run
   - Hash computation incremental for large packs

3. **Timeout Configuration**
   ```python
   from services.worker.src.agents.release_guardian import ReleaseGuardianConfig

   config = ReleaseGuardianConfig(timeout_seconds=600)
   agent = ReleaseGuardianAgent(config)
   ```

## Getting Help

### Check Logs

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose Release Guardian logs
logging.getLogger("release_guardian").setLevel(logging.DEBUG)
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| "CI status check failed" | GitHub token invalid | Verify GITHUB_TOKEN |
| "Evidence pack not found" | Path incorrect | Check evidence_pack_path |
| "FAVES not approved" | Status != "APPROVED" | Complete FAVES assessment |
| "Rollback plan not tested" | rollback_tested = False | Test rollback procedure |
| "Monitoring dashboard URL not configured" | Missing field | Add monitoring_dashboard_url |

## Next Steps

1. **Test in DEMO mode** - Low risk evaluation
2. **Review results** - Understand gate results
3. **Fix any issues** - Address blocking gates
4. **Deploy to LIVE** - When all gates pass
5. **Monitor** - Watch deployment progress

## Additional Resources

- **Full Documentation:** `README.md`
- **Implementation Details:** `RELEASE_GUARDIAN_IMPLEMENTATION.md`
- **Architecture:** See `agent.py` docstrings
- **Gate Details:** See `gates.py` docstrings
- **Validator Details:** See `validators.py` docstrings

---

**Quick Links:**
- GitHub Docs: https://docs.github.com/en/rest
- Notion API: https://developers.notion.com
- OpenAI Docs: https://platform.openai.com/docs
- LangGraph: https://langgraph.com/docs
