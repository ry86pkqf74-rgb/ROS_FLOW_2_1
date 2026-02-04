# Track E Quick Start Guide

## 5-Minute Setup

### 1. Audit Logging

```python
from audit import get_audit_logger

# Initialize (auto-creates database)
logger = get_audit_logger("sqlite:///audit.db")

# Log an event
entry_id = logger.append_entry(
    action="UPDATE",
    actor="data_scientist_alice",
    resource_type="model",
    resource_id="prod_model_v2",
    data={"threshold": 0.85}
)

# Verify integrity
result = logger.verify_chain()
print(f"Chain valid: {result['valid']}")

# Export for compliance
audit_data = logger.export_chain(output_format="json")
```

### 2. Drift Detection Scheduler

```python
from monitoring import DriftScheduler, ScheduleInterval

# Initialize
scheduler = DriftScheduler()

# Configure model
scheduler.configure_model(
    model_id="fraud_detector",
    model_version="2.0.0",
    schedule_interval=ScheduleInterval.DAILY,
    baseline_data={
        "amount": [100, 500, 1000, 5000],
        "days_old": [30, 90, 365, 1000]
    }
)

# Start scheduling
scheduler.start()

# Check results
stats = scheduler.get_statistics()
print(f"Models monitored: {stats['total_models_configured']}")
print(f"Success rate: {stats['success_rate']}%")

# Graceful shutdown
scheduler.stop()
```

## Common Patterns

### Pattern 1: Audit All Model Changes

```python
from audit import get_audit_logger

audit = get_audit_logger()

def deploy_model(model_id, model_file, metrics):
    # Deploy logic...

    # Audit the deployment
    audit.append_entry(
        action="DEPLOY",
        actor="ci_cd_system",
        resource_type="model",
        resource_id=model_id,
        data={"file": model_file, "metrics": metrics}
    )
```

### Pattern 2: Alerts on Drift

```python
from monitoring import DriftScheduler, ScheduleInterval

scheduler = DriftScheduler()

def on_drift_alert(model_id, details):
    print(f"ALERT: Drift detected in {model_id}")
    print(f"Status: {details['overall_status']}")
    send_slack_message(f"Model {model_id} drift alert")

scheduler.configure_model(
    model_id="recommendation_engine",
    model_version="1.0.0",
    schedule_interval=ScheduleInterval.DAILY,
    alert_callback=on_drift_alert
)

scheduler.start()
```

### Pattern 3: Integrated Audit + Monitoring

```python
from audit import get_audit_logger
from monitoring import DriftScheduler, ScheduleInterval

audit = get_audit_logger()
scheduler = DriftScheduler()

# Log drift alerts
def log_drift_alert(model_id, details):
    audit.append_entry(
        action="DRIFT_ALERT",
        actor="automated_system",
        resource_type="model",
        resource_id=model_id,
        data=details
    )

scheduler.configure_model(
    model_id="credit_risk",
    model_version="3.1.0",
    schedule_interval=ScheduleInterval.DAILY,
    alert_callback=log_drift_alert
)

scheduler.start()
```

## Checking Status

```python
# Audit statistics
from audit import get_audit_logger
logger = get_audit_logger()
stats = logger.get_statistics()
print(f"Total audited events: {stats['total_entries']}")
print(f"Unique actors: {stats['unique_actors']}")

# Drift scheduler statistics
from monitoring import get_drift_scheduler
scheduler = get_drift_scheduler()
stats = scheduler.get_statistics()
print(f"Models monitored: {stats['total_models_enabled']}")
print(f"Execution success rate: {stats['success_rate']}%")
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: SQLAlchemy` | `pip install sqlalchemy>=2.0.38` |
| Chain verification fails | Database corruption - restore backup |
| No APScheduler | `pip install apscheduler>=3.10.0` or call `run_scheduled()` manually |
| Drift check timeout | Reduce data window, use sampling |

## Key Files

- **Audit**: `/src/audit/hash_chain.py` (22 KB)
- **Scheduler**: `/src/monitoring/drift_scheduler.py` (22 KB)
- **Tests**: `/tests/test_audit_hash_chain.py` (11 KB)
- **Tests**: `/tests/test_drift_scheduler.py` (12 KB)
- **Documentation**: `/IMPLEMENTATION_TRACK_E.md` (full reference)

## Dependencies

```bash
# Required
pip install sqlalchemy>=2.0.38

# Optional (for scheduling)
pip install apscheduler>=3.10.0
```

## Next Steps

1. Initialize audit logger in your application startup
2. Configure drift detection for production models
3. Set up alert callbacks for critical drift
4. Run periodic verification of audit chain integrity
5. Export audit logs for compliance reviews

For detailed documentation, see `IMPLEMENTATION_TRACK_E.md`
