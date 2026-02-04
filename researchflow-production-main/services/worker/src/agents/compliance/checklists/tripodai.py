"""
TRIPOD+AI Checklist Validator

Validates AI/ML model reporting against TRIPOD+AI (Transparent Reporting of
Evaluations with Nonrandomized Designs plus AI) guidelines.

Implements 27-item checklist for transparent reporting of AI/ML diagnostic
and prognostic models in healthcare.

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
class TRIPODAIItem:
    """Represents a single TRIPOD+AI checklist item."""

    item_id: str
    category: str
    subcategory: str
    description: str
    required: bool = True
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


class TRIPODAIValidator:
    """Validator for TRIPOD+AI checklist compliance."""

    # TRIPOD+AI framework sections
    CATEGORIES = {
        "Title": 1,
        "Abstract": 1,
        "Introduction": 2,
        "Methods": 8,
        "Results": 4,
        "Discussion": 3,
        "Other": 2,
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize TRIPOD+AI validator.

        Args:
            config_path: Path to TRIPOD+AI YAML configuration file
        """
        self.config_path = config_path or self._get_default_config_path()
        self.items: Dict[str, TRIPODAIItem] = {}
        self.validation_results: Dict[str, ValidationResult] = {}

        self._load_config()
        logger.info(f"TRIPOD+AI validator initialized with {len(self.items)} items")

    def _get_default_config_path(self) -> Path:
        """Get default config path."""
        return Path(__file__).parent.parent.parent.parent.parent.parent / "config" / "tripod-ai-checklist.yaml"

    def _load_config(self) -> None:
        """Load TRIPOD+AI configuration from YAML."""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                self._create_default_config()
                return

            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            checklist_config = config.get("tripod_ai_checklist", {})
            items_list = checklist_config.get("items", [])

            for item_config in items_list:
                item = TRIPODAIItem(
                    item_id=item_config.get("id", ""),
                    category=item_config.get("category", ""),
                    subcategory=item_config.get("subcategory", ""),
                    description=item_config.get("description", ""),
                    required=item_config.get("required", True),
                    evidence_types=item_config.get("evidence_types", []),
                    validation_rules=item_config.get("validation_rules", []),
                )
                self.items[item.item_id] = item

            logger.info(f"Loaded {len(self.items)} TRIPOD+AI checklist items")

        except Exception as e:
            logger.error(f"Error loading TRIPOD+AI config: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create a default minimal configuration."""
        logger.info("Creating default TRIPOD+AI configuration")

        # Create minimal configuration with key items
        default_items = [
            TRIPODAIItem(
                item_id="T1",
                category="Title",
                subcategory="Title and Keywords",
                description="Identify study as developing/validating a prediction model",
            ),
            TRIPODAIItem(
                item_id="M7",
                category="Methods",
                subcategory="Statistical Analysis",
                description="Describe model type and all specifications including hyperparameters",
            ),
            TRIPODAIItem(
                item_id="R3",
                category="Results",
                subcategory="Model Specification",
                description="Present full prediction model with all coefficients and parameters",
            ),
            TRIPODAIItem(
                item_id="R4",
                category="Results",
                subcategory="Model Performance",
                description="Report model performance including calibration and discrimination",
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
                errors=["Item not found in TRIPOD+AI checklist"],
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
        item: TRIPODAIItem,
        evidence: List[str],
        result: ValidationResult,
    ) -> bool:
        """
        Validate evidence against item rules.

        Args:
            item: TRIPOD+AI item
            evidence: Evidence provided
            result: ValidationResult to update

        Returns:
            True if evidence is valid, False otherwise
        """
        is_valid = True

        # Check if evidence types are provided
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
            # Basic validation rule checking
            if "must" in rule.lower():
                # These are hard requirements
                if not self._check_validation_rule(rule, evidence):
                    result.errors.append(f"Validation failed: {rule}")
                    is_valid = False
            elif "should" in rule.lower():
                # These are recommendations
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
        # Simple rule checking based on keywords
        rule_lower = rule.lower()

        if "include" in rule_lower or "report" in rule_lower:
            # Check if any evidence is provided
            return len(evidence) > 0

        if "document" in rule_lower or "describe" in rule_lower:
            return len(evidence) > 0

        # Default: if evidence is provided, consider it satisfied
        return len(evidence) > 0

    def validate_checklist(
        self,
        item_completions: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """
        Validate complete TRIPOD+AI checklist.

        Args:
            item_completions: Dict mapping item IDs to evidence lists

        Returns:
            Comprehensive validation report
        """
        logger.info("Starting TRIPOD+AI checklist validation")

        self.validation_results.clear()

        for item_id, evidence in item_completions.items():
            self.validate_item(item_id, evidence)

        # Also validate items not provided
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

    def get_critical_missing_items(self) -> List[str]:
        """
        Get list of required items not yet completed.

        Returns:
            List of required item IDs that are incomplete
        """
        return [
            item_id
            for item_id in self.get_missing_items()
            if self.items.get(item_id, TRIPODAIItem("", "", "", "")).required
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

        critical_missing = self.get_critical_missing_items()

        summary = f"""TRIPOD+AI Validation Summary
================================
Total Items: {total}
Completed: {completed} ({completed/total*100:.1f}%)
Valid: {valid} ({valid/total*100:.1f}%)

Critical Missing Items: {len(critical_missing)}
"""

        if critical_missing:
            summary += f"Missing: {', '.join(critical_missing)}\n"

        return summary
