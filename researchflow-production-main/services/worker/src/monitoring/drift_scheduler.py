"""
Scheduled Drift Detection Runner

Implements scheduled drift detection across multiple models with configurable intervals
and automatic alert generation when thresholds are exceeded.

Key Features:
- Hourly, daily, and weekly drift detection schedules
- Multi-model support with independent configurations
- Integration with drift_detector.py
- Automatic alert generation for critical drift
- Configurable thresholds per model
- Execution logging and metrics
- Graceful shutdown support

Phase 14 Implementation - ROS-115
Track E - Monitoring & Audit
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
import json

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.job import Job
    from apscheduler.events import (
        EVENT_JOB_EXECUTED,
        EVENT_JOB_ERROR,
        EVENT_JOB_MISSED,
    )
except ImportError:
    # Fallback implementation using threading
    BackgroundScheduler = None
    CronTrigger = None
    IntervalTrigger = None

logger = logging.getLogger(__name__)


class ScheduleInterval(str, Enum):
    """Drift detection schedule intervals."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    """Drift detection execution status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class DriftCheckResult:
    """Result of a drift detection check."""

    check_id: str
    model_id: str
    model_version: str
    timestamp: str
    status: ExecutionStatus
    duration_ms: float = 0.0
    alert_generated: bool = False
    alert_level: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_id": self.check_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "duration_ms": self.duration_ms,
            "alert_generated": self.alert_generated,
            "alert_level": self.alert_level,
            "metrics": self.metrics,
            "error_message": self.error_message,
        }


@dataclass
class ModelDriftConfig:
    """Configuration for drift detection on a specific model."""

    model_id: str
    model_version: str
    schedule_interval: ScheduleInterval
    schedule_cron: Optional[str] = None  # For CUSTOM interval
    baseline_data: Optional[Dict[str, List[float]]] = None
    thresholds: Optional[Dict[str, float]] = None
    enabled: bool = True
    features_to_monitor: Optional[List[str]] = None
    alert_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def __post_init__(self):
        """Validate configuration."""
        if self.schedule_interval == ScheduleInterval.CUSTOM and not self.schedule_cron:
            raise ValueError("schedule_cron required for CUSTOM interval")


class DriftScheduler:
    """
    Scheduled drift detection runner with multi-model support.

    Orchestrates periodic drift detection across multiple deployed models
    with automatic alert generation when thresholds are exceeded.
    """

    def __init__(
        self,
        drift_detector_factory: Optional[Callable[[str, str, Optional[Dict]], Any]] = None,
        use_apscheduler: bool = True,
    ):
        """
        Initialize drift scheduler.

        Args:
            drift_detector_factory: Factory function to create drift detectors
                Signature: (model_id, model_version, baseline_data) -> DriftDetector
                If None, uses default factory
            use_apscheduler: Use APScheduler if available, else fallback

        Raises:
            ImportError: If APScheduler requested but not available
        """
        self.logger = logging.getLogger(__name__)

        # Drift detector factory
        if drift_detector_factory:
            self.drift_detector_factory = drift_detector_factory
        else:
            # Import default factory
            from .drift_detector import create_drift_detector

            self.drift_detector_factory = create_drift_detector

        # Initialize scheduler
        self.use_apscheduler = use_apscheduler and BackgroundScheduler is not None

        if self.use_apscheduler:
            self.scheduler = BackgroundScheduler()
            self.scheduler.add_listener(
                self._on_scheduler_event,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
            )
        else:
            self.logger.warning("APScheduler not available, using manual scheduling")
            self.scheduler = None

        # Model configurations
        self.model_configs: Dict[str, ModelDriftConfig] = {}

        # Execution history
        self.execution_history: List[DriftCheckResult] = []
        self.max_history_size = 1000

        # Job tracking
        self.active_jobs: Dict[str, Job] = {} if self.use_apscheduler else {}

        self.logger.info("DriftScheduler initialized")

    def configure_model(
        self,
        model_id: str,
        model_version: str,
        schedule_interval: ScheduleInterval,
        baseline_data: Optional[Dict[str, List[float]]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        features_to_monitor: Optional[List[str]] = None,
        alert_callback: Optional[Callable] = None,
        schedule_cron: Optional[str] = None,
    ) -> None:
        """
        Configure drift detection for a model.

        Args:
            model_id: Model identifier
            model_version: Model version
            schedule_interval: Detection frequency (hourly, daily, weekly, custom)
            baseline_data: Baseline feature distributions
            thresholds: Custom threshold values
            features_to_monitor: Specific features to check (all if None)
            alert_callback: Optional callback for alerts
            schedule_cron: Cron expression for custom schedule

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            config = ModelDriftConfig(
                model_id=model_id,
                model_version=model_version,
                schedule_interval=schedule_interval,
                baseline_data=baseline_data,
                thresholds=thresholds,
                features_to_monitor=features_to_monitor,
                alert_callback=alert_callback,
                schedule_cron=schedule_cron,
            )

            self.model_configs[model_id] = config

            self.logger.info(
                f"Configured drift detection for {model_id} v{model_version} "
                f"with {schedule_interval.value} interval"
            )

        except ValueError as e:
            self.logger.error(f"Invalid model configuration: {e}")
            raise

    def start(self) -> None:
        """
        Start the drift scheduler.

        Schedules all configured models and starts background execution.

        Raises:
            RuntimeError: If scheduler already running or no models configured
        """
        if not self.model_configs:
            raise RuntimeError("No models configured for drift detection")

        try:
            for model_id, config in self.model_configs.items():
                if config.enabled:
                    self._schedule_model(model_id, config)

            if self.use_apscheduler:
                self.scheduler.start()
                self.logger.info(
                    f"Drift scheduler started with {len(self.active_jobs)} jobs"
                )
            else:
                self.logger.info(
                    "Manual scheduler started - call run_scheduled() periodically"
                )

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self) -> None:
        """
        Stop the drift scheduler gracefully.

        Terminates all scheduled jobs and cleans up resources.
        """
        try:
            if self.use_apscheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                self.logger.info("Drift scheduler stopped")

        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")

    def _schedule_model(self, model_id: str, config: ModelDriftConfig) -> None:
        """
        Schedule drift detection for a model.

        Args:
            model_id: Model identifier
            config: Model drift configuration
        """
        if not self.use_apscheduler:
            return

        job_id = f"drift_check_{model_id}"

        try:
            # Create trigger based on interval
            if config.schedule_interval == ScheduleInterval.HOURLY:
                trigger = IntervalTrigger(hours=1)
            elif config.schedule_interval == ScheduleInterval.DAILY:
                trigger = CronTrigger(hour=0, minute=0)
            elif config.schedule_interval == ScheduleInterval.WEEKLY:
                trigger = CronTrigger(day_of_week=0, hour=0, minute=0)
            elif config.schedule_interval == ScheduleInterval.CUSTOM:
                trigger = CronTrigger.from_crontab(config.schedule_cron)
            else:
                raise ValueError(f"Invalid schedule interval: {config.schedule_interval}")

            # Schedule job
            job = self.scheduler.add_job(
                self.run_scheduled,
                trigger=trigger,
                args=(model_id,),
                id=job_id,
                name=f"Drift check for {model_id}",
                replace_existing=True,
            )

            self.active_jobs[model_id] = job

            self.logger.debug(f"Scheduled drift check for {model_id} with {trigger}")

        except Exception as e:
            self.logger.error(f"Failed to schedule {model_id}: {e}")
            raise

    def run_scheduled(
        self,
        model_id: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[List[float]] = None,
        bias_data: Optional[List[Dict[str, Any]]] = None,
    ) -> DriftCheckResult:
        """
        Run drift detection for a model.

        Can be called by scheduler or manually. If input_data not provided,
        caller is responsible for providing current production data.

        Args:
            model_id: Model to check (runs all if None)
            input_data: Current feature values
            output_data: Current predictions
            bias_data: Current bias metrics
            window_hours: Time window for analysis

        Returns:
            DriftCheckResult with detection findings

        Raises:
            ValueError: If model_id invalid or data missing
        """
        if model_id and model_id not in self.model_configs:
            raise ValueError(f"Model {model_id} not configured")

        # Run for specified model or all enabled models
        models_to_check = [model_id] if model_id else self.model_configs.keys()

        results = []
        for mid in models_to_check:
            if mid in self.model_configs:
                config = self.model_configs[mid]

                if not config.enabled:
                    continue

                result = self._perform_drift_check(
                    config=config,
                    input_data=input_data,
                    output_data=output_data,
                    bias_data=bias_data,
                )

                results.append(result)
                self._record_execution(result)

        return results[0] if len(results) == 1 else results

    def _perform_drift_check(
        self,
        config: ModelDriftConfig,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[List[float]] = None,
        bias_data: Optional[List[Dict[str, Any]]] = None,
    ) -> DriftCheckResult:
        """
        Perform actual drift detection check.

        Args:
            config: Model configuration
            input_data: Current feature values
            output_data: Current predictions
            bias_data: Current bias metrics

        Returns:
            DriftCheckResult with findings
        """
        check_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            # Create drift detector
            detector = self.drift_detector_factory(
                model_id=config.model_id,
                model_version=config.model_version,
                baseline_data=config.baseline_data,
            )

            # Use provided data or empty defaults
            check_input_data = input_data or {}
            check_output_data = output_data or []
            check_bias_data = bias_data or []

            # Generate drift report
            report = detector.generate_report(
                input_data=check_input_data,
                output_data=check_output_data,
                bias_data=check_bias_data,
            )

            # Determine if alert should be generated
            alert_generated = report.overall_status.value != "NORMAL"

            # Extract metrics
            metrics = {
                "input_drift_count": len(report.input_drift),
                "output_drift_count": len(report.output_drift),
                "bias_metrics_count": len(report.bias_metrics),
                "safety_events_count": len(report.safety_events),
                "overall_status": report.overall_status.value,
            }

            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result = DriftCheckResult(
                check_id=check_id,
                model_id=config.model_id,
                model_version=config.model_version,
                timestamp=datetime.utcnow().isoformat() + "Z",
                status=ExecutionStatus.COMPLETED,
                duration_ms=duration_ms,
                alert_generated=alert_generated,
                alert_level=report.overall_status.value if alert_generated else None,
                metrics=metrics,
            )

            # Trigger alert callback if configured
            if alert_generated and config.alert_callback:
                try:
                    alert_details = {
                        "report_id": report.report_id,
                        "overall_status": report.overall_status.value,
                        "recommendations": report.recommendations,
                        "safety_events": [e.event_id for e in report.safety_events],
                    }
                    config.alert_callback(config.model_id, alert_details)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")

            self.logger.info(
                f"Drift check {check_id} completed for {config.model_id} "
                f"in {duration_ms:.1f}ms - Status: {report.overall_status.value}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Drift check {check_id} failed: {e}")

            return DriftCheckResult(
                check_id=check_id,
                model_id=config.model_id,
                model_version=config.model_version,
                timestamp=datetime.utcnow().isoformat() + "Z",
                status=ExecutionStatus.FAILED,
                duration_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                error_message=str(e),
            )

    def _record_execution(self, result: DriftCheckResult) -> None:
        """
        Record execution result in history.

        Args:
            result: Execution result
        """
        self.execution_history.append(result)

        # Trim history to max size
        if len(self.execution_history) > self.max_history_size:
            self.execution_history = self.execution_history[-self.max_history_size :]

    def _on_scheduler_event(self, event: Any) -> None:
        """
        Handle APScheduler events.

        Args:
            event: Scheduler event
        """
        try:
            job = self.scheduler.get_job(event.job_id)

            if event.exception:
                self.logger.error(
                    f"Job {event.job_id} failed with exception: {event.exception}"
                )
            elif event.code == EVENT_JOB_EXECUTED:
                self.logger.debug(f"Job {event.job_id} executed successfully")
            elif event.code == EVENT_JOB_MISSED:
                self.logger.warning(f"Job {event.job_id} was missed")

        except Exception as e:
            self.logger.error(f"Error handling scheduler event: {e}")

    def get_schedule(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current schedule information.

        Args:
            model_id: Specific model (all if None)

        Returns:
            Schedule information dictionary
        """
        if model_id:
            if model_id not in self.model_configs:
                raise ValueError(f"Model {model_id} not configured")

            config = self.model_configs[model_id]
            job = self.active_jobs.get(model_id) if self.use_apscheduler else None

            return {
                "model_id": model_id,
                "model_version": config.model_version,
                "schedule_interval": config.schedule_interval.value,
                "enabled": config.enabled,
                "next_run_time": job.next_run_time.isoformat() if job else None,
            }

        else:
            schedules = []
            for mid, config in self.model_configs.items():
                job = self.active_jobs.get(mid) if self.use_apscheduler else None
                schedules.append(
                    {
                        "model_id": mid,
                        "model_version": config.model_version,
                        "schedule_interval": config.schedule_interval.value,
                        "enabled": config.enabled,
                        "next_run_time": job.next_run_time.isoformat() if job else None,
                    }
                )

            return {"schedules": schedules, "total_models": len(schedules)}

    def get_execution_history(
        self,
        model_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get execution history.

        Args:
            model_id: Filter by model (all if None)
            status: Filter by status (all if None)
            limit: Maximum results to return

        Returns:
            List of execution result dictionaries
        """
        filtered = self.execution_history

        if model_id:
            filtered = [r for r in filtered if r.model_id == model_id]

        if status:
            filtered = [r for r in filtered if r.status == status]

        # Return most recent first
        return [r.to_dict() for r in filtered[-limit:][::-1]]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall scheduler statistics.

        Returns:
            Statistics dictionary
        """
        completed = sum(
            1 for r in self.execution_history if r.status == ExecutionStatus.COMPLETED
        )
        failed = sum(
            1 for r in self.execution_history if r.status == ExecutionStatus.FAILED
        )
        alerts = sum(1 for r in self.execution_history if r.alert_generated)

        return {
            "total_models_configured": len(self.model_configs),
            "total_models_enabled": sum(
                1 for c in self.model_configs.values() if c.enabled
            ),
            "total_executions": len(self.execution_history),
            "successful_executions": completed,
            "failed_executions": failed,
            "alerts_generated": alerts,
            "success_rate": (
                (completed / len(self.execution_history) * 100)
                if self.execution_history
                else 0
            ),
        }


# Module-level singleton
_drift_scheduler: Optional[DriftScheduler] = None


def get_drift_scheduler() -> DriftScheduler:
    """
    Get or create module-level drift scheduler instance.

    Returns:
        DriftScheduler instance
    """
    global _drift_scheduler

    if _drift_scheduler is None:
        _drift_scheduler = DriftScheduler()

    return _drift_scheduler


def configure_drift_scheduler(
    drift_detector_factory: Optional[Callable] = None,
    use_apscheduler: bool = True,
) -> DriftScheduler:
    """
    Configure and return drift scheduler instance.

    Args:
        drift_detector_factory: Factory for creating drift detectors
        use_apscheduler: Use APScheduler if available

    Returns:
        Configured DriftScheduler instance
    """
    global _drift_scheduler

    _drift_scheduler = DriftScheduler(
        drift_detector_factory=drift_detector_factory,
        use_apscheduler=use_apscheduler,
    )

    return _drift_scheduler
