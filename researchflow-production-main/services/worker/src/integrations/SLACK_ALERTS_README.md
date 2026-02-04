# Slack Alerts Integration

Comprehensive webhook-based Slack integration for sending drift alerts, FAVES violations, and safety events with advanced formatting, severity levels, and rate limiting.

## Features

- **Webhook-based Integration**: Uses Slack incoming webhooks for reliable message delivery
- **Multiple Alert Types**: Support for drift alerts, FAVES violations, and safety events
- **Severity Levels**: INFO, WARNING, and CRITICAL with color-coded messages
- **Rich Message Formatting**: Slack block kit format with structured blocks and action buttons
- **Rate Limiting**: Per-model rate limiting to prevent alert flooding
- **Retry Strategy**: Automatic retries with exponential backoff for resilience
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Error Handling**: Graceful error handling with proper exception management

## Installation

Ensure the following dependencies are installed:

```bash
pip install requests urllib3
```

## Usage

### Basic Setup

```python
from slack_alerts import SlackAlertClient, DriftAlert, SeverityLevel
from datetime import datetime

client = SlackAlertClient(
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    channel="#ml-alerts",  # Optional
    username="Drift Alert Bot",
    rate_limit_per_minute=10,
    timeout_seconds=10,
)
```

### Sending a Drift Alert

```python
alert = DriftAlert(
    model_id="model-v2",
    model_name="Customer Classification Model",
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
    }
)

success = client.send_drift_alert(alert)
```

### Sending a FAVES Violation

```python
violation = FAVESViolation(
    model_id="model-lending-v3",
    model_name="Loan Approval Model",
    violation_type="Fairness",
    description="Disparate impact detected for protected group.",
    severity=SeverityLevel.CRITICAL,
    timestamp=datetime.now().isoformat(),
    affected_groups=["Female", "Age 18-25"],
    details={
        "approval_rate_disparity": "12.5%",
        "statistical_significance": "p < 0.001",
    }
)

success = client.send_faves_violation(violation)
```

### Sending a Safety Event

```python
event = SafetyEvent(
    event_type="Adversarial Attack Detection",
    model_id="model-nlp-sentiment-v1",
    description="Adversarial input detected.",
    severity=SeverityLevel.CRITICAL,
    timestamp=datetime.now().isoformat(),
    metadata={
        "attack_type": "Jailbreak Attempt",
        "confidence_score": 0.98,
    }
)

success = client.send_safety_event(event)
```

## API Reference

### Classes

#### SlackAlertClient

Main client for sending alerts to Slack.

**Constructor Parameters:**
- `webhook_url` (str): Slack webhook URL (required)
- `channel` (str, optional): Slack channel override
- `username` (str): Bot username (default: "Drift Alert Bot")
- `rate_limit_per_minute` (int): Max alerts per minute (default: 10)
- `timeout_seconds` (int): HTTP timeout (default: 10)

**Methods:**
- `send_drift_alert(alert, skip_rate_limit=False) -> bool`
- `send_faves_violation(violation, skip_rate_limit=False) -> bool`
- `send_safety_event(event, skip_rate_limit=False) -> bool`
- `format_drift_message(alert) -> Dict[str, Any]`
- `format_compliance_message(violation) -> Dict[str, Any]`
- `format_safety_message(event) -> Dict[str, Any]`

#### DriftAlert (Dataclass)

Represents a drift detection alert.

**Fields:**
- `model_id`: str - Unique model identifier
- `model_name`: str - Human-readable model name
- `metric`: str - Metric name (e.g., "accuracy", "f1_score")
- `current_value`: float - Current metric value
- `baseline_value`: float - Baseline/training metric value
- `threshold`: float - Alert threshold
- `drift_percentage`: float - Detected drift percentage
- `timestamp`: str - ISO format timestamp
- `severity`: SeverityLevel - Alert severity
- `details`: Optional[Dict[str, Any]] - Additional context

#### FAVESViolation (Dataclass)

Represents a FAVES (Fairness, Accountability, Validation, Ethics, Safety) violation.

**Fields:**
- `model_id`: str - Model identifier
- `model_name`: str - Model name
- `violation_type`: str - Type of violation
- `description`: str - Violation description
- `severity`: SeverityLevel - Severity level
- `timestamp`: str - ISO format timestamp
- `affected_groups`: Optional[List[str]] - Affected demographic groups
- `details`: Optional[Dict[str, Any]] - Additional context

#### SafetyEvent (Dataclass)

Represents a safety-related event.

**Fields:**
- `event_type`: str - Type of safety event
- `model_id`: str - Model identifier
- `description`: str - Event description
- `severity`: SeverityLevel - Severity level
- `timestamp`: str - ISO format timestamp
- `metadata`: Optional[Dict[str, Any]] - Event metadata

#### SeverityLevel (Enum)

Alert severity levels with color mapping.

**Values:**
- `INFO` - Green (#36a64f)
- `WARNING` - Orange (#ff9800)
- `CRITICAL` - Red (#d32f2f)

**Methods:**
- `to_color() -> str` - Returns hex color code

#### RateLimiter

Rate limiting utility for preventing alert flooding.

**Constructor Parameters:**
- `max_messages_per_window`: Maximum messages in window
- `window_size_seconds`: Time window in seconds

**Methods:**
- `is_allowed(key: str) -> bool` - Check if message is allowed
- `get_retry_after(key: str) -> float` - Get seconds until next message allowed

## Message Formatting

Messages are formatted using Slack Block Kit with the following structure:

### Drift Alert Message

```
[Header Block] Drift Alert - SEVERITY
[Fields Block] Model | Model ID | Metric | Severity
[Section Block] Metric Details
[Optional] Additional Details
[Context Block] Timestamp
[Actions Block] View Dashboard | Acknowledge
```

### FAVES Violation Message

```
[Header Block] FAVES Violation - SEVERITY
[Fields Block] Model | Model ID | Violation Type | Severity
[Section Block] Description
[Optional] Affected Groups
[Optional] Additional Details
[Context Block] Timestamp
[Actions Block] Review Audit Log | Escalate
```

### Safety Event Message

```
[Header Block] Safety Event - SEVERITY
[Fields Block] Event Type | Model ID | Severity
[Section Block] Description
[Optional] Event Metadata
[Context Block] Timestamp
[Actions Block] (Critical only) Immediate Action | View Logs
```

## Rate Limiting

Rate limiting is implemented per model to prevent alert flooding:

```python
# Default: 10 alerts per minute per model
client = SlackAlertClient(..., rate_limit_per_minute=10)

# Check if message is allowed (happens automatically)
# Returns False if rate limit exceeded

# Bypass rate limiting for critical events
success = client.send_drift_alert(alert, skip_rate_limit=True)
```

## Error Handling

The client handles various error scenarios gracefully:

- **ValueError**: Invalid webhook URL raises immediately
- **Connection Errors**: Logged and returns False
- **Timeout Errors**: Logged with timeout value and returns False
- **HTTP Errors**: Logged with status code and response and returns False
- **Retry Strategy**: Automatic retries for 429, 5xx errors with exponential backoff

## Logging

Configure logging to monitor the client:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('slack_alerts')
```

## Examples

See `slack_alerts_example.py` for comprehensive examples including:
- Basic drift alert
- FAVES violation
- Safety event
- Rate limiting behavior
- Skipping rate limits
- Error handling

## Integration Points

### Drift Detection Service

```python
from integrations.slack_alerts import SlackAlertClient, DriftAlert, SeverityLevel

def notify_drift(model_id, metric_name, current_val, baseline_val, drift_pct):
    client = SlackAlertClient(
        webhook_url=os.getenv('SLACK_WEBHOOK_URL'),
        channel="#ml-alerts"
    )
    
    alert = DriftAlert(
        model_id=model_id,
        model_name=get_model_name(model_id),
        metric=metric_name,
        current_value=current_val,
        baseline_value=baseline_val,
        threshold=0.05,
        drift_percentage=drift_pct,
        timestamp=datetime.now().isoformat(),
        severity=SeverityLevel.CRITICAL if drift_pct > 0.10 else SeverityLevel.WARNING,
    )
    
    return client.send_drift_alert(alert)
```

### Compliance Monitoring

```python
from integrations.slack_alerts import SlackAlertClient, FAVESViolation

def notify_fairness_violation(model_id, disparate_impact):
    client = SlackAlertClient(webhook_url=os.getenv('SLACK_WEBHOOK_URL'))
    
    violation = FAVESViolation(
        model_id=model_id,
        model_name=get_model_name(model_id),
        violation_type="Disparate Impact",
        description=f"Detected {disparate_impact*100:.1f}% disparate impact",
        severity=SeverityLevel.CRITICAL,
        timestamp=datetime.now().isoformat(),
        affected_groups=get_affected_groups(model_id),
    )
    
    return client.send_faves_violation(violation)
```

## Performance Considerations

- **Async Calls**: For high-throughput scenarios, consider calling send methods asynchronously
- **Batch Messages**: If possible, batch alerts within rate limit windows
- **Session Reuse**: SlackAlertClient reuses HTTP sessions for efficiency
- **Connection Pooling**: Automatic connection pooling through requests library

## Troubleshooting

### Messages not appearing in Slack

1. Verify webhook URL is correct
2. Check bot has proper permissions in target channel
3. Review logs for error messages
4. Ensure timestamp is ISO format

### Rate limiting messages

- Check rate_limit_per_minute setting
- Use `skip_rate_limit=True` for critical alerts
- Review model_id consistency

### Connection timeouts

- Increase `timeout_seconds` parameter
- Check network connectivity
- Review Slack webhook status

## Security Considerations

- Store webhook URLs in environment variables
- Do not log full webhook URLs
- Validate model_id and model_name inputs
- Sanitize additional details before sending
- Consider message encryption for sensitive data

## License

Part of the ResearchFlow production system.
