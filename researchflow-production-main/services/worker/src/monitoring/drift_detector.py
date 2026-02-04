"""
Drift Detection Module
Monitors input/output drift and bias degradation for deployed models.

Phase 14 Implementation - ResearchFlow Transparency Execution Plan
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math
import uuid


class DriftType(str, Enum):
    """Types of drift to monitor."""
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    CONCEPT = "CONCEPT"


class AlertLevel(str, Enum):
    """Drift alert severity levels."""
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class SafetySeverity(str, Enum):
    """Safety event severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DriftMetric:
    """Single drift measurement."""
    drift_type: DriftType
    feature_name: Optional[str]
    metric_name: str
    baseline_value: float
    current_value: float
    threshold_warning: float
    threshold_critical: float
    alert_level: AlertLevel
    measured_at: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    sample_size: int = 0


@dataclass
class BiasMetric:
    """Bias measurement over time."""
    metric_name: str
    stratum_type: str
    stratum_value: str
    baseline_value: float
    current_value: float
    tolerance: float
    alert_triggered: bool
    measured_at: str
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    sample_size: int = 0


@dataclass
class SafetyEvent:
    """Safety incident record."""
    event_id: str
    model_id: str
    event_type: str
    severity: SafetySeverity
    description: str
    details: Dict[str, Any]
    auto_paused: bool
    linear_ticket_id: Optional[str] = None
    slack_thread_ts: Optional[str] = None
    resolution_status: str = "OPEN"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class DriftReport:
    """Complete drift detection report."""
    report_id: str
    model_id: str
    model_version: str
    generated_at: str
    window_start: str
    window_end: str
    input_drift: List[DriftMetric]
    output_drift: List[DriftMetric]
    bias_metrics: List[BiasMetric]
    safety_events: List[SafetyEvent]
    overall_status: AlertLevel
    recommendations: List[str]


class PopulationStabilityIndex:
    """Calculate Population Stability Index (PSI) for drift detection."""

    @staticmethod
    def calculate(
        expected: List[float],
        actual: List[float],
        bins: int = 10
    ) -> float:
        """
        Calculate PSI between expected and actual distributions.

        Args:
            expected: Baseline distribution values
            actual: Current distribution values
            bins: Number of bins for histogram

        Returns:
            PSI value (0 = no drift, >0.25 = significant drift)
        """
        if len(expected) == 0 or len(actual) == 0:
            return 0.0

        # Calculate bin edges from expected
        min_val = min(min(expected), min(actual))
        max_val = max(max(expected), max(actual))
        bin_edges = [min_val + i * (max_val - min_val) / bins for i in range(bins + 1)]

        # Count frequencies
        def bin_counts(values: List[float]) -> List[float]:
            counts = [0] * bins
            for v in values:
                for i in range(bins):
                    if bin_edges[i] <= v < bin_edges[i + 1]:
                        counts[i] += 1
                        break
                    elif i == bins - 1 and v == bin_edges[i + 1]:
                        counts[i] += 1
            # Convert to proportions with smoothing
            total = len(values)
            return [(c + 0.001) / (total + 0.001 * bins) for c in counts]

        expected_props = bin_counts(expected)
        actual_props = bin_counts(actual)

        # Calculate PSI
        psi = 0.0
        for e, a in zip(expected_props, actual_props):
            if e > 0 and a > 0:
                psi += (a - e) * math.log(a / e)

        return psi


class KLDivergence:
    """Calculate KL Divergence for drift detection."""

    @staticmethod
    def calculate(
        p: List[float],
        q: List[float],
        bins: int = 10
    ) -> float:
        """
        Calculate KL divergence D(P || Q).

        Args:
            p: Reference distribution
            q: Comparison distribution
            bins: Number of bins

        Returns:
            KL divergence value
        """
        if len(p) == 0 or len(q) == 0:
            return 0.0

        min_val = min(min(p), min(q))
        max_val = max(max(p), max(q))
        bin_edges = [min_val + i * (max_val - min_val) / bins for i in range(bins + 1)]

        def bin_probs(values: List[float]) -> List[float]:
            counts = [0] * bins
            for v in values:
                for i in range(bins):
                    if bin_edges[i] <= v < bin_edges[i + 1]:
                        counts[i] += 1
                        break
            total = len(values) + bins * 0.001
            return [(c + 0.001) / total for c in counts]

        p_probs = bin_probs(p)
        q_probs = bin_probs(q)

        kl = 0.0
        for pi, qi in zip(p_probs, q_probs):
            if pi > 0 and qi > 0:
                kl += pi * math.log(pi / qi)

        return kl


class DriftDetector:
    """
    Drift detection engine for deployed models.

    Monitors:
    - Input feature distributions
    - Output prediction distributions
    - Subgroup performance degradation
    """

    DEFAULT_THRESHOLDS = {
        "psi_warning": 0.1,
        "psi_critical": 0.25,
        "kl_warning": 0.1,
        "kl_critical": 0.2,
        "bias_tolerance": 0.05,
        "auc_drop_threshold": 0.05,
    }

    def __init__(
        self,
        model_id: str,
        model_version: str,
        baseline_data: Optional[Dict[str, List[float]]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        notifier: Optional[Callable[[SafetyEvent], None]] = None
    ):
        """
        Initialize drift detector.

        Args:
            model_id: Model identifier
            model_version: Model version
            baseline_data: Baseline distributions by feature name
            thresholds: Custom threshold values
            notifier: Callback for safety events
        """
        self.model_id = model_id
        self.model_version = model_version
        self.baseline_data = baseline_data or {}
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.notifier = notifier
        self.psi_calculator = PopulationStabilityIndex()
        self.kl_calculator = KLDivergence()

    def detect_input_drift(
        self,
        feature_name: str,
        current_values: List[float],
        baseline_values: Optional[List[float]] = None
    ) -> DriftMetric:
        """
        Detect drift in input feature distribution.

        Args:
            feature_name: Name of the feature
            current_values: Current feature values
            baseline_values: Baseline values (uses stored baseline if None)

        Returns:
            DriftMetric with PSI-based drift assessment
        """
        baseline = baseline_values or self.baseline_data.get(feature_name, [])

        if not baseline:
            return DriftMetric(
                drift_type=DriftType.INPUT,
                feature_name=feature_name,
                metric_name="PSI",
                baseline_value=0.0,
                current_value=0.0,
                threshold_warning=self.thresholds["psi_warning"],
                threshold_critical=self.thresholds["psi_critical"],
                alert_level=AlertLevel.NORMAL,
                measured_at=datetime.utcnow().isoformat() + "Z",
                sample_size=len(current_values)
            )

        psi = self.psi_calculator.calculate(baseline, current_values)

        if psi >= self.thresholds["psi_critical"]:
            alert_level = AlertLevel.CRITICAL
        elif psi >= self.thresholds["psi_warning"]:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.NORMAL

        return DriftMetric(
            drift_type=DriftType.INPUT,
            feature_name=feature_name,
            metric_name="PSI",
            baseline_value=0.0,  # PSI is relative
            current_value=psi,
            threshold_warning=self.thresholds["psi_warning"],
            threshold_critical=self.thresholds["psi_critical"],
            alert_level=alert_level,
            measured_at=datetime.utcnow().isoformat() + "Z",
            sample_size=len(current_values)
        )

    def detect_output_drift(
        self,
        current_predictions: List[float],
        baseline_predictions: Optional[List[float]] = None
    ) -> DriftMetric:
        """
        Detect drift in output prediction distribution.

        Args:
            current_predictions: Current model predictions
            baseline_predictions: Baseline predictions

        Returns:
            DriftMetric with output drift assessment
        """
        baseline = baseline_predictions or self.baseline_data.get("predictions", [])

        if not baseline:
            return DriftMetric(
                drift_type=DriftType.OUTPUT,
                feature_name=None,
                metric_name="PSI",
                baseline_value=0.0,
                current_value=0.0,
                threshold_warning=self.thresholds["psi_warning"],
                threshold_critical=self.thresholds["psi_critical"],
                alert_level=AlertLevel.NORMAL,
                measured_at=datetime.utcnow().isoformat() + "Z",
                sample_size=len(current_predictions)
            )

        psi = self.psi_calculator.calculate(baseline, current_predictions)

        if psi >= self.thresholds["psi_critical"]:
            alert_level = AlertLevel.CRITICAL
        elif psi >= self.thresholds["psi_warning"]:
            alert_level = AlertLevel.WARNING
        else:
            alert_level = AlertLevel.NORMAL

        return DriftMetric(
            drift_type=DriftType.OUTPUT,
            feature_name=None,
            metric_name="PSI",
            baseline_value=0.0,
            current_value=psi,
            threshold_warning=self.thresholds["psi_warning"],
            threshold_critical=self.thresholds["psi_critical"],
            alert_level=alert_level,
            measured_at=datetime.utcnow().isoformat() + "Z",
            sample_size=len(current_predictions)
        )

    def detect_bias_drift(
        self,
        metric_name: str,
        stratum_type: str,
        stratum_value: str,
        baseline_value: float,
        current_value: float,
        sample_size: int = 0
    ) -> BiasMetric:
        """
        Detect drift in fairness metrics.

        Args:
            metric_name: Name of fairness metric (e.g., "demographic_parity_gap")
            stratum_type: Type of stratification (e.g., "RACE")
            stratum_value: Specific stratum value (e.g., "Black")
            baseline_value: Baseline metric value
            current_value: Current metric value
            sample_size: Number of samples

        Returns:
            BiasMetric with drift assessment
        """
        tolerance = self.thresholds["bias_tolerance"]
        diff = abs(current_value - baseline_value)
        alert_triggered = diff > tolerance

        return BiasMetric(
            metric_name=metric_name,
            stratum_type=stratum_type,
            stratum_value=stratum_value,
            baseline_value=baseline_value,
            current_value=current_value,
            tolerance=tolerance,
            alert_triggered=alert_triggered,
            measured_at=datetime.utcnow().isoformat() + "Z",
            sample_size=sample_size
        )

    def detect_performance_degradation(
        self,
        baseline_auc: float,
        current_auc: float
    ) -> Tuple[bool, float]:
        """
        Check if model performance has degraded.

        Args:
            baseline_auc: Validation AUC
            current_auc: Rolling AUC on production data

        Returns:
            Tuple of (degraded, drop_amount)
        """
        drop = baseline_auc - current_auc
        degraded = drop > self.thresholds["auc_drop_threshold"]
        return degraded, drop

    def create_safety_event(
        self,
        event_type: str,
        severity: SafetySeverity,
        description: str,
        details: Dict[str, Any]
    ) -> SafetyEvent:
        """
        Create and optionally notify about a safety event.

        Args:
            event_type: Type of event
            severity: Severity level
            description: Human-readable description
            details: Additional event details

        Returns:
            SafetyEvent record
        """
        auto_pause = severity == SafetySeverity.CRITICAL

        event = SafetyEvent(
            event_id=str(uuid.uuid4()),
            model_id=self.model_id,
            event_type=event_type,
            severity=severity,
            description=description,
            details=details,
            auto_paused=auto_pause
        )

        # Notify if callback provided
        if self.notifier and severity in [SafetySeverity.ERROR, SafetySeverity.CRITICAL]:
            self.notifier(event)

        return event

    def generate_report(
        self,
        input_data: Dict[str, List[float]],
        output_data: List[float],
        bias_data: Optional[List[Dict[str, Any]]] = None,
        window_hours: int = 24
    ) -> DriftReport:
        """
        Generate comprehensive drift report.

        Args:
            input_data: Dict of feature_name -> current values
            output_data: Current predictions
            bias_data: List of bias metric dicts
            window_hours: Time window for report

        Returns:
            DriftReport with all drift metrics
        """
        now = datetime.utcnow()
        window_start = (now - timedelta(hours=window_hours)).isoformat() + "Z"
        window_end = now.isoformat() + "Z"

        # Detect input drift for all features
        input_drift = []
        for feature_name, values in input_data.items():
            metric = self.detect_input_drift(feature_name, values)
            metric.window_start = window_start
            metric.window_end = window_end
            input_drift.append(metric)

        # Detect output drift
        output_drift_metric = self.detect_output_drift(output_data)
        output_drift_metric.window_start = window_start
        output_drift_metric.window_end = window_end
        output_drift = [output_drift_metric]

        # Process bias data
        bias_metrics = []
        if bias_data:
            for bd in bias_data:
                metric = self.detect_bias_drift(
                    metric_name=bd.get("metric_name", "unknown"),
                    stratum_type=bd.get("stratum_type", "CUSTOM"),
                    stratum_value=bd.get("stratum_value", "unknown"),
                    baseline_value=bd.get("baseline_value", 0.0),
                    current_value=bd.get("current_value", 0.0),
                    sample_size=bd.get("sample_size", 0)
                )
                metric.window_start = window_start
                metric.window_end = window_end
                bias_metrics.append(metric)

        # Determine overall status
        all_metrics = input_drift + output_drift
        if any(m.alert_level == AlertLevel.CRITICAL for m in all_metrics):
            overall_status = AlertLevel.CRITICAL
        elif any(m.alert_level == AlertLevel.WARNING for m in all_metrics):
            overall_status = AlertLevel.WARNING
        else:
            overall_status = AlertLevel.NORMAL

        # Generate safety events for critical drift
        safety_events = []
        for metric in all_metrics:
            if metric.alert_level == AlertLevel.CRITICAL:
                event = self.create_safety_event(
                    event_type="DRIFT_ALERT",
                    severity=SafetySeverity.WARNING,
                    description=f"Critical drift detected in {metric.feature_name or 'predictions'}",
                    details={
                        "drift_type": metric.drift_type.value,
                        "metric_name": metric.metric_name,
                        "current_value": metric.current_value,
                        "threshold": metric.threshold_critical,
                    }
                )
                safety_events.append(event)

        # Bias alerts
        for bm in bias_metrics:
            if bm.alert_triggered:
                event = self.create_safety_event(
                    event_type="BIAS_ALERT",
                    severity=SafetySeverity.WARNING,
                    description=f"Bias drift detected: {bm.metric_name} for {bm.stratum_type}={bm.stratum_value}",
                    details={
                        "metric_name": bm.metric_name,
                        "stratum": f"{bm.stratum_type}={bm.stratum_value}",
                        "baseline": bm.baseline_value,
                        "current": bm.current_value,
                        "tolerance": bm.tolerance,
                    }
                )
                safety_events.append(event)

        # Recommendations
        recommendations = []
        if overall_status == AlertLevel.CRITICAL:
            recommendations.append("Consider pausing model deployment pending investigation")
            recommendations.append("Review recent data quality and pipeline changes")
        elif overall_status == AlertLevel.WARNING:
            recommendations.append("Monitor drift metrics closely over next 24-48 hours")
            recommendations.append("Prepare contingency plan for retraining if drift continues")

        if any(bm.alert_triggered for bm in bias_metrics):
            recommendations.append("Investigate subgroup performance degradation")
            recommendations.append("Review recent training data composition changes")

        return DriftReport(
            report_id=str(uuid.uuid4()),
            model_id=self.model_id,
            model_version=self.model_version,
            generated_at=now.isoformat() + "Z",
            window_start=window_start,
            window_end=window_end,
            input_drift=input_drift,
            output_drift=output_drift,
            bias_metrics=bias_metrics,
            safety_events=safety_events,
            overall_status=overall_status,
            recommendations=recommendations
        )


# Factory function
def create_drift_detector(
    model_id: str,
    model_version: str,
    baseline_data: Optional[Dict[str, List[float]]] = None
) -> DriftDetector:
    """Create drift detector instance."""
    return DriftDetector(
        model_id=model_id,
        model_version=model_version,
        baseline_data=baseline_data
    )
