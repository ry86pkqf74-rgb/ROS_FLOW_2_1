"""
FAVES Gate Validator

Validates AI/ML models against FAVES compliance gates:
- Fair: Fairness and bias assessment
- Appropriate: Appropriate use case and justification
- Valid: Validation and testing evidence
- Effective: Effectiveness and performance metrics
- Safe: Safety and risk management

@author Claude
@created 2026-01-30
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class GateStatus(str, Enum):
    """Status of a FAVES gate."""

    PASSED = "PASSED"
    CONDITIONAL = "CONDITIONAL"
    FAILED = "FAILED"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass
class GateEvaluation:
    """Evaluation result for a single FAVES gate."""

    dimension: str  # FAIR, APPROPRIATE, VALID, EFFECTIVE, SAFE
    score: float  # 0-100
    status: GateStatus
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    evidence_provided: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class FAVESValidator:
    """Validator for FAVES compliance gates."""

    # Passing thresholds for each dimension
    PASS_THRESHOLD = 80.0
    CONDITIONAL_THRESHOLD = 60.0

    DIMENSIONS = ["FAIR", "APPROPRIATE", "VALID", "EFFECTIVE", "SAFE"]

    def __init__(self):
        """Initialize FAVES validator."""
        self.evaluations: Dict[str, GateEvaluation] = {}
        logger.info("FAVES validator initialized")

    def evaluate_fair_gate(
        self,
        bias_assessment_performed: bool,
        fairness_metrics_reported: bool,
        demographic_parity_achieved: Optional[bool] = None,
        equalized_odds_achieved: Optional[bool] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> GateEvaluation:
        """
        Evaluate FAIR gate (Fairness).

        Args:
            bias_assessment_performed: Whether bias assessment was conducted
            fairness_metrics_reported: Whether fairness metrics are reported
            demographic_parity_achieved: Whether demographic parity achieved
            equalized_odds_achieved: Whether equalized odds achieved
            evidence: Supporting evidence

        Returns:
            GateEvaluation for FAIR dimension
        """
        score = 0.0
        findings = []
        recommendations = []

        # Check bias assessment
        if bias_assessment_performed:
            score += 30
            findings.append("Bias assessment performed")
        else:
            recommendations.append("Conduct comprehensive bias assessment")

        # Check fairness metrics
        if fairness_metrics_reported:
            score += 30
            findings.append("Fairness metrics reported")
        else:
            recommendations.append("Report fairness metrics by demographic group")

        # Check fairness criteria
        fairness_criteria_met = 0
        if demographic_parity_achieved:
            fairness_criteria_met += 1
            findings.append("Demographic parity achieved")
        else:
            recommendations.append("Address demographic parity gaps")

        if equalized_odds_achieved:
            fairness_criteria_met += 1
            findings.append("Equalized odds achieved")
        else:
            recommendations.append("Address equalized odds gaps")

        score += fairness_criteria_met * 20  # 0-40 points

        # Determine status
        if score >= self.PASS_THRESHOLD:
            status = GateStatus.PASSED
        elif score >= self.CONDITIONAL_THRESHOLD:
            status = GateStatus.CONDITIONAL
            recommendations.append("Fairness metrics need improvement")
        else:
            status = GateStatus.FAILED
            recommendations.append("FAIR gate not met - significant fairness concerns")

        evaluation = GateEvaluation(
            dimension="FAIR",
            score=min(score, 100.0),
            status=status,
            findings=findings,
            recommendations=recommendations,
            evidence_provided=evidence or {},
        )

        self.evaluations["FAIR"] = evaluation
        logger.info(f"FAIR gate evaluated: {status.value} ({score:.1f}%)")
        return evaluation

    def evaluate_appropriate_gate(
        self,
        intended_use_documented: bool,
        use_case_justified: bool,
        target_population_defined: bool,
        inclusion_exclusion_criteria_clear: bool,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> GateEvaluation:
        """
        Evaluate APPROPRIATE gate (Appropriate use case).

        Args:
            intended_use_documented: Whether intended use is documented
            use_case_justified: Whether use case is justified
            target_population_defined: Whether target population is defined
            inclusion_exclusion_criteria_clear: Whether criteria are clear
            evidence: Supporting evidence

        Returns:
            GateEvaluation for APPROPRIATE dimension
        """
        score = 0.0
        findings = []
        recommendations = []

        if intended_use_documented:
            score += 25
            findings.append("Intended use documented")
        else:
            recommendations.append("Document intended use clearly")

        if use_case_justified:
            score += 25
            findings.append("Use case justified")
        else:
            recommendations.append("Provide justification for selected use case")

        if target_population_defined:
            score += 25
            findings.append("Target population clearly defined")
        else:
            recommendations.append("Define target population precisely")

        if inclusion_exclusion_criteria_clear:
            score += 25
            findings.append("Inclusion/exclusion criteria defined")
        else:
            recommendations.append("Establish clear inclusion/exclusion criteria")

        # Determine status
        if score >= self.PASS_THRESHOLD:
            status = GateStatus.PASSED
        elif score >= self.CONDITIONAL_THRESHOLD:
            status = GateStatus.CONDITIONAL
            recommendations.append("Some appropriateness criteria need clarification")
        else:
            status = GateStatus.FAILED
            recommendations.append("APPROPRIATE gate not met - use case not adequately justified")

        evaluation = GateEvaluation(
            dimension="APPROPRIATE",
            score=min(score, 100.0),
            status=status,
            findings=findings,
            recommendations=recommendations,
            evidence_provided=evidence or {},
        )

        self.evaluations["APPROPRIATE"] = evaluation
        logger.info(f"APPROPRIATE gate evaluated: {status.value} ({score:.1f}%)")
        return evaluation

    def evaluate_valid_gate(
        self,
        validation_performed: bool,
        test_set_used: bool,
        cross_validation_applied: bool,
        external_validation_performed: bool,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> GateEvaluation:
        """
        Evaluate VALID gate (Validation).

        Args:
            validation_performed: Whether validation was performed
            test_set_used: Whether separate test set was used
            cross_validation_applied: Whether cross-validation was used
            external_validation_performed: Whether external validation done
            evidence: Supporting evidence

        Returns:
            GateEvaluation for VALID dimension
        """
        score = 0.0
        findings = []
        recommendations = []

        if validation_performed:
            score += 20
            findings.append("Model validation performed")
        else:
            recommendations.append("Perform model validation")

        if test_set_used:
            score += 25
            findings.append("Separate test set used")
        else:
            recommendations.append("Use separate test set for validation")

        if cross_validation_applied:
            score += 25
            findings.append("Cross-validation applied")
        else:
            recommendations.append("Apply cross-validation procedures")

        if external_validation_performed:
            score += 30
            findings.append("External validation performed")
        else:
            recommendations.append("Perform external validation in independent dataset")

        # Determine status
        if score >= self.PASS_THRESHOLD:
            status = GateStatus.PASSED
        elif score >= self.CONDITIONAL_THRESHOLD:
            status = GateStatus.CONDITIONAL
            recommendations.append("Validation procedures could be strengthened")
        else:
            status = GateStatus.FAILED
            recommendations.append("VALID gate not met - insufficient validation evidence")

        evaluation = GateEvaluation(
            dimension="VALID",
            score=min(score, 100.0),
            status=status,
            findings=findings,
            recommendations=recommendations,
            evidence_provided=evidence or {},
        )

        self.evaluations["VALID"] = evaluation
        logger.info(f"VALID gate evaluated: {status.value} ({score:.1f}%)")
        return evaluation

    def evaluate_effective_gate(
        self,
        performance_metrics_reported: bool,
        auc_threshold_met: Optional[bool] = None,
        sensitivity_threshold_met: Optional[bool] = None,
        specificity_threshold_met: Optional[bool] = None,
        calibration_checked: bool = False,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> GateEvaluation:
        """
        Evaluate EFFECTIVE gate (Effectiveness).

        Args:
            performance_metrics_reported: Whether performance metrics reported
            auc_threshold_met: Whether AUC meets minimum threshold
            sensitivity_threshold_met: Whether sensitivity meets minimum
            specificity_threshold_met: Whether specificity meets minimum
            calibration_checked: Whether model calibration was checked
            evidence: Supporting evidence

        Returns:
            GateEvaluation for EFFECTIVE dimension
        """
        score = 0.0
        findings = []
        recommendations = []

        if performance_metrics_reported:
            score += 20
            findings.append("Performance metrics reported")
        else:
            recommendations.append("Report comprehensive performance metrics")

        performance_criteria_met = 0

        if auc_threshold_met:
            performance_criteria_met += 1
            findings.append("AUC meets minimum threshold")
        else:
            recommendations.append("Model AUC-ROC does not meet minimum threshold")

        if sensitivity_threshold_met:
            performance_criteria_met += 1
            findings.append("Sensitivity meets minimum threshold")
        else:
            recommendations.append("Improve model sensitivity")

        if specificity_threshold_met:
            performance_criteria_met += 1
            findings.append("Specificity meets minimum threshold")
        else:
            recommendations.append("Improve model specificity")

        score += performance_criteria_met * 20  # 0-60 points

        if calibration_checked:
            score += 20
            findings.append("Model calibration assessed")
        else:
            recommendations.append("Assess model calibration")

        # Determine status
        if score >= self.PASS_THRESHOLD:
            status = GateStatus.PASSED
        elif score >= self.CONDITIONAL_THRESHOLD:
            status = GateStatus.CONDITIONAL
            recommendations.append("Model effectiveness needs improvement")
        else:
            status = GateStatus.FAILED
            recommendations.append("EFFECTIVE gate not met - insufficient performance")

        evaluation = GateEvaluation(
            dimension="EFFECTIVE",
            score=min(score, 100.0),
            status=status,
            findings=findings,
            recommendations=recommendations,
            evidence_provided=evidence or {},
        )

        self.evaluations["EFFECTIVE"] = evaluation
        logger.info(f"EFFECTIVE gate evaluated: {status.value} ({score:.1f}%)")
        return evaluation

    def evaluate_safe_gate(
        self,
        risk_assessment_performed: bool,
        safety_requirements_defined: bool,
        failure_modes_identified: bool,
        monitoring_plan_established: bool,
        adverse_event_protocol_defined: bool,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> GateEvaluation:
        """
        Evaluate SAFE gate (Safety).

        Args:
            risk_assessment_performed: Whether risk assessment performed
            safety_requirements_defined: Whether safety requirements defined
            failure_modes_identified: Whether failure modes identified
            monitoring_plan_established: Whether monitoring plan established
            adverse_event_protocol_defined: Whether adverse event protocol exists
            evidence: Supporting evidence

        Returns:
            GateEvaluation for SAFE dimension
        """
        score = 0.0
        findings = []
        recommendations = []

        if risk_assessment_performed:
            score += 20
            findings.append("Risk assessment performed")
        else:
            recommendations.append("Conduct formal risk assessment")

        if safety_requirements_defined:
            score += 20
            findings.append("Safety requirements defined")
        else:
            recommendations.append("Define clear safety requirements")

        if failure_modes_identified:
            score += 20
            findings.append("Failure modes identified")
        else:
            recommendations.append("Identify and document failure modes")

        if monitoring_plan_established:
            score += 20
            findings.append("Monitoring plan established")
        else:
            recommendations.append("Establish post-deployment monitoring plan")

        if adverse_event_protocol_defined:
            score += 20
            findings.append("Adverse event protocol defined")
        else:
            recommendations.append("Define protocol for responding to adverse events")

        # Determine status
        if score >= self.PASS_THRESHOLD:
            status = GateStatus.PASSED
        elif score >= self.CONDITIONAL_THRESHOLD:
            status = GateStatus.CONDITIONAL
            recommendations.append("Safety protocols need strengthening")
        else:
            status = GateStatus.FAILED
            recommendations.append("SAFE gate not met - safety concerns exist")

        evaluation = GateEvaluation(
            dimension="SAFE",
            score=min(score, 100.0),
            status=status,
            findings=findings,
            recommendations=recommendations,
            evidence_provided=evidence or {},
        )

        self.evaluations["SAFE"] = evaluation
        logger.info(f"SAFE gate evaluated: {status.value} ({score:.1f}%)")
        return evaluation

    def generate_overall_assessment(self) -> Dict[str, Any]:
        """
        Generate overall FAVES assessment.

        Returns:
            Comprehensive assessment report
        """
        if not self.evaluations:
            logger.warning("No FAVES gates evaluated")
            return {
                "status": "NOT_EVALUATED",
                "message": "No gates have been evaluated",
            }

        # Calculate overall scores
        total_score = sum(
            eval.score for eval in self.evaluations.values()
        ) / len(self.evaluations)

        passed_gates = sum(
            1 for eval in self.evaluations.values() if eval.status == GateStatus.PASSED
        )

        failed_gates = sum(
            1 for eval in self.evaluations.values() if eval.status == GateStatus.FAILED
        )

        # Determine overall status
        if failed_gates > 0:
            overall_status = GateStatus.FAILED
        elif len(self.evaluations) - passed_gates > 0:
            overall_status = GateStatus.CONDITIONAL
        else:
            overall_status = GateStatus.PASSED

        return {
            "overall_status": overall_status.value,
            "overall_score": total_score,
            "passed_gates": passed_gates,
            "conditional_gates": len(self.evaluations) - passed_gates - failed_gates,
            "failed_gates": failed_gates,
            "total_gates": len(self.evaluations),
            "gate_results": {
                dim: {
                    "score": eval.score,
                    "status": eval.status.value,
                    "findings": eval.findings,
                    "recommendations": eval.recommendations,
                }
                for dim, eval in self.evaluations.items()
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def generate_summary(self) -> str:
        """
        Generate human-readable summary.

        Returns:
            Summary string
        """
        assessment = self.generate_overall_assessment()

        if assessment["overall_status"] == "NOT_EVALUATED":
            return "FAVES Assessment: Not yet evaluated"

        summary = f"""FAVES Compliance Assessment
================================
Overall Status: {assessment['overall_status']}
Overall Score: {assessment['overall_score']:.1f}/100

Gate Results:
- Passed: {assessment['passed_gates']}/{assessment['total_gates']}
- Conditional: {assessment['conditional_gates']}/{assessment['total_gates']}
- Failed: {assessment['failed_gates']}/{assessment['total_gates']}

Individual Gates:
"""

        for dim, result in assessment["gate_results"].items():
            summary += f"  {dim}: {result['status']} ({result['score']:.1f}%)\n"

        return summary
