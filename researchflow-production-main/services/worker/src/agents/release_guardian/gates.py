"""
Release Gates - Pre-deployment validation checks

Implements individual gate checks that must pass before deployment.
Each gate represents a specific validation requirement in the release process.

Linear Issue: ROS-150
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Gate Result Type
# =============================================================================

@dataclass
class GateResult:
    """Result of a gate check."""
    gate_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "gate_name": self.gate_name,
            "passed": self.passed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "remediation": self.remediation,
        }


# =============================================================================
# Base Gate Class
# =============================================================================

class Gate(ABC):
    """Abstract base class for release gates."""

    def __init__(self, name: str, description: str, required: bool = True):
        """
        Initialize a gate.

        Args:
            name: Gate identifier
            description: Human-readable description
            required: Whether this gate must pass
        """
        self.name = name
        self.description = description
        self.required = required

    @abstractmethod
    async def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check if gate requirements are met.

        Args:
            context: Release context containing deployment info

        Returns:
            GateResult indicating pass/fail status
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, required={self.required})"


# =============================================================================
# Gate Implementations
# =============================================================================

class CIStatusGate(Gate):
    """Gate: Verify all CI checks pass."""

    def __init__(self):
        super().__init__(
            name="CI_STATUS_CHECK",
            description="Verify all GitHub Actions CI checks pass",
            required=True,
        )

    async def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check CI status via GitHub.

        Expected context keys:
        - github_token: GitHub API token
        - repo_owner: Repository owner
        - repo_name: Repository name
        - branch: Branch to check (default: main)
        - commit_sha: Specific commit to check (optional)
        """
        try:
            from .validators import GitHubCIValidator

            validator = GitHubCIValidator()
            ci_checks = await validator.check_ci_status(
                token=context.get("github_token"),
                owner=context.get("repo_owner"),
                repo=context.get("repo_name"),
                branch=context.get("branch", "main"),
                commit=context.get("commit_sha"),
            )

            if not ci_checks:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="No CI checks found",
                    details={"reason": "No checks to validate"},
                    remediation="Ensure CI workflow is configured and triggered",
                )

            # Check if all required checks passed
            failed_checks = [c for c in ci_checks if not c.get("passed", False)]

            if failed_checks:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message=f"{len(failed_checks)} CI check(s) failed",
                    details={
                        "failed_checks": failed_checks,
                        "total_checks": len(ci_checks),
                    },
                    remediation="Fix failing CI checks before attempting deployment",
                )

            return GateResult(
                gate_name=self.name,
                passed=True,
                message=f"All {len(ci_checks)} CI checks passed",
                details={
                    "passed_checks": ci_checks,
                    "total_checks": len(ci_checks),
                },
            )

        except Exception as e:
            logger.error(f"CI status gate error: {e}")
            return GateResult(
                gate_name=self.name,
                passed=False,
                message=f"CI status check failed: {str(e)}",
                details={"error": str(e)},
                remediation="Verify GitHub token and repository configuration",
            )


class EvidencePackGate(Gate):
    """Gate: Verify evidence pack exists and is hashed."""

    def __init__(self):
        super().__init__(
            name="EVIDENCE_PACK_CHECK",
            description="Verify evidence pack exists with computed hash",
            required=True,
        )

    async def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check evidence pack existence and hash.

        Expected context keys:
        - evidence_pack_path: Path to evidence pack directory/file
        - expected_hash: Expected SHA256 hash (optional)
        """
        try:
            from .validators import EvidenceHashValidator

            validator = EvidenceHashValidator()
            evidence_pack_path = context.get("evidence_pack_path")

            if not evidence_pack_path:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="No evidence pack path provided",
                    details={"reason": "Missing context"},
                    remediation="Provide evidence_pack_path in release context",
                )

            pack_info = await validator.verify_and_hash_pack(evidence_pack_path)

            if not pack_info.get("exists"):
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Evidence pack not found",
                    details={"path": evidence_pack_path},
                    remediation="Generate evidence pack before deployment",
                )

            # Verify hash if expected hash is provided
            expected_hash = context.get("expected_hash")
            if expected_hash and pack_info.get("hash") != expected_hash:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Evidence pack hash mismatch",
                    details={
                        "expected": expected_hash,
                        "actual": pack_info.get("hash"),
                    },
                    remediation="Ensure evidence pack matches expected version",
                )

            return GateResult(
                gate_name=self.name,
                passed=True,
                message="Evidence pack verified",
                details={
                    "path": evidence_pack_path,
                    "hash": pack_info.get("hash"),
                    "size_bytes": pack_info.get("size"),
                },
            )

        except Exception as e:
            logger.error(f"Evidence pack gate error: {e}")
            return GateResult(
                gate_name=self.name,
                passed=False,
                message=f"Evidence pack check failed: {str(e)}",
                details={"error": str(e)},
                remediation="Verify evidence pack is accessible and valid",
            )


class FAVESGate(Gate):
    """Gate: Verify FAVES compliance (for LIVE deployments only)."""

    def __init__(self):
        super().__init__(
            name="FAVES_COMPLIANCE_CHECK",
            description="Verify FAVES compliance gate for LIVE deployments",
            required=False,  # Only required for LIVE mode
        )

    async def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check FAVES compliance.

        Expected context keys:
        - deployment_mode: 'DEMO' or 'LIVE'
        - faves_assessment: FAVES assessment document/record
        - faves_date: Date of FAVES assessment
        """
        try:
            from .validators import DeploymentModeValidator

            deployment_mode = context.get("deployment_mode", "DEMO")

            # Skip check if not LIVE deployment
            if deployment_mode.upper() != "LIVE":
                return GateResult(
                    gate_name=self.name,
                    passed=True,
                    message="FAVES check skipped (DEMO mode)",
                    details={"deployment_mode": deployment_mode},
                )

            # LIVE mode requires FAVES assessment
            faves_assessment = context.get("faves_assessment")
            if not faves_assessment:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="FAVES assessment required for LIVE deployment",
                    details={"deployment_mode": "LIVE"},
                    remediation="Complete FAVES assessment and provide documentation",
                )

            # Verify assessment has required fields
            required_fields = ["assessment_date", "risk_level", "approval_status"]
            missing_fields = [
                f for f in required_fields if f not in faves_assessment
            ]

            if missing_fields:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="FAVES assessment incomplete",
                    details={"missing_fields": missing_fields},
                    remediation="Complete all required FAVES assessment fields",
                )

            # Check approval status
            approval_status = faves_assessment.get("approval_status", "").upper()
            if approval_status != "APPROVED":
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message=f"FAVES not approved (status: {approval_status})",
                    details={"approval_status": approval_status},
                    remediation="Obtain FAVES approval before LIVE deployment",
                )

            return GateResult(
                gate_name=self.name,
                passed=True,
                message="FAVES compliance verified",
                details={
                    "deployment_mode": "LIVE",
                    "risk_level": faves_assessment.get("risk_level"),
                    "assessment_date": faves_assessment.get("assessment_date"),
                    "approval_status": approval_status,
                },
            )

        except Exception as e:
            logger.error(f"FAVES gate error: {e}")
            return GateResult(
                gate_name=self.name,
                passed=False,
                message=f"FAVES check failed: {str(e)}",
                details={"error": str(e)},
                remediation="Verify FAVES documentation and context",
            )


class RollbackGate(Gate):
    """Gate: Verify rollback plan is documented."""

    def __init__(self):
        super().__init__(
            name="ROLLBACK_PLAN_CHECK",
            description="Verify rollback plan is documented and tested",
            required=True,
        )

    async def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check rollback plan existence and completeness.

        Expected context keys:
        - rollback_plan: Rollback plan document
        - rollback_tested: Whether plan has been tested
        - rollback_duration_minutes: Expected rollback time
        """
        try:
            rollback_plan = context.get("rollback_plan")

            if not rollback_plan:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="No rollback plan provided",
                    details={"reason": "Missing context"},
                    remediation="Create and document a rollback plan before deployment",
                )

            # Check required rollback plan fields
            required_fields = ["steps", "estimated_duration_minutes", "contact"]
            missing_fields = [
                f for f in required_fields if f not in rollback_plan
            ]

            if missing_fields:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Rollback plan incomplete",
                    details={"missing_fields": missing_fields},
                    remediation="Complete all required rollback plan fields",
                )

            # Check if plan has been tested
            tested = context.get("rollback_tested", False)

            details = {
                "steps": len(rollback_plan.get("steps", [])),
                "duration_minutes": rollback_plan.get("estimated_duration_minutes"),
                "contact": rollback_plan.get("contact"),
                "tested": tested,
            }

            if not tested:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Rollback plan not tested",
                    details=details,
                    remediation="Test rollback plan before production deployment",
                )

            return GateResult(
                gate_name=self.name,
                passed=True,
                message="Rollback plan verified",
                details=details,
            )

        except Exception as e:
            logger.error(f"Rollback gate error: {e}")
            return GateResult(
                gate_name=self.name,
                passed=False,
                message=f"Rollback check failed: {str(e)}",
                details={"error": str(e)},
                remediation="Verify rollback plan structure and format",
            )


class MonitoringGate(Gate):
    """Gate: Verify monitoring dashboard is configured."""

    def __init__(self):
        super().__init__(
            name="MONITORING_CONFIG_CHECK",
            description="Verify monitoring dashboard is configured for deployment",
            required=True,
        )

    async def check(self, context: Dict[str, Any]) -> GateResult:
        """
        Check monitoring configuration.

        Expected context keys:
        - monitoring_dashboard_url: URL to monitoring dashboard
        - alerting_rules: Alert rules configuration
        - metrics_configured: List of configured metrics
        """
        try:
            dashboard_url = context.get("monitoring_dashboard_url")
            alerting_rules = context.get("alerting_rules", {})
            metrics = context.get("metrics_configured", [])

            if not dashboard_url:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Monitoring dashboard URL not configured",
                    details={},
                    remediation="Configure monitoring dashboard URL before deployment",
                )

            # Check for required alerting rules
            required_alerts = [
                "error_rate",
                "latency_p99",
                "memory_usage",
                "database_connection_pool",
            ]
            missing_alerts = [a for a in required_alerts if a not in alerting_rules]

            if missing_alerts:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Missing required alerting rules",
                    details={"missing_alerts": missing_alerts},
                    remediation="Configure all required alerting rules",
                )

            # Check for minimum required metrics
            required_metrics = ["cpu_usage", "memory_usage", "error_rate", "latency"]
            missing_metrics = [m for m in required_metrics if m not in metrics]

            if missing_metrics:
                return GateResult(
                    gate_name=self.name,
                    passed=False,
                    message="Missing required metrics",
                    details={"missing_metrics": missing_metrics},
                    remediation="Enable all required metrics in monitoring dashboard",
                )

            return GateResult(
                gate_name=self.name,
                passed=True,
                message="Monitoring configured",
                details={
                    "dashboard_url": dashboard_url,
                    "alerting_rules": len(alerting_rules),
                    "metrics": len(metrics),
                    "missing_alerts": missing_alerts,
                },
            )

        except Exception as e:
            logger.error(f"Monitoring gate error: {e}")
            return GateResult(
                gate_name=self.name,
                passed=False,
                message=f"Monitoring check failed: {str(e)}",
                details={"error": str(e)},
                remediation="Verify monitoring configuration and context",
            )
