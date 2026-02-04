"""
FAVES Compliance Evaluator
Fair, Appropriate, Valid, Effective, Safe evaluation for AI models.

Phase 10 Implementation - ResearchFlow Transparency Execution Plan
"""

import json
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid


class FAVESDimension(str, Enum):
    """FAVES dimensions."""
    FAIR = "FAIR"
    APPROPRIATE = "APPROPRIATE"
    VALID = "VALID"
    EFFECTIVE = "EFFECTIVE"
    SAFE = "SAFE"


class FAVESStatus(str, Enum):
    """FAVES evaluation status."""
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass
class MetricResult:
    """Individual metric evaluation result."""
    metric_name: str
    value: float
    threshold: float
    passed: bool
    unit: str = ""
    description: str = ""


@dataclass
class ArtifactCheck:
    """Artifact existence check."""
    name: str
    path: str
    required: bool
    exists: bool
    last_modified: Optional[str] = None


@dataclass
class DimensionResult:
    """Result for single FAVES dimension."""
    dimension: FAVESDimension
    status: FAVESStatus
    score: float
    passed: bool
    metrics: List[MetricResult]
    required_artifacts: List[ArtifactCheck]
    missing_requirements: List[str]
    recommendations: List[str] = field(default_factory=list)


@dataclass
class FAVESResult:
    """Complete FAVES evaluation result."""
    evaluation_id: str
    model_id: str
    model_version: str
    evaluated_at: str
    evaluated_by: str
    overall_status: FAVESStatus
    overall_score: float
    deployment_allowed: bool
    dimensions: Dict[str, DimensionResult]
    total_metrics_passed: int
    total_metrics_failed: int
    total_artifacts_present: int
    total_artifacts_missing: int
    blocking_issues: List[str]
    schema_version: str = "1.0.0"
    ci_run_id: Optional[str] = None
    git_commit_sha: Optional[str] = None


class FAVESRequirements:
    """FAVES requirements matrix from execution plan."""

    # Minimum thresholds for passing
    THRESHOLDS = {
        FAVESDimension.FAIR: {
            "demographic_parity_gap": 0.1,
            "min_subgroup_auc": 0.7,
            "equalized_odds_diff": 0.1,
        },
        FAVESDimension.APPROPRIATE: {
            "intended_use_coverage": 0.9,
            "workflow_fit_score": 0.8,
        },
        FAVESDimension.VALID: {
            "calibration_error": 0.1,
            "brier_score": 0.25,
            "external_validation_auc": 0.7,
        },
        FAVESDimension.EFFECTIVE: {
            "net_benefit_positive": 0.0,
            "decision_curve_improvement": 0.0,
        },
        FAVESDimension.SAFE: {
            "max_error_rate": 0.05,
            "failure_mode_coverage": 0.9,
            "human_override_availability": 1.0,
        },
    }

    # Required artifacts per dimension
    ARTIFACTS = {
        FAVESDimension.FAIR: [
            ("representativeness_report.json", True),
            ("fairness_analysis.md", True),
            ("bias_audit.md", False),
        ],
        FAVESDimension.APPROPRIATE: [
            ("intended_use.md", True),
            ("out_of_scope.md", True),
            ("workflow_integration.md", True),
        ],
        FAVESDimension.VALID: [
            ("calibration_report.json", True),
            ("external_validation.md", True),
            ("internal_validation.md", False),
        ],
        FAVESDimension.EFFECTIVE: [
            ("utility_analysis.md", True),
            ("actionability_doc.md", True),
            ("decision_curve.json", False),
        ],
        FAVESDimension.SAFE: [
            ("error_analysis.md", True),
            ("rollback_policy.md", True),
            ("monitoring_plan.md", True),
            ("human_oversight.md", False),
        ],
    }

    # Required metrics per dimension
    METRICS = {
        FAVESDimension.FAIR: [
            "stratified_auc",
            "stratified_sensitivity",
            "stratified_specificity",
            "demographic_parity",
            "equalized_odds",
        ],
        FAVESDimension.APPROPRIATE: [
            "intended_use_coverage_score",
            "workflow_fit_score",
        ],
        FAVESDimension.VALID: [
            "calibration_error",
            "brier_score",
            "external_validation_auc",
            "hosmer_lemeshow_pvalue",
        ],
        FAVESDimension.EFFECTIVE: [
            "decision_curve_auc",
            "net_benefit_at_threshold",
            "number_needed_to_treat",
        ],
        FAVESDimension.SAFE: [
            "overall_error_rate",
            "error_rate_by_subgroup",
            "failure_mode_coverage",
        ],
    }


class FAVESEvaluator:
    """
    FAVES compliance evaluator for AI models.

    Evaluates models against Fair, Appropriate, Valid, Effective, Safe criteria.
    """

    def __init__(
        self,
        model_id: str,
        model_version: str,
        artifacts_dir: str = "docs/faves",
        metrics_provider: Optional[Callable[[str], Dict[str, float]]] = None
    ):
        """
        Initialize FAVES evaluator.

        Args:
            model_id: UUID of the model
            model_version: Model version string
            artifacts_dir: Directory containing FAVES artifacts
            metrics_provider: Callable to fetch metrics by name
        """
        self.model_id = model_id
        self.model_version = model_version
        self.artifacts_dir = artifacts_dir
        self.metrics_provider = metrics_provider or self._default_metrics_provider
        self.requirements = FAVESRequirements()

    def _default_metrics_provider(self, metric_name: str) -> Optional[float]:
        """Default metrics provider returns None (metric not available)."""
        return None

    def _check_artifact(self, artifact_name: str, required: bool) -> ArtifactCheck:
        """Check if artifact exists."""
        path = os.path.join(self.artifacts_dir, artifact_name)
        exists = os.path.isfile(path)
        last_modified = None

        if exists:
            mtime = os.path.getmtime(path)
            last_modified = datetime.fromtimestamp(mtime).isoformat()

        return ArtifactCheck(
            name=artifact_name,
            path=path,
            required=required,
            exists=exists,
            last_modified=last_modified
        )

    def _evaluate_metric(
        self,
        metric_name: str,
        threshold_key: str,
        thresholds: Dict[str, float],
        higher_is_better: bool = True
    ) -> Optional[MetricResult]:
        """
        Evaluate single metric against threshold.

        Args:
            metric_name: Name of the metric
            threshold_key: Key in thresholds dict
            thresholds: Threshold values
            higher_is_better: Whether higher values are better

        Returns:
            MetricResult or None if metric unavailable
        """
        value = self.metrics_provider(metric_name)
        if value is None:
            return None

        threshold = thresholds.get(threshold_key, 0.0)

        if higher_is_better:
            passed = value >= threshold
        else:
            passed = value <= threshold

        return MetricResult(
            metric_name=metric_name,
            value=value,
            threshold=threshold,
            passed=passed,
            description=f"{'≥' if higher_is_better else '≤'} {threshold}"
        )

    def evaluate_fairness(self) -> DimensionResult:
        """Evaluate FAIR dimension."""
        dimension = FAVESDimension.FAIR
        thresholds = self.requirements.THRESHOLDS[dimension]
        metrics: List[MetricResult] = []
        missing = []
        recommendations = []

        # Check artifacts
        artifacts = [
            self._check_artifact(name, req)
            for name, req in self.requirements.ARTIFACTS[dimension]
        ]

        # Evaluate metrics
        # Demographic parity (lower is better)
        result = self._evaluate_metric(
            "demographic_parity_gap",
            "demographic_parity_gap",
            thresholds,
            higher_is_better=False
        )
        if result:
            metrics.append(result)
        else:
            missing.append("demographic_parity_gap metric not available")

        # Minimum subgroup AUC
        result = self._evaluate_metric(
            "min_subgroup_auc",
            "min_subgroup_auc",
            thresholds,
            higher_is_better=True
        )
        if result:
            metrics.append(result)
        else:
            missing.append("min_subgroup_auc metric not available")

        # Check required artifacts
        for art in artifacts:
            if art.required and not art.exists:
                missing.append(f"Required artifact missing: {art.name}")

        # Calculate score
        metrics_passed = sum(1 for m in metrics if m.passed)
        artifacts_present = sum(1 for a in artifacts if a.exists)
        required_artifacts = sum(1 for a in artifacts if a.required)

        if metrics and required_artifacts > 0:
            score = (
                (metrics_passed / len(metrics)) * 50 +
                (artifacts_present / len(artifacts)) * 50
            )
        else:
            score = 0.0

        passed = len(missing) == 0 and all(m.passed for m in metrics)

        # Recommendations
        if not passed:
            if any(not m.passed for m in metrics):
                recommendations.append("Review subgroup performance and address disparities")
            if any(not a.exists for a in artifacts if a.required):
                recommendations.append("Complete required fairness documentation")

        return DimensionResult(
            dimension=dimension,
            status=FAVESStatus.PASS if passed else FAVESStatus.FAIL,
            score=score,
            passed=passed,
            metrics=metrics,
            required_artifacts=artifacts,
            missing_requirements=missing,
            recommendations=recommendations
        )

    def evaluate_appropriateness(self) -> DimensionResult:
        """Evaluate APPROPRIATE dimension."""
        dimension = FAVESDimension.APPROPRIATE
        thresholds = self.requirements.THRESHOLDS[dimension]
        metrics: List[MetricResult] = []
        missing = []
        recommendations = []

        # Check artifacts
        artifacts = [
            self._check_artifact(name, req)
            for name, req in self.requirements.ARTIFACTS[dimension]
        ]

        # Evaluate metrics
        result = self._evaluate_metric(
            "intended_use_coverage_score",
            "intended_use_coverage",
            thresholds,
            higher_is_better=True
        )
        if result:
            metrics.append(result)
        else:
            missing.append("intended_use_coverage_score not evaluated")

        result = self._evaluate_metric(
            "workflow_fit_score",
            "workflow_fit_score",
            thresholds,
            higher_is_better=True
        )
        if result:
            metrics.append(result)
        else:
            missing.append("workflow_fit_score not evaluated")

        # Check required artifacts
        for art in artifacts:
            if art.required and not art.exists:
                missing.append(f"Required artifact missing: {art.name}")

        # Calculate score
        artifacts_present = sum(1 for a in artifacts if a.exists)
        score = (artifacts_present / len(artifacts)) * 100 if artifacts else 0.0

        passed = all(a.exists for a in artifacts if a.required)

        if not passed:
            recommendations.append("Complete intended use and workflow documentation")

        return DimensionResult(
            dimension=dimension,
            status=FAVESStatus.PASS if passed else FAVESStatus.FAIL,
            score=score,
            passed=passed,
            metrics=metrics,
            required_artifacts=artifacts,
            missing_requirements=missing,
            recommendations=recommendations
        )

    def evaluate_validity(self) -> DimensionResult:
        """Evaluate VALID dimension."""
        dimension = FAVESDimension.VALID
        thresholds = self.requirements.THRESHOLDS[dimension]
        metrics: List[MetricResult] = []
        missing = []
        recommendations = []

        # Check artifacts
        artifacts = [
            self._check_artifact(name, req)
            for name, req in self.requirements.ARTIFACTS[dimension]
        ]

        # Calibration error (lower is better)
        result = self._evaluate_metric(
            "calibration_error",
            "calibration_error",
            thresholds,
            higher_is_better=False
        )
        if result:
            metrics.append(result)
        else:
            missing.append("calibration_error not available")

        # Brier score (lower is better)
        result = self._evaluate_metric(
            "brier_score",
            "brier_score",
            thresholds,
            higher_is_better=False
        )
        if result:
            metrics.append(result)
        else:
            missing.append("brier_score not available")

        # External validation AUC
        result = self._evaluate_metric(
            "external_validation_auc",
            "external_validation_auc",
            thresholds,
            higher_is_better=True
        )
        if result:
            metrics.append(result)
        else:
            missing.append("external_validation_auc not available")

        # Check required artifacts
        for art in artifacts:
            if art.required and not art.exists:
                missing.append(f"Required artifact missing: {art.name}")

        # Calculate score
        metrics_passed = sum(1 for m in metrics if m.passed)
        artifacts_present = sum(1 for a in artifacts if a.exists)

        if metrics:
            score = (metrics_passed / len(metrics)) * 100
        else:
            score = 0.0

        passed = len(missing) == 0 and all(m.passed for m in metrics)

        if not passed:
            if any(not m.passed for m in metrics):
                recommendations.append("Improve model calibration and external validation")

        return DimensionResult(
            dimension=dimension,
            status=FAVESStatus.PASS if passed else FAVESStatus.FAIL,
            score=score,
            passed=passed,
            metrics=metrics,
            required_artifacts=artifacts,
            missing_requirements=missing,
            recommendations=recommendations
        )

    def evaluate_effectiveness(self) -> DimensionResult:
        """Evaluate EFFECTIVE dimension."""
        dimension = FAVESDimension.EFFECTIVE
        thresholds = self.requirements.THRESHOLDS[dimension]
        metrics: List[MetricResult] = []
        missing = []
        recommendations = []

        # Check artifacts
        artifacts = [
            self._check_artifact(name, req)
            for name, req in self.requirements.ARTIFACTS[dimension]
        ]

        # Net benefit (higher is better, but threshold is 0 = must be positive)
        result = self._evaluate_metric(
            "net_benefit_at_threshold",
            "net_benefit_positive",
            thresholds,
            higher_is_better=True
        )
        if result:
            metrics.append(result)
        else:
            missing.append("net_benefit_at_threshold not evaluated")

        # Check required artifacts
        for art in artifacts:
            if art.required and not art.exists:
                missing.append(f"Required artifact missing: {art.name}")

        # Calculate score
        artifacts_present = sum(1 for a in artifacts if a.exists)
        score = (artifacts_present / len(artifacts)) * 100 if artifacts else 0.0

        passed = all(a.exists for a in artifacts if a.required)

        if not passed:
            recommendations.append("Complete utility analysis and actionability documentation")

        return DimensionResult(
            dimension=dimension,
            status=FAVESStatus.PASS if passed else FAVESStatus.FAIL,
            score=score,
            passed=passed,
            metrics=metrics,
            required_artifacts=artifacts,
            missing_requirements=missing,
            recommendations=recommendations
        )

    def evaluate_safety(self) -> DimensionResult:
        """Evaluate SAFE dimension."""
        dimension = FAVESDimension.SAFE
        thresholds = self.requirements.THRESHOLDS[dimension]
        metrics: List[MetricResult] = []
        missing = []
        recommendations = []

        # Check artifacts
        artifacts = [
            self._check_artifact(name, req)
            for name, req in self.requirements.ARTIFACTS[dimension]
        ]

        # Max error rate (lower is better)
        result = self._evaluate_metric(
            "overall_error_rate",
            "max_error_rate",
            thresholds,
            higher_is_better=False
        )
        if result:
            metrics.append(result)
        else:
            missing.append("overall_error_rate not available")

        # Failure mode coverage (higher is better)
        result = self._evaluate_metric(
            "failure_mode_coverage",
            "failure_mode_coverage",
            thresholds,
            higher_is_better=True
        )
        if result:
            metrics.append(result)
        else:
            missing.append("failure_mode_coverage not evaluated")

        # Check required artifacts
        for art in artifacts:
            if art.required and not art.exists:
                missing.append(f"Required artifact missing: {art.name}")

        # Calculate score
        artifacts_present = sum(1 for a in artifacts if a.exists)
        required_artifacts = [a for a in artifacts if a.required]
        required_present = sum(1 for a in required_artifacts if a.exists)

        if required_artifacts:
            score = (required_present / len(required_artifacts)) * 100
        else:
            score = 0.0

        passed = all(a.exists for a in artifacts if a.required)

        if not passed:
            recommendations.append("Complete error analysis, rollback policy, and monitoring plan")

        return DimensionResult(
            dimension=dimension,
            status=FAVESStatus.PASS if passed else FAVESStatus.FAIL,
            score=score,
            passed=passed,
            metrics=metrics,
            required_artifacts=artifacts,
            missing_requirements=missing,
            recommendations=recommendations
        )

    def evaluate(self) -> FAVESResult:
        """
        Run complete FAVES evaluation.

        Returns:
            FAVESResult with all dimension evaluations
        """
        # Evaluate all dimensions
        fair = self.evaluate_fairness()
        appropriate = self.evaluate_appropriateness()
        valid = self.evaluate_validity()
        effective = self.evaluate_effectiveness()
        safe = self.evaluate_safety()

        dimensions = {
            "fair": fair,
            "appropriate": appropriate,
            "valid": valid,
            "effective": effective,
            "safe": safe,
        }

        # Calculate totals
        all_metrics = (
            fair.metrics + appropriate.metrics + valid.metrics +
            effective.metrics + safe.metrics
        )
        all_artifacts = (
            fair.required_artifacts + appropriate.required_artifacts +
            valid.required_artifacts + effective.required_artifacts +
            safe.required_artifacts
        )

        total_metrics_passed = sum(1 for m in all_metrics if m.passed)
        total_metrics_failed = sum(1 for m in all_metrics if not m.passed)
        total_artifacts_present = sum(1 for a in all_artifacts if a.exists)
        total_artifacts_missing = sum(1 for a in all_artifacts if not a.exists)

        # Overall score (average of dimension scores)
        overall_score = sum(d.score for d in dimensions.values()) / 5

        # Overall status
        all_passed = all(d.passed for d in dimensions.values())
        any_passed = any(d.passed for d in dimensions.values())

        if all_passed:
            overall_status = FAVESStatus.PASS
        elif any_passed:
            overall_status = FAVESStatus.PARTIAL
        else:
            overall_status = FAVESStatus.FAIL

        # Deployment allowed only if all pass
        deployment_allowed = all_passed

        # Collect blocking issues
        blocking_issues = []
        for dim_name, dim_result in dimensions.items():
            if not dim_result.passed:
                blocking_issues.extend([
                    f"[{dim_name.upper()}] {issue}"
                    for issue in dim_result.missing_requirements
                ])

        return FAVESResult(
            evaluation_id=str(uuid.uuid4()),
            model_id=self.model_id,
            model_version=self.model_version,
            evaluated_at=datetime.utcnow().isoformat() + "Z",
            evaluated_by=os.getenv("FAVES_EVALUATOR_ID", "system"),
            overall_status=overall_status,
            overall_score=overall_score,
            deployment_allowed=deployment_allowed,
            dimensions=dimensions,
            total_metrics_passed=total_metrics_passed,
            total_metrics_failed=total_metrics_failed,
            total_artifacts_present=total_artifacts_present,
            total_artifacts_missing=total_artifacts_missing,
            blocking_issues=blocking_issues,
            ci_run_id=os.getenv("CI_RUN_ID"),
            git_commit_sha=os.getenv("GIT_COMMIT_SHA"),
        )

    def to_json(self, result: FAVESResult) -> str:
        """Convert result to JSON string."""
        def serialize(obj):
            if isinstance(obj, Enum):
                return obj.value
            elif hasattr(obj, '__dict__'):
                return {k: serialize(v) for k, v in obj.__dict__.items()}
            elif isinstance(obj, list):
                return [serialize(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            return obj

        return json.dumps(serialize(result), indent=2)


class FAVESGate:
    """
    CI/CD gate that blocks deployment if FAVES fails.
    """

    def __init__(self, evaluator: FAVESEvaluator):
        self.evaluator = evaluator

    def check(self) -> Tuple[bool, FAVESResult]:
        """
        Run FAVES gate check.

        Returns:
            Tuple of (passed, result)
        """
        result = self.evaluator.evaluate()
        return result.deployment_allowed, result

    def enforce(self) -> None:
        """
        Enforce FAVES gate, exit with error code if failed.
        """
        passed, result = self.check()

        print(f"\n{'='*60}")
        print("FAVES COMPLIANCE GATE")
        print(f"{'='*60}")
        print(f"Model: {result.model_id} v{result.model_version}")
        print(f"Overall Status: {result.overall_status.value}")
        print(f"Overall Score: {result.overall_score:.1f}%")
        print(f"Deployment Allowed: {result.deployment_allowed}")
        print(f"{'='*60}\n")

        for dim_name, dim_result in result.dimensions.items():
            status_icon = "✅" if dim_result.passed else "❌"
            print(f"{status_icon} {dim_name.upper()}: {dim_result.score:.1f}%")

        if result.blocking_issues:
            print(f"\n{'='*60}")
            print("BLOCKING ISSUES:")
            for issue in result.blocking_issues:
                print(f"  - {issue}")

        if not passed:
            print(f"\n❌ FAVES GATE FAILED - Deployment blocked")
            exit(1)
        else:
            print(f"\n✅ FAVES GATE PASSED - Deployment allowed")


# Factory function
def create_faves_evaluator(
    model_id: str,
    model_version: str,
    artifacts_dir: str = "docs/faves"
) -> FAVESEvaluator:
    """Create FAVES evaluator instance."""
    return FAVESEvaluator(
        model_id=model_id,
        model_version=model_version,
        artifacts_dir=artifacts_dir
    )
