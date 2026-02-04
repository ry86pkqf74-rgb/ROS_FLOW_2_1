"""
Slack integration module for drift alerts and compliance events.

This module provides a webhook-based Slack integration for sending drift alerts,
FAVES (Fairness, Accountability, Validation, Ethics, Safety) violations, and
other safety events with proper formatting, severity levels, and rate limiting.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    def to_color(self) -> str:
        """Convert severity level to Slack message color."""
        color_map = {
            SeverityLevel.INFO: "#36a64f",      # Green
            SeverityLevel.WARNING: "#ff9800",   # Orange
            SeverityLevel.CRITICAL: "#d32f2f",  # Red
        }
        return color_map.get(self, "#808080")  # Gray as default


@dataclass
class DriftAlert:
    """Data class for drift alert information."""
    model_id: str
    model_name: str
    metric: str
    current_value: float
    baseline_value: float
    threshold: float
    drift_percentage: float
    timestamp: str
    severity: SeverityLevel
    details: Optional[Dict[str, Any]] = None


@dataclass
class FAVESViolation:
    """Data class for FAVES violation information."""
    model_id: str
    model_name: str
    violation_type: str
    description: str
    severity: SeverityLevel
    timestamp: str
    affected_groups: Optional[List[str]] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SafetyEvent:
    """Data class for safety event information."""
    event_type: str
    model_id: str
    description: str
    severity: SeverityLevel
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class RateLimiter:
    """Rate limiter for Slack messages to prevent flooding."""

    def __init__(self, max_messages_per_window: int = 10, window_size_seconds: int = 60):
        """
        Initialize the rate limiter.

        Args:
            max_messages_per_window: Maximum messages allowed in the time window
            window_size_seconds: Size of the time window in seconds
        """
        self.max_messages = max_messages_per_window
        self.window_size = window_size_seconds
        self.message_timestamps = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """
        Check if a message should be allowed based on rate limiting rules.

        Args:
            key: Identifier for the rate limit bucket (e.g., model_id)

        Returns:
            True if message is allowed, False if rate limit exceeded
        """
        current_time = time.time()
        window_start = current_time - self.window_size

        # Clean old timestamps outside the window
        self.message_timestamps[key] = [
            ts for ts in self.message_timestamps[key] if ts > window_start
        ]

        # Check if we're under the limit
        if len(self.message_timestamps[key]) < self.max_messages:
            self.message_timestamps[key].append(current_time)
            return True

        return False

    def get_retry_after(self, key: str) -> float:
        """
        Get the time (in seconds) until the next message is allowed.

        Args:
            key: Identifier for the rate limit bucket

        Returns:
            Seconds until the next message is allowed
        """
        if not self.message_timestamps[key]:
            return 0

        oldest_timestamp = min(self.message_timestamps[key])
        retry_after = (oldest_timestamp + self.window_size) - time.time()
        return max(0, retry_after)


class SlackAlertClient:
    """Client for sending drift alerts and compliance events to Slack."""

    def __init__(
        self,
        webhook_url: str,
        channel: Optional[str] = None,
        username: str = "Drift Alert Bot",
        rate_limit_per_minute: int = 10,
        timeout_seconds: int = 10,
    ):
        """
        Initialize the Slack alert client.

        Args:
            webhook_url: Slack webhook URL for posting messages
            channel: Optional Slack channel to post to (overrides webhook channel)
            username: Username for the bot in Slack
            rate_limit_per_minute: Maximum alerts per minute per model
            timeout_seconds: Timeout for HTTP requests

        Raises:
            ValueError: If webhook_url is empty or invalid
        """
        if not webhook_url:
            raise ValueError("Webhook URL cannot be empty")

        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.timeout = timeout_seconds

        # Initialize rate limiter (convert per-minute to per-minute window)
        self.rate_limiter = RateLimiter(
            max_messages_per_window=rate_limit_per_minute,
            window_size_seconds=60,
        )

        # Session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(
            f"SlackAlertClient initialized for webhook endpoint "
            f"(channel={channel or 'default'})"
        )

    def send_drift_alert(
        self,
        alert: DriftAlert,
        skip_rate_limit: bool = False,
    ) -> bool:
        """
        Send a drift alert to Slack.

        Args:
            alert: DriftAlert object containing alert details
            skip_rate_limit: If True, bypass rate limiting (use with caution)

        Returns:
            True if message was sent successfully, False otherwise
        """
        # Check rate limiting
        if not skip_rate_limit:
            if not self.rate_limiter.is_allowed(alert.model_id):
                retry_after = self.rate_limiter.get_retry_after(alert.model_id)
                logger.warning(
                    f"Drift alert for {alert.model_id} rate limited. "
                    f"Retry after {retry_after:.1f}s"
                )
                return False

        message = self.format_drift_message(alert)
        return self._send_message(message)

    def send_faves_violation(
        self,
        violation: FAVESViolation,
        skip_rate_limit: bool = False,
    ) -> bool:
        """
        Send a FAVES violation alert to Slack.

        Args:
            violation: FAVESViolation object containing violation details
            skip_rate_limit: If True, bypass rate limiting (use with caution)

        Returns:
            True if message was sent successfully, False otherwise
        """
        # Check rate limiting
        if not skip_rate_limit:
            if not self.rate_limiter.is_allowed(violation.model_id):
                retry_after = self.rate_limiter.get_retry_after(violation.model_id)
                logger.warning(
                    f"FAVES violation for {violation.model_id} rate limited. "
                    f"Retry after {retry_after:.1f}s"
                )
                return False

        message = self.format_compliance_message(violation)
        return self._send_message(message)

    def send_safety_event(
        self,
        event: SafetyEvent,
        skip_rate_limit: bool = False,
    ) -> bool:
        """
        Send a safety event alert to Slack.

        Args:
            event: SafetyEvent object containing event details
            skip_rate_limit: If True, bypass rate limiting (use with caution)

        Returns:
            True if message was sent successfully, False otherwise
        """
        # Check rate limiting
        if not skip_rate_limit:
            if not self.rate_limiter.is_allowed(event.model_id):
                retry_after = self.rate_limiter.get_retry_after(event.model_id)
                logger.warning(
                    f"Safety event for {event.model_id} rate limited. "
                    f"Retry after {retry_after:.1f}s"
                )
                return False

        message = self.format_safety_message(event)
        return self._send_message(message)

    def format_drift_message(self, alert: DriftAlert) -> Dict[str, Any]:
        """
        Format a drift alert into a Slack message block.

        Args:
            alert: DriftAlert object to format

        Returns:
            Dictionary representing a Slack message with blocks
        """
        color = alert.severity.to_color()
        timestamp_dt = datetime.fromisoformat(alert.timestamp)
        formatted_time = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Drift Alert - {alert.severity.value.upper()}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Model:*\n{alert.model_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Model ID:*\n`{alert.model_id}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Metric:*\n{alert.metric}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{alert.severity.value}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Metric Details:*\n"
                            f"• Current Value: `{alert.current_value:.6f}`\n"
                            f"• Baseline Value: `{alert.baseline_value:.6f}`\n"
                            f"• Threshold: `{alert.threshold:.6f}`\n"
                            f"• Drift: `{alert.drift_percentage:.2f}%`",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Time: {formatted_time}",
                    },
                ],
            },
        ]

        # Add additional details if provided
        if alert.details:
            detail_text = "*Additional Details:*\n"
            for key, value in alert.details.items():
                detail_text += f"• {key}: `{value}`\n"

            blocks.insert(3, {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detail_text.rstrip(),
                },
            })

        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View Dashboard",
                        "emoji": True,
                    },
                    "value": alert.model_id,
                    "action_id": "view_dashboard_drift",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Acknowledge",
                        "emoji": True,
                    },
                    "value": alert.model_id,
                    "action_id": "acknowledge_alert",
                    "style": "primary",
                },
            ],
        })

        message = {
            "username": self.username,
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ],
        }

        if self.channel:
            message["channel"] = self.channel

        return message

    def format_compliance_message(self, violation: FAVESViolation) -> Dict[str, Any]:
        """
        Format a FAVES violation into a Slack message block.

        Args:
            violation: FAVESViolation object to format

        Returns:
            Dictionary representing a Slack message with blocks
        """
        color = violation.severity.to_color()
        timestamp_dt = datetime.fromisoformat(violation.timestamp)
        formatted_time = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"FAVES Violation - {violation.severity.value.upper()}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Model:*\n{violation.model_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Model ID:*\n`{violation.model_id}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Violation Type:*\n{violation.violation_type}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{violation.severity.value}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{violation.description}",
                },
            },
        ]

        # Add affected groups if provided
        if violation.affected_groups:
            groups_text = "*Affected Groups:*\n"
            for group in violation.affected_groups:
                groups_text += f"• {group}\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": groups_text.rstrip(),
                },
            })

        # Add additional details if provided
        if violation.details:
            detail_text = "*Additional Details:*\n"
            for key, value in violation.details.items():
                detail_text += f"• {key}: `{value}`\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": detail_text.rstrip(),
                },
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Time: {formatted_time}",
                },
            ],
        })

        # Add action buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Review Audit Log",
                        "emoji": True,
                    },
                    "value": violation.model_id,
                    "action_id": "review_audit_log",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Escalate",
                        "emoji": True,
                    },
                    "value": violation.model_id,
                    "action_id": "escalate_violation",
                    "style": "danger",
                },
            ],
        })

        message = {
            "username": self.username,
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ],
        }

        if self.channel:
            message["channel"] = self.channel

        return message

    def format_safety_message(self, event: SafetyEvent) -> Dict[str, Any]:
        """
        Format a safety event into a Slack message block.

        Args:
            event: SafetyEvent object to format

        Returns:
            Dictionary representing a Slack message with blocks
        """
        color = event.severity.to_color()
        timestamp_dt = datetime.fromisoformat(event.timestamp)
        formatted_time = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Safety Event - {event.severity.value.upper()}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Event Type:*\n{event.event_type}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Model ID:*\n`{event.model_id}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{event.severity.value}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:*\n{event.description}",
                },
            },
        ]

        # Add metadata if provided
        if event.metadata:
            meta_text = "*Event Metadata:*\n"
            for key, value in event.metadata.items():
                meta_text += f"• {key}: `{value}`\n"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": meta_text.rstrip(),
                },
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Time: {formatted_time}",
                },
            ],
        })

        # Add action buttons for critical events
        if event.severity == SeverityLevel.CRITICAL:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Immediate Action",
                            "emoji": True,
                        },
                        "value": event.model_id,
                        "action_id": "immediate_action",
                        "style": "danger",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Logs",
                            "emoji": True,
                        },
                        "value": event.model_id,
                        "action_id": "view_logs",
                    },
                ],
            })

        message = {
            "username": self.username,
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                }
            ],
        }

        if self.channel:
            message["channel"] = self.channel

        return message

    def _send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a formatted message to Slack.

        Args:
            message: Message dictionary to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            response = self.session.post(
                self.webhook_url,
                json=message,
                timeout=self.timeout,
            )

            # Check for successful response
            if response.status_code == 200:
                logger.info("Slack message sent successfully")
                return True
            else:
                logger.error(
                    f"Failed to send Slack message. Status: {response.status_code}, "
                    f"Response: {response.text}"
                )
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending Slack message (timeout={self.timeout}s)")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error sending Slack message: {str(e)}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error sending Slack message: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {str(e)}")
            return False

    def __del__(self):
        """Clean up session on object destruction."""
        try:
            self.session.close()
        except Exception:
            pass
