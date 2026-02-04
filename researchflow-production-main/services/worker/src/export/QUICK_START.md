# Evidence Bundle Exporter - Quick Start Guide

## Installation

```bash
# Basic installation (JSON, Markdown, ZIP only)
pip install -e .

# With PDF support
pip install reportlab
```

## 30-Second Example

```python
from export.evidence_bundle_exporter import *
from datetime import datetime

# Create metadata
meta = EvidenceBundleMetadata(
    bundle_id="MODEL_V1",
    model_name="My Model",
    model_version="1.0.0"
)

# Create model card
card = ModelCard(
    model_name="My Model",
    model_version="1.0.0",
    description="A predictive model"
)

# Create metrics
metrics = PerformanceMetrics(
    metrics={"accuracy": 0.95, "precision": 0.92}
)

# Bundle and export
bundle = EvidenceBundle(meta, card, metrics)
exporter = EvidenceBundleExporter()

# Export to all formats
results = exporter.export_all_formats(bundle, "/output")
# Returns: {
#   ExportFormat.JSON: "/output/...",
#   ExportFormat.MARKDOWN: "/output/...",
#   ExportFormat.ZIP: "/output/..."
# }
```

## Common Patterns

### Export to Single Format
```python
# JSON
path = exporter.export_to_json(bundle, "bundle.json")

# Markdown
path = exporter.export_to_markdown(bundle, "bundle.md")

# PDF (requires reportlab)
path = exporter.export_to_pdf(bundle, "bundle.pdf")

# ZIP Archive
path = exporter.export_to_archive(bundle, "bundle.zip")
```

### Add Fairness Analysis
```python
fairness = FairnessAnalysis(
    fairness_metrics={"demographic_parity": 0.98},
    protected_attributes=["gender", "age"],
    bias_assessment="Model shows good fairness metrics"
)

bundle = EvidenceBundle(
    meta, card, metrics,
    fairness_analysis=fairness
)
```

### Add Validation Results
```python
validation = ValidationResults(
    test_suites={
        "unit_tests": {"passed": 100, "failed": 0},
        "integration_tests": {"passed": 25, "failed": 0}
    },
    overall_status="passed",
    test_coverage=95.0
)

bundle = EvidenceBundle(
    meta, card, metrics,
    validation_results=validation
)
```

### Add Audit Trail
```python
audit = AuditTrail()
audit.add_event("model_created", "alice@example.com", {"version": "1.0.0"})
audit.add_event("model_trained", "ml_pipeline", {"epochs": 50})
audit.add_event("validated", "qa_team", {"status": "passed"})

bundle = EvidenceBundle(
    meta, card, metrics,
    audit_trail=audit
)
```

### Add Regulatory Compliance
```python
compliance = RegulatoryCompliance(
    applicable_regulations=["HIPAA", "GDPR"],
    compliance_status={
        "HIPAA": "Compliant",
        "GDPR": "Compliant"
    },
    certifications=["ISO 27001", "SOC 2"],
    privacy_measures=["Encryption", "De-identification"],
    security_measures=["Access Control", "Audit Logging"]
)

bundle = EvidenceBundle(
    meta, card, metrics,
    regulatory_compliance=compliance
)
```

### Complete Full Bundle
```python
bundle = EvidenceBundle(
    metadata=meta,
    model_card=card,
    performance_metrics=metrics,
    fairness_analysis=fairness,
    validation_results=validation,
    audit_trail=audit,
    regulatory_compliance=compliance
)

# Export everything
results = exporter.export_all_formats(bundle, "/output")
```

## What Each Format Looks Like

### JSON
```json
{
  "metadata": {
    "bundle_id": "MODEL_V1",
    "model_name": "My Model",
    "model_version": "1.0.0",
    "created_at": "2024-01-30T12:00:00",
    ...
  },
  "model_card": { ... },
  "performance_metrics": { ... },
  ...
}
```

### Markdown
```markdown
# Evidence Bundle Report

## Metadata
- **Bundle ID**: MODEL_V1
- **Model Name**: My Model
- **Model Version**: 1.0.0

## Model Card
### Basic Information
- **Model Name**: My Model
...

## Performance Metrics
### Metrics
- **accuracy**: 0.9500
...
```

### PDF
Professional multi-page report with:
- Title page with metadata
- Model card details
- Performance metrics in tables
- Fairness analysis with charts
- Validation results summary
- Audit trail
- Compliance checklist

### ZIP
Contains all above formats plus:
- `README.txt` with archive contents
- All files compressed and organized

## Error Handling

```python
from export.exceptions import ExportError

try:
    exporter.export_to_json(bundle, output_path)
except ExportError as e:
    print(f"Export failed: {e}")
```

## Tips & Tricks

1. **Optional Components**: Start with just metadata, model card, and metrics. Add others as needed.

2. **Bulk Export**: Use `export_all_formats()` to create all formats at once.

3. **ZIP for Distribution**: Use ZIP archives to share evidence bundles with stakeholders.

4. **Confidence Intervals**: Include confidence intervals for key metrics:
   ```python
   metrics = PerformanceMetrics(
       metrics={"accuracy": 0.95},
       confidence_intervals={"accuracy": (0.94, 0.96)}
   )
   ```

5. **Audit Trail Events**: Use meaningful action names:
   - `model_creation`
   - `model_trained`
   - `model_validated`
   - `model_deployed`
   - `parameter_updated`

6. **Protected Attributes**: Document fairness across meaningful demographics:
   ```python
   FairnessAnalysis(
       protected_attributes=["gender", "age_group", "ethnicity", "zip_code"]
   )
   ```

7. **Chain of Custody**: Track artifact versions:
   ```python
   audit.chain_of_custody = [
       "Model: model_v1.0.0.pkl (SHA256: abc...)",
       "Data: training_dataset_2024.parquet (Access: Restricted)",
       "Report: validation_report.json"
   ]
   ```

## Full Example File

See `example_evidence_bundle.py` for a complete working example with:
- All component types
- Real-world data
- All export formats
- Best practices demonstrated

## Next Steps

1. Read `EVIDENCE_BUNDLE_README.md` for comprehensive documentation
2. Review `example_evidence_bundle.py` for real-world usage
3. Run tests with `pytest test_evidence_bundle_exporter.py -v`
4. Check docstrings in `evidence_bundle_exporter.py` for API details
