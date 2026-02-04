"""
Model Monitoring and Drift Detection
Post-deployment monitoring for production ML models.

Key Components:
- drift_detector: Core drift detection engine
- drift_scheduler: Scheduled drift detection with multi-model support
- Automatic alert generation for critical drift
- Immutable audit logging integration

Phase 14 Implementation - ROS-114, ROS-115
Track E - Monitoring & Audit
"""

from .drift_detector import (
    DriftDetector,
    DriftReport,
    PopulationStabilityIndex,
    KLDivergence,
    AlertLevel,
    DriftType,
    SafetySeverity,
    DriftMetric,
    BiasMetric,
    SafetyEvent,
)

from .drift_scheduler import (
    DriftScheduler,
    DriftCheckResult,
    ModelDriftConfig,
    ScheduleInterval,
    ExecutionStatus,
    get_drift_scheduler,
    configure_drift_scheduler,
)

__all__ = [
    # Drift detection
    "DriftDetector",
    "DriftReport",
    "PopulationStabilityIndex",
    "KLDivergence",
    "AlertLevel",
    "DriftType",
    "SafetySeverity",
    "DriftMetric",
    "BiasMetric",
    "SafetyEvent",
    # Drift scheduling
    "DriftScheduler",
    "DriftCheckResult",
    "ModelDriftConfig",
    "ScheduleInterval",
    "ExecutionStatus",
    "get_drift_scheduler",
    "configure_drift_scheduler",
]
