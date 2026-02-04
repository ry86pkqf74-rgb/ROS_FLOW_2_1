"""
Example usage of the SlackAlertClient for sending drift alerts to Slack.

This module demonstrates how to use the SlackAlertClient class to send
different types of alerts (drift, FAVES violations, and safety events)
to Slack channels using a webhook integration.
"""

from datetime import datetime
from slack_alerts import (
    SlackAlertClient,
    DriftAlert,
    FAVESViolation,
    SafetyEvent,
    SeverityLevel,
)


def example_drift_alert():
    """Example: Send a drift alert to Slack."""
    # Initialize the client with your webhook URL
    client = SlackAlertClient(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        channel="#ml-alerts",  # Optional: override webhook default channel
        username="Drift Alert Bot",
        rate_limit_per_minute=10,
        timeout_seconds=10,
    )

    # Create a drift alert
    alert = DriftAlert(
        model_id="model-classification-v2",
        model_name="Customer Classification Model v2",
        metric="accuracy",
        current_value=0.845,
        baseline_value=0.920,
        threshold=0.900,
        drift_percentage=8.15,
        timestamp=datetime.now().isoformat(),
        severity=SeverityLevel.WARNING,
        details={
            "feature_importance_change": "15%",
            "data_shift_detected": "Yes",
            "affected_segments": "Mobile Users",
        }
    )

    # Send the alert
    success = client.send_drift_alert(alert)
    print(f"Drift alert sent: {success}")


def example_faves_violation():
    """Example: Send a FAVES violation alert to Slack."""
    client = SlackAlertClient(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        channel="#compliance-alerts",
        username="Compliance Bot",
    )

    # Create a FAVES violation
    violation = FAVESViolation(
        model_id="model-lending-v3",
        model_name="Loan Approval Model v3",
        violation_type="Fairness",
        description="Disparate impact detected for protected group.",
        severity=SeverityLevel.CRITICAL,
        timestamp=datetime.now().isoformat(),
        affected_groups=["Female", "Age 18-25", "Low Income"],
        details={
            "approval_rate_disparity": "12.5%",
            "statistical_significance": "p < 0.001",
            "recommended_action": "Model retrain required",
        }
    )

    # Send the violation alert
    success = client.send_faves_violation(violation)
    print(f"FAVES violation alert sent: {success}")


def example_safety_event():
    """Example: Send a safety event alert to Slack."""
    client = SlackAlertClient(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        channel="#safety-alerts",
        username="Safety Monitor Bot",
    )

    # Create a safety event
    event = SafetyEvent(
        event_type="Adversarial Attack Detection",
        model_id="model-nlp-sentiment-v1",
        description="Adversarial input detected that bypasses content filter.",
        severity=SeverityLevel.CRITICAL,
        timestamp=datetime.now().isoformat(),
        metadata={
            "attack_type": "Jailbreak Attempt",
            "confidence_score": 0.98,
            "containment_status": "Blocked",
            "incident_id": "INC-2026-001234",
        }
    )

    # Send the safety event
    success = client.send_safety_event(event)
    print(f"Safety event alert sent: {success}")


def example_rate_limiting():
    """Example: Demonstrate rate limiting in action."""
    client = SlackAlertClient(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        rate_limit_per_minute=3,  # Allow only 3 alerts per minute
    )

    # Try sending multiple alerts quickly
    for i in range(5):
        alert = DriftAlert(
            model_id="model-test",
            model_name="Test Model",
            metric="precision",
            current_value=0.85,
            baseline_value=0.90,
            threshold=0.88,
            drift_percentage=5.56,
            timestamp=datetime.now().isoformat(),
            severity=SeverityLevel.INFO,
        )

        success = client.send_drift_alert(alert)
        print(f"Alert {i+1}: {'Sent' if success else 'Rate limited'}")
        # Note: First 3 will succeed, rest will be rate limited


def example_skip_rate_limit():
    """Example: Skip rate limiting for critical events."""
    client = SlackAlertClient(
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        rate_limit_per_minute=1,  # Restrictive limit
    )

    alert = DriftAlert(
        model_id="model-critical",
        model_name="Critical Production Model",
        metric="f1_score",
        current_value=0.70,
        baseline_value=0.95,
        threshold=0.90,
        drift_percentage=26.32,
        timestamp=datetime.now().isoformat(),
        severity=SeverityLevel.CRITICAL,
    )

    # Skip rate limiting for critical alerts
    success = client.send_drift_alert(alert, skip_rate_limit=True)
    print(f"Critical alert sent (rate limit bypassed): {success}")


def example_error_handling():
    """Example: Demonstrate error handling."""
    try:
        # Invalid webhook URL will raise ValueError
        client = SlackAlertClient(webhook_url="")
    except ValueError as e:
        print(f"Error initializing client: {e}")

    # Valid client with bad webhook URL will log errors and return False
    client = SlackAlertClient(
        webhook_url="https://hooks.slack.com/services/INVALID/URL",
        timeout_seconds=5,
    )

    alert = DriftAlert(
        model_id="model-test",
        model_name="Test Model",
        metric="accuracy",
        current_value=0.80,
        baseline_value=0.90,
        threshold=0.85,
        drift_percentage=11.11,
        timestamp=datetime.now().isoformat(),
        severity=SeverityLevel.WARNING,
    )

    # This will fail gracefully and log the error
    success = client.send_drift_alert(alert)
    print(f"Alert sent (expected to fail): {success}")


if __name__ == "__main__":
    print("SlackAlertClient Examples\n")
    print("=" * 50)
    print("\nNote: Replace webhook URLs with actual Slack webhook URLs")
    print("to run these examples with real Slack integration.\n")

    # Uncomment to run examples:
    # example_drift_alert()
    # example_faves_violation()
    # example_safety_event()
    # example_rate_limiting()
    # example_skip_rate_limit()
    # example_error_handling()
