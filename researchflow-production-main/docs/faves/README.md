# FAVES Compliance Framework

**FAVES** stands for **Fair, Appropriate, Valid, Effective, Safe** - a comprehensive evaluation framework for AI models deployed in healthcare and research contexts.

## Overview

The FAVES framework ensures AI models meet rigorous standards across five critical dimensions before deployment. All dimensions must **PASS** for deployment to be allowed.

---

## The Five Dimensions

### 1. FAIR (Fairness)

**Purpose**: Ensure the model performs equitably across demographic subgroups.

**Requirements**:
- **Metrics**:
  - Stratified AUC by subgroup (age, sex, race)
  - Demographic parity gap ≤ 0.1
  - Equalized odds difference ≤ 0.1
  - Minimum subgroup AUC ≥ 0.7
  
- **Required Artifacts**:
  - `representativeness_report.json` - Dataset representativeness analysis
  - `fairness_analysis.md` - Fairness metrics breakdown

- **Thresholds**:
  ```json
  {
    "demographic_parity_gap": 0.1,
    "min_subgroup_auc": 0.7
  }
  ```

**Example Evaluation**:
```bash
# Python evaluator
from evaluators.faves_evaluator import FAVESEvaluator

evaluator = FAVESEvaluator(
    model_id="550e8400-e29b-41d4-a716-446655440000",
    model_version="1.2.0",
    artifacts_dir="docs/faves"
)

result = evaluator.evaluate_fairness()
print(f"Status: {result.status}")
print(f"Score: {result.score}/100")
```

---

### 2. APPROPRIATE (Appropriateness)

**Purpose**: Verify the model is used for its intended purpose and fits clinical workflow.

**Requirements**:
- **Metrics**:
  - Intended use coverage score ≥ 0.9
  - Workflow fit score ≥ 0.8
  
- **Required Artifacts**:
  - `intended_use.md` - Clear statement of intended use
  - `out_of_scope.md` - Explicit contraindications and out-of-scope scenarios
  - `workflow_integration.md` - How model integrates into clinical workflow

**Thresholds**:
```json
{
  "intended_use_coverage": 0.9,
  "workflow_fit": 0.8
}
```

**Documentation Template**:
```markdown
# Intended Use

## Clinical Context
- **Population**: Adult patients (18+) with suspected sepsis
- **Setting**: Emergency department triage
- **Decision Support**: Risk stratification for sepsis severity

## User Profile
- **Primary Users**: Emergency physicians, triage nurses
- **Training Required**: 2-hour certification course
- **Supervision**: Results reviewed by attending physician

## Contraindications
- Pediatric patients (< 18 years)
- Patients with known immune disorders
- Post-surgical patients (< 72 hours)
```

---

### 3. VALID (Validity)

**Purpose**: Ensure model is well-calibrated and validated on external datasets.

**Requirements**:
- **Metrics**:
  - Calibration error ≤ 0.1
  - Brier score ≤ 0.25
  - External validation AUC ≥ 0.7
  - Hosmer-Lemeshow p-value
  
- **Required Artifacts**:
  - `calibration_report.json` - Calibration curve and metrics
  - `external_validation.md` - External validation study results

**Thresholds**:
```json
{
  "calibration_error": 0.1,
  "brier_score": 0.25,
  "external_validation_auc": 0.7
}
```

**External Validation Requirements**:
- Separate dataset from training/internal validation
- Different time period or geographic location
- Minimum 500 samples
- Similar clinical context

---

### 4. EFFECTIVE (Effectiveness)

**Purpose**: Demonstrate clinical utility via decision curve analysis.

**Requirements**:
- **Metrics**:
  - Net benefit at clinically relevant threshold > 0
  - Decision curve AUC
  - Number needed to treat (NNT)
  
- **Required Artifacts**:
  - `utility_analysis.md` - Decision curve analysis results
  - `actionability_doc.md` - How predictions lead to clinical actions

**Thresholds**:
```json
{
  "net_benefit_positive": 0.0
}
```

**Decision Curve Analysis**:
A model is considered effective if it provides positive net benefit compared to "treat all" or "treat none" strategies across clinically relevant threshold probabilities.

---

### 5. SAFE (Safety)

**Purpose**: Identify failure modes and ensure safety controls are in place.

**Requirements**:
- **Metrics**:
  - Overall error rate ≤ 0.05
  - Error rate by subgroup
  - Failure mode coverage ≥ 0.9
  
- **Required Artifacts**:
  - `error_analysis.md` - Systematic error analysis
  - `rollback_policy.md` - Model rollback procedures
  - `monitoring_plan.md` - Post-deployment monitoring strategy

**Thresholds**:
```json
{
  "max_error_rate": 0.05,
  "failure_mode_coverage": 0.9
}
```

**Required Safety Controls**:
1. Human override capability
2. Alerting for out-of-distribution inputs
3. Automated rollback triggers
4. Incident response procedures

---

## API Endpoints

### List Evaluations
```bash
GET /api/faves/evaluations?limit=50&deployment_allowed=true
```

**Response**:
```json
{
  "evaluations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "model_id": "660e8400-e29b-41d4-a716-446655440001",
      "model_version": "1.2.0",
      "overall_status": "PASS",
      "overall_score": 87.5,
      "deployment_allowed": true,
      "fair_score": 85,
      "appropriate_score": 90,
      "valid_score": 88,
      "effective_score": 86,
      "safe_score": 89,
      "evaluated_at": "2026-02-01T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 25,
    "limit": 50,
    "offset": 0
  }
}
```

### Get Single Evaluation
```bash
GET /api/faves/evaluations/:id
```

### Check Deployment Gate
```bash
GET /api/faves/gate/:modelId?version=1.2.0
```

**Response**:
```json
{
  "model_id": "660e8400-e29b-41d4-a716-446655440001",
  "gate_status": "PASS",
  "deployment_allowed": true,
  "overall_score": 87.5,
  "dimension_scores": {
    "fair": 85,
    "appropriate": 90,
    "valid": 88,
    "effective": 86,
    "safe": 89
  },
  "blocking_issues": [],
  "evaluated_at": "2026-02-01T10:30:00Z",
  "days_since_evaluation": 2,
  "is_stale": false
}
```

### Get Statistics
```bash
GET /api/faves/stats
```

### Create Evaluation
```bash
POST /api/faves/evaluations
Content-Type: application/json

{
  "model_id": "660e8400-e29b-41d4-a716-446655440001",
  "model_version": "1.2.0",
  "evaluation_type": "PRE_DEPLOYMENT"
}
```

### Submit Dimension Results
```bash
POST /api/faves/evaluations/:id/dimensions
Content-Type: application/json

[
  {
    "dimension": "FAIR",
    "status": "PASS",
    "score": 85,
    "metrics": [
      {
        "metric_name": "demographic_parity_gap",
        "value": 0.08,
        "threshold": 0.1,
        "passed": true
      }
    ],
    "missing_requirements": [],
    "recommendations": []
  }
]
```

---

## CI/CD Integration

The FAVES gate runs automatically on model deployments via GitHub Actions.

### Workflow Trigger
```yaml
# .github/workflows/faves-gate.yml
on:
  push:
    branches: [main, develop]
    paths:
      - 'services/worker/src/models/**'
  workflow_dispatch:
    inputs:
      model_id:
        description: 'Model UUID to evaluate'
        required: true
```

### Manual Trigger
```bash
gh workflow run faves-gate.yml \
  -f model_id=660e8400-e29b-41d4-a716-446655440001 \
  -f model_version=1.2.0
```

### Gate Enforcement
The workflow will **block deployment** if any dimension fails:
```
❌ FAVES GATE FAILED - Deployment blocked

Blocking dimensions:
  - FAIR: Demographic parity gap exceeded threshold
  - SAFE: Missing rollback_policy.md
```

---

## Python Evaluator Usage

### Basic Evaluation
```python
from evaluators.faves_evaluator import FAVESEvaluator, FAVESGate

# Create evaluator
evaluator = FAVESEvaluator(
    model_id="660e8400-e29b-41d4-a716-446655440001",
    model_version="1.2.0",
    artifacts_dir="docs/faves"
)

# Run full evaluation
result = evaluator.evaluate()

print(f"Overall Status: {result.overall_status}")
print(f"Overall Score: {result.overall_score:.1f}%")
print(f"Deployment Allowed: {result.deployment_allowed}")

# Check individual dimensions
for dim_name, dim_result in result.dimensions.items():
    print(f"{dim_name.upper()}: {dim_result.score:.1f}% - {dim_result.status}")
```

### CI/CD Gate Enforcement
```python
from evaluators.faves_evaluator import FAVESEvaluator, FAVESGate

evaluator = FAVESEvaluator(
    model_id=os.getenv("MODEL_ID"),
    model_version=os.getenv("MODEL_VERSION"),
    artifacts_dir="docs/faves"
)

gate = FAVESGate(evaluator)
gate.enforce()  # Exits with code 1 if failed
```

### Custom Metrics Provider
```python
def my_metrics_provider(metric_name: str) -> float:
    # Fetch from your model registry/metrics store
    return model_metrics.get(metric_name)

evaluator = FAVESEvaluator(
    model_id="...",
    model_version="1.2.0",
    artifacts_dir="docs/faves",
    metrics_provider=my_metrics_provider
)
```

---

## Frontend Dashboard

Access the FAVES dashboard at:
```
http://localhost:5173/transparency/faves
```

**Features**:
- View all model evaluations
- Filter by pass/fail status
- Drill down into individual dimension scores
- View blocking issues
- Track evaluation history

---

## Artifact Directory Structure

```
docs/faves/
├── README.md (this file)
├── intended_use.md
├── out_of_scope.md
├── workflow_integration.md
├── representativeness_report.json
├── fairness_analysis.md
├── calibration_report.json
├── external_validation.md
├── utility_analysis.md
├── actionability_doc.md
├── error_analysis.md
├── rollback_policy.md
└── monitoring_plan.md
```

---

## Compliance Standards

FAVES aligns with:
- **NIST AI RMF** - Risk management framework
- **WHO FAST** - Framework for AI in healthcare
- **FDA Guidance** - Software as a Medical Device (SaMD)
- **EU AI Act** - High-risk AI system requirements

---

## Stale Evaluations

Evaluations older than **90 days** are considered stale and will block deployment until re-evaluation.

---

## Override Requests

If a model fails FAVES but deployment is urgent, stewards/admins can request an override:

```bash
POST /api/faves/gate/:modelId/override
Content-Type: application/json

{
  "reason": "Critical bug fix for production incident. Fairness gap (0.12) slightly exceeds threshold but is being actively addressed in next version.",
  "risk_acknowledgment": true,
  "approval_expires_at": "2026-02-15T00:00:00Z"
}
```

**Requirements**:
- Reason must be ≥ 50 characters
- Risk acknowledgment required
- Requires STEWARD or ADMIN role
- Logged to audit trail
- Requires admin approval

---

## Support

For questions or issues:
- **Documentation**: `/docs/faves/`
- **API Reference**: `GET /api/faves/evaluations`
- **GitHub Issues**: Tag with `transparency` label

---

**Last Updated**: February 3, 2026
**Schema Version**: 1.0.0
