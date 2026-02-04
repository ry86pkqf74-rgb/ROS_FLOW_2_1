# Evidence Bundle Exporter Module

A comprehensive Python module for exporting evidence bundles to multiple formats (JSON, Markdown, PDF, and ZIP archives). Ideal for model governance, audit trails, regulatory compliance, and documentation purposes.

## Features

### Export Formats
- **JSON**: Structured data format for programmatic access
- **Markdown**: Human-readable formatted documentation
- **PDF**: Professional formatted reports (requires reportlab)
- **ZIP Archive**: Multi-format bundles with metadata

### Evidence Bundle Components
1. **Metadata**: Bundle identification and creation information
2. **Model Card**: Model description, architecture, intended use
3. **Performance Metrics**: Evaluation results with confidence intervals
4. **Fairness Analysis**: Bias metrics, protected attributes, mitigation strategies
5. **Validation Results**: Test suite results, coverage, failure cases
6. **Audit Trail**: Event log with chain of custody
7. **Regulatory Compliance**: Regulations, certifications, privacy/security measures

## Installation

### Basic Installation
```bash
pip install -e .
```

### With PDF Support
```bash
pip install -e ".[pdf]"
# or explicitly
pip install reportlab
```

## Quick Start

```python
from export.evidence_bundle_exporter import (
    EvidenceBundleExporter,
    EvidenceBundle,
    EvidenceBundleMetadata,
    ModelCard,
    PerformanceMetrics,
)
from datetime import datetime

# Create metadata
metadata = EvidenceBundleMetadata(
    bundle_id="BUNDLE_2024_001",
    model_name="Risk Predictor",
    model_version="1.0.0",
    created_by="Data Science Team",
    organization="Your Organization",
)

# Create model card
model_card = ModelCard(
    model_name="Risk Predictor",
    model_version="1.0.0",
    description="A predictive model for risk assessment",
    model_type="classifier",
)

# Create performance metrics
metrics = PerformanceMetrics(
    metrics={
        "accuracy": 0.92,
        "precision": 0.89,
        "recall": 0.94,
    },
    evaluation_dataset="Test set with 10,000 samples",
)

# Create bundle
bundle = EvidenceBundle(
    metadata=metadata,
    model_card=model_card,
    performance_metrics=metrics,
)

# Export to formats
exporter = EvidenceBundleExporter()

# Single format exports
json_path = exporter.export_to_json(bundle, "/output/bundle.json")
md_path = exporter.export_to_markdown(bundle, "/output/bundle.md")
pdf_path = exporter.export_to_pdf(bundle, "/output/bundle.pdf")
zip_path = exporter.export_to_archive(bundle, "/output/bundle.zip")

# All formats at once
results = exporter.export_all_formats(bundle, "/output/directory")
```

## Module Components

### Core Classes

#### EvidenceBundleMetadata
```python
metadata = EvidenceBundleMetadata(
    bundle_id: str,
    model_name: str,
    model_version: str,
    created_at: Optional[datetime] = None,
    created_by: Optional[str] = None,
    organization: Optional[str] = None,
    description: Optional[str] = None,
)
```

#### ModelCard
```python
model_card = ModelCard(
    model_name: str,
    model_version: str,
    description: str,
    intended_use: Optional[str] = None,
    training_data: Optional[str] = None,
    model_type: Optional[str] = None,
    architecture: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    limitations: Optional[List[str]] = None,
    ethical_considerations: Optional[str] = None,
)
```

#### PerformanceMetrics
```python
metrics = PerformanceMetrics(
    metrics: Dict[str, float],
    evaluation_dataset: Optional[str] = None,
    evaluation_date: Optional[datetime] = None,
    confidence_intervals: Optional[Dict[str, tuple]] = None,
    confidence_level: float = 0.95,
)
```

#### FairnessAnalysis
```python
fairness = FairnessAnalysis(
    fairness_metrics: Dict[str, float],
    protected_attributes: Optional[List[str]] = None,
    disparate_impact_ratio: Optional[Dict[str, float]] = None,
    bias_assessment: Optional[str] = None,
    mitigation_strategies: Optional[List[str]] = None,
)
```

#### ValidationResults
```python
validation = ValidationResults(
    test_suites: Dict[str, Dict[str, Any]],
    overall_status: str = "passed",
    test_coverage: Optional[float] = None,
    failure_cases: Optional[List[Dict[str, Any]]] = None,
    validation_date: Optional[datetime] = None,
)
```

#### AuditTrail
```python
audit = AuditTrail()
audit.add_event(
    action: str,
    actor: str,
    details: Optional[Dict[str, Any]] = None,
    timestamp: Optional[datetime] = None,
)
```

#### RegulatoryCompliance
```python
compliance = RegulatoryCompliance(
    applicable_regulations: Optional[List[str]] = None,
    compliance_status: Optional[Dict[str, str]] = None,
    certifications: Optional[List[str]] = None,
    data_governance: Optional[Dict[str, Any]] = None,
    privacy_measures: Optional[List[str]] = None,
    security_measures: Optional[List[str]] = None,
)
```

#### EvidenceBundle
```python
bundle = EvidenceBundle(
    metadata: EvidenceBundleMetadata,
    model_card: ModelCard,
    performance_metrics: PerformanceMetrics,
    fairness_analysis: Optional[FairnessAnalysis] = None,
    validation_results: Optional[ValidationResults] = None,
    audit_trail: Optional[AuditTrail] = None,
    regulatory_compliance: Optional[RegulatoryCompliance] = None,
)
```

### Exporter Class

#### EvidenceBundleExporter
Main interface for exporting bundles.

```python
exporter = EvidenceBundleExporter()

# Export to individual formats
json_path = exporter.export_to_json(bundle, output_path)
md_path = exporter.export_to_markdown(bundle, output_path)
pdf_path = exporter.export_to_pdf(bundle, output_path, page_size="letter")
zip_path = exporter.export_to_archive(bundle, output_path)

# Export all formats
results = exporter.export_all_formats(bundle, output_directory)
```

## Export Format Details

### JSON Export
- Structured representation of all bundle data
- Machine-readable format
- Suitable for automated processing and APIs
- Includes all optional sections

### Markdown Export
- Human-readable formatted document
- Organized by sections with clear headings
- Tables for metrics and compliance info
- Suitable for documentation and review

### PDF Export
- Professional formatted report
- Multi-page layout with section breaks
- Tables with styled headers
- Color-coded sections for visual organization
- Requires `reportlab` library

### ZIP Archive Export
- Contains JSON, Markdown, and (optionally) PDF
- README.txt with archive contents description
- Convenient for distribution and archival
- All formats in single compressed file

## Error Handling

```python
from export.exceptions import ExportError

try:
    exporter.export_to_json(bundle, output_path)
except ExportError as e:
    print(f"Export failed: {e}")
```

## Common Use Cases

### 1. Model Governance Documentation
```python
# Create comprehensive evidence for model review board
bundle = create_full_evidence_bundle()
exporter.export_all_formats(bundle, "/governance/models/v1.0.0/")
```

### 2. Regulatory Compliance
```python
# Generate audit-ready documentation
compliance = RegulatoryCompliance(
    applicable_regulations=["HIPAA", "GDPR", "FDA"],
    compliance_status={"HIPAA": "Compliant", ...},
)
bundle = EvidenceBundle(..., regulatory_compliance=compliance)
exporter.export_to_pdf(bundle, "/compliance/report.pdf")
```

### 3. Model Versioning
```python
# Archive evidence for each model version
bundle = create_versioned_bundle()
results = exporter.export_all_formats(bundle, f"/models/v{version}/")
```

### 4. Fairness Audit
```python
# Create fairness documentation for stakeholders
fairness = FairnessAnalysis(...)
bundle = EvidenceBundle(..., fairness_analysis=fairness)
exporter.export_to_markdown(bundle, "/audits/fairness_report.md")
```

## Performance Considerations

- **Memory**: Bundle size depends on amount of data. Large audit trails can increase size.
- **PDF Generation**: Reportlab is fast; typical PDF generation < 1 second.
- **ZIP Archives**: Compression is good; typical bundle < 1 MB.
- **Formatting**: Markdown generation is fastest; JSON generation is optimized with streaming.

## Dependencies

### Required
- Python 3.8+
- Standard library: json, zipfile, pathlib, logging, datetime

### Optional
- `reportlab`: For PDF export (version 3.6+)
- `weasyprint`: For alternative HTML-to-PDF (not currently used but available for future use)

## Type Safety

The module uses Python type hints throughout for better IDE support and type checking:

```python
# Full typing support
bundle: EvidenceBundle = create_bundle()
exporter: EvidenceBundleExporter = EvidenceBundleExporter()
results: Dict[ExportFormat, str] = exporter.export_all_formats(bundle, output_dir)
```

## Logging

The module logs all operations:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("export.evidence_bundle_exporter")

# Export operations are logged
exporter.export_to_json(bundle, output_path)  # Logs: "Exported bundle to JSON: ..."
```

## Testing

See `example_evidence_bundle.py` for a complete working example with all component types.

## Contributing

When adding new functionality:
1. Maintain type hints throughout
2. Add comprehensive docstrings
3. Update this README
4. Include error handling with ExportError
5. Add logging for all operations

## License

See parent repository license.
