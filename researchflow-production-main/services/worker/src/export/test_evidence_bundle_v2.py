"""
Test Suite for Evidence Bundle V2

Tests for Track B (ROS-109, ROS-110, ROS-111) enhancements:
- FAVES compliance score management
- Drift detection analysis
- Audit trail operations
- Source provenance tracking
- Multi-format export (JSON, HTML, PDF)
- Regulatory compliance tracking

Priority: P0 - CRITICAL
Module: services/worker/src/export/test_evidence_bundle_v2
Version: 1.0.0

@author Claude
@created 2026-01-30
"""

import unittest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from evidence_bundle_v2 import (
    EvidenceBundleV2,
    FAVESComplianceScore,
    DriftMetrics,
    AuditTrailEntry,
    AuditTrailManager,
    DriftDetectionEngine,
    SourceProvenance,
    RegulatoryComplianceDetails,
    ComplianceFramework,
    DriftType,
    ExportFormat,
)


class TestFAVESComplianceScore(unittest.TestCase):
    """Test FAVES compliance score calculation."""

    def test_faves_score_creation(self):
        """Test creating FAVES score object."""
        score = FAVESComplianceScore(
            fair=85,
            appropriate=82,
            valid=88,
            effective=80,
            safe=86,
        )

        self.assertEqual(score.fair, 85)
        self.assertEqual(score.appropriate, 82)
        self.assertEqual(score.valid, 88)
        self.assertEqual(score.effective, 80)
        self.assertEqual(score.safe, 86)
        self.assertAlmostEqual(score.overall_score, 84.2, places=1)

    def test_faves_score_to_dict(self):
        """Test converting FAVES score to dictionary."""
        score = FAVESComplianceScore(
            fair=90, appropriate=85, valid=95, effective=88, safe=92
        )

        score_dict = score.to_dict()

        self.assertIn("fair", score_dict)
        self.assertIn("overall_score", score_dict)
        self.assertEqual(score_dict["fair"], 90)

    def test_faves_score_validation(self):
        """Test FAVES score validation."""
        with self.assertRaises(ValueError):
            FAVESComplianceScore(fair=150, appropriate=85, valid=95, effective=88, safe=92)

        with self.assertRaises(ValueError):
            FAVESComplianceScore(fair=-10, appropriate=85, valid=95, effective=88, safe=92)


class TestAuditTrailManager(unittest.TestCase):
    """Test audit trail management."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = AuditTrailManager()

    def test_add_entry(self):
        """Test adding audit trail entry."""
        entry = AuditTrailEntry(
            timestamp=datetime.utcnow(),
            action="CREATE",
            user_id="test_user",
            system_id="evidence_bundle_v2",
            resource_type="BUNDLE",
            resource_id="bundle_123",
        )

        self.manager.add_entry(entry)
        self.assertEqual(len(self.manager.entries), 1)

    def test_create_entry(self):
        """Test creating and adding entry in one call."""
        self.manager.create_entry(
            action="UPDATE",
            resource_type="FAVES_SCORES",
            resource_id="bundle_123",
            user_id="test_user",
        )

        self.assertEqual(len(self.manager.entries), 1)
        self.assertEqual(self.manager.entries[0].action, "UPDATE")

    def test_entry_hash_computation(self):
        """Test that entry hash is computed correctly."""
        entry = AuditTrailEntry(
            timestamp=datetime.utcnow(),
            action="CREATE",
            user_id="test_user",
            system_id="evidence_bundle_v2",
            resource_type="BUNDLE",
            resource_id="bundle_123",
        )

        self.assertIsNotNone(entry.entry_hash)
        self.assertEqual(len(entry.entry_hash), 64)  # SHA256 hex length

    def test_filter_entries(self):
        """Test filtering audit trail entries."""
        now = datetime.utcnow()

        self.manager.create_entry(
            action="CREATE",
            resource_type="BUNDLE",
            resource_id="bundle_1",
            user_id="user1",
        )

        self.manager.create_entry(
            action="UPDATE",
            resource_type="FAVES_SCORES",
            resource_id="bundle_1",
            user_id="user2",
        )

        # Filter by resource type
        bundle_entries = self.manager.get_entries(resource_type="BUNDLE")
        self.assertEqual(len(bundle_entries), 1)

        # Filter by resource ID
        id_entries = self.manager.get_entries(resource_id="bundle_1")
        self.assertEqual(len(id_entries), 2)

    def test_to_dict(self):
        """Test converting audit trail to dictionary."""
        self.manager.create_entry(
            action="CREATE",
            resource_type="BUNDLE",
            resource_id="bundle_123",
        )

        entries_dict = self.manager.to_dict()

        self.assertIsInstance(entries_dict, list)
        self.assertEqual(len(entries_dict), 1)
        self.assertIn("action", entries_dict[0])
        self.assertIn("timestamp", entries_dict[0])


class TestDriftDetectionEngine(unittest.TestCase):
    """Test drift detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = DriftDetectionEngine()

    def test_covariate_shift_detection_no_drift(self):
        """Test covariate shift detection when no shift exists."""
        baseline = {
            "feature_1": [1.0, 1.1, 0.9, 1.0],
            "feature_2": [5.0, 5.1, 4.9, 5.0],
        }

        current = {
            "feature_1": [1.0, 1.05, 0.95, 1.0],
            "feature_2": [5.0, 5.05, 4.95, 5.0],
        }

        metrics = self.engine.detect_covariate_shift(baseline, current, threshold=0.1)

        self.assertFalse(metrics.detected)
        self.assertEqual(metrics.drift_type, DriftType.COVARIATE_SHIFT)

    def test_covariate_shift_detection_with_drift(self):
        """Test covariate shift detection when shift exists."""
        baseline = {
            "feature_1": [1.0, 1.0, 1.0, 1.0],
            "feature_2": [5.0, 5.0, 5.0, 5.0],
        }

        current = {
            "feature_1": [3.0, 3.0, 3.0, 3.0],
            "feature_2": [10.0, 10.0, 10.0, 10.0],
        }

        metrics = self.engine.detect_covariate_shift(baseline, current, threshold=0.05)

        self.assertTrue(metrics.detected)
        self.assertGreater(metrics.confidence, 0)

    def test_concept_drift_detection_no_drift(self):
        """Test concept drift detection when performance is stable."""
        baseline = {
            "accuracy": 0.95,
            "precision": 0.92,
            "recall": 0.88,
        }

        current = {
            "accuracy": 0.94,
            "precision": 0.91,
            "recall": 0.87,
        }

        metrics = self.engine.detect_concept_drift(baseline, current, threshold=0.1)

        self.assertFalse(metrics.detected)

    def test_concept_drift_detection_with_drift(self):
        """Test concept drift detection when performance degrades."""
        baseline = {
            "accuracy": 0.95,
            "precision": 0.92,
            "recall": 0.88,
        }

        current = {
            "accuracy": 0.80,
            "precision": 0.75,
            "recall": 0.70,
        }

        metrics = self.engine.detect_concept_drift(baseline, current, threshold=0.1)

        self.assertTrue(metrics.detected)
        self.assertGreater(metrics.confidence, 0)

    def test_get_all_metrics(self):
        """Test retrieving all drift metrics."""
        self.engine.detect_covariate_shift(
            {"f1": [1.0]}, {"f1": [1.0]}, threshold=0.1
        )
        self.engine.detect_concept_drift(
            {"acc": 0.9}, {"acc": 0.9}, threshold=0.1
        )

        all_metrics = self.engine.get_all_metrics()

        self.assertEqual(len(all_metrics), 2)


class TestSourceProvenance(unittest.TestCase):
    """Test data source provenance tracking."""

    def test_source_provenance_creation(self):
        """Test creating source provenance object."""
        now = datetime.utcnow()
        provenance = SourceProvenance(
            source_id="source_1",
            source_name="EHR System",
            source_type="ELECTRONIC_HEALTH_RECORD",
            collection_date=now,
            collection_method="DIRECT_EXPORT",
            data_custodian="Medical Records Team",
        )

        self.assertEqual(provenance.source_id, "source_1")
        self.assertEqual(provenance.source_name, "EHR System")
        self.assertEqual(provenance.record_count, 0)

    def test_compute_data_hash(self):
        """Test data integrity hash computation."""
        provenance = SourceProvenance(
            source_id="source_1",
            source_name="Test Source",
            source_type="TEST",
            collection_date=datetime.utcnow(),
            collection_method="TEST_METHOD",
            data_custodian="Test",
        )

        data = {"key": "value", "count": 100}
        hash_value = provenance.compute_hash(data)

        self.assertIsNotNone(hash_value)
        self.assertEqual(len(hash_value), 64)  # SHA256

    def test_source_provenance_to_dict(self):
        """Test converting provenance to dictionary."""
        now = datetime.utcnow()
        provenance = SourceProvenance(
            source_id="source_1",
            source_name="Test Source",
            source_type="TEST",
            collection_date=now,
            collection_method="TEST_METHOD",
            data_custodian="Test",
            record_count=1000,
        )

        prov_dict = provenance.to_dict()

        self.assertEqual(prov_dict["source_id"], "source_1")
        self.assertEqual(prov_dict["record_count"], 1000)


class TestEvidenceBundleV2(unittest.TestCase):
    """Test Evidence Bundle V2 functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.bundle = EvidenceBundleV2(
            organization="Test Org",
            created_by="test_user",
        )

    def test_bundle_creation(self):
        """Test creating evidence bundle."""
        self.assertIsNotNone(self.bundle.bundle_id)
        self.assertEqual(self.bundle.organization, "Test Org")
        self.assertEqual(self.bundle.created_by, "test_user")
        self.assertIsNotNone(self.bundle.created_at)

    def test_set_faves_scores(self):
        """Test setting FAVES scores."""
        self.bundle.set_faves_scores(
            fair=85, appropriate=82, valid=88, effective=80, safe=86
        )

        self.assertIsNotNone(self.bundle.faves_scores)
        self.assertEqual(self.bundle.faves_scores.fair, 85)
        self.assertAlmostEqual(self.bundle.faves_scores.overall_score, 84.2, places=1)

    def test_faves_status_determination(self):
        """Test FAVES status determination."""
        self.bundle.set_faves_scores(
            fair=85, appropriate=82, valid=88, effective=80, safe=86
        )

        status = self.bundle._determine_faves_status()
        self.assertEqual(status, "APPROVED")

        self.bundle.set_faves_scores(
            fair=50, appropriate=55, valid=60, effective=65, safe=70
        )

        status = self.bundle._determine_faves_status()
        self.assertEqual(status, "CONDITIONAL")

    def test_add_regulatory_compliance(self):
        """Test adding regulatory compliance information."""
        self.bundle.add_regulatory_compliance(
            framework=ComplianceFramework.HTI_1,
            compliance_status="COMPLIANT",
        )

        self.assertIn(ComplianceFramework.HTI_1, self.bundle.regulatory_compliance)

    def test_add_data_source(self):
        """Test adding data source."""
        provenance = self.bundle.add_data_source(
            source_id="source_1",
            source_name="Test EHR",
            source_type="ELECTRONIC_HEALTH_RECORD",
            collection_date=datetime.utcnow(),
            collection_method="API",
            data_custodian="IT Team",
            record_count=5000,
        )

        self.assertEqual(len(self.bundle.source_provenance), 1)
        self.assertEqual(provenance.source_id, "source_1")

    def test_analyze_covariate_shift(self):
        """Test covariate shift analysis."""
        baseline = {"feature_1": [1.0, 1.0, 1.0]}
        current = {"feature_1": [1.0, 1.0, 1.0]}

        metrics = self.bundle.analyze_covariate_shift(baseline, current)

        self.assertIn("drift_type", metrics)
        self.assertIn("detected", metrics)

    def test_analyze_concept_drift(self):
        """Test concept drift analysis."""
        baseline = {"accuracy": 0.95}
        current = {"accuracy": 0.94}

        metrics = self.bundle.analyze_concept_drift(baseline, current)

        self.assertIn("drift_type", metrics)
        self.assertIn("detected", metrics)

    def test_export_to_json(self):
        """Test JSON export."""
        self.bundle.set_faves_scores(85, 82, 88, 80, 86)
        self.bundle.add_regulatory_compliance(
            ComplianceFramework.HTI_1, "COMPLIANT"
        )
        self.bundle.add_data_source(
            source_id="source_1",
            source_name="Test",
            source_type="TEST",
            collection_date=datetime.utcnow(),
            collection_method="TEST",
            data_custodian="TEST",
        )

        export_data = self.bundle.export_to_json()

        self.assertIn("bundle_id", export_data)
        self.assertIn("faves_compliance", export_data)
        self.assertIn("regulatory_compliance", export_data)
        self.assertIn("data_sources", export_data)
        self.assertIn("audit_trail", export_data)

    def test_export_to_json_file(self):
        """Test JSON file export."""
        self.bundle.set_faves_scores(85, 82, 88, 80, 86)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "bundle.json"
            result = self.bundle.export_to_json_file(filepath)

            self.assertTrue(result.exists())
            self.assertTrue(result.suffix == ".json")

            with open(result) as f:
                data = json.load(f)
                self.assertIn("bundle_id", data)

    def test_export_to_html(self):
        """Test HTML export."""
        self.bundle.set_faves_scores(85, 82, 88, 80, 86)
        self.bundle.add_regulatory_compliance(
            ComplianceFramework.HTI_1, "COMPLIANT"
        )

        html = self.bundle.export_to_html()

        self.assertIsInstance(html, str)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn(self.bundle.bundle_id, html)
        self.assertIn("FAVES Compliance", html)

    def test_export_to_html_file(self):
        """Test HTML file export."""
        self.bundle.set_faves_scores(85, 82, 88, 80, 86)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "bundle.html"
            result = self.bundle.export_to_html_file(filepath)

            self.assertTrue(result.exists())
            self.assertTrue(result.suffix == ".html")

    def test_audit_trail_creation(self):
        """Test audit trail entries are created."""
        self.bundle.set_faves_scores(85, 82, 88, 80, 86)
        self.bundle.add_data_source(
            source_id="source_1",
            source_name="Test",
            source_type="TEST",
            collection_date=datetime.utcnow(),
            collection_method="TEST",
            data_custodian="TEST",
        )

        audit_entries = self.bundle.audit_manager.to_dict()

        self.assertGreater(len(audit_entries), 0)

    def test_to_dict(self):
        """Test converting bundle to dictionary."""
        self.bundle.set_faves_scores(85, 82, 88, 80, 86)

        bundle_dict = self.bundle.to_dict()

        self.assertIn("bundle_id", bundle_dict)
        self.assertIn("faves_compliance", bundle_dict)


class TestBatchOperations(unittest.TestCase):
    """Test batch operations for multiple bundles."""

    def test_multiple_bundles_with_shared_audit_manager(self):
        """Test creating multiple bundles and sharing audit info."""
        bundle1 = EvidenceBundleV2(organization="Org1", created_by="user1")
        bundle2 = EvidenceBundleV2(organization="Org2", created_by="user2")

        bundle1.set_faves_scores(85, 82, 88, 80, 86)
        bundle2.set_faves_scores(75, 78, 80, 75, 80)

        self.assertNotEqual(bundle1.bundle_id, bundle2.bundle_id)
        self.assertEqual(len(bundle1.audit_manager.entries), 1)
        self.assertEqual(len(bundle2.audit_manager.entries), 1)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and edge cases."""

    def test_invalid_faves_score(self):
        """Test handling invalid FAVES scores."""
        bundle = EvidenceBundleV2()

        with self.assertRaises(ValueError):
            bundle.set_faves_scores(150, 85, 88, 80, 86)

    def test_empty_drift_analysis(self):
        """Test handling empty drift analysis."""
        engine = DriftDetectionEngine()
        metrics = engine.get_all_metrics()

        self.assertEqual(len(metrics), 0)

    def test_missing_export_directory(self):
        """Test that export creates missing directories."""
        bundle = EvidenceBundleV2()
        bundle.set_faves_scores(85, 82, 88, 80, 86)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "subdir" / "bundle.json"
            result = bundle.export_to_json_file(filepath)

            self.assertTrue(result.exists())


def run_tests():
    """Run all tests."""
    unittest.main(argv=[""], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
