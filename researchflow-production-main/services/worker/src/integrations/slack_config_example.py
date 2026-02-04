"""
Configuration examples for Slack alerts integration.

This module shows various ways to configure and use the SlackAlertClient
in different scenarios and environments.
"""

import os
from datetime import datetime
from slack_alerts import (
    SlackAlertClient,
    DriftAlert,
    FAVESViolation,
    SafetyEvent,
    SeverityLevel,
)


class SlackAlertsConfig:
    """Configuration class for Slack alerts."""

    # Environment-based configuration
    WEBHOOK_URL = os.getenv(
        "SLACK_WEBHOOK_URL",
        "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    )
    ML_ALERTS_CHANNEL = "#ml-alerts"
    COMPLIANCE_ALERTS_CHANNEL = "#compliance-alerts"
    SAFETY_ALERTS_CHANNEL = "#safety-alerts"

    # Rate limiting settings (alerts per minute)
    DRIFT_RATE_LIMIT = 10
    COMPLIANCE_RATE_LIMIT = 5
    SAFETY_RATE_LIMIT = 20  # More permissive for safety

    # HTTP timeout in seconds
    TIMEOUT_SECONDS = 10

    @staticmethod
    def get_drift_client():
        """Get configured client for drift alerts."""
        return SlackAlertClient(
            webhook_url=SlackAlertsConfig.WEBHOOK_URL,
            channel=SlackAlertsConfig.ML_ALERTS_CHANNEL,
            username="ML Drift Monitor",
            rate_limit_per_minute=SlackAlertsConfig.DRIFT_RATE_LIMIT,
            timeout_seconds=SlackAlertsConfig.TIMEOUT_SECONDS,
        )

    @staticmethod
    def get_compliance_client():
        """Get configured client for compliance alerts."""
        return SlackAlertClient(
            webhook_url=SlackAlertsConfig.WEBHOOK_URL,
            channel=SlackAlertsConfig.COMPLIANCE_ALERTS_CHANNEL,
            username="Compliance Monitor",
            rate_limit_per_minute=SlackAlertsConfig.COMPLIANCE_RATE_LIMIT,
            timeout_seconds=SlackAlertsConfig.TIMEOUT_SECONDS,
        )

    @staticmethod
    def get_safety_client():
        """Get configured client for safety alerts."""
        return SlackAlertClient(
            webhook_url=SlackAlertsConfig.WEBHOOK_URL,
            channel=SlackAlertsConfig.SAFETY_ALERTS_CHANNEL,
            username="Safety Monitor",
            rate_limit_per_minute=SlackAlertsConfig.SAFETY_RATE_LIMIT,
            timeout_seconds=SlackAlertsConfig.TIMEOUT_SECONDS,
        )


# Example: Integration with drift detection pipeline
class DriftDetectionPipeline:
    """Example drift detection pipeline with Slack integration."""

    def __init__(self):
        self.slack_client = SlackAlertsConfig.get_drift_client()

    def detect_and_alert(self, model_id, model_name, metrics):
        """Detect drift and send Slack alert if threshold exceeded."""
        for metric_name, (current_val, baseline_val, threshold) in metrics.items():
            drift_pct = abs(current_val - baseline_val) / baseline_val * 100

            if drift_pct >= threshold:
                alert = DriftAlert(
                    model_id=model_id,
                    model_name=model_name,
                    metric=metric_name,
                    current_value=current_val,
                    baseline_value=baseline_val,
                    threshold=threshold,
                    drift_percentage=drift_pct,
                    timestamp=datetime.now().isoformat(),
                    severity=self._determine_severity(drift_pct, threshold),
                    details={
                        "detection_method": "Statistical Test",
                        "confidence": "99%",
                        "sample_size": "10000",
                    }
                )
                self.slack_client.send_drift_alert(alert)

    @staticmethod
    def _determine_severity(drift_pct, threshold):
        """Determine severity based on drift percentage."""
        if drift_pct >= threshold * 2:
            return SeverityLevel.CRITICAL
        elif drift_pct >= threshold * 1.5:
            return SeverityLevel.WARNING
        return SeverityLevel.INFO


# Example: Integration with fairness monitoring
class FairnessMonitor:
    """Example fairness monitoring with Slack integration."""

    def __init__(self):
        self.slack_client = SlackAlertsConfig.get_compliance_client()
        self.disparate_impact_threshold = 0.20  # 20% difference

    def monitor_and_alert(self, model_id, model_name, fairness_metrics):
        """Monitor fairness metrics and alert on violations."""
        for protected_group, approval_rate in fairness_metrics.items():
            disparate_impact = self._calculate_disparate_impact(
                approval_rate,
                fairness_metrics,
                protected_group
            )

            if disparate_impact >= self.disparate_impact_threshold:
                violation = FAVESViolation(
                    model_id=model_id,
                    model_name=model_name,
                    violation_type="Disparate Impact",
                    description=(
                        f"{disparate_impact*100:.1f}% disparate impact "
                        f"detected for {protected_group}"
                    ),
                    severity=SeverityLevel.CRITICAL,
                    timestamp=datetime.now().isoformat(),
                    affected_groups=[protected_group],
                    details={
                        "approval_rate": f"{approval_rate*100:.1f}%",
                        "statistical_test": "Four-Fifths Rule",
                        "confidence_level": "95%",
                    }
                )
                self.slack_client.send_faves_violation(violation)

    @staticmethod
    def _calculate_disparate_impact(rate, rates_dict, group):
        """Calculate disparate impact ratio."""
        reference_rate = max(v for k, v in rates_dict.items() if k != group)
        return 1 - (rate / reference_rate) if reference_rate > 0 else 0


# Example: Integration with security monitoring
class SecurityMonitor:
    """Example security monitoring with Slack integration."""

    def __init__(self):
        self.slack_client = SlackAlertsConfig.get_safety_client()

    def detect_and_alert(self, event_type, model_id, detection_confidence, details):
        """Detect security events and send Slack alert."""
        severity = self._determine_severity(detection_confidence)

        event = SafetyEvent(
            event_type=event_type,
            model_id=model_id,
            description=f"Potential {event_type} detected",
            severity=severity,
            timestamp=datetime.now().isoformat(),
            metadata={
                "confidence": f"{detection_confidence*100:.1f}%",
                "detection_method": "Adversarial Robustness Check",
                "incident_id": self._generate_incident_id(),
                **details
            }
        )

        # Skip rate limiting for critical security events
        skip_rate_limit = severity == SeverityLevel.CRITICAL
        self.slack_client.send_safety_event(event, skip_rate_limit=skip_rate_limit)

    @staticmethod
    def _determine_severity(confidence):
        """Determine severity based on detection confidence."""
        if confidence >= 0.9:
            return SeverityLevel.CRITICAL
        elif confidence >= 0.7:
            return SeverityLevel.WARNING
        return SeverityLevel.INFO

    @staticmethod
    def _generate_incident_id():
        """Generate unique incident ID."""
        from datetime import datetime
        return f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"


# Example usage
if __name__ == "__main__":
    # Initialize monitors
    drift_monitor = DriftDetectionPipeline()
    fairness_monitor = FairnessMonitor()
    security_monitor = SecurityMonitor()

    # Example: Detect drift
    print("Testing drift detection...")
    drift_monitor.detect_and_alert(
        model_id="model-classification-v2",
        model_name="Customer Classification",
        metrics={
            "accuracy": (0.845, 0.920, 0.05),  # current, baseline, threshold
            "precision": (0.810, 0.880, 0.04),
        }
    )

    # Example: Detect fairness violation
    print("Testing fairness monitoring...")
    fairness_monitor.monitor_and_alert(
        model_id="model-lending-v3",
        model_name="Loan Approval Model",
        fairness_metrics={
            "Female": 0.65,
            "Male": 0.82,
            "Unknown": 0.75,
        }
    )

    # Example: Detect security event
    print("Testing security monitoring...")
    security_monitor.detect_and_alert(
        event_type="Adversarial Attack",
        model_id="model-nlp-sentiment-v1",
        detection_confidence=0.95,
        details={
            "attack_type": "Jailbreak Attempt",
            "input_length": 254,
            "bypass_success": False,
        }
    )

    print("Configuration examples executed successfully!")
