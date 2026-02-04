"""
Unit tests for the Slack alerts integration module.

Tests cover:
- SlackAlertClient initialization and validation
- Message formatting for all alert types
- Rate limiting behavior
- Error handling and resilience
- HTTP communication
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from slack_alerts import (
    SlackAlertClient,
    DriftAlert,
    FAVESViolation,
    SafetyEvent,
    SeverityLevel,
    RateLimiter,
)


class TestSeverityLevel(unittest.TestCase):
    """Test SeverityLevel enum."""

    def test_severity_colors(self):
        """Test color mapping for severity levels."""
        self.assertEqual(SeverityLevel.INFO.to_color(), "#36a64f")
        self.assertEqual(SeverityLevel.WARNING.to_color(), "#ff9800")
        self.assertEqual(SeverityLevel.CRITICAL.to_color(), "#d32f2f")

    def test_severity_values(self):
        """Test severity level values."""
        self.assertEqual(SeverityLevel.INFO.value, "info")
        self.assertEqual(SeverityLevel.WARNING.value, "warning")
        self.assertEqual(SeverityLevel.CRITICAL.value, "critical")


class TestRateLimiter(unittest.TestCase):
    """Test RateLimiter class."""

    def setUp(self):
        self.limiter = RateLimiter(max_messages_per_window=3, window_size_seconds=1)

    def test_allows_messages_within_limit(self):
        """Test that messages within limit are allowed."""
        self.assertTrue(self.limiter.is_allowed("model1"))
        self.assertTrue(self.limiter.is_allowed("model1"))
        self.assertTrue(self.limiter.is_allowed("model1"))

    def test_blocks_messages_exceeding_limit(self):
        """Test that messages exceeding limit are blocked."""
        # Allow 3 messages
        for _ in range(3):
            self.assertTrue(self.limiter.is_allowed("model1"))

        # 4th message should be blocked
        self.assertFalse(self.limiter.is_allowed("model1"))

    def test_different_keys_have_separate_limits(self):
        """Test that different models have separate rate limit buckets."""
        for _ in range(3):
            self.assertTrue(self.limiter.is_allowed("model1"))

        # model2 should still be allowed
        self.assertTrue(self.limiter.is_allowed("model2"))
        self.assertTrue(self.limiter.is_allowed("model2"))
        self.assertTrue(self.limiter.is_allowed("model2"))

    def test_retry_after_calculation(self):
        """Test retry_after time calculation."""
        self.limiter.is_allowed("model1")
        self.assertEqual(self.limiter.get_retry_after("model1"), 0)

        # Fill the bucket
        for _ in range(2):
            self.limiter.is_allowed("model1")

        # Should be blocked
        self.limiter.is_allowed("model1")
        retry_after = self.limiter.get_retry_after("model1")
        self.assertGreater(retry_after, 0)
        self.assertLessEqual(retry_after, 1)


class TestSlackAlertClientInit(unittest.TestCase):
    """Test SlackAlertClient initialization."""

    def test_valid_initialization(self):
        """Test client initialization with valid parameters."""
        client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
        )
        self.assertIsNotNone(client)
        self.assertEqual(client.username, "Drift Alert Bot")
        self.assertEqual(client.timeout, 10)

    def test_invalid_webhook_url_raises_error(self):
        """Test that empty webhook URL raises ValueError."""
        with self.assertRaises(ValueError):
            SlackAlertClient(webhook_url="")

    def test_none_webhook_url_raises_error(self):
        """Test that None webhook URL raises ValueError."""
        with self.assertRaises(ValueError):
            SlackAlertClient(webhook_url=None)

    def test_custom_parameters(self):
        """Test client initialization with custom parameters."""
        client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/TEST",
            channel="#alerts",
            username="Custom Bot",
            rate_limit_per_minute=5,
            timeout_seconds=20,
        )
        self.assertEqual(client.channel, "#alerts")
        self.assertEqual(client.username, "Custom Bot")
        self.assertEqual(client.timeout, 20)


class TestDriftAlertFormatting(unittest.TestCase):
    """Test drift alert message formatting."""

    def setUp(self):
        self.client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/TEST"
        )
        self.alert = DriftAlert(
            model_id="model-1",
            model_name="Test Model",
            metric="accuracy",
            current_value=0.85,
            baseline_value=0.95,
            threshold=0.90,
            drift_percentage=10.53,
            timestamp=datetime.now().isoformat(),
            severity=SeverityLevel.WARNING,
        )

    def test_drift_message_structure(self):
        """Test that drift message has correct structure."""
        message = self.client.format_drift_message(self.alert)

        self.assertIn("username", message)
        self.assertIn("attachments", message)
        self.assertEqual(len(message["attachments"]), 1)

        attachment = message["attachments"][0]
        self.assertEqual(attachment["color"], "#ff9800")  # Warning color
        self.assertIn("blocks", attachment)

    def test_drift_message_has_header(self):
        """Test that drift message includes header block."""
        message = self.client.format_drift_message(self.alert)
        blocks = message["attachments"][0]["blocks"]

        headers = [b for b in blocks if b["type"] == "header"]
        self.assertEqual(len(headers), 1)
        self.assertIn("WARNING", headers[0]["text"]["text"])

    def test_drift_message_has_actions(self):
        """Test that drift message includes action buttons."""
        message = self.client.format_drift_message(self.alert)
        blocks = message["attachments"][0]["blocks"]

        actions = [b for b in blocks if b["type"] == "actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(len(actions[0]["elements"]), 2)

    def test_drift_message_with_details(self):
        """Test drift message formatting with additional details."""
        self.alert.details = {"key1": "value1", "key2": "value2"}
        message = self.client.format_drift_message(self.alert)
        blocks = message["attachments"][0]["blocks"]

        sections = [b for b in blocks if b["type"] == "section"]
        detail_sections = [
            s for s in sections
            if "Additional Details" in s.get("text", {}).get("text", "")
        ]
        self.assertEqual(len(detail_sections), 1)


class TestFAVESViolationFormatting(unittest.TestCase):
    """Test FAVES violation message formatting."""

    def setUp(self):
        self.client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/TEST"
        )
        self.violation = FAVESViolation(
            model_id="model-2",
            model_name="Lending Model",
            violation_type="Fairness",
            description="Disparate impact detected",
            severity=SeverityLevel.CRITICAL,
            timestamp=datetime.now().isoformat(),
            affected_groups=["Female", "Age 18-25"],
        )

    def test_violation_message_structure(self):
        """Test that violation message has correct structure."""
        message = self.client.format_compliance_message(self.violation)

        self.assertIn("attachments", message)
        attachment = message["attachments"][0]
        self.assertEqual(attachment["color"], "#d32f2f")  # Critical color

    def test_violation_message_has_affected_groups(self):
        """Test that violation message includes affected groups."""
        message = self.client.format_compliance_message(self.violation)
        blocks = message["attachments"][0]["blocks"]

        sections_text = [
            b.get("text", {}).get("text", "")
            for b in blocks if b["type"] == "section"
        ]
        all_text = " ".join(sections_text)
        self.assertIn("Female", all_text)
        self.assertIn("Age 18-25", all_text)


class TestSafetyEventFormatting(unittest.TestCase):
    """Test safety event message formatting."""

    def setUp(self):
        self.client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/TEST"
        )

    def test_non_critical_event_no_actions(self):
        """Test that non-critical events don't have action buttons."""
        event = SafetyEvent(
            event_type="Log Event",
            model_id="model-3",
            description="Informational event",
            severity=SeverityLevel.INFO,
            timestamp=datetime.now().isoformat(),
        )

        message = self.client.format_safety_message(event)
        blocks = message["attachments"][0]["blocks"]

        actions = [b for b in blocks if b["type"] == "actions"]
        self.assertEqual(len(actions), 0)

    def test_critical_event_has_actions(self):
        """Test that critical events have action buttons."""
        event = SafetyEvent(
            event_type="Attack Detected",
            model_id="model-3",
            description="Adversarial attack",
            severity=SeverityLevel.CRITICAL,
            timestamp=datetime.now().isoformat(),
        )

        message = self.client.format_safety_message(event)
        blocks = message["attachments"][0]["blocks"]

        actions = [b for b in blocks if b["type"] == "actions"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(len(actions[0]["elements"]), 2)


class TestMessageSending(unittest.TestCase):
    """Test message sending functionality."""

    def setUp(self):
        self.client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/TEST"
        )

    @patch('slack_alerts.requests.Session.post')
    def test_successful_send(self, mock_post):
        """Test successful message send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        alert = DriftAlert(
            model_id="model-1",
            model_name="Test",
            metric="accuracy",
            current_value=0.85,
            baseline_value=0.95,
            threshold=0.90,
            drift_percentage=10.53,
            timestamp=datetime.now().isoformat(),
            severity=SeverityLevel.INFO,
        )

        result = self.client.send_drift_alert(alert)
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch('slack_alerts.requests.Session.post')
    def test_failed_send(self, mock_post):
        """Test failed message send."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        alert = DriftAlert(
            model_id="model-1",
            model_name="Test",
            metric="accuracy",
            current_value=0.85,
            baseline_value=0.95,
            threshold=0.90,
            drift_percentage=10.53,
            timestamp=datetime.now().isoformat(),
            severity=SeverityLevel.INFO,
        )

        result = self.client.send_drift_alert(alert)
        self.assertFalse(result)


class TestRateLimitingInSending(unittest.TestCase):
    """Test rate limiting during message sending."""

    @patch('slack_alerts.requests.Session.post')
    def test_rate_limiting_blocks_send(self, mock_post):
        """Test that rate limiting prevents message send."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        client = SlackAlertClient(
            webhook_url="https://hooks.slack.com/services/TEST",
            rate_limit_per_minute=2,
        )

        alert = DriftAlert(
            model_id="model-1",
            model_name="Test",
            metric="accuracy",
            current_value=0.85,
            baseline_value=0.95,
            threshold=0.90,
            drift_percentage=10.53,
            timestamp=datetime.now().isoformat(),
            severity=SeverityLevel.INFO,
        )

        # First two should succeed
        self.assertTrue(client.send_drift_alert(alert))
        self.assertTrue(client.send_drift_alert(alert))

        # Third should be rate limited
        result = client.send_drift_alert(alert)
        self.assertFalse(result)

        # But with skip_rate_limit it should succeed
        result = client.send_drift_alert(alert, skip_rate_limit=True)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
