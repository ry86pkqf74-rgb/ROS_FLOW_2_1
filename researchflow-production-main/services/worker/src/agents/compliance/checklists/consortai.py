"""
CONSORT-AI Checklist Validator

Validates AI-integrated trial reporting against CONSORT-AI guidelines.

CONSORT-AI is an extension of CONSORT 2010 guidelines specifically for
randomized controlled trials utilizing artificial intelligence.

@author Claude
@created 2026-01-30
"""

import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CONSORTAIItem:
    """Represents a single CONSORT-AI checklist item."""

    item_id: str
    category: str
    subcategory: str
    description: str
    required: bool = True
    cross_reference: Optional[Dict[str, str]] = None
    evidence_types: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating a single checklist item."""

    item_id: str
    item_description: str
    status: str  # not_started, in_progress, completed, skipped
    is_valid: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    evidence_provided: List[str] = field(default_factory=list)
    notes: Optional[str] = None


class CONSORTAIValidator:
    """Validator for CONSORT-AI checklist compliance."""

    # CONSORT-AI framework sections
    SECTIONS = {
        "AI Model Specification": 3,
        "Trial Integration and Deployment": 3,
        "Validation and Performance Assessment": 3,
        "Interpretation and Implementation": 3,
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize CONSORT-AI validator.

        Args:
            config_path: Path to CONSORT-AI YAML configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.items: Dict[str, CONSORTAIItem] = {}
        self.validation_results: Dict[str, ValidationResult] = {}
        self.tripod_references: Dict[str, str] = {}

        self._load_config()
        logger.info(f"CONSORT-AI validator initialized with {len(self.items)} items")

    def _get_default_config_path(self) -> Path:
        """Get default config path."""
        return Path(__file__).parent.parent.parent.parent.parent.parent / "config" / "consort-ai-checklist.yaml"

    def _load_config(self) -> None:
        """Load CONSORT-AI configuration from YAML."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                self._create_default_config()
                return

            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            checklist_config = config.get("consort_ai_checklist", {})
            sections = checklist_config.get("sections", [])

            for section in sections:
                items_list = section.get("items", [])
                for item_config in items_list:
                    item = CONSORTAIItem(
                        item_id=item_config.get("id", ""),
                        category=item_config.get("category", ""),
                        subcategory=item_config.get("subcategory", ""),
                        description=item_config.get("description", ""),
                        required=item_config.get("required", True),
                        cross_reference=item_config.get("cross_reference"),
                        evidence_types=item_config.get("evidence_types", []),
                        validation_rules=item_config.get("validation_rules", []),
                    )
                    self.items[item.item_id] = item

                    # Track TRIPOD references
                    if item.cross_reference:
                        tripod_item = item.cross_reference.get("tripod_item")
                        if tripod_item:
                            self.tripod_references[item.item_id] = tripod_item

            logger.info(f"Loaded {len(self.items)} CONSORT-AI checklist items")

        except Exception as e:
            logger.error(f"Error loading CONSORT-AI config: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create a default minimal configuration."""
        logger.info("Creating default CONSORT-AI configuration")

        default_items = [
            CONSORTAIItem(
                item_id="CONSORT-AI-1",
                category="AI Model Specification",
                subcategory="Model Architecture",
                description="Specify the type of AI/ML model used",
            ),
            CONSORTAIItem(
                item_id="CONSORT-AI-2",
                category="AI Model Specification",
                subcategory="Training Data",
                description="Report source, size, and characteristics of training data",
            ),
            CONSORTAIItem(
                item_id="CONSORT-AI-4",
                category="Trial Integration",
                subcategory="Deployment",
                description="Describe AI model integration into trial workflow",
            ),
            CONSORTAIItem(
                item_id="CONSORT-AI-7",
                category="Trial Validation",
                subcategory="Model Performance",
                description="Report AI model performance in trial participants",
            ),
        ]

        for item in default_items:
            self.items[item.item_id] = item

    def validate_item(
        self,
        item_id: str,
        evidence: List[str],
        notes: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate a single checklist item.

        Args:
            item_id: Item identifier
            evidence: List of evidence artifacts provided
            notes: Additional notes

        Returns:
            ValidationResult object
        """
        if item_id not in self.items:
            logger.warning(f"Unknown item ID: {item_id}")
            return ValidationResult(
                item_id=item_id,
                item_description="Unknown",
                status="not_started",
                is_valid=False,
                errors=["Item not found in CONSORT-AI checklist"],
            )

        item = self.items[item_id]
        result = ValidationResult(
            item_id=item_id,
            item_description=item.description,
            status="not_started" if not evidence else "completed",
            evidence_provided=evidence,
            notes=notes,
        )

        # Validate evidence
        if not evidence and item.required:
            result.errors.append(f"No evidence provided for required item {item_id}")
            result.is_valid = False
        elif evidence:
            result.is_valid = self._validate_evidence(item, evidence, result)

        self.validation_results[item_id] = result
        return result

    def _validate_evidence(
        self,
        item: CONSORTAIItem,
        evidence: List[str],
        result: ValidationResult,
    ) -> bool:
        """
        Validate evidence against item rules.

        Args:
            item: CONSORT-AI item
            evidence: Evidence provided
            result: ValidationResult to update

        Returns:
            True if evidence is valid, False otherwise
        """
        is_valid = True

        # Check expected evidence types
        if item.evidence_types and evidence:
            for ev in evidence:
                found = False
                for ev_type in item.evidence_types:
                    if ev_type.lower() in ev.lower():
                        found = True
                        break
                if not found:
                    result.warnings.append(
                        f"Evidence '{ev}' may not match expected types: {item.evidence_types}"
                    )

        # Apply validation rules
        for rule in item.validation_rules:
            if "must" in rule.lower():
                if not self._check_validation_rule(rule, evidence):
                    result.errors.append(f"Validation failed: {rule}")
                    is_valid = False
            elif "should" in rule.lower():
                if not self._check_validation_rule(rule, evidence):
                    result.warnings.append(f"Recommendation not met: {rule}")

        return is_valid

    def _check_validation_rule(self, rule: str, evidence: List[str]) -> bool:
        """
        Check if evidence satisfies a validation rule.

        Args:
            rule: Validation rule text
            evidence: Evidence provided

        Returns:
            True if rule is satisfied, False otherwise
        """
        if "report" in rule.lower() or "document" in rule.lower():
            return len(evidence) > 0

        if "compare" in rule.lower() or "analyze" in rule.lower():
            return len(evidence) > 1

        # Default: if evidence is provided, consider it satisfied
        return len(evidence) > 0

    def validate_trial_specific_requirements(
        self,
        trial_id: str,
        clinician_override_rate: Optional[float] = None,
        model_retraining_events: int = 0,
        fairness_analysis_performed: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate CONSORT-AI trial-specific requirements.

        Args:
            trial_id: Trial identifier
            clinician_override_rate: Percentage of recommendations overridden
            model_retraining_events: Number of retraining events during trial
            fairness_analysis_performed: Whether fairness analysis was done

        Returns:
            Validation results for trial-specific items
        """
        findings = {
            "trial_id": trial_id,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "recommendations": [],
        }

        # Check clinician interaction (CONSORT-AI-5)
        if clinician_override_rate is not None:
            if clinician_override_rate < 5:
                findings["checks"]["clinician_acceptance"] = "EXCELLENT"
                findings["checks"]["clinician_override_rate"] = clinician_override_rate
            elif clinician_override_rate < 20:
                findings["checks"]["clinician_acceptance"] = "GOOD"
                findings["checks"]["clinician_override_rate"] = clinician_override_rate
            else:
                findings["checks"]["clinician_acceptance"] = "LOW"
                findings["checks"]["clinician_override_rate"] = clinician_override_rate
                findings["recommendations"].append(
                    "High clinician override rate suggests model may not be meeting clinical needs"
                )

        # Check model monitoring (CONSORT-AI-6)
        if model_retraining_events > 0:
            findings["checks"]["model_monitoring"] = "ACTIVE"
            findings["checks"]["retraining_events"] = model_retraining_events
            findings["recommendations"].append(
                f"Document rationale for {model_retraining_events} retraining event(s)"
            )
        else:
            findings["checks"]["model_monitoring"] = "PASSIVE"
            findings["recommendations"].append(
                "Consider implementing more active model performance monitoring during trial"
            )

        # Check fairness assessment (CONSORT-AI-8)
        if fairness_analysis_performed:
            findings["checks"]["fairness_analysis"] = "COMPLETED"
        else:
            findings["checks"]["fairness_analysis"] = "NOT_COMPLETED"
            findings["recommendations"].append(
                "Fairness analysis across demographic groups is required"
            )

        return findings

    def validate_checklist(
        self,
        item_completions: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        Validate complete CONSORT-AI checklist.

        Args:
            item_completions: Dict mapping item IDs to evidence lists

        Returns:
            Comprehensive validation report
        """
        logger.info("Starting CONSORT-AI checklist validation")

        self.validation_results.clear()

        for item_id, evidence in item_completions.items():
            self.validate_item(item_id, evidence)

        # Validate items not provided
        for item_id in self.items:
            if item_id not in item_completions:
                result = ValidationResult(
                    item_id=item_id,
                    item_description=self.items[item_id].description,
                    status="not_started",
                    is_valid=False,
                    errors=["No evidence provided"] if self.items[item_id].required else [],
                )
                self.validation_results[item_id] = result

        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        total_items = len(self.validation_results)
        completed_items = sum(
            1 for r in self.validation_results.values() if r.status == "completed"
        )
        valid_items = sum(1 for r in self.validation_results.values() if r.is_valid)
        items_with_errors = [
            r for r in self.validation_results.values() if r.errors
        ]

        completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0
        validity_percentage = (valid_items / total_items * 100) if total_items > 0 else 0

        return {
            "total_items": total_items,
            "completed_items": completed_items,
            "valid_items": valid_items,
            "completion_percentage": completion_percentage,
            "validity_percentage": validity_percentage,
            "is_complete": completed_items == total_items,
            "is_valid": len(items_with_errors) == 0,
            "items_with_errors": [
                {
                    "item_id": r.item_id,
                    "description": r.item_description,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "tripod_reference": self.tripod_references.get(r.item_id),
                }
                for r in items_with_errors
            ],
            "detailed_results": {
                r.item_id: {
                    "status": r.status,
                    "is_valid": r.is_valid,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "evidence_count": len(r.evidence_provided),
                }
                for r in self.validation_results.values()
            },
            "validation_timestamp": datetime.utcnow().isoformat(),
        }

    def get_missing_items(self) -> List[str]:
        """
        Get list of items not yet completed.

        Returns:
            List of item IDs that are incomplete
        """
        return [
            item_id
            for item_id, result in self.validation_results.items()
            if result.status != "completed"
        ]

    def generate_summary(self) -> str:
        """
        Generate human-readable summary of validation status.

        Returns:
            Summary string
        """
        total = len(self.validation_results)
        completed = sum(
            1 for r in self.validation_results.values() if r.status == "completed"
        )
        valid = sum(1 for r in self.validation_results.values() if r.is_valid)

        missing = self.get_missing_items()

        summary = f"""CONSORT-AI Validation Summary
================================
Total Items: {total}
Completed: {completed} ({completed/total*100:.1f}%)
Valid: {valid} ({valid/total*100:.1f}%)

Missing Items: {len(missing)}
"""

        if missing:
            summary += f"Incomplete: {', '.join(missing)}\n"

        return summary
