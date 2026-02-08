# Release Guardian Agent - Phase 1.5

Pre-deployment gate enforcement system for ResearchFlow releases. Ensures all deployment readiness checks pass before allowing deployment to production.

**Linear Issue:** ROS-150

## Overview

The Release Guardian Agent implements a comprehensive pre-deployment validation system that:

1. **Evaluates Deployment Gates** - Runs all required validation checks
2. **Analyzes Results** - Uses GPT-4o for policy-based reasoning
3. **Makes Decisions** - Approves or blocks deployment
4. **Executes Actions** - Implements appropriate follow-ups
5. **Reports Status** - Generates deployment readiness documentation

## Architecture

```
Release Guardian Agent (LangGraph)
├── evaluate_gates_node
│   ├── CIStatusGate
│   ├── EvidencePackGate
│   ├── FAVESGate (LIVE only)
│   ├── RollbackGate
│   └── MonitoringGate
├── analyze_results_node (GPT-4o policy reasoning)
├── make_decision_node
├── execute_actions_node
│   ├── BlockDeployment
│   ├── ApproveDeployment
│   ├── RequestSignoff
│   └── GenerateReleaseReport
└── generate_report_node
```

## Validation Checklist

The following checks are enforced:

- [ ] **All CI checks passed** - GitHub Actions workflows complete successfully
- [ ] **Evidence pack hash computed and recorded** - Deployment artifacts verified
- [ ] **FAVES gate passed** - LIVE deployments only, compliance verified
- [ ] **Rollback plan documented** - Tested recovery procedure in place
- [ ] **Monitoring dashboard configured** - Alerting rules and metrics enabled

## Gate Definitions

### CIStatusGate

Verifies that all GitHub Actions CI checks pass.

**Context Required:**
- `github_token` - GitHub API token
- `repo_owner` - Repository owner
- `repo_name` - Repository name
- `branch` - Branch to check (default: main)
- `commit_sha` - Optional specific commit

**Failure Handling:**
- Blocks deployment automatically
- Provides list of failing checks
- Recommends fix before retry

### EvidencePackGate

Verifies evidence pack exists and is hashed for audit trail.

**Context Required:**
- `evidence_pack_path` - Path to evidence pack
- `expected_hash` - Optional expected SHA256 hash

**Computations:**
- SHA256 hash of files (single) or directory tree
- File/directory size calculation
- Timestamps

### FAVESGate

LIVE-mode only gate verifying FAVES compliance (Fairness, Accountability, Transparency).

**Context Required:**
- `deployment_mode` - "LIVE" or "DEMO"
- `faves_assessment` - Assessment document with:
  - `assessment_date` - Date of assessment
  - `risk_level` - Risk classification
  - `approval_status` - Must be "APPROVED"

**Behavior:**
- Skipped for DEMO deployments
- Required for LIVE deployments
- Blocks if not approved

### RollbackGate

Verifies rollback plan is documented and tested.

**Context Required:**
- `rollback_plan` - Plan document with:
  - `steps` - Array of rollback steps
  - `estimated_duration_minutes` - Time estimate
  - `contact` - Escalation contact
- `rollback_tested` - Boolean indicating plan testing

**Behavior:**
- Blocks if plan missing
- Blocks if plan not tested
- Used for operational safety

### MonitoringGate

Ensures monitoring dashboard is configured with required alerts and metrics.

**Context Required:**
- `monitoring_dashboard_url` - URL to monitoring system
- `alerting_rules` - Object with alert types:
  - `error_rate` - Application error alerts
  - `latency_p99` - Performance alerts
  - `memory_usage` - Resource alerts
  - `database_connection_pool` - Database alerts
- `metrics_configured` - Array of metric names

**Minimum Required Metrics:**
- `cpu_usage`
- `memory_usage`
- `error_rate`
- `latency`

## Validators

### GitHubCIValidator

Checks GitHub Actions workflow status.

```python
validator = GitHubCIValidator()
checks = await validator.check_ci_status(
    token="github_token",
    owner="researchflow",
    repo="main",
    branch="main"
)
```

Returns list of check results:
```python
[
    {
        "name": "test-suite",
        "passed": True,
        "status": "completed",
        "conclusion": "success",
        "url": "https://github.com/.../runs/123"
    }
]
```

### EvidenceHashValidator

Computes and verifies evidence pack hashes.

```python
validator = EvidenceHashValidator()
pack_info = await validator.verify_and_hash_pack(
    pack_path="/path/to/evidence",
    hash_algorithm="sha256"
)
```

Returns:
```python
{
    "exists": True,
    "path": "/path/to/evidence",
    "hash": "a1b2c3d4...",
    "size": 1024000,
    "type": "directory",
    "file_count": 42,
    "created": "2026-01-30T15:30:00",
    "modified": "2026-01-30T15:35:00"
}
```

### NotionSignoffValidator

Queries Notion for release signoffs.

```python
validator = NotionSignoffValidator()
signoffs = await validator.check_release_signoffs(
    notion_token="notion_token",
    database_id="db_id",
    release_id="RLS-001"
)
```

Returns:
```python
{
    "complete": True,
    "release_id": "RLS-001",
    "signoffs": {
        "product_owner": True,
        "security": True,
        "qa": True,
        "deployment": True
    },
    "page_url": "https://notion.so/..."
}
```

### DeploymentModeValidator

Determines DEMO vs LIVE deployment mode.

```python
mode = DeploymentModeValidator.determine_mode(context)
# Returns: "LIVE" or "DEMO"

requirements = DeploymentModeValidator.get_mode_requirements(mode)
# Returns mode-specific requirements
```

**Mode Determination:**
- Explicit `deployment_mode` in context
- Branch-based: main/master/production → LIVE
- Target-based: prod/production → LIVE
- Default: DEMO

## Actions

### BlockDeployment

Blocks deployment with documented reason.

```python
action = BlockDeployment()
result = await action.execute({
    "release_id": "RLS-001",
    "reason": "Critical CI checks failed",
    "blocking_gates": ["ci_status", "monitoring"],
    "notification_channel": "slack"
})
```

**Sends Notifications:**
- Slack integration (via Composio)
- Email notifications (configurable)
- Webhook callbacks

### ApproveDeployment

Approves deployment and logs decision.

```python
action = ApproveDeployment()
result = await action.execute({
    "release_id": "RLS-001",
    "approval_reason": "All gates passed",
    "approved_by": "ReleaseGuardianAgent",
    "gate_results": [...]
})
```

**Audit Logging:**
- Records approval decision
- Captures gate results at approval time
- Timestamps decision

### RequestSignoff

Requests missing signoffs from stakeholders.

```python
action = RequestSignoff()
result = await action.execute({
    "release_id": "RLS-001",
    "missing_signoffs": ["qa", "security"],
    "notion_database_id": "db_id",
    "stakeholder_emails": ["qa@researchflow.io"]
})
```

**Integrations:**
- Updates Notion tracking database
- Sends email notifications
- Tracks completion status

### GenerateReleaseReport

Generates comprehensive deployment readiness report.

```python
action = GenerateReleaseReport()
result = await action.execute({
    "release_id": "RLS-001",
    "gate_results": [...],
    "deployment_mode": "LIVE",
    "deployment_target": "prod-us-east-1"
})
```

**Report Contents:**
- Gate pass/fail summary
- Remediation recommendations
- Deployment readiness assessment
- Audit trail

## Usage Example

```python
from agents.release_guardian import ReleaseGuardianAgent

# Initialize agent
agent = ReleaseGuardianAgent()

# Prepare release context
context = {
    "github_token": "<your-github-token>",
    "repo_owner": "researchflow",
    "repo_name": "main",
    "branch": "main",
    "evidence_pack_path": "/releases/v2.0.0",
    "expected_hash": "a1b2c3d4...",
    "rollback_plan": {
        "steps": [
            "Scale down new deployment",
            "Restore previous database snapshot",
            "Update load balancer routing"
        ],
        "estimated_duration_minutes": 15,
        "contact": "oncall@researchflow.io"
    },
    "rollback_tested": True,
    "monitoring_dashboard_url": "https://grafana.researchflow.io/...",
    "alerting_rules": {
        "error_rate": {"threshold": "5%"},
        "latency_p99": {"threshold": "500ms"},
        "memory_usage": {"threshold": "80%"},
        "database_connection_pool": {"threshold": "90%"}
    },
    "metrics_configured": ["cpu_usage", "memory_usage", "error_rate", "latency"],
    "deployment_mode": "LIVE",
    "faves_assessment": {
        "assessment_date": "2026-01-30",
        "risk_level": "low",
        "approval_status": "APPROVED"
    }
}

# Run evaluation
result = await agent.run(
    release_id="RLS-v2.0.0",
    release_context=context
)

# Check result
if result.deployment_approved:
    print(f"Deployment approved! Gates passed: {result.gates_passed}")
else:
    print(f"Deployment blocked. Gates failed: {result.gates_failed}")
    for action in result.actions_taken:
        print(f"  - {action.action_name}: {action.message}")
```

## Decision Logic

**Approval Criteria:**

1. **All gates pass** → Automatic approval
2. **Critical gates fail** (CI, Rollback, Monitoring) → Automatic block
3. **Non-critical gates fail** → Request manual signoff

**Mode-Specific:**

- **LIVE Mode:**
  - All gates required
  - FAVES assessment required
  - Rollback plan must be tested
  - Security review required

- **DEMO Mode:**
  - CI status required
  - Monitoring required
  - FAVES and security review optional
  - Rollback plan optional

## Error Handling

All components include robust error handling:

1. **Gate Errors** - Logged and result recorded as failed
2. **Validator Errors** - Logged, returned in details
3. **Action Errors** - Logged, execution continues
4. **LLM Errors** - Fallback to rule-based logic
5. **Network Errors** - Retry logic with exponential backoff

## Integration with Composio

### GitHub Toolkit

Used for:
- Fetching workflow run status
- Checking branch protection rules
- Commenting on releases
- Creating deployment records

### Notion Toolkit

Used for:
- Querying signoff database
- Updating release status
- Recording gate results
- Tracking deployment history

## Configuration

```python
from agents.release_guardian import ReleaseGuardianConfig, ReleaseGuardianAgent

config = ReleaseGuardianConfig(
    llm_model="gpt-4o",
    llm_temperature=0.3,
    max_iterations=3,
    timeout_seconds=300,
    enable_composio_github=True,
    enable_composio_notion=True
)

agent = ReleaseGuardianAgent(config)
```

## Logging

All operations are logged with contextual information:

```
[Release Guardian] Starting evaluation for RLS-v2.0.0
[Release Guardian] Deployment mode: LIVE
[Release Guardian] Running gate: ci_status
[Release Guardian] Analyzing gate results for RLS-v2.0.0
[Release Guardian] Making decision for RLS-v2.0.0
[Release Guardian] All gates passed - deployment approved
[Release Guardian] Executing actions for RLS-v2.0.0
[Release Guardian] Evaluation complete for RLS-v2.0.0: approved=True, gates_passed=5, gates_failed=0
```

## Testing

Run tests with pytest:

```bash
pytest tests/unit/release_guardian/
```

Test coverage includes:
- Individual gate checks
- Validator functions
- Action execution
- Decision logic
- Full end-to-end workflows
- Error scenarios

## Performance

- **Typical Execution:** 5-15 seconds
- **Timeout:** 300 seconds (configurable)
- **Gate Parallelization:** Gates run sequentially for consistency
- **LLM Analysis:** ~2-3 seconds for policy reasoning

## Security

- GitHub tokens handled securely (environment variables)
- Notion tokens never logged
- No sensitive data in error messages
- Audit trail of all decisions
- Role-based access control (future)

## Future Enhancements

- [ ] Parallel gate execution
- [ ] Custom gate definitions
- [ ] Deployment approval dashboard
- [ ] A/B testing support
- [ ] Canary deployment integration
- [ ] Feature flag coordination
- [ ] Automatic rollback triggering
- [ ] Machine learning-based risk scoring
