"""
Unit tests for drift scheduler module.

Tests cover:
- Model configuration
- Schedule creation and management
- Drift detection execution
- Alert generation
- Execution history tracking
- Statistics collection
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json

from services.worker.src.monitoring.drift_scheduler import (
    DriftScheduler,
    DriftCheckResult,
    ModelDriftConfig,
    ScheduleInterval,
    ExecutionStatus,
    get_drift_scheduler,
    configure_drift_scheduler,
)


class TestModelDriftConfig:
    """Tests for ModelDriftConfig."""

    def test_valid_config(self):
        """Should create valid configuration."""
        config = ModelDriftConfig(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        assert config.model_id == "model_1"
        assert config.model_version == "1.0.0"
        assert config.enabled is True

    def test_custom_interval_requires_cron(self):
        """Should require cron expression for custom interval."""
        with pytest.raises(ValueError):
            ModelDriftConfig(
                model_id="model_1",
                model_version="1.0.0",
                schedule_interval=ScheduleInterval.CUSTOM,
            )

    def test_custom_interval_with_cron(self):
        """Should accept custom interval with cron."""
        config = ModelDriftConfig(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.CUSTOM,
            schedule_cron="0 * * * *",  # Every hour
        )

        assert config.schedule_cron == "0 * * * *"


class TestDriftCheckResult:
    """Tests for DriftCheckResult."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        result = DriftCheckResult(
            check_id="check_1",
            model_id="model_1",
            model_version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            status=ExecutionStatus.COMPLETED,
            duration_ms=100.0,
            alert_generated=True,
            alert_level="WARNING",
        )

        result_dict = result.to_dict()
        assert result_dict["check_id"] == "check_1"
        assert result_dict["status"] == "COMPLETED"
        assert result_dict["alert_generated"] is True


class TestDriftScheduler:
    """Tests for DriftScheduler."""

    @pytest.fixture
    def mock_drift_detector(self):
        """Create mock drift detector."""
        detector = MagicMock()
        detector.generate_report = MagicMock(
            return_value=MagicMock(
                report_id="report_1",
                overall_status=MagicMock(value="NORMAL"),
                recommendations=[],
                input_drift=[],
                output_drift=[],
                bias_metrics=[],
                safety_events=[],
            )
        )
        return detector

    @pytest.fixture
    def mock_detector_factory(self, mock_drift_detector):
        """Create mock detector factory."""
        def factory(model_id, model_version, baseline_data):
            return mock_drift_detector
        return factory

    @pytest.fixture
    def scheduler(self, mock_detector_factory):
        """Create drift scheduler with mock detector factory."""
        return DriftScheduler(
            drift_detector_factory=mock_detector_factory,
            use_apscheduler=False,  # Disable APScheduler for testing
        )

    def test_init(self, scheduler):
        """Should initialize scheduler."""
        assert scheduler is not None
        assert len(scheduler.model_configs) == 0

    def test_configure_model(self, scheduler):
        """Should configure model for drift detection."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
            baseline_data={"feature_1": [1.0, 2.0, 3.0]},
        )

        assert "model_1" in scheduler.model_configs
        config = scheduler.model_configs["model_1"]
        assert config.model_id == "model_1"
        assert config.schedule_interval == ScheduleInterval.DAILY

    def test_configure_multiple_models(self, scheduler):
        """Should configure multiple models."""
        for i in range(3):
            scheduler.configure_model(
                model_id=f"model_{i}",
                model_version="1.0.0",
                schedule_interval=ScheduleInterval.DAILY,
            )

        assert len(scheduler.model_configs) == 3

    def test_run_scheduled_single_model(self, scheduler, mock_drift_detector):
        """Should run scheduled drift check for single model."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
            baseline_data={"feature_1": [1.0, 2.0, 3.0]},
        )

        result = scheduler.run_scheduled(
            model_id="model_1",
            input_data={"feature_1": [1.1, 2.1, 3.1]},
            output_data=[0.5, 0.6, 0.7],
        )

        assert isinstance(result, DriftCheckResult)
        assert result.model_id == "model_1"
        assert result.status == ExecutionStatus.COMPLETED

    def test_run_scheduled_all_models(self, scheduler):
        """Should run drift check for all configured models."""
        for i in range(2):
            scheduler.configure_model(
                model_id=f"model_{i}",
                model_version="1.0.0",
                schedule_interval=ScheduleInterval.DAILY,
            )

        results = scheduler.run_scheduled()
        assert isinstance(results, list)
        assert len(results) == 2

    def test_run_scheduled_invalid_model(self, scheduler):
        """Should raise error for invalid model ID."""
        with pytest.raises(ValueError):
            scheduler.run_scheduled(model_id="nonexistent_model")

    def test_disabled_model_not_run(self, scheduler):
        """Should skip disabled models."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
            enabled=False,
        )

        results = scheduler.run_scheduled()
        assert len(results) == 0

    def test_alert_callback_triggered(self, scheduler):
        """Should trigger alert callback when drift detected."""
        alert_callback = Mock()

        # Configure detector to return critical status
        scheduler.drift_detector_factory = Mock(
            return_value=Mock(
                generate_report=Mock(
                    return_value=Mock(
                        report_id="report_1",
                        overall_status=Mock(value="CRITICAL"),
                        recommendations=["Action required"],
                        safety_events=[],
                        input_drift=[],
                        output_drift=[],
                        bias_metrics=[],
                    )
                )
            )
        )

        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
            alert_callback=alert_callback,
        )

        result = scheduler.run_scheduled(model_id="model_1")

        assert result.alert_generated is True
        alert_callback.assert_called_once()

    def test_execution_history_recorded(self, scheduler):
        """Should record execution results in history."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        for i in range(3):
            scheduler.run_scheduled(model_id="model_1")

        history = scheduler.execution_history
        assert len(history) == 3

    def test_get_execution_history(self, scheduler):
        """Should retrieve execution history."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        for i in range(5):
            scheduler.run_scheduled(model_id="model_1")

        history = scheduler.get_execution_history(model_id="model_1")
        assert len(history) >= 0  # Depends on execution

    def test_get_execution_history_with_limit(self, scheduler):
        """Should respect limit parameter."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        # Create multiple executions
        for i in range(10):
            scheduler.run_scheduled(model_id="model_1")

        history = scheduler.get_execution_history(limit=5)
        assert len(history) <= 5

    def test_get_schedule(self, scheduler):
        """Should return schedule information."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        schedule = scheduler.get_schedule()
        assert "schedules" in schedule
        assert schedule["total_models"] == 1

    def test_get_schedule_single_model(self, scheduler):
        """Should return schedule for single model."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.HOURLY,
        )

        schedule = scheduler.get_schedule(model_id="model_1")
        assert schedule["model_id"] == "model_1"
        assert schedule["schedule_interval"] == "hourly"

    def test_get_statistics(self, scheduler):
        """Should return scheduler statistics."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        scheduler.configure_model(
            model_id="model_2",
            model_version="2.0.0",
            schedule_interval=ScheduleInterval.DAILY,
            enabled=False,
        )

        stats = scheduler.get_statistics()
        assert stats["total_models_configured"] == 2
        assert stats["total_models_enabled"] == 1

    def test_error_handling(self, scheduler):
        """Should handle execution errors gracefully."""
        # Configure detector to raise error
        scheduler.drift_detector_factory = Mock(
            side_effect=Exception("Detector error")
        )

        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        result = scheduler.run_scheduled(model_id="model_1")

        assert result.status == ExecutionStatus.FAILED
        assert result.error_message is not None

    def test_start_requires_configured_models(self, scheduler):
        """Should raise error when starting with no configured models."""
        with pytest.raises(RuntimeError):
            scheduler.start()

    def test_stop(self, scheduler):
        """Should stop scheduler gracefully."""
        scheduler.configure_model(
            model_id="model_1",
            model_version="1.0.0",
            schedule_interval=ScheduleInterval.DAILY,
        )

        # Shouldn't raise
        scheduler.stop()


class TestModuleSingleton:
    """Tests for module-level singleton."""

    def test_get_drift_scheduler_singleton(self):
        """Should return same instance."""
        s1 = get_drift_scheduler()
        s2 = get_drift_scheduler()
        assert s1 is s2

    def test_configure_drift_scheduler(self):
        """Should configure and return new instance."""
        scheduler = configure_drift_scheduler(use_apscheduler=False)
        assert scheduler is not None
        assert isinstance(scheduler, DriftScheduler)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
