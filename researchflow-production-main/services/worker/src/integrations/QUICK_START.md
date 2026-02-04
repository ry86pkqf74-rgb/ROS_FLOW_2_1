# Slack Alerts Integration - Quick Start Guide

## Installation

```bash
# Ensure dependencies are installed
pip install requests urllib3
```

## Basic Setup (30 seconds)

```python
from slack_alerts import SlackAlertClient, DriftAlert, SeverityLevel
from datetime import datetime

# Initialize client
client = SlackAlertClient(
    webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
    channel="#ml-alerts"
)

# Create and send alert
alert = DriftAlert(
    model_id="model-v1",
    model_name="My Model",
    metric="accuracy",
    current_value=0.85,
    baseline_value=0.95,
    threshold=0.90,
    drift_percentage=10.53,
    timestamp=datetime.now().isoformat(),
    severity=SeverityLevel.WARNING,
)

client.send_drift_alert(alert)
```

## Alert Types

### 1. Drift Alert
Model performance degradation detection
```python
alert = DriftAlert(
    model_id="...",
    model_name="...",
    metric="accuracy",           # e.g., "f1_score", "precision"
    current_value=0.85,
    baseline_value=0.95,
    threshold=0.90,
    drift_percentage=10.53,
    timestamp=datetime.now().isoformat(),
    severity=SeverityLevel.WARNING,
    details={"key": "value"}     # Optional
)
client.send_drift_alert(alert)
```

### 2. FAVES Violation (Compliance)
Fairness/ethics/safety violations
```python
violation = FAVESViolation(
    model_id="...",
    model_name="...",
    violation_type="Fairness",   # e.g., "Accountability", "Safety"
    description="Disparate impact detected",
    severity=SeverityLevel.CRITICAL,
    timestamp=datetime.now().isoformat(),
    affected_groups=["Female", "Age 18-25"],  # Optional
    details={"key": "value"}     # Optional
)
client.send_faves_violation(violation)
```

### 3. Safety Event
Security and safety incidents
```python
event = SafetyEvent(
    event_type="Adversarial Attack",
    model_id="...",
    description="Jailbreak attempt detected",
    severity=SeverityLevel.CRITICAL,
    timestamp=datetime.now().isoformat(),
    metadata={"attack_type": "prompt_injection"}  # Optional
)
client.send_safety_event(event)
```

## Severity Levels

```python
SeverityLevel.INFO      # Green - Informational
SeverityLevel.WARNING   # Orange - Warning
SeverityLevel.CRITICAL  # Red - Critical
```

## Rate Limiting

```python
# Default: 10 alerts per minute per model
client = SlackAlertClient(..., rate_limit_per_minute=10)

# For critical alerts, skip rate limiting
client.send_drift_alert(alert, skip_rate_limit=True)

# Check if message would be rate limited
if not client.rate_limiter.is_allowed(model_id):
    retry_after = client.rate_limiter.get_retry_after(model_id)
    print(f"Rate limited. Retry after {retry_after:.1f}s")
```

## Configuration from Environment

```python
import os

webhook_url = os.getenv("SLACK_WEBHOOK_URL")
client = SlackAlertClient(webhook_url=webhook_url)
```

## Error Handling

```python
try:
    success = client.send_drift_alert(alert)
    if success:
        print("Alert sent successfully")
    else:
        print("Alert send failed (check logs)")
except ValueError as e:
    print(f"Invalid configuration: {e}")
```

## Common Integration Patterns

### Pattern 1: Integration with Drift Detection
```python
from integrations.slack_alerts import SlackAlertClient, DriftAlert, SeverityLevel

def detect_drift(model_id, metrics):
    client = SlackAlertClient(
        webhook_url="...",
        rate_limit_per_minute=10
    )
    
    for metric, (current, baseline) in metrics.items():
        drift = abs(current - baseline) / baseline * 100
        
        if drift > 5:  # 5% threshold
            alert = DriftAlert(
                model_id=model_id,
                model_name="Model Name",
                metric=metric,
                current_value=current,
                baseline_value=baseline,
                threshold=0.05,
                drift_percentage=drift,
                timestamp=datetime.now().isoformat(),
                severity=SeverityLevel.CRITICAL if drift > 10 else SeverityLevel.WARNING
            )
            client.send_drift_alert(alert)
```

### Pattern 2: Integration with Fairness Monitoring
```python
from integrations.slack_alerts import SlackAlertClient, FAVESViolation, SeverityLevel

def check_fairness(model_id, approval_rates):
    client = SlackAlertClient(
        webhook_url="...",
        channel="#compliance"
    )
    
    # Check disparate impact (4/5 rule)
    min_rate = min(approval_rates.values())
    max_rate = max(approval_rates.values())
    
    if min_rate / max_rate < 0.8:  # 4/5 threshold
        violation = FAVESViolation(
            model_id=model_id,
            model_name="Model Name",
            violation_type="Disparate Impact",
            description="Approval rate disparity exceeds threshold",
            severity=SeverityLevel.CRITICAL,
            timestamp=datetime.now().isoformat(),
            affected_groups=[k for k, v in approval_rates.items() if v == min_rate]
        )
        client.send_faves_violation(violation)
```

### Pattern 3: Integration with Security Monitoring
```python
from integrations.slack_alerts import SlackAlertClient, SafetyEvent, SeverityLevel

def detect_adversarial_attack(model_id, confidence):
    client = SlackAlertClient(webhook_url="...")
    
    if confidence > 0.9:
        event = SafetyEvent(
            event_type="Adversarial Attack",
            model_id=model_id,
            description="High confidence adversarial input detected",
            severity=SeverityLevel.CRITICAL,
            timestamp=datetime.now().isoformat(),
            metadata={"confidence": str(confidence)}
        )
        # Skip rate limit for critical security events
        client.send_safety_event(event, skip_rate_limit=True)
```

## Testing

```bash
# Run unit tests
python -m unittest test_slack_alerts.py

# Run specific test class
python -m unittest test_slack_alerts.TestSlackAlertClientInit

# Run specific test
python -m unittest test_slack_alerts.TestSlackAlertClientInit.test_valid_initialization
```

## Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('slack_alerts')

# Now you'll see all Slack alert operations logged
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Message not appearing" | Check webhook URL, verify bot channel access |
| "Rate limited" | Increase `rate_limit_per_minute` or use `skip_rate_limit=True` |
| "Connection timeout" | Increase `timeout_seconds` parameter |
| "ValueError on init" | Ensure webhook URL is not empty |
| "No logs appearing" | Configure logging with `logging.basicConfig(level=logging.INFO)` |

## Files Reference

| File | Purpose |
|------|---------|
| `slack_alerts.py` | Main implementation (700 lines) |
| `slack_alerts_example.py` | Usage examples |
| `slack_config_example.py` | Configuration patterns |
| `test_slack_alerts.py` | Unit tests (26+ tests) |
| `SLACK_ALERTS_README.md` | Full documentation |
| `IMPLEMENTATION_SUMMARY.md` | Architecture overview |

## Next Steps

1. Get Slack webhook URL from your workspace
2. Set `SLACK_WEBHOOK_URL` environment variable
3. Copy example code from above
4. Integrate into your monitoring pipeline
5. Adjust rate limiting as needed
6. Run tests to validate setup

## Support & Resources

- Full API docs: See `SLACK_ALERTS_README.md`
- Examples: See `slack_alerts_example.py` and `slack_config_example.py`
- Tests: See `test_slack_alerts.py` for usage patterns
- Architecture: See `IMPLEMENTATION_SUMMARY.md`

---
Happy monitoring! Send all your alerts to Slack with confidence.
