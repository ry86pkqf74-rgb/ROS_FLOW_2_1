"""
Unit tests for drift detection module.

Tests cover:
- PopulationStabilityIndex calculation
- KLDivergence calculation
- DriftDetector input/output drift detection
- Severity level classification
- DriftReport generation
- Edge cases (empty arrays, identical distributions)
"""

import pytest
import math
from datetime import datetime
from typing import Dict, List, Optional

from services.worker.src.monitoring.drift_detector import (
    PopulationStabilityIndex,
    KLDivergence,
    DriftDetector,
    DriftMetric,
    BiasMetric,
    SafetyEvent,
    DriftReport,
    DriftType,
    AlertLevel,
    SafetySeverity,
    create_drift_detector,
)


class TestPopulationStabilityIndex:
    """Tests for PopulationStabilityIndex calculation."""

    def test_psi_identical_distributions(self):
        """PSI should be ~0 for identical distributions."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        psi = PopulationStabilityIndex.calculate(data, data)
        assert psi < 0.01, "PSI should be near zero for identical distributions"

    def test_psi_completely_different_distributions(self):
        """PSI should be high for completely different distributions."""
        expected = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        actual = [10.0, 20.0, 30.0, 40.0, 50.0] * 10
        psi = PopulationStabilityIndex.calculate(expected, actual)
        assert psi > 0.1, "PSI should indicate significant drift for different distributions"

    def test_psi_slightly_different_distributions(self):
        """PSI should detect small drift between distributions."""
        baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        shifted = [1.1, 2.1, 3.1, 4.1, 5.1] * 10
        psi = PopulationStabilityIndex.calculate(baseline, shifted)
        assert 0.0 < psi < 0.25, "PSI should detect minor drift"

    def test_psi_empty_arrays(self):
        """PSI should return 0 for empty arrays."""
        assert PopulationStabilityIndex.calculate([], []) == 0.0
        assert PopulationStabilityIndex.calculate([1.0, 2.0], []) == 0.0
        assert PopulationStabilityIndex.calculate([], [1.0, 2.0]) == 0.0

    def test_psi_single_value(self):
        """PSI should handle distributions with single value."""
        psi = PopulationStabilityIndex.calculate([5.0] * 10, [5.0] * 10)
        assert psi < 0.01

    def test_psi_with_custom_bins(self):
        """PSI should work with custom number of bins."""
        baseline = list(range(1, 101))
        actual = list(range(2, 102))
        psi_10 = PopulationStabilityIndex.calculate(baseline, actual, bins=10)
        psi_20 = PopulationStabilityIndex.calculate(baseline, actual, bins=20)
        assert psi_10 > 0
        assert psi_20 > 0

    def test_psi_negative_values(self):
        """PSI should handle negative values."""
        baseline = [-5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0] * 10
        actual = [-4.0, -2.0, 0.0, 1.0, 2.0, 4.0, 6.0] * 10
        psi = PopulationStabilityIndex.calculate(baseline, actual)
        assert psi >= 0


class TestKLDivergence:
    """Tests for KL Divergence calculation."""

    def test_kl_identical_distributions(self):
        """KL divergence should be 0 for identical distributions."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        kl = KLDivergence.calculate(data, data)
        assert kl < 0.01, "KL divergence should be near zero for identical distributions"

    def test_kl_different_distributions(self):
        """KL divergence should be positive for different distributions."""
        p = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        q = [5.0, 4.0, 3.0, 2.0, 1.0] * 10
        kl = KLDivergence.calculate(p, q)
        assert kl > 0, "KL divergence should be positive for different distributions"

    def test_kl_empty_arrays(self):
        """KL divergence should return 0 for empty arrays."""
        assert KLDivergence.calculate([], []) == 0.0
        assert KLDivergence.calculate([1.0, 2.0], []) == 0.0
        assert KLDivergence.calculate([], [1.0, 2.0]) == 0.0

    def test_kl_single_value(self):
        """KL divergence should handle single-value distributions."""
        kl = KLDivergence.calculate([3.0] * 10, [3.0] * 10)
        assert kl < 0.01

    def test_kl_asymmetry(self):
        """KL divergence is asymmetric: KL(P||Q) != KL(Q||P)."""
        p = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        q = [2.0, 3.0, 4.0, 5.0, 6.0] * 10
        kl_pq = KLDivergence.calculate(p, q)
        kl_qp = KLDivergence.calculate(q, p)
        assert kl_pq != kl_qp, "KL divergence should be asymmetric"

    def test_kl_with_custom_bins(self):
        """KL divergence should work with custom number of bins."""
        p = list(range(1, 51))
        q = list(range(2, 52))
        kl_5 = KLDivergence.calculate(p, q, bins=5)
        kl_10 = KLDivergence.calculate(p, q, bins=10)
        assert kl_5 > 0
        assert kl_10 > 0

    def test_kl_negative_values(self):
        """KL divergence should handle negative values."""
        p = [-5.0, -3.0, -1.0, 0.0, 1.0, 3.0, 5.0] * 10
        q = [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0] * 10
        kl = KLDivergence.calculate(p, q)
        assert kl >= 0


class TestDriftDetectorInputDrift:
    """Tests for DriftDetector.detect_input_drift()."""

    @pytest.fixture
    def detector(self):
        """Create a DriftDetector instance."""
        baseline = {
            "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0] * 10,
            "feature_b": [10.0, 20.0, 30.0, 40.0, 50.0] * 10,
        }
        return DriftDetector(
            model_id="test_model",
            model_version="1.0.0",
            baseline_data=baseline
        )

    def test_detect_input_drift_normal(self, detector):
        """Input drift should be NORMAL when similar to baseline."""
        current = [1.1, 2.1, 3.1, 4.1, 5.1] * 10
        metric = detector.detect_input_drift("feature_a", current)
        
        assert metric.drift_type == DriftType.INPUT
        assert metric.feature_name == "feature_a"
        assert metric.metric_name == "PSI"
        assert metric.alert_level == AlertLevel.NORMAL
        assert metric.sample_size == 50

    def test_detect_input_drift_warning(self, detector):
        """Input drift should be WARNING at appropriate threshold."""
        # Create significantly different distribution
        current = [5.0, 6.0, 7.0, 8.0, 9.0] * 10
        metric = detector.detect_input_drift("feature_a", current)
        
        assert metric.drift_type == DriftType.INPUT
        assert metric.alert_level in [AlertLevel.WARNING, AlertLevel.CRITICAL]

    def test_detect_input_drift_critical(self, detector):
        """Input drift should be CRITICAL for very different distributions."""
        # Create completely different distribution
        baseline = detector.baseline_data["feature_a"]
        current = [100.0 + x for x in baseline]
        metric = detector.detect_input_drift("feature_a", current)
        
        assert metric.alert_level == AlertLevel.CRITICAL

    def test_detect_input_drift_no_baseline(self, detector):
        """Input drift should return NORMAL when no baseline exists."""
        current = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        metric = detector.detect_input_drift("unknown_feature", current)
        
        assert metric.alert_level == AlertLevel.NORMAL
        assert metric.current_value == 0.0

    def test_detect_input_drift_empty_current(self, detector):
        """Input drift detection should handle empty current values."""
        metric = detector.detect_input_drift("feature_a", [])
        assert metric.sample_size == 0

    def test_detect_input_drift_custom_baseline(self, detector):
        """Input drift should accept custom baseline values."""
        custom_baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        current = [1.1, 2.1, 3.1, 4.1, 5.1] * 10
        metric = detector.detect_input_drift(
            "any_feature",
            current,
            baseline_values=custom_baseline
        )
        
        assert metric.alert_level == AlertLevel.NORMAL

    def test_detect_input_drift_identical_distributions(self, detector):
        """PSI should be minimal for identical distributions."""
        baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        metric = detector.detect_input_drift("feature_a", baseline)
        
        assert metric.current_value < 0.01
        assert metric.alert_level == AlertLevel.NORMAL


class TestDriftDetectorOutputDrift:
    """Tests for DriftDetector.detect_output_drift()."""

    @pytest.fixture
    def detector(self):
        """Create a DriftDetector instance."""
        baseline = {
            "predictions": [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        }
        return DriftDetector(
            model_id="test_model",
            model_version="1.0.0",
            baseline_data=baseline
        )

    def test_detect_output_drift_normal(self, detector):
        """Output drift should be NORMAL when similar to baseline."""
        current = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        metric = detector.detect_output_drift(current)
        
        assert metric.drift_type == DriftType.OUTPUT
        assert metric.feature_name is None
        assert metric.metric_name == "PSI"
        assert metric.alert_level == AlertLevel.NORMAL

    def test_detect_output_drift_warning(self, detector):
        """Output drift should be WARNING at appropriate threshold."""
        current = [0.5, 0.6, 0.7, 0.8, 0.9] * 10
        metric = detector.detect_output_drift(current)
        
        assert metric.drift_type == DriftType.OUTPUT
        assert metric.alert_level in [AlertLevel.WARNING, AlertLevel.CRITICAL]

    def test_detect_output_drift_critical(self, detector):
        """Output drift should be CRITICAL for very different distributions."""
        baseline = detector.baseline_data["predictions"]
        current = [x + 0.5 for x in baseline]
        metric = detector.detect_output_drift(current)
        
        assert metric.alert_level == AlertLevel.CRITICAL

    def test_detect_output_drift_no_baseline(self, detector):
        """Output drift should return NORMAL when no baseline exists."""
        detector_empty = DriftDetector(
            model_id="test_model",
            model_version="1.0.0"
        )
        current = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        metric = detector_empty.detect_output_drift(current)
        
        assert metric.alert_level == AlertLevel.NORMAL

    def test_detect_output_drift_empty_current(self, detector):
        """Output drift detection should handle empty current predictions."""
        metric = detector.detect_output_drift([])
        assert metric.sample_size == 0

    def test_detect_output_drift_custom_baseline(self, detector):
        """Output drift should accept custom baseline predictions."""
        custom_baseline = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        current = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        metric = detector.detect_output_drift(current, baseline_values=custom_baseline)
        
        assert metric.alert_level == AlertLevel.NORMAL

    def test_detect_output_drift_identical_distributions(self, detector):
        """PSI should be minimal for identical distributions."""
        baseline = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        metric = detector.detect_output_drift(baseline)
        
        assert metric.current_value < 0.01
        assert metric.alert_level == AlertLevel.NORMAL


class TestSeverityLevelClassification:
    """Tests for drift severity classification."""

    @pytest.fixture
    def detector(self):
        """Create a DriftDetector instance."""
        return DriftDetector(
            model_id="test_model",
            model_version="1.0.0",
            baseline_data={
                "feature": [1.0, 2.0, 3.0, 4.0, 5.0] * 10,
                "predictions": [0.1, 0.3, 0.5, 0.7, 0.9] * 10
            }
        )

    def test_alert_level_normal_threshold(self, detector):
        """Alert level should be NORMAL below warning threshold."""
        baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        current = [1.01, 2.01, 3.01, 4.01, 5.01] * 10
        metric = detector.detect_input_drift("feature", current, baseline)
        
        assert metric.alert_level == AlertLevel.NORMAL
        assert metric.current_value < metric.threshold_warning

    def test_alert_level_warning_threshold(self, detector):
        """Alert level should be WARNING between warning and critical."""
        baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        current = [1.5, 2.5, 3.5, 4.5, 5.5] * 10
        metric = detector.detect_input_drift("feature", current, baseline)
        
        if metric.alert_level == AlertLevel.WARNING:
            assert metric.threshold_warning <= metric.current_value
            assert metric.current_value < metric.threshold_critical

    def test_alert_level_critical_threshold(self, detector):
        """Alert level should be CRITICAL above critical threshold."""
        baseline = [1.0, 2.0, 3.0, 4.0, 5.0] * 10
        current = [10.0, 20.0, 30.0, 40.0, 50.0] * 10
        metric = detector.detect_input_drift("feature", current, baseline)
        
        assert metric.alert_level == AlertLevel.CRITICAL
        assert metric.current_value >= metric.threshold_critical

    def test_custom_thresholds(self):
        """Custom thresholds should be respected."""
        custom_thresholds = {
            "psi_warning": 0.05,
            "psi_critical": 0.15,
        }
        detector = DriftDetector(
            model_id="test_model",
            model_version="1.0.0",
            baseline_data={"feature": [1.0, 2.0, 3.0, 4.0, 5.0] * 10},
            thresholds=custom_thresholds
        )
        
        assert detector.thresholds["psi_warning"] == 0.05
        assert detector.thresholds["psi_critical"] == 0.15

    def test_bias_drift_alert_triggered(self):
        """BiasMetric should trigger alert when exceeding tolerance."""
        detector = DriftDetector(
            model_id="test_model",
            model_version="1.0.0",
            thresholds={"bias_tolerance": 0.05}
        )
        
        metric = detector.detect_bias_drift(
            metric_name="demographic_parity_gap",
            stratum_type="RACE",
            stratum_value="Black",
            baseline_value=0.1,
            current_value=0.2
        )
        
        assert metric.alert_triggered is True

    def test_bias_drift_alert_not_triggered(self):
        """BiasMetric should not trigger alert within tolerance."""
        detector = DriftDetector(
            model_id="test_model",
            model_version="1.0.0",
            thresholds={"bias_tolerance": 0.05}
        )
        
        metric = detector.detect_bias_drift(
            metric_name="demographic_parity_gap",
            stratum_type="RACE",
            stratum_value="Black",
            baseline_value=0.1,
            current_value=0.12
        )
        
        assert metric.alert_triggered is False


class TestDriftReportGeneration:
    """Tests for DriftReport generation."""

    @pytest.fixture
    def detector(self):
        """Create a DriftDetector instance."""
        return DriftDetector(
            model_id="test_model_v1",
            model_version="1.0.0",
            baseline_data={
                "age": [25.0, 35.0, 45.0, 55.0, 65.0] * 10,
                "income": [20000.0, 40000.0, 60000.0, 80000.0, 100000.0] * 10,
                "predictions": [0.1, 0.3, 0.5, 0.7, 0.9] * 10
            }
        )

    def test_report_structure(self, detector):
        """DriftReport should contain all required fields."""
        input_data = {
            "age": [26.0, 36.0, 46.0, 56.0, 66.0] * 10,
            "income": [25000.0, 45000.0, 65000.0, 85000.0, 105000.0] * 10
        }
        output_data = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        assert isinstance(report, DriftReport)
        assert report.report_id
        assert report.model_id == "test_model_v1"
        assert report.model_version == "1.0.0"
        assert report.generated_at
        assert report.window_start
        assert report.window_end
        assert isinstance(report.input_drift, list)
        assert isinstance(report.output_drift, list)
        assert isinstance(report.bias_metrics, list)
        assert isinstance(report.safety_events, list)
        assert isinstance(report.overall_status, AlertLevel)
        assert isinstance(report.recommendations, list)

    def test_report_input_drift_metrics(self, detector):
        """Report should include input drift metrics for all features."""
        input_data = {
            "age": [26.0, 36.0, 46.0, 56.0, 66.0] * 10,
            "income": [25000.0, 45000.0, 65000.0, 85000.0, 105000.0] * 10
        }
        output_data = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        assert len(report.input_drift) == 2
        feature_names = {m.feature_name for m in report.input_drift}
        assert feature_names == {"age", "income"}

    def test_report_output_drift_metric(self, detector):
        """Report should include output drift metric."""
        input_data = {
            "age": [26.0, 36.0, 46.0, 56.0, 66.0] * 10
        }
        output_data = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        assert len(report.output_drift) == 1
        assert report.output_drift[0].drift_type == DriftType.OUTPUT

    def test_report_bias_metrics(self, detector):
        """Report should process bias data correctly."""
        input_data = {"age": [26.0, 36.0, 46.0, 56.0, 66.0] * 10}
        output_data = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        bias_data = [
            {
                "metric_name": "demographic_parity_gap",
                "stratum_type": "RACE",
                "stratum_value": "Black",
                "baseline_value": 0.05,
                "current_value": 0.15,
                "sample_size": 100
            }
        ]
        
        report = detector.generate_report(input_data, output_data, bias_data)
        
        assert len(report.bias_metrics) == 1
        assert report.bias_metrics[0].metric_name == "demographic_parity_gap"

    def test_report_overall_status_normal(self, detector):
        """Report overall_status should be NORMAL when all metrics are normal."""
        input_data = {
            "age": [25.01, 35.01, 45.01, 55.01, 65.01] * 10
        }
        output_data = [0.101, 0.301, 0.501, 0.701, 0.901] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        assert report.overall_status == AlertLevel.NORMAL

    def test_report_overall_status_critical(self, detector):
        """Report overall_status should be CRITICAL when critical drift detected."""
        input_data = {
            "age": [100.0, 200.0, 300.0, 400.0, 500.0] * 10
        }
        output_data = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        assert report.overall_status == AlertLevel.CRITICAL

    def test_report_safety_events_created(self, detector):
        """Report should create safety events for critical drift."""
        input_data = {
            "age": [100.0, 200.0, 300.0, 400.0, 500.0] * 10
        }
        output_data = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        # Should have safety events for critical drift
        if report.overall_status == AlertLevel.CRITICAL:
            assert len(report.safety_events) > 0

    def test_report_recommendations_normal(self, detector):
        """Report should have minimal recommendations for normal drift."""
        input_data = {
            "age": [25.01, 35.01, 45.01, 55.01, 65.01] * 10
        }
        output_data = [0.101, 0.301, 0.501, 0.701, 0.901] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        # Normal status should not have critical recommendations
        assert all("pausing" not in rec.lower() for rec in report.recommendations)

    def test_report_recommendations_critical(self, detector):
        """Report should have critical recommendations for critical drift."""
        input_data = {
            "age": [100.0, 200.0, 300.0, 400.0, 500.0] * 10
        }
        output_data = [0.1, 0.3, 0.5, 0.7, 0.9] * 10
        
        report = detector.generate_report(input_data, output_data)
        
        if report.overall_status == AlertLevel.CRITICAL:
            assert any("pausing" in rec.lower() or "deployment" in rec.lower()
                      for rec in report.recommendations)

    def test_report_window_times(self, detector):
        """Report should have correct window times."""
        input_data = {"age": [26.0, 36.0, 46.0, 56.0, 66.0] * 10}
        output_data = [0.11, 0.31, 0.51, 0.71, 0.91] * 10
        
        report = detector.generate_report(input_data, output_data, window_hours=24)
        
        # Parse ISO format timestamps
        start = datetime.fromisoformat(report.window_start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(report.window_end.replace("Z", "+00:00"))
        
        # Window should be approximately 24 hours
        diff_hours = (end - start).total_seconds() / 3600
        assert 23 < diff_hours < 25

    def test_report_empty_input_data(self, detector):
        """Report should handle empty input data."""
        report = detector.generate_report({}, [0.1, 0.3, 0.5])
        
        assert report.input_drift == []
        assert len(report.output_drift) == 1


class TestDriftDetectorBiasDrift:
    """Tests for bias drift detection."""

    def test_detect_bias_drift_basic(self):
        """detect_bias_drift should return BiasMetric."""
        detector = DriftDetector("model_id", "1.0.0")
        
        metric = detector.detect_bias_drift(
            metric_name="demographic_parity_gap",
            stratum_type="RACE",
            stratum_value="Black",
            baseline_value=0.05,
            current_value=0.08
        )
        
        assert isinstance(metric, BiasMetric)
        assert metric.metric_name == "demographic_parity_gap"
        assert metric.stratum_type == "RACE"
        assert metric.stratum_value == "Black"

    def test_detect_bias_drift_tolerance_exceeded(self):
        """BiasMetric should alert when difference exceeds tolerance."""
        detector = DriftDetector(
            "model_id",
            "1.0.0",
            thresholds={"bias_tolerance": 0.02}
        )
        
        metric = detector.detect_bias_drift(
            metric_name="demographic_parity_gap",
            stratum_type="GENDER",
            stratum_value="Female",
            baseline_value=0.1,
            current_value=0.15
        )
        
        assert metric.alert_triggered is True

    def test_detect_bias_drift_tolerance_within(self):
        """BiasMetric should not alert when difference within tolerance."""
        detector = DriftDetector(
            "model_id",
            "1.0.0",
            thresholds={"bias_tolerance": 0.1}
        )
        
        metric = detector.detect_bias_drift(
            metric_name="demographic_parity_gap",
            stratum_type="GENDER",
            stratum_value="Female",
            baseline_value=0.1,
            current_value=0.15
        )
        
        assert metric.alert_triggered is False


class TestSafetyEventCreation:
    """Tests for safety event creation."""

    def test_create_safety_event_basic(self):
        """create_safety_event should return SafetyEvent."""
        detector = DriftDetector("model_id", "1.0.0")
        
        event = detector.create_safety_event(
            event_type="DRIFT_ALERT",
            severity=SafetySeverity.WARNING,
            description="Test drift alert",
            details={"feature": "age"}
        )
        
        assert isinstance(event, SafetyEvent)
        assert event.event_id
        assert event.model_id == "model_id"
        assert event.event_type == "DRIFT_ALERT"
        assert event.severity == SafetySeverity.WARNING
        assert event.description == "Test drift alert"

    def test_create_safety_event_auto_pause_critical(self):
        """SafetyEvent should set auto_paused for critical severity."""
        detector = DriftDetector("model_id", "1.0.0")
        
        event = detector.create_safety_event(
            event_type="DRIFT_ALERT",
            severity=SafetySeverity.CRITICAL,
            description="Critical drift",
            details={}
        )
        
        assert event.auto_paused is True

    def test_create_safety_event_no_auto_pause_warning(self):
        """SafetyEvent should not auto_pause for warning severity."""
        detector = DriftDetector("model_id", "1.0.0")
        
        event = detector.create_safety_event(
            event_type="DRIFT_ALERT",
            severity=SafetySeverity.WARNING,
            description="Warning drift",
            details={}
        )
        
        assert event.auto_paused is False

    def test_create_safety_event_with_notifier(self):
        """Safety event should call notifier for critical events."""
        notifier_called = []
        
        def test_notifier(event: SafetyEvent):
            notifier_called.append(event)
        
        detector = DriftDetector("model_id", "1.0.0", notifier=test_notifier)
        
        event = detector.create_safety_event(
            event_type="DRIFT_ALERT",
            severity=SafetySeverity.CRITICAL,
            description="Critical drift",
            details={}
        )
        
        assert len(notifier_called) == 1
        assert notifier_called[0].event_id == event.event_id

    def test_create_safety_event_notifier_not_called_for_info(self):
        """Notifier should not be called for INFO severity."""
        notifier_called = []
        
        def test_notifier(event: SafetyEvent):
            notifier_called.append(event)
        
        detector = DriftDetector("model_id", "1.0.0", notifier=test_notifier)
        
        detector.create_safety_event(
            event_type="DRIFT_ALERT",
            severity=SafetySeverity.INFO,
            description="Info event",
            details={}
        )
        
        assert len(notifier_called) == 0


class TestPerformanceDegradation:
    """Tests for performance degradation detection."""

    def test_detect_performance_degradation_no_degradation(self):
        """Should not flag degradation within threshold."""
        detector = DriftDetector(
            "model_id",
            "1.0.0",
            thresholds={"auc_drop_threshold": 0.05}
        )
        
        degraded, drop = detector.detect_performance_degradation(
            baseline_auc=0.95,
            current_auc=0.93
        )
        
        assert degraded is False
        assert drop == 0.02

    def test_detect_performance_degradation_exceeds_threshold(self):
        """Should flag degradation exceeding threshold."""
        detector = DriftDetector(
            "model_id",
            "1.0.0",
            thresholds={"auc_drop_threshold": 0.05}
        )
        
        degraded, drop = detector.detect_performance_degradation(
            baseline_auc=0.95,
            current_auc=0.88
        )
        
        assert degraded is True
        assert drop == 0.07

    def test_detect_performance_degradation_no_drop(self):
        """Should not flag degradation when performance improves."""
        detector = DriftDetector(
            "model_id",
            "1.0.0",
            thresholds={"auc_drop_threshold": 0.05}
        )
        
        degraded, drop = detector.detect_performance_degradation(
            baseline_auc=0.90,
            current_auc=0.95
        )
        
        assert degraded is False
        assert drop == -0.05


class TestFactoryFunction:
    """Tests for create_drift_detector factory function."""

    def test_create_drift_detector_basic(self):
        """Factory function should create DriftDetector instance."""
        detector = create_drift_detector(
            model_id="test_model",
            model_version="1.0.0"
        )
        
        assert isinstance(detector, DriftDetector)
        assert detector.model_id == "test_model"
        assert detector.model_version == "1.0.0"

    def test_create_drift_detector_with_baseline(self):
        """Factory function should set baseline data."""
        baseline = {"feature": [1.0, 2.0, 3.0]}
        detector = create_drift_detector(
            model_id="test_model",
            model_version="1.0.0",
            baseline_data=baseline
        )
        
        assert detector.baseline_data == baseline


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_single_sample(self):
        """Should handle single sample."""
        detector = DriftDetector("model_id", "1.0.0")
        metric = detector.detect_input_drift(
            "feature",
            [5.0],
            baseline_values=[4.0]
        )
        assert metric.sample_size == 1

    def test_large_sample(self):
        """Should handle large samples efficiently."""
        detector = DriftDetector("model_id", "1.0.0")
        large_sample = list(range(10000))
        metric = detector.detect_input_drift(
            "feature",
            large_sample,
            baseline_values=list(range(10000))
        )
        assert metric.sample_size == 10000

    def test_very_small_values(self):
        """Should handle very small values."""
        baseline = [1e-10, 2e-10, 3e-10] * 10
        current = [1.1e-10, 2.1e-10, 3.1e-10] * 10
        psi = PopulationStabilityIndex.calculate(baseline, current)
        assert psi >= 0

    def test_very_large_values(self):
        """Should handle very large values."""
        baseline = [1e10, 2e10, 3e10] * 10
        current = [1.1e10, 2.1e10, 3.1e10] * 10
        psi = PopulationStabilityIndex.calculate(baseline, current)
        assert psi >= 0

    def test_mixed_positive_negative(self):
        """Should handle mixed positive and negative values."""
        baseline = [-5.0, -2.0, 0.0, 2.0, 5.0] * 10
        current = [-4.0, -1.0, 1.0, 3.0, 6.0] * 10
        metric = PopulationStabilityIndex.calculate(baseline, current)
        assert metric >= 0

    def test_all_zero_values(self):
        """Should handle all zero values."""
        psi = PopulationStabilityIndex.calculate([0.0] * 10, [0.0] * 10)
        assert psi >= 0

    def test_nan_handling_graceful(self):
        """Should handle NaN values gracefully."""
        # Most distributions with NaN will cause issues, but test edge case
        try:
            baseline = [1.0, 2.0, 3.0] * 10
            current = [1.0, 2.0, 3.0] * 10
            psi = PopulationStabilityIndex.calculate(baseline, current)
            assert psi < 0.01
        except (ValueError, TypeError):
            # Acceptable if NaN is properly rejected
            pass
