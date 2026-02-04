"""
Unit tests for the Evidence Bundle Exporter module.

Tests cover all export formats and bundle components.
"""

import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
import pytest

from export.evidence_bundle_exporter import (
    EvidenceBundleExporter,
    EvidenceBundle,
    EvidenceBundleMetadata,
    ModelCard,
    PerformanceMetrics,
    FairnessAnalysis,
    ValidationResults,
    AuditTrail,
    RegulatoryCompliance,
    ExportFormat,
)
from export.exceptions import ExportError


@pytest.fixture
def sample_metadata():
    """Create sample metadata."""
    return EvidenceBundleMetadata(
        bundle_id="TEST_BUNDLE_001",
        model_name="Test Model",
        model_version="1.0.0",
        created_by="Test User",
        organization="Test Org",
        description="Test bundle for unit tests",
    )


@pytest.fixture
def sample_model_card():
    """Create sample model card."""
    return ModelCard(
        model_name="Test Model",
        model_version="1.0.0",
        description="A test model",
        model_type="classifier",
        parameters={"learning_rate": 0.01, "max_depth": 5},
        limitations=["Test limitation 1", "Test limitation 2"],
    )


@pytest.fixture
def sample_performance_metrics():
    """Create sample performance metrics."""
    return PerformanceMetrics(
        metrics={"accuracy": 0.95, "precision": 0.92, "recall": 0.97},
        evaluation_dataset="Test dataset",
        confidence_intervals={
            "accuracy": (0.94, 0.96),
        },
    )


@pytest.fixture
def sample_fairness_analysis():
    """Create sample fairness analysis."""
    return FairnessAnalysis(
        fairness_metrics={"demographic_parity_difference": 0.05},
        protected_attributes=["gender", "age"],
        disparate_impact_ratio={"gender": 0.95},
        bias_assessment="Model shows acceptable fairness metrics",
        mitigation_strategies=["Threshold adjustment"],
    )


@pytest.fixture
def sample_validation_results():
    """Create sample validation results."""
    return ValidationResults(
        test_suites={
            "unit_tests": {"passed": 50, "failed": 0},
            "integration_tests": {"passed": 20, "failed": 0},
        },
        overall_status="passed",
        test_coverage=92.0,
    )


@pytest.fixture
def sample_audit_trail():
    """Create sample audit trail."""
    audit = AuditTrail()
    audit.add_event("model_creation", "Test User", {"version": "1.0.0"})
    audit.add_event("model_trained", "ML Pipeline", {})
    audit.chain_of_custody = ["Artifact 1", "Artifact 2"]
    return audit


@pytest.fixture
def sample_compliance():
    """Create sample regulatory compliance."""
    return RegulatoryCompliance(
        applicable_regulations=["HIPAA", "GDPR"],
        compliance_status={"HIPAA": "Compliant", "GDPR": "Compliant"},
        certifications=["ISO 27001"],
        privacy_measures=["Encryption", "Access Control"],
        security_measures=["Audit Logging"],
    )


@pytest.fixture
def sample_bundle(
    sample_metadata,
    sample_model_card,
    sample_performance_metrics,
    sample_fairness_analysis,
    sample_validation_results,
    sample_audit_trail,
    sample_compliance,
):
    """Create a complete sample bundle."""
    return EvidenceBundle(
        metadata=sample_metadata,
        model_card=sample_model_card,
        performance_metrics=sample_performance_metrics,
        fairness_analysis=sample_fairness_analysis,
        validation_results=sample_validation_results,
        audit_trail=sample_audit_trail,
        regulatory_compliance=sample_compliance,
    )


class TestEvidenceBundleMetadata:
    """Test EvidenceBundleMetadata class."""

    def test_initialization(self):
        """Test metadata initialization."""
        metadata = EvidenceBundleMetadata(
            bundle_id="TEST_001",
            model_name="Test Model",
            model_version="1.0.0",
        )
        assert metadata.bundle_id == "TEST_001"
        assert metadata.model_name == "Test Model"
        assert metadata.model_version == "1.0.0"
        assert metadata.created_at is not None

    def test_to_dict(self, sample_metadata):
        """Test conversion to dictionary."""
        data = sample_metadata.to_dict()
        assert data["bundle_id"] == "TEST_BUNDLE_001"
        assert data["model_name"] == "Test Model"
        assert data["created_by"] == "Test User"


class TestModelCard:
    """Test ModelCard class."""

    def test_initialization(self, sample_model_card):
        """Test model card initialization."""
        assert sample_model_card.model_name == "Test Model"
        assert sample_model_card.model_type == "classifier"
        assert len(sample_model_card.limitations) == 2

    def test_to_dict(self, sample_model_card):
        """Test conversion to dictionary."""
        data = sample_model_card.to_dict()
        assert data["model_name"] == "Test Model"
        assert data["parameters"]["learning_rate"] == 0.01


class TestJSONExporter:
    """Test JSON export functionality."""

    def test_json_export(self, sample_bundle):
        """Test JSON export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.json"
            exporter = EvidenceBundleExporter()

            result = exporter.export_to_json(sample_bundle, str(output_path))

            assert Path(result).exists()
            with open(output_path, "r") as f:
                data = json.load(f)
            assert data["metadata"]["bundle_id"] == "TEST_BUNDLE_001"
            assert "model_card" in data
            assert "performance_metrics" in data

    def test_json_export_creates_parent_directories(self, sample_bundle):
        """Test that export creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dir" / "bundle.json"
            exporter = EvidenceBundleExporter()

            result = exporter.export_to_json(sample_bundle, str(output_path))

            assert Path(result).exists()
            assert Path(result).parent.exists()

    def test_json_export_contains_all_sections(self, sample_bundle):
        """Test that JSON export contains all bundle sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.json"
            exporter = EvidenceBundleExporter()

            exporter.export_to_json(sample_bundle, str(output_path))

            with open(output_path, "r") as f:
                data = json.load(f)

            assert "metadata" in data
            assert "model_card" in data
            assert "performance_metrics" in data
            assert "fairness_analysis" in data
            assert "validation_results" in data
            assert "audit_trail" in data
            assert "regulatory_compliance" in data


class TestMarkdownExporter:
    """Test Markdown export functionality."""

    def test_markdown_export(self, sample_bundle):
        """Test Markdown export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.md"
            exporter = EvidenceBundleExporter()

            result = exporter.export_to_markdown(sample_bundle, str(output_path))

            assert Path(result).exists()
            with open(output_path, "r") as f:
                content = f.read()
            assert "# Evidence Bundle Report" in content
            assert "## Metadata" in content
            assert "## Model Card" in content
            assert "## Performance Metrics" in content

    def test_markdown_export_formatting(self, sample_bundle):
        """Test Markdown formatting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.md"
            exporter = EvidenceBundleExporter()

            exporter.export_to_markdown(sample_bundle, str(output_path))

            with open(output_path, "r") as f:
                content = f.read()

            # Check for proper formatting
            assert "**Bundle ID**:" in content
            assert "**Model Name**:" in content
            assert "### Basic Information" in content
            assert "- **accuracy**: 0.9500" in content


class TestAuditTrail:
    """Test AuditTrail class."""

    def test_add_event(self):
        """Test adding events to audit trail."""
        audit = AuditTrail()
        audit.add_event("test_action", "test_actor", {"detail": "value"})

        assert len(audit.events) == 1
        assert audit.events[0]["action"] == "test_action"
        assert audit.events[0]["actor"] == "test_actor"
        assert audit.events[0]["details"]["detail"] == "value"

    def test_chain_of_custody(self, sample_audit_trail):
        """Test chain of custody."""
        assert len(sample_audit_trail.chain_of_custody) == 2
        data = sample_audit_trail.to_dict()
        assert "chain_of_custody" in data


class TestZipArchiveExporter:
    """Test ZIP archive export functionality."""

    def test_zip_export_basic(self, sample_bundle):
        """Test basic ZIP export."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.zip"
            exporter = EvidenceBundleExporter()

            result = exporter.export_to_archive(sample_bundle, str(output_path))

            assert Path(result).exists()

    def test_zip_archive_contents(self, sample_bundle):
        """Test ZIP archive contains expected files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.zip"
            exporter = EvidenceBundleExporter()

            exporter.export_to_archive(sample_bundle, str(output_path))

            with zipfile.ZipFile(output_path, "r") as zf:
                names = zf.namelist()
                # Should contain JSON and Markdown at minimum
                json_files = [n for n in names if n.endswith(".json")]
                md_files = [n for n in names if n.endswith(".md")]
                assert len(json_files) > 0
                assert len(md_files) > 0
                assert "README.txt" in names

    def test_zip_archive_readability(self, sample_bundle):
        """Test ZIP archive contents are readable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bundle.zip"
            exporter = EvidenceBundleExporter()

            exporter.export_to_archive(sample_bundle, str(output_path))

            with zipfile.ZipFile(output_path, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".json"):
                        content = zf.read(name).decode("utf-8")
                        data = json.loads(content)
                        assert "metadata" in data


class TestEvidenceBundleExporter:
    """Test main EvidenceBundleExporter class."""

    def test_initialization(self):
        """Test exporter initialization."""
        exporter = EvidenceBundleExporter()
        assert exporter is not None
        assert len(exporter._exporters) > 0

    def test_export_all_formats(self, sample_bundle):
        """Test exporting to all formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = EvidenceBundleExporter()
            results = exporter.export_all_formats(sample_bundle, tmpdir)

            assert ExportFormat.JSON in results
            assert ExportFormat.MARKDOWN in results
            assert ExportFormat.ZIP in results
            assert Path(results[ExportFormat.JSON]).exists()
            assert Path(results[ExportFormat.MARKDOWN]).exists()
            assert Path(results[ExportFormat.ZIP]).exists()

    def test_minimal_bundle_export(self):
        """Test exporting minimal bundle (metadata, model card, metrics only)."""
        minimal_bundle = EvidenceBundle(
            metadata=EvidenceBundleMetadata(
                bundle_id="MINIMAL",
                model_name="Minimal",
                model_version="1.0.0",
            ),
            model_card=ModelCard(
                model_name="Minimal",
                model_version="1.0.0",
                description="Minimal model",
            ),
            performance_metrics=PerformanceMetrics(
                metrics={"accuracy": 0.95},
            ),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "minimal.json"
            exporter = EvidenceBundleExporter()
            result = exporter.export_to_json(minimal_bundle, str(output_path))

            assert Path(result).exists()
            with open(output_path, "r") as f:
                data = json.load(f)
            assert "fairness_analysis" not in data  # Optional sections not included


class TestBundleConversions:
    """Test bundle data conversions."""

    def test_full_bundle_to_dict(self, sample_bundle):
        """Test converting full bundle to dictionary."""
        data = sample_bundle.to_dict()

        assert "metadata" in data
        assert "model_card" in data
        assert "performance_metrics" in data
        assert "fairness_analysis" in data
        assert "validation_results" in data
        assert "audit_trail" in data
        assert "regulatory_compliance" in data

    def test_partial_bundle_to_dict(self):
        """Test converting partial bundle to dictionary."""
        bundle = EvidenceBundle(
            metadata=EvidenceBundleMetadata(
                bundle_id="PARTIAL",
                model_name="Partial",
                model_version="1.0.0",
            ),
            model_card=ModelCard(
                model_name="Partial",
                model_version="1.0.0",
                description="Partial model",
            ),
            performance_metrics=PerformanceMetrics(
                metrics={"accuracy": 0.95},
            ),
        )
        data = bundle.to_dict()

        assert "metadata" in data
        assert "fairness_analysis" not in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
