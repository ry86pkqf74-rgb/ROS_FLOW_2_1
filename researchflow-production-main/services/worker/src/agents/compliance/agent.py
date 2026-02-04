"""
Compliance Agent

AI-powered agent for managing compliance validation and evidence collection
for AI/ML research projects. Orchestrates FAVES gates, TRIPOD+AI, and CONSORT-AI
checklist validation.

@author Claude
@created 2026-01-30
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    # Try relative imports first (when used as package)
    from .checklists.tripodai import TRIPODAIValidator
    from .checklists.consortai import CONSORTAIValidator
    from .checklists.faves import FAVESValidator
    from ..base.models import (
        ComplianceReport,
        FAVESAssessment,
        TRIPODAIChecklistCompletion,
        CONSORTAIChecklistCompletion,
        ComplianceStatus,
    )
except ImportError:
    # Fall back to direct imports (when used as standalone module)
    from compliance.checklists.tripodai import TRIPODAIValidator
    from compliance.checklists.consortai import CONSORTAIValidator
    from compliance.checklists.faves import FAVESValidator
    from base.models import (
        ComplianceReport,
        FAVESAssessment,
        TRIPODAIChecklistCompletion,
        CONSORTAIChecklistCompletion,
        ComplianceStatus,
    )

logger = logging.getLogger(__name__)


class ComplianceAgent:
    """
    Compliance agent for AI/ML research projects.

    Manages compliance validation across multiple frameworks:
    - FAVES gates (Fair, Appropriate, Valid, Effective, Safe)
    - TRIPOD+AI checklist (27 items for AI/ML model reporting)
    - CONSORT-AI checklist (12 items for AI-integrated trials)
    - HTI-1 disclosure documentation
    - Evidence bundle management

    Integrates with Notion for registry management and GitHub for PR comments.
    """

    def __init__(self, research_id: str, organization: Optional[str] = None):
        """
        Initialize compliance agent.

        Args:
            research_id: Research project identifier
            organization: Organization name
        """
        self.research_id = research_id
        self.organization = organization
        self.created_at = datetime.utcnow()

        # Initialize validators
        self.faves_validator = FAVESValidator()
        self.tripod_validator = TRIPODAIValidator()
        self.consort_validator = CONSORTAIValidator()

        # Evidence tracking
        self.faves_assessment: Optional[FAVESAssessment] = None
        self.tripod_completion: Optional[TRIPODAIChecklistCompletion] = None
        self.consort_completion: Optional[CONSORTAIChecklistCompletion] = None
        self.compliance_report: Optional[ComplianceReport] = None

        logger.info(f"Compliance agent initialized for research {research_id}")

    # ========================================================================
    # FAVES Gate Validation
    # ========================================================================

    def validate_faves_gates(
        self,
        fair_data: Dict[str, Any],
        appropriate_data: Dict[str, Any],
        valid_data: Dict[str, Any],
        effective_data: Dict[str, Any],
        safe_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate all FAVES gates for the model.

        Args:
            fair_data: Data for FAIR gate evaluation
            appropriate_data: Data for APPROPRIATE gate evaluation
            valid_data: Data for VALID gate evaluation
            effective_data: Data for EFFECTIVE gate evaluation
            safe_data: Data for SAFE gate evaluation

        Returns:
            Overall FAVES assessment
        """
        logger.info(f"Validating FAVES gates for research {self.research_id}")

        # Evaluate each gate
        self.faves_validator.evaluate_fair_gate(
            bias_assessment_performed=fair_data.get("bias_assessment_performed", False),
            fairness_metrics_reported=fair_data.get("fairness_metrics_reported", False),
            demographic_parity_achieved=fair_data.get("demographic_parity_achieved"),
            equalized_odds_achieved=fair_data.get("equalized_odds_achieved"),
            evidence=fair_data.get("evidence"),
        )

        self.faves_validator.evaluate_appropriate_gate(
            intended_use_documented=appropriate_data.get(
                "intended_use_documented", False
            ),
            use_case_justified=appropriate_data.get("use_case_justified", False),
            target_population_defined=appropriate_data.get(
                "target_population_defined", False
            ),
            inclusion_exclusion_criteria_clear=appropriate_data.get(
                "inclusion_exclusion_criteria_clear", False
            ),
            evidence=appropriate_data.get("evidence"),
        )

        self.faves_validator.evaluate_valid_gate(
            validation_performed=valid_data.get("validation_performed", False),
            test_set_used=valid_data.get("test_set_used", False),
            cross_validation_applied=valid_data.get("cross_validation_applied", False),
            external_validation_performed=valid_data.get(
                "external_validation_performed", False
            ),
            evidence=valid_data.get("evidence"),
        )

        self.faves_validator.evaluate_effective_gate(
            performance_metrics_reported=effective_data.get(
                "performance_metrics_reported", False
            ),
            auc_threshold_met=effective_data.get("auc_threshold_met"),
            sensitivity_threshold_met=effective_data.get("sensitivity_threshold_met"),
            specificity_threshold_met=effective_data.get("specificity_threshold_met"),
            calibration_checked=effective_data.get("calibration_checked", False),
            evidence=effective_data.get("evidence"),
        )

        self.faves_validator.evaluate_safe_gate(
            risk_assessment_performed=safe_data.get("risk_assessment_performed", False),
            safety_requirements_defined=safe_data.get(
                "safety_requirements_defined", False
            ),
            failure_modes_identified=safe_data.get("failure_modes_identified", False),
            monitoring_plan_established=safe_data.get(
                "monitoring_plan_established", False
            ),
            adverse_event_protocol_defined=safe_data.get(
                "adverse_event_protocol_defined", False
            ),
            evidence=safe_data.get("evidence"),
        )

        assessment = self.faves_validator.generate_overall_assessment()

        logger.info(
            f"FAVES validation complete: {assessment['overall_status']} "
            f"({assessment['overall_score']:.1f}/100)"
        )

        return assessment

    # ========================================================================
    # TRIPOD+AI Checklist Validation
    # ========================================================================

    def validate_tripod_ai_checklist(
        self,
        item_completions: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        Validate TRIPOD+AI checklist completion.

        Args:
            item_completions: Dict mapping TRIPOD+AI item IDs to evidence lists

        Returns:
            Validation report
        """
        logger.info(f"Validating TRIPOD+AI checklist for research {self.research_id}")

        report = self.tripod_validator.validate_checklist(item_completions)

        logger.info(
            f"TRIPOD+AI validation complete: "
            f"{report['completion_percentage']:.1f}% complete, "
            f"{report['validity_percentage']:.1f}% valid"
        )

        return report

    # ========================================================================
    # CONSORT-AI Checklist Validation
    # ========================================================================

    def validate_consort_ai_checklist(
        self,
        item_completions: Dict[str, List[str]],
        trial_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate CONSORT-AI checklist completion.

        Args:
            item_completions: Dict mapping CONSORT-AI item IDs to evidence lists
            trial_id: Trial identifier

        Returns:
            Validation report
        """
        logger.info(f"Validating CONSORT-AI checklist for research {self.research_id}")

        report = self.consort_validator.validate_checklist(item_completions)

        logger.info(
            f"CONSORT-AI validation complete: "
            f"{report['completion_percentage']:.1f}% complete, "
            f"{report['validity_percentage']:.1f}% valid"
        )

        return report

    # ========================================================================
    # Compliance Report Generation
    # ========================================================================

    def generate_compliance_report(
        self,
        faves_assessment_data: Optional[Dict[str, Any]] = None,
        tripod_completions: Optional[Dict[str, List[str]]] = None,
        consort_completions: Optional[Dict[str, List[str]]] = None,
    ) -> ComplianceReport:
        """
        Generate comprehensive compliance report.

        Args:
            faves_assessment_data: FAVES evaluation data
            tripod_completions: TRIPOD+AI item completions
            consort_completions: CONSORT-AI item completions

        Returns:
            ComplianceReport object
        """
        logger.info(f"Generating compliance report for research {self.research_id}")

        report = ComplianceReport(
            id=f"compliance-{self.research_id}-{datetime.utcnow().timestamp()}",
            research_id=self.research_id,
            generated_by="compliance_agent",
        )

        # Add FAVES assessment if provided
        if faves_assessment_data:
            faves_evaluation = self.validate_faves_gates(
                fair_data=faves_assessment_data.get("fair", {}),
                appropriate_data=faves_assessment_data.get("appropriate", {}),
                valid_data=faves_assessment_data.get("valid", {}),
                effective_data=faves_assessment_data.get("effective", {}),
                safe_data=faves_assessment_data.get("safe", {}),
            )

            # Map assessment to model
            overall_score = faves_evaluation.get("overall_score", 0.0)
            overall_status = faves_evaluation.get("overall_status", "NOT_EVALUATED")

            # Convert to ComplianceStatus
            status_map = {
                "PASSED": ComplianceStatus.COMPLIANT,
                "CONDITIONAL": ComplianceStatus.PARTIAL,
                "FAILED": ComplianceStatus.NON_COMPLIANT,
            }

            report.faves_assessment = FAVESAssessment(
                id=f"faves-{self.research_id}",
                research_id=self.research_id,
                fair_score=faves_evaluation["gate_results"]["FAIR"]["score"],
                appropriate_score=faves_evaluation["gate_results"]["APPROPRIATE"][
                    "score"
                ],
                valid_score=faves_evaluation["gate_results"]["VALID"]["score"],
                effective_score=faves_evaluation["gate_results"]["EFFECTIVE"]["score"],
                safe_score=faves_evaluation["gate_results"]["SAFE"]["score"],
                overall_score=overall_score,
                status=status_map.get(
                    overall_status, ComplianceStatus.NOT_APPLICABLE
                ),
                passed=overall_status == "PASSED",
            )

        # Add TRIPOD+AI completion if provided
        if tripod_completions:
            tripod_report = self.validate_tripod_ai_checklist(tripod_completions)

            report.tripod_completion = TRIPODAIChecklistCompletion(
                id=f"tripod-{self.research_id}",
                research_id=self.research_id,
                completed_items=tripod_report.get("completed_items", 0),
                completion_percentage=tripod_report.get("completion_percentage", 0.0),
                is_valid=tripod_report.get("is_valid", False),
            )

        # Add CONSORT-AI completion if provided
        if consort_completions:
            consort_report = self.validate_consort_ai_checklist(consort_completions)

            report.consort_completion = CONSORTAIChecklistCompletion(
                id=f"consort-{self.research_id}",
                research_id=self.research_id,
                completed_items=consort_report.get("completed_items", 0),
                completion_percentage=consort_report.get("completion_percentage", 0.0),
                is_valid=consort_report.get("is_valid", False),
            )

        # Calculate overall compliance
        compliance_scores = []
        if report.faves_assessment:
            compliance_scores.append(report.faves_assessment.overall_score)
        if report.tripod_completion:
            compliance_scores.append(report.tripod_completion.completion_percentage)
        if report.consort_completion:
            compliance_scores.append(report.consort_completion.completion_percentage)

        if compliance_scores:
            report.compliance_score = sum(compliance_scores) / len(compliance_scores)
            report.overall_compliance_status = (
                ComplianceStatus.COMPLIANT
                if report.compliance_score >= 80
                else ComplianceStatus.PARTIAL
                if report.compliance_score >= 60
                else ComplianceStatus.NON_COMPLIANT
            )

        self.compliance_report = report
        logger.info(
            f"Compliance report generated: "
            f"{report.overall_compliance_status.value} ({report.compliance_score:.1f}%)"
        )

        return report

    # ========================================================================
    # Evidence & Integration Methods (Placeholders for Composio Integration)
    # ========================================================================

    def post_to_notion_registry(
        self,
        report: ComplianceReport,
    ) -> Dict[str, Any]:
        """
        Post compliance status to Notion model registry.

        Args:
            report: ComplianceReport to post

        Returns:
            Response from Notion API
        """
        logger.info(f"Posting compliance status to Notion for {self.research_id}")

        # This would be implemented with Composio Notion toolkit
        # Placeholder implementation
        return {
            "status": "success",
            "message": f"Posted to Notion: {report.overall_compliance_status.value}",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def add_github_pr_comment(
        self,
        repo: str,
        pr_number: int,
        missing_items: List[str],
    ) -> Dict[str, Any]:
        """
        Add PR comment about missing compliance items.

        Args:
            repo: GitHub repository (owner/repo format)
            pr_number: Pull request number
            missing_items: List of missing compliance items

        Returns:
            Response from GitHub API
        """
        logger.info(
            f"Adding GitHub PR comment for {repo}#{pr_number}: {len(missing_items)} missing items"
        )

        # This would be implemented with Composio GitHub toolkit
        # Placeholder implementation
        comment = f"""
## Compliance Check

Missing compliance items detected:
{chr(10).join(f"- {item}" for item in missing_items)}

Please address these items before merge.
"""

        return {
            "status": "success",
            "message": "Comment added to PR",
            "comment": comment,
        }

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_summary(self) -> str:
        """
        Get human-readable compliance summary.

        Returns:
            Summary string
        """
        summary = f"Compliance Summary for {self.research_id}\n"
        summary += "=" * 50 + "\n"

        summary += "\nFAVES Assessment:\n"
        summary += self.faves_validator.generate_summary()

        summary += "\nTRIPOD+AI Checklist:\n"
        summary += self.tripod_validator.generate_summary()

        summary += "\nCONSORT-AI Checklist:\n"
        summary += self.consort_validator.generate_summary()

        if self.compliance_report:
            summary += f"\nOverall Compliance: {self.compliance_report.overall_compliance_status.value}"
            summary += f" ({self.compliance_report.compliance_score:.1f}%)\n"

        return summary

    def export_to_json(self) -> Dict[str, Any]:
        """
        Export compliance state to JSON.

        Returns:
            JSON-serializable dictionary
        """
        return {
            "research_id": self.research_id,
            "organization": self.organization,
            "created_at": self.created_at.isoformat(),
            "faves_assessment": (
                self.faves_validator.generate_overall_assessment()
                if self.faves_validator.evaluations
                else None
            ),
            "tripod_summary": (
                self.tripod_validator.generate_summary()
                if self.tripod_validator.validation_results
                else None
            ),
            "consort_summary": (
                self.consort_validator.generate_summary()
                if self.consort_validator.validation_results
                else None
            ),
            "compliance_report": (
                json.loads(self.compliance_report.model_dump_json())
                if self.compliance_report
                else None
            ),
        }
