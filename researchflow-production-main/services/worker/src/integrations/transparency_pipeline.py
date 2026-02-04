"""
ResearchFlow Transparency Monitoring Pipeline
==============================================
End-to-end pipeline for AI model transparency monitoring, FAVES compliance,
and automated alerting via integrated tools (LangSmith, Composio, Linear, Slack).

Pipeline Flow:
1. Monitor model metrics (PSI, KL divergence, confidence scores)
2. Analyze drift using LangSmith transparency-monitor-agent
3. Validate FAVES compliance dimensions
4. Trigger alerts via Composio workflows (Linear, Slack, GitHub)
5. Generate evidence bundles for documentation
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from .orchestration_router import (
    OrchestrationRouter,
    TransparencyMonitorClient,
    ComposioWorkflowClient,
    get_router
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ComplianceStatus(Enum):
    """FAVES compliance status."""
    COMPLIANT = "compliant"
    REVIEW_REQUIRED = "review_required"
    NON_COMPLIANT = "non_compliant"


@dataclass
class DriftMetrics:
    """Model drift metrics."""
    model_id: str
    psi: float
    kl_divergence: float
    confidence_score: float
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class FAVESValidation:
    """FAVES compliance validation result."""
    fair: bool
    appropriate: bool
    valid: bool
    effective: bool
    safe: bool
    overall_status: ComplianceStatus = ComplianceStatus.COMPLIANT
    notes: List[str] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = []

        # Determine overall status
        dimensions = [self.fair, self.appropriate, self.valid, self.effective, self.safe]
        if all(dimensions):
            self.overall_status = ComplianceStatus.COMPLIANT
        elif not self.safe or sum(dimensions) < 3:
            self.overall_status = ComplianceStatus.NON_COMPLIANT
        else:
            self.overall_status = ComplianceStatus.REVIEW_REQUIRED


@dataclass
class TransparencyReport:
    """Complete transparency monitoring report."""
    model_id: str
    metrics: DriftMetrics
    faves_validation: FAVESValidation
    alerts_triggered: List[Dict[str, Any]]
    evidence_bundle_id: Optional[str]
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class TransparencyMonitoringPipeline:
    """
    Main transparency monitoring pipeline.

    Orchestrates the complete flow from metric collection to alerting
    and evidence bundle generation.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the pipeline with configuration."""
        self.router = get_router(config_path)
        self.transparency_client = TransparencyMonitorClient(self.router)
        self.workflow_client = ComposioWorkflowClient(self.router)

        # Get FAVES thresholds
        faves_config = self.router.get_faves_config()
        self.thresholds = faves_config.get("thresholds", {
            "psi": 0.2,
            "kl_divergence": 0.1,
            "confidence_minimum": 0.7
        })

        logger.info("TransparencyMonitoringPipeline initialized")

    def run(
        self,
        model_id: str,
        psi: float,
        kl_divergence: float,
        confidence_score: float,
        feature_distributions: Dict[str, Any] = None
    ) -> TransparencyReport:
        """
        Run the complete transparency monitoring pipeline.

        Args:
            model_id: Identifier for the model being monitored
            psi: Population Stability Index value
            kl_divergence: KL divergence value
            confidence_score: Model confidence score
            feature_distributions: Optional feature distribution data

        Returns:
            TransparencyReport with complete analysis and actions taken
        """
        logger.info(f"Running transparency pipeline for model: {model_id}")

        # Step 1: Collect metrics
        metrics = DriftMetrics(
            model_id=model_id,
            psi=psi,
            kl_divergence=kl_divergence,
            confidence_score=confidence_score
        )

        # Step 2: Analyze drift via LangSmith agent
        drift_analysis = self.transparency_client.analyze_drift(
            model_id=model_id,
            psi_value=psi,
            kl_divergence=kl_divergence,
            feature_distributions=feature_distributions or {}
        )

        # Step 3: Validate FAVES compliance
        faves_validation = self._validate_faves(metrics, drift_analysis)

        # Step 4: Determine if alerts needed
        alerts_triggered = []
        if faves_validation.overall_status != ComplianceStatus.COMPLIANT:
            alerts_triggered = self._trigger_alerts(model_id, metrics, faves_validation)

        # Step 5: Generate evidence bundle ID
        evidence_bundle_id = None
        if faves_validation.overall_status == ComplianceStatus.NON_COMPLIANT:
            evidence_bundle_id = self._generate_evidence_bundle(model_id, metrics, faves_validation)

        # Build final report
        report = TransparencyReport(
            model_id=model_id,
            metrics=metrics,
            faves_validation=faves_validation,
            alerts_triggered=alerts_triggered,
            evidence_bundle_id=evidence_bundle_id
        )

        logger.info(f"Pipeline complete for {model_id}: status={faves_validation.overall_status.value}")

        return report

    def _validate_faves(
        self,
        metrics: DriftMetrics,
        drift_analysis: Dict[str, Any]
    ) -> FAVESValidation:
        """Validate FAVES compliance dimensions."""
        notes = []

        # Fair: Check for bias indicators
        fair = drift_analysis.get("faves_dimensions", {}).get("fair", True)
        if not fair:
            notes.append("Fairness concern detected in feature distributions")

        # Appropriate: Context-dependent, default to True
        appropriate = True

        # Valid: PSI within acceptable range
        valid = metrics.psi < self.thresholds["psi"] * 1.25  # 25% margin
        if not valid:
            notes.append(f"PSI ({metrics.psi}) exceeds validity threshold")

        # Effective: KL divergence acceptable
        effective = metrics.kl_divergence < self.thresholds["kl_divergence"] * 1.5
        if not effective:
            notes.append(f"KL divergence ({metrics.kl_divergence}) indicates reduced effectiveness")

        # Safe: All critical thresholds met
        safe = (
            metrics.psi < self.thresholds["psi"] and
            metrics.confidence_score >= self.thresholds["confidence_minimum"]
        )
        if not safe:
            notes.append("Safety thresholds exceeded - immediate review required")

        return FAVESValidation(
            fair=fair,
            appropriate=appropriate,
            valid=valid,
            effective=effective,
            safe=safe,
            notes=notes
        )

    def _trigger_alerts(
        self,
        model_id: str,
        metrics: DriftMetrics,
        validation: FAVESValidation
    ) -> List[Dict[str, Any]]:
        """Trigger alerts via Composio workflow."""
        alerts = []

        # Determine severity
        severity = AlertSeverity.WARNING
        if validation.overall_status == ComplianceStatus.NON_COMPLIANT:
            severity = AlertSeverity.CRITICAL

        # Build alert message
        failed_dimensions = []
        if not validation.fair:
            failed_dimensions.append("Fair")
        if not validation.appropriate:
            failed_dimensions.append("Appropriate")
        if not validation.valid:
            failed_dimensions.append("Valid")
        if not validation.effective:
            failed_dimensions.append("Effective")
        if not validation.safe:
            failed_dimensions.append("Safe")

        issue_title = f"FAVES Compliance Alert: {model_id}"
        issue_description = f"""
## Model Drift Detected

**Model ID**: {model_id}
**Severity**: {severity.value.upper()}
**Timestamp**: {metrics.timestamp}

### Metrics
- PSI: {metrics.psi} (threshold: {self.thresholds['psi']})
- KL Divergence: {metrics.kl_divergence} (threshold: {self.thresholds['kl_divergence']})
- Confidence Score: {metrics.confidence_score}

### FAVES Compliance
- **Status**: {validation.overall_status.value}
- **Failed Dimensions**: {', '.join(failed_dimensions) if failed_dimensions else 'None'}

### Notes
{chr(10).join('- ' + note for note in validation.notes) if validation.notes else 'No additional notes'}

### Required Actions
1. Review model performance metrics
2. Investigate root cause of drift
3. Update FAVES compliance documentation
4. Consider model retraining if threshold consistently exceeded
"""

        # Trigger Composio workflow
        try:
            workflow_result = self.workflow_client.trigger_compliance_alert(
                issue_title=issue_title,
                issue_description=issue_description.strip(),
                labels=["compliance", "faves", severity.value],
                slack_channel="compliance-updates"
            )
            alerts.append(workflow_result)
            logger.info(f"Alert triggered for {model_id}: {issue_title}")

        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
            alerts.append({
                "status": "error",
                "error": str(e),
                "issue_title": issue_title
            })

        return alerts

    def _generate_evidence_bundle(
        self,
        model_id: str,
        metrics: DriftMetrics,
        validation: FAVESValidation
    ) -> str:
        """Generate evidence bundle ID for documentation."""
        # Generate unique bundle ID
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        bundle_id = f"EB-{model_id}-{timestamp}"

        logger.info(f"Evidence bundle generated: {bundle_id}")

        return bundle_id


class TransparencyMonitoringScheduler:
    """
    Scheduler for periodic transparency monitoring.
    """

    def __init__(self, pipeline: TransparencyMonitoringPipeline):
        self.pipeline = pipeline
        self.monitored_models: Dict[str, Dict[str, Any]] = {}

    def register_model(
        self,
        model_id: str,
        check_interval_minutes: int = 60,
        custom_thresholds: Dict[str, float] = None
    ):
        """Register a model for monitoring."""
        self.monitored_models[model_id] = {
            "interval": check_interval_minutes,
            "thresholds": custom_thresholds,
            "last_check": None,
            "status": "registered"
        }
        logger.info(f"Model {model_id} registered for monitoring")

    def check_all(self, metrics_provider: callable) -> List[TransparencyReport]:
        """
        Check all registered models.

        Args:
            metrics_provider: Callable that returns metrics for a model_id

        Returns:
            List of TransparencyReports
        """
        reports = []

        for model_id in self.monitored_models:
            try:
                # Get current metrics
                metrics = metrics_provider(model_id)

                # Run pipeline
                report = self.pipeline.run(
                    model_id=model_id,
                    psi=metrics.get("psi", 0),
                    kl_divergence=metrics.get("kl_divergence", 0),
                    confidence_score=metrics.get("confidence_score", 1.0),
                    feature_distributions=metrics.get("distributions")
                )

                reports.append(report)

                # Update tracking
                self.monitored_models[model_id]["last_check"] = datetime.utcnow().isoformat()
                self.monitored_models[model_id]["status"] = report.faves_validation.overall_status.value

            except Exception as e:
                logger.error(f"Error checking model {model_id}: {e}")

        return reports


# Convenience functions
def create_pipeline(config_path: Optional[str] = None) -> TransparencyMonitoringPipeline:
    """Create a configured transparency monitoring pipeline."""
    return TransparencyMonitoringPipeline(config_path)


def quick_check(
    model_id: str,
    psi: float,
    kl_divergence: float,
    confidence_score: float = 0.9
) -> Dict[str, Any]:
    """
    Quick transparency check for a model.

    Returns a simplified result dict.
    """
    pipeline = create_pipeline()
    report = pipeline.run(
        model_id=model_id,
        psi=psi,
        kl_divergence=kl_divergence,
        confidence_score=confidence_score
    )

    return {
        "model_id": model_id,
        "status": report.faves_validation.overall_status.value,
        "metrics": {
            "psi": psi,
            "kl_divergence": kl_divergence,
            "confidence": confidence_score
        },
        "alerts_count": len(report.alerts_triggered),
        "evidence_bundle": report.evidence_bundle_id,
        "timestamp": report.timestamp
    }


if __name__ == "__main__":
    # Example: Run pipeline for a model with concerning metrics
    pipeline = create_pipeline()

    # Simulate metrics that exceed threshold
    report = pipeline.run(
        model_id="diabetes-risk-v2.1",
        psi=0.25,  # Exceeds 0.2 threshold
        kl_divergence=0.08,
        confidence_score=0.75
    )

    print(f"\n=== Transparency Report ===")
    print(f"Model: {report.model_id}")
    print(f"Status: {report.faves_validation.overall_status.value}")
    print(f"FAVES Dimensions:")
    print(f"  - Fair: {report.faves_validation.fair}")
    print(f"  - Appropriate: {report.faves_validation.appropriate}")
    print(f"  - Valid: {report.faves_validation.valid}")
    print(f"  - Effective: {report.faves_validation.effective}")
    print(f"  - Safe: {report.faves_validation.safe}")
    print(f"Alerts Triggered: {len(report.alerts_triggered)}")
    if report.evidence_bundle_id:
        print(f"Evidence Bundle: {report.evidence_bundle_id}")
