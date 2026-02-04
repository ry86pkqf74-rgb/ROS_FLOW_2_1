"""
ResearchFlow Integrations Package
=================================
Unified integrations for AI orchestration, transparency monitoring,
and multi-tool workflows.

Components:
- Slack Alerts: Notifications for drift detection and compliance alerts
- Orchestration Router: Routes tasks to appropriate AI providers
- Transparency Pipeline: End-to-end FAVES compliance monitoring

External Integrations:
- LangSmith: transparency-monitor-agent for drift analysis
- Composio: Multi-tool workflows (Linear, Slack, GitHub, Notion)
- Linear: Issue tracking for compliance reviews
"""

from .slack_alerts import (
    SlackAlertClient,
    DriftAlert,
    FAVESViolation,
    SafetyEvent,
    SeverityLevel,
    RateLimiter,
)

from .orchestration_router import (
    OrchestrationRouter,
    TransparencyMonitorClient,
    ComposioWorkflowClient,
    TaskType,
    Provider,
    RoutingResult,
    get_router,
    route_task,
    trigger_drift_alert,
)

from .transparency_pipeline import (
    TransparencyMonitoringPipeline,
    TransparencyMonitoringScheduler,
    DriftMetrics,
    FAVESValidation,
    TransparencyReport,
    AlertSeverity,
    ComplianceStatus,
    create_pipeline,
    quick_check,
)

__all__ = [
    # Slack Alerts
    "SlackAlertClient",
    "DriftAlert",
    "FAVESViolation",
    "SafetyEvent",
    "SeverityLevel",
    "RateLimiter",

    # Orchestration Router
    "OrchestrationRouter",
    "TransparencyMonitorClient",
    "ComposioWorkflowClient",
    "TaskType",
    "Provider",
    "RoutingResult",
    "get_router",
    "route_task",
    "trigger_drift_alert",

    # Transparency Pipeline
    "TransparencyMonitoringPipeline",
    "TransparencyMonitoringScheduler",
    "DriftMetrics",
    "FAVESValidation",
    "TransparencyReport",
    "AlertSeverity",
    "ComplianceStatus",
    "create_pipeline",
    "quick_check",
]

__version__ = "2.0.0"
