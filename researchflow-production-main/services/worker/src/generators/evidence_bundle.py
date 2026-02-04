"""
Evidence Bundle Generator
Creates transparency artifacts for TRIPOD+AI, HTI-1, and FAVES compliance.

Phase 8 Implementation - ResearchFlow Transparency Execution Plan
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import os

# Optional imports for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
    from reportlab.lib.styles import getSampleStyleSheet
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class MetricType(str, Enum):
    """Performance metric types."""
    AUC = "AUC"
    SENSITIVITY = "SENSITIVITY"
    SPECIFICITY = "SPECIFICITY"
    PPV = "PPV"
    NPV = "NPV"
    CALIBRATION = "CALIBRATION"
    BRIER_SCORE = "BRIER_SCORE"
    F1 = "F1"
    ACCURACY = "ACCURACY"


class StratumType(str, Enum):
    """Demographic stratification types."""
    SEX = "SEX"
    RACE = "RACE"
    AGE_GROUP = "AGE_GROUP"
    SITE = "SITE"
    COMORBIDITY = "COMORBIDITY"
    CUSTOM = "CUSTOM"


class LimitationSeverity(str, Enum):
    """Limitation severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PerformanceMetric:
    """Single performance metric."""
    metric_type: MetricType
    overall_value: float
    confidence_interval: Optional[Dict[str, float]] = None
    validation_cohort: str = "internal"
    sample_size: int = 0


@dataclass
class StratifiedMetric:
    """Stratified metric by demographic group."""
    stratum_type: StratumType
    stratum_value: str
    metrics: List[PerformanceMetric]


@dataclass
class InputFeature:
    """Model input feature specification."""
    name: str
    data_type: str
    source: str
    timeframe: Optional[str] = None
    required: bool = True
    description: str = ""


@dataclass
class Limitation:
    """Known limitation of the model."""
    category: str
    description: str
    severity: LimitationSeverity
    mitigation: Optional[str] = None


@dataclass
class SafetyControl:
    """Safety control mechanism."""
    control_type: str
    description: str
    trigger_condition: Optional[str] = None
    response_action: str = ""
    responsible_role: str = ""


@dataclass
class ModelMetadata:
    """Model identification and versioning."""
    model_id: str
    name: str
    version: str
    semantic_version: str
    framework: str
    git_commit_sha: Optional[str] = None
    container_digest: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EvidenceBundleGenerator:
    """
    Generates transparency evidence bundles for AI models.

    Supports multiple output formats: JSON, Markdown, PDF.
    Implements TRIPOD+AI, HTI-1, and FAVES compliance requirements.
    """

    SCHEMA_VERSION = "1.0.0"

    def __init__(
        self,
        model_metadata: ModelMetadata,
        output_dir: str = "/data/artifacts/evidence_bundles"
    ):
        """
        Initialize bundle generator.

        Args:
            model_metadata: Model identification information
            output_dir: Base directory for output files
        """
        self.model_metadata = model_metadata
        self.output_dir = output_dir
        self.bundle_data: Dict[str, Any] = {}

        # Initialize bundle structure
        self._init_bundle()

    def _init_bundle(self):
        """Initialize empty bundle structure."""
        self.bundle_data = {
            "bundle_id": self._generate_bundle_id(),
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generated_by": os.getenv("BUNDLE_GENERATOR_ID", "system"),
            "model_metadata": asdict(self.model_metadata),
            "intended_use": "",
            "contraindications": [],
            "input_spec": {
                "features": [],
                "preprocessing_steps": [],
                "missing_data_handling": ""
            },
            "output_spec": {
                "prediction_type": "",
                "output_range": None,
                "thresholds": [],
                "confidence_intervals": False,
                "calibration_method": None
            },
            "training_summary": {},
            "validation_summary": [],
            "performance_metrics": [],
            "stratified_metrics": [],
            "limitations": [],
            "safety_controls": [],
            "update_policy": {},
            "sbom_reference": None
        }

    def _generate_bundle_id(self) -> str:
        """Generate unique bundle identifier."""
        import uuid
        return str(uuid.uuid4())

    def set_intended_use(self, description: str, contraindications: List[str] = None):
        """
        Set intended use and contraindications.

        Args:
            description: Plain-language description (min 100 chars for HTI-1)
            contraindications: List of scenarios where model should NOT be used
        """
        if len(description) < 100:
            print(f"Warning: HTI-1 requires intended_use >= 100 chars, got {len(description)}")

        self.bundle_data["intended_use"] = description
        self.bundle_data["contraindications"] = contraindications or []

    def set_input_spec(
        self,
        features: List[InputFeature],
        preprocessing_steps: List[str],
        missing_data_handling: str
    ):
        """
        Set input specification.

        Args:
            features: List of input features
            preprocessing_steps: Data preprocessing pipeline
            missing_data_handling: How missing values are handled
        """
        self.bundle_data["input_spec"] = {
            "features": [asdict(f) for f in features],
            "preprocessing_steps": preprocessing_steps,
            "missing_data_handling": missing_data_handling
        }

    def set_output_spec(
        self,
        prediction_type: str,
        output_range: Optional[Dict[str, float]] = None,
        thresholds: List[Dict] = None,
        confidence_intervals: bool = False,
        calibration_method: Optional[str] = None
    ):
        """
        Set output specification.

        Args:
            prediction_type: BINARY, MULTICLASS, REGRESSION, PROBABILITY, RISK_SCORE
            output_range: Min/max values
            thresholds: Decision thresholds with labels
            confidence_intervals: Whether CIs are provided
            calibration_method: Calibration technique used
        """
        self.bundle_data["output_spec"] = {
            "prediction_type": prediction_type,
            "output_range": output_range,
            "thresholds": thresholds or [],
            "confidence_intervals": confidence_intervals,
            "calibration_method": calibration_method
        }

    def set_training_summary(
        self,
        data_source: str,
        timeframe_start: str,
        timeframe_end: str,
        sample_size: int,
        inclusion_criteria: List[str],
        exclusion_criteria: List[str],
        demographic_breakdown: Dict[str, int],
        label_source: str,
        label_timeframe: Optional[str] = None
    ):
        """Set training data summary."""
        self.bundle_data["training_summary"] = {
            "data_source": data_source,
            "timeframe": {
                "start": timeframe_start,
                "end": timeframe_end
            },
            "sample_size": sample_size,
            "inclusion_criteria": inclusion_criteria,
            "exclusion_criteria": exclusion_criteria,
            "demographic_breakdown": demographic_breakdown,
            "label_source": label_source,
            "label_timeframe": label_timeframe
        }

    def add_validation(
        self,
        validation_type: str,
        sites: List[str],
        timeframe_start: str,
        timeframe_end: str,
        sample_size: int,
        demographic_breakdown: Optional[Dict[str, int]] = None
    ):
        """Add validation cohort information."""
        self.bundle_data["validation_summary"].append({
            "validation_type": validation_type,
            "sites": sites,
            "timeframe": {
                "start": timeframe_start,
                "end": timeframe_end
            },
            "sample_size": sample_size,
            "demographic_breakdown": demographic_breakdown
        })

    def add_performance_metric(self, metric: PerformanceMetric):
        """Add overall performance metric."""
        self.bundle_data["performance_metrics"].append(asdict(metric))

    def add_stratified_metric(self, stratified: StratifiedMetric):
        """Add stratified performance metric."""
        data = {
            "stratum_type": stratified.stratum_type.value,
            "stratum_value": stratified.stratum_value,
            "metrics": [asdict(m) for m in stratified.metrics]
        }
        self.bundle_data["stratified_metrics"].append(data)

    def add_limitation(self, limitation: Limitation):
        """Add known limitation."""
        self.bundle_data["limitations"].append(asdict(limitation))

    def add_safety_control(self, control: SafetyControl):
        """Add safety control mechanism."""
        self.bundle_data["safety_controls"].append(asdict(control))

    def set_update_policy(
        self,
        retraining_frequency: str,
        drift_monitoring_enabled: bool,
        drift_thresholds: Optional[Dict[str, float]] = None,
        version_control: str = "semantic",
        rollback_procedure: str = ""
    ):
        """Set model update and maintenance policy."""
        self.bundle_data["update_policy"] = {
            "retraining_frequency": retraining_frequency,
            "drift_monitoring_enabled": drift_monitoring_enabled,
            "drift_thresholds": drift_thresholds,
            "version_control": version_control,
            "rollback_procedure": rollback_procedure
        }

    def set_sbom_reference(self, sbom_path: str):
        """Set reference to Software Bill of Materials."""
        self.bundle_data["sbom_reference"] = sbom_path

    def validate(self) -> List[str]:
        """
        Validate bundle completeness.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # HTI-1 Required fields
        if len(self.bundle_data.get("intended_use", "")) < 100:
            errors.append("intended_use must be at least 100 characters")

        if not self.bundle_data.get("input_spec", {}).get("features"):
            errors.append("input_spec.features is required")

        if not self.bundle_data.get("output_spec", {}).get("prediction_type"):
            errors.append("output_spec.prediction_type is required")

        if not self.bundle_data.get("training_summary"):
            errors.append("training_summary is required")

        if not self.bundle_data.get("validation_summary"):
            errors.append("At least one validation cohort is required")

        if not self.bundle_data.get("performance_metrics"):
            errors.append("At least one performance metric is required")

        if not self.bundle_data.get("limitations"):
            errors.append("At least one known limitation must be documented")

        if not self.bundle_data.get("safety_controls"):
            errors.append("At least one safety control is required")

        if not self.bundle_data.get("update_policy"):
            errors.append("update_policy is required")

        return errors

    def generate_json(self) -> str:
        """
        Generate JSON representation.

        Returns:
            JSON string of the evidence bundle
        """
        return json.dumps(self.bundle_data, indent=2, default=str)

    def generate_markdown(self) -> str:
        """
        Generate Markdown representation.

        Returns:
            Markdown string of the evidence bundle
        """
        md = []
        md.append(f"# Evidence Bundle: {self.model_metadata.name} v{self.model_metadata.version}")
        md.append(f"\n**Generated:** {self.bundle_data['generated_at']}")
        md.append(f"**Schema Version:** {self.SCHEMA_VERSION}")
        md.append(f"**Bundle ID:** {self.bundle_data['bundle_id']}")

        md.append("\n---\n")

        # Intended Use
        md.append("## Intended Use")
        md.append(self.bundle_data.get("intended_use", "Not specified"))

        if self.bundle_data.get("contraindications"):
            md.append("\n### Contraindications")
            for c in self.bundle_data["contraindications"]:
                md.append(f"- {c}")

        # Input Specification
        md.append("\n## Input Specification")
        input_spec = self.bundle_data.get("input_spec", {})
        if input_spec.get("features"):
            md.append("\n### Features")
            md.append("| Name | Type | Source | Required |")
            md.append("|------|------|--------|----------|")
            for f in input_spec["features"]:
                md.append(f"| {f['name']} | {f['data_type']} | {f['source']} | {f['required']} |")

        # Output Specification
        md.append("\n## Output Specification")
        output_spec = self.bundle_data.get("output_spec", {})
        md.append(f"- **Prediction Type:** {output_spec.get('prediction_type', 'N/A')}")
        if output_spec.get("output_range"):
            md.append(f"- **Range:** {output_spec['output_range']['min']} - {output_spec['output_range']['max']}")

        # Training Summary
        md.append("\n## Training Summary")
        training = self.bundle_data.get("training_summary", {})
        if training:
            md.append(f"- **Data Source:** {training.get('data_source', 'N/A')}")
            md.append(f"- **Sample Size:** {training.get('sample_size', 'N/A'):,}")
            if training.get("timeframe"):
                md.append(f"- **Timeframe:** {training['timeframe']['start']} to {training['timeframe']['end']}")

        # Performance Metrics
        md.append("\n## Performance Metrics")
        if self.bundle_data.get("performance_metrics"):
            md.append("| Metric | Value | 95% CI | Cohort | N |")
            md.append("|--------|-------|--------|--------|---|")
            for m in self.bundle_data["performance_metrics"]:
                ci = m.get("confidence_interval")
                ci_str = f"[{ci['lower']:.3f}, {ci['upper']:.3f}]" if ci else "N/A"
                md.append(f"| {m['metric_type']} | {m['overall_value']:.3f} | {ci_str} | {m['validation_cohort']} | {m['sample_size']:,} |")

        # Stratified Metrics
        if self.bundle_data.get("stratified_metrics"):
            md.append("\n## Stratified Performance")
            for strat in self.bundle_data["stratified_metrics"]:
                md.append(f"\n### By {strat['stratum_type']}: {strat['stratum_value']}")
                for m in strat["metrics"]:
                    md.append(f"- {m['metric_type']}: {m['overall_value']:.3f}")

        # Limitations
        md.append("\n## Known Limitations")
        for lim in self.bundle_data.get("limitations", []):
            md.append(f"\n### {lim['category']} ({lim['severity']})")
            md.append(lim['description'])
            if lim.get('mitigation'):
                md.append(f"\n**Mitigation:** {lim['mitigation']}")

        # Safety Controls
        md.append("\n## Safety Controls")
        for ctrl in self.bundle_data.get("safety_controls", []):
            md.append(f"\n### {ctrl['control_type']}")
            md.append(ctrl['description'])
            if ctrl.get('response_action'):
                md.append(f"\n**Response:** {ctrl['response_action']}")

        # Update Policy
        md.append("\n## Update Policy")
        policy = self.bundle_data.get("update_policy", {})
        if policy:
            md.append(f"- **Retraining Frequency:** {policy.get('retraining_frequency', 'N/A')}")
            md.append(f"- **Drift Monitoring:** {'Enabled' if policy.get('drift_monitoring_enabled') else 'Disabled'}")
            if policy.get('rollback_procedure'):
                md.append(f"- **Rollback:** {policy['rollback_procedure']}")

        return "\n".join(md)

    def generate_pdf(self, output_path: str) -> bool:
        """
        Generate PDF representation.

        Args:
            output_path: Path for output PDF file

        Returns:
            True if successful, False if reportlab not available
        """
        if not REPORTLAB_AVAILABLE:
            print("Warning: reportlab not installed, cannot generate PDF")
            return False

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        story.append(Paragraph(
            f"Evidence Bundle: {self.model_metadata.name} v{self.model_metadata.version}",
            styles['Title']
        ))
        story.append(Spacer(1, 12))

        # Metadata
        story.append(Paragraph(f"Generated: {self.bundle_data['generated_at']}", styles['Normal']))
        story.append(Paragraph(f"Bundle ID: {self.bundle_data['bundle_id']}", styles['Normal']))
        story.append(Spacer(1, 12))

        # Intended Use
        story.append(Paragraph("Intended Use", styles['Heading2']))
        story.append(Paragraph(self.bundle_data.get("intended_use", ""), styles['Normal']))
        story.append(Spacer(1, 12))

        # Build PDF
        doc.build(story)
        return True

    def save(self, formats: List[str] = None) -> Dict[str, str]:
        """
        Save bundle to disk in specified formats.

        Args:
            formats: List of formats ['json', 'markdown', 'pdf']

        Returns:
            Dict mapping format to output path
        """
        if formats is None:
            formats = ['json', 'markdown']

        # Create output directory
        model_dir = os.path.join(
            self.output_dir,
            self.model_metadata.model_id,
            self.model_metadata.version
        )
        os.makedirs(model_dir, exist_ok=True)

        outputs = {}

        if 'json' in formats:
            json_path = os.path.join(model_dir, "evidence_bundle.json")
            with open(json_path, 'w') as f:
                f.write(self.generate_json())
            outputs['json'] = json_path

        if 'markdown' in formats:
            md_path = os.path.join(model_dir, "evidence_bundle.md")
            with open(md_path, 'w') as f:
                f.write(self.generate_markdown())
            outputs['markdown'] = md_path

        if 'pdf' in formats:
            pdf_path = os.path.join(model_dir, "evidence_bundle.pdf")
            if self.generate_pdf(pdf_path):
                outputs['pdf'] = pdf_path

        return outputs


# Factory function for easy instantiation
def create_bundle_generator(
    model_id: str,
    model_name: str,
    version: str,
    framework: str = "CUSTOM"
) -> EvidenceBundleGenerator:
    """
    Create a new evidence bundle generator.

    Args:
        model_id: UUID of the model
        model_name: Human-readable model name
        version: Model version string
        framework: ML framework used

    Returns:
        Configured EvidenceBundleGenerator instance
    """
    metadata = ModelMetadata(
        model_id=model_id,
        name=model_name,
        version=version,
        semantic_version=version if '.' in version else f"{version}.0.0",
        framework=framework,
        created_at=datetime.utcnow().isoformat() + "Z",
        updated_at=datetime.utcnow().isoformat() + "Z"
    )
    return EvidenceBundleGenerator(metadata)
