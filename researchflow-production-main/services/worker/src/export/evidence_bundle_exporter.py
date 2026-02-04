"""
Evidence Bundle Exporter Module

Exports evidence bundles to multiple formats including JSON, Markdown, PDF, and ZIP archives.
Supports comprehensive documentation of model cards, performance metrics, fairness analysis,
validation results, audit trails, and regulatory compliance information.

This module provides the EvidenceBundleExporter class for generating standardized evidence
bundles suitable for model governance, audit trails, and regulatory compliance documentation.
"""

import json
import os
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import logging

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
        Table,
        TableStyle,
        Image,
    )
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

from .exceptions import ExportError


logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    ZIP = "zip"


class EvidenceBundleMetadata:
    """Metadata for an evidence bundle."""

    def __init__(
        self,
        bundle_id: str,
        model_name: str,
        model_version: str,
        created_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        organization: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        Initialize evidence bundle metadata.

        Args:
            bundle_id: Unique identifier for the bundle.
            model_name: Name of the model being documented.
            model_version: Version of the model.
            created_at: Timestamp of bundle creation. Defaults to current time.
            created_by: Name of person/system creating the bundle.
            organization: Organization responsible for the model.
            description: Detailed description of the bundle purpose.
        """
        self.bundle_id = bundle_id
        self.model_name = model_name
        self.model_version = model_version
        self.created_at = created_at or datetime.utcnow()
        self.created_by = created_by
        self.organization = organization
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "bundle_id": self.bundle_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "organization": self.organization,
            "description": self.description,
        }


class ModelCard:
    """Model card documentation."""

    def __init__(
        self,
        model_name: str,
        model_version: str,
        description: str,
        intended_use: Optional[str] = None,
        training_data: Optional[str] = None,
        model_type: Optional[str] = None,
        architecture: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        limitations: Optional[List[str]] = None,
        ethical_considerations: Optional[str] = None,
    ):
        """
        Initialize a model card.

        Args:
            model_name: Name of the model.
            model_version: Version identifier.
            description: Model description.
            intended_use: Intended use case(s) for the model.
            training_data: Description of training data.
            model_type: Type of model (e.g., "classifier", "regression").
            architecture: Architecture description.
            parameters: Model hyperparameters and configuration.
            limitations: Known limitations and failure modes.
            ethical_considerations: Ethical considerations for use.
        """
        self.model_name = model_name
        self.model_version = model_version
        self.description = description
        self.intended_use = intended_use
        self.training_data = training_data
        self.model_type = model_type
        self.architecture = architecture
        self.parameters = parameters or {}
        self.limitations = limitations or []
        self.ethical_considerations = ethical_considerations

    def to_dict(self) -> Dict[str, Any]:
        """Convert model card to dictionary."""
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "description": self.description,
            "intended_use": self.intended_use,
            "training_data": self.training_data,
            "model_type": self.model_type,
            "architecture": self.architecture,
            "parameters": self.parameters,
            "limitations": self.limitations,
            "ethical_considerations": self.ethical_considerations,
        }


class PerformanceMetrics:
    """Performance metrics for the model."""

    def __init__(
        self,
        metrics: Dict[str, float],
        evaluation_dataset: Optional[str] = None,
        evaluation_date: Optional[datetime] = None,
        confidence_intervals: Optional[Dict[str, tuple]] = None,
        confidence_level: float = 0.95,
    ):
        """
        Initialize performance metrics.

        Args:
            metrics: Dictionary of metric names to values.
            evaluation_dataset: Description of evaluation dataset.
            evaluation_date: Date of evaluation.
            confidence_intervals: Confidence intervals for metrics (metric_name -> (lower, upper)).
            confidence_level: Confidence level used (default 95%).
        """
        self.metrics = metrics
        self.evaluation_dataset = evaluation_dataset
        self.evaluation_date = evaluation_date or datetime.utcnow()
        self.confidence_intervals = confidence_intervals or {}
        self.confidence_level = confidence_level

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metrics": self.metrics,
            "evaluation_dataset": self.evaluation_dataset,
            "evaluation_date": self.evaluation_date.isoformat(),
            "confidence_intervals": {
                k: {"lower": v[0], "upper": v[1]}
                for k, v in self.confidence_intervals.items()
            },
            "confidence_level": self.confidence_level,
        }


class FairnessAnalysis:
    """Fairness analysis and bias metrics."""

    def __init__(
        self,
        fairness_metrics: Dict[str, float],
        protected_attributes: Optional[List[str]] = None,
        disparate_impact_ratio: Optional[Dict[str, float]] = None,
        bias_assessment: Optional[str] = None,
        mitigation_strategies: Optional[List[str]] = None,
    ):
        """
        Initialize fairness analysis.

        Args:
            fairness_metrics: Dictionary of fairness metrics.
            protected_attributes: List of protected attributes analyzed.
            disparate_impact_ratio: Disparate impact ratios by attribute.
            bias_assessment: Overall bias assessment narrative.
            mitigation_strategies: List of bias mitigation strategies applied.
        """
        self.fairness_metrics = fairness_metrics
        self.protected_attributes = protected_attributes or []
        self.disparate_impact_ratio = disparate_impact_ratio or {}
        self.bias_assessment = bias_assessment
        self.mitigation_strategies = mitigation_strategies or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fairness_metrics": self.fairness_metrics,
            "protected_attributes": self.protected_attributes,
            "disparate_impact_ratio": self.disparate_impact_ratio,
            "bias_assessment": self.bias_assessment,
            "mitigation_strategies": self.mitigation_strategies,
        }


class ValidationResults:
    """Validation and testing results."""

    def __init__(
        self,
        test_suites: Dict[str, Dict[str, Any]],
        overall_status: str = "passed",
        test_coverage: Optional[float] = None,
        failure_cases: Optional[List[Dict[str, Any]]] = None,
        validation_date: Optional[datetime] = None,
    ):
        """
        Initialize validation results.

        Args:
            test_suites: Dictionary mapping test suite names to test results.
            overall_status: Overall validation status (passed/failed/partial).
            test_coverage: Code/feature test coverage percentage.
            failure_cases: List of documented failure cases.
            validation_date: Date validation was performed.
        """
        self.test_suites = test_suites
        self.overall_status = overall_status
        self.test_coverage = test_coverage
        self.failure_cases = failure_cases or []
        self.validation_date = validation_date or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_suites": self.test_suites,
            "overall_status": self.overall_status,
            "test_coverage": self.test_coverage,
            "failure_cases": self.failure_cases,
            "validation_date": self.validation_date.isoformat(),
        }


class AuditTrail:
    """Audit trail for model changes and decisions."""

    def __init__(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
        chain_of_custody: Optional[List[str]] = None,
    ):
        """
        Initialize audit trail.

        Args:
            events: List of audit events (timestamp, action, actor, details).
            chain_of_custody: Chain of custody for model artifacts.
        """
        self.events = events or []
        self.chain_of_custody = chain_of_custody or []

    def add_event(
        self,
        action: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Add an event to the audit trail.

        Args:
            action: Type of action (e.g., "model_creation", "parameter_update").
            actor: Who performed the action.
            details: Additional event details.
            timestamp: When the event occurred.
        """
        event = {
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "action": action,
            "actor": actor,
            "details": details or {},
        }
        self.events.append(event)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "events": self.events,
            "chain_of_custody": self.chain_of_custody,
        }


class RegulatoryCompliance:
    """Regulatory compliance documentation."""

    def __init__(
        self,
        applicable_regulations: Optional[List[str]] = None,
        compliance_status: Optional[Dict[str, str]] = None,
        certifications: Optional[List[str]] = None,
        data_governance: Optional[Dict[str, Any]] = None,
        privacy_measures: Optional[List[str]] = None,
        security_measures: Optional[List[str]] = None,
    ):
        """
        Initialize regulatory compliance information.

        Args:
            applicable_regulations: List of applicable regulations (HIPAA, GDPR, etc.).
            compliance_status: Compliance status for each regulation.
            certifications: List of certifications and standards met.
            data_governance: Data governance policies and procedures.
            privacy_measures: Privacy protection measures implemented.
            security_measures: Security measures implemented.
        """
        self.applicable_regulations = applicable_regulations or []
        self.compliance_status = compliance_status or {}
        self.certifications = certifications or []
        self.data_governance = data_governance or {}
        self.privacy_measures = privacy_measures or []
        self.security_measures = security_measures or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "applicable_regulations": self.applicable_regulations,
            "compliance_status": self.compliance_status,
            "certifications": self.certifications,
            "data_governance": self.data_governance,
            "privacy_measures": self.privacy_measures,
            "security_measures": self.security_measures,
        }


class EvidenceBundle:
    """Complete evidence bundle containing all documentation."""

    def __init__(
        self,
        metadata: EvidenceBundleMetadata,
        model_card: ModelCard,
        performance_metrics: PerformanceMetrics,
        fairness_analysis: Optional[FairnessAnalysis] = None,
        validation_results: Optional[ValidationResults] = None,
        audit_trail: Optional[AuditTrail] = None,
        regulatory_compliance: Optional[RegulatoryCompliance] = None,
    ):
        """
        Initialize an evidence bundle.

        Args:
            metadata: Bundle metadata.
            model_card: Model card documentation.
            performance_metrics: Model performance metrics.
            fairness_analysis: Fairness analysis (optional).
            validation_results: Validation results (optional).
            audit_trail: Audit trail (optional).
            regulatory_compliance: Regulatory compliance info (optional).
        """
        self.metadata = metadata
        self.model_card = model_card
        self.performance_metrics = performance_metrics
        self.fairness_analysis = fairness_analysis
        self.validation_results = validation_results
        self.audit_trail = audit_trail
        self.regulatory_compliance = regulatory_compliance

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire bundle to dictionary."""
        bundle_dict = {
            "metadata": self.metadata.to_dict(),
            "model_card": self.model_card.to_dict(),
            "performance_metrics": self.performance_metrics.to_dict(),
        }

        if self.fairness_analysis:
            bundle_dict["fairness_analysis"] = self.fairness_analysis.to_dict()
        if self.validation_results:
            bundle_dict["validation_results"] = self.validation_results.to_dict()
        if self.audit_trail:
            bundle_dict["audit_trail"] = self.audit_trail.to_dict()
        if self.regulatory_compliance:
            bundle_dict["regulatory_compliance"] = (
                self.regulatory_compliance.to_dict()
            )

        return bundle_dict


class BaseExporter(ABC):
    """Abstract base class for exporters."""

    @abstractmethod
    def export(self, bundle: EvidenceBundle, output_path: str) -> str:
        """
        Export a bundle to the specified format.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the export.

        Returns:
            Path to the exported file.

        Raises:
            ExportError: If export fails.
        """
        pass


class JSONExporter(BaseExporter):
    """Exporter for JSON format."""

    def export(self, bundle: EvidenceBundle, output_path: str) -> str:
        """
        Export bundle to JSON format.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the JSON file.

        Returns:
            Path to the exported JSON file.

        Raises:
            ExportError: If export fails.
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            bundle_dict = bundle.to_dict()

            with open(output_file, "w") as f:
                json.dump(bundle_dict, f, indent=2, default=str)

            logger.info(f"Exported bundle to JSON: {output_file}")
            return str(output_file)
        except Exception as e:
            raise ExportError(f"Failed to export bundle to JSON: {str(e)}") from e


class MarkdownExporter(BaseExporter):
    """Exporter for Markdown format."""

    def export(self, bundle: EvidenceBundle, output_path: str) -> str:
        """
        Export bundle to Markdown format.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the Markdown file.

        Returns:
            Path to the exported Markdown file.

        Raises:
            ExportError: If export fails.
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            content = self._generate_markdown(bundle)

            with open(output_file, "w") as f:
                f.write(content)

            logger.info(f"Exported bundle to Markdown: {output_file}")
            return str(output_file)
        except Exception as e:
            raise ExportError(
                f"Failed to export bundle to Markdown: {str(e)}"
            ) from e

    def _generate_markdown(self, bundle: EvidenceBundle) -> str:
        """Generate Markdown content for the bundle."""
        lines = []

        # Header
        lines.append("# Evidence Bundle Report")
        lines.append("")

        # Metadata
        lines.extend(self._format_metadata(bundle.metadata))
        lines.append("")

        # Model Card
        lines.extend(self._format_model_card(bundle.model_card))
        lines.append("")

        # Performance Metrics
        lines.extend(self._format_performance_metrics(bundle.performance_metrics))
        lines.append("")

        # Fairness Analysis
        if bundle.fairness_analysis:
            lines.extend(self._format_fairness_analysis(bundle.fairness_analysis))
            lines.append("")

        # Validation Results
        if bundle.validation_results:
            lines.extend(self._format_validation_results(bundle.validation_results))
            lines.append("")

        # Audit Trail
        if bundle.audit_trail:
            lines.extend(self._format_audit_trail(bundle.audit_trail))
            lines.append("")

        # Regulatory Compliance
        if bundle.regulatory_compliance:
            lines.extend(
                self._format_regulatory_compliance(bundle.regulatory_compliance)
            )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_metadata(metadata: EvidenceBundleMetadata) -> List[str]:
        """Format metadata section."""
        lines = [
            "## Metadata",
            "",
            f"- **Bundle ID**: {metadata.bundle_id}",
            f"- **Model Name**: {metadata.model_name}",
            f"- **Model Version**: {metadata.model_version}",
            f"- **Created At**: {metadata.created_at.isoformat()}",
        ]
        if metadata.created_by:
            lines.append(f"- **Created By**: {metadata.created_by}")
        if metadata.organization:
            lines.append(f"- **Organization**: {metadata.organization}")
        if metadata.description:
            lines.append(f"- **Description**: {metadata.description}")
        return lines

    @staticmethod
    def _format_model_card(model_card: ModelCard) -> List[str]:
        """Format model card section."""
        lines = [
            "## Model Card",
            "",
            f"### Basic Information",
            f"- **Model Name**: {model_card.model_name}",
            f"- **Version**: {model_card.model_version}",
            f"- **Type**: {model_card.model_type or 'Not specified'}",
            f"- **Description**: {model_card.description}",
            "",
        ]

        if model_card.intended_use:
            lines.extend(
                [
                    f"### Intended Use",
                    f"{model_card.intended_use}",
                    "",
                ]
            )

        if model_card.training_data:
            lines.extend(
                [
                    f"### Training Data",
                    f"{model_card.training_data}",
                    "",
                ]
            )

        if model_card.architecture:
            lines.extend(
                [
                    f"### Architecture",
                    f"{model_card.architecture}",
                    "",
                ]
            )

        if model_card.parameters:
            lines.append("### Parameters")
            for key, value in model_card.parameters.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")

        if model_card.limitations:
            lines.append("### Limitations")
            for limitation in model_card.limitations:
                lines.append(f"- {limitation}")
            lines.append("")

        if model_card.ethical_considerations:
            lines.extend(
                [
                    f"### Ethical Considerations",
                    f"{model_card.ethical_considerations}",
                    "",
                ]
            )

        return lines

    @staticmethod
    def _format_performance_metrics(metrics: PerformanceMetrics) -> List[str]:
        """Format performance metrics section."""
        lines = [
            "## Performance Metrics",
            "",
            f"**Evaluation Date**: {metrics.evaluation_date.isoformat()}",
            "",
        ]

        if metrics.evaluation_dataset:
            lines.extend(
                [
                    f"**Dataset**: {metrics.evaluation_dataset}",
                    "",
                ]
            )

        lines.append("### Metrics")
        for metric_name, metric_value in metrics.metrics.items():
            if metric_name in metrics.confidence_intervals:
                lower, upper = metrics.confidence_intervals[metric_name]
                lines.append(
                    f"- **{metric_name}**: {metric_value:.4f} "
                    f"(95% CI: [{lower:.4f}, {upper:.4f}])"
                )
            else:
                lines.append(f"- **{metric_name}**: {metric_value:.4f}")

        return lines

    @staticmethod
    def _format_fairness_analysis(fairness: FairnessAnalysis) -> List[str]:
        """Format fairness analysis section."""
        lines = [
            "## Fairness Analysis",
            "",
        ]

        if fairness.protected_attributes:
            lines.append("### Protected Attributes")
            for attr in fairness.protected_attributes:
                lines.append(f"- {attr}")
            lines.append("")

        lines.append("### Fairness Metrics")
        for metric_name, metric_value in fairness.fairness_metrics.items():
            lines.append(f"- **{metric_name}**: {metric_value:.4f}")
        lines.append("")

        if fairness.disparate_impact_ratio:
            lines.append("### Disparate Impact Ratios")
            for attr, ratio in fairness.disparate_impact_ratio.items():
                lines.append(f"- **{attr}**: {ratio:.4f}")
            lines.append("")

        if fairness.bias_assessment:
            lines.extend(
                [
                    "### Overall Bias Assessment",
                    fairness.bias_assessment,
                    "",
                ]
            )

        if fairness.mitigation_strategies:
            lines.append("### Mitigation Strategies")
            for strategy in fairness.mitigation_strategies:
                lines.append(f"- {strategy}")

        return lines

    @staticmethod
    def _format_validation_results(validation: ValidationResults) -> List[str]:
        """Format validation results section."""
        lines = [
            "## Validation Results",
            "",
            f"**Status**: {validation.overall_status}",
            f"**Validation Date**: {validation.validation_date.isoformat()}",
            "",
        ]

        if validation.test_coverage:
            lines.append(f"**Test Coverage**: {validation.test_coverage:.1f}%")
            lines.append("")

        lines.append("### Test Suites")
        for suite_name, suite_results in validation.test_suites.items():
            lines.append(f"- **{suite_name}**: {suite_results}")
        lines.append("")

        if validation.failure_cases:
            lines.append("### Documented Failure Cases")
            for idx, failure in enumerate(validation.failure_cases, 1):
                lines.append(f"{idx}. {failure}")

        return lines

    @staticmethod
    def _format_audit_trail(audit: AuditTrail) -> List[str]:
        """Format audit trail section."""
        lines = [
            "## Audit Trail",
            "",
        ]

        if audit.events:
            lines.append("### Events")
            for event in audit.events:
                lines.append(f"- **{event['action']}** by {event['actor']}")
                lines.append(f"  - Timestamp: {event['timestamp']}")
                if event.get("details"):
                    lines.append(f"  - Details: {event['details']}")
            lines.append("")

        if audit.chain_of_custody:
            lines.append("### Chain of Custody")
            for custody_item in audit.chain_of_custody:
                lines.append(f"- {custody_item}")

        return lines

    @staticmethod
    def _format_regulatory_compliance(compliance: RegulatoryCompliance) -> List[str]:
        """Format regulatory compliance section."""
        lines = [
            "## Regulatory Compliance",
            "",
        ]

        if compliance.applicable_regulations:
            lines.append("### Applicable Regulations")
            for regulation in compliance.applicable_regulations:
                status = compliance.compliance_status.get(regulation, "Unknown")
                lines.append(f"- **{regulation}**: {status}")
            lines.append("")

        if compliance.certifications:
            lines.append("### Certifications")
            for cert in compliance.certifications:
                lines.append(f"- {cert}")
            lines.append("")

        if compliance.privacy_measures:
            lines.append("### Privacy Measures")
            for measure in compliance.privacy_measures:
                lines.append(f"- {measure}")
            lines.append("")

        if compliance.security_measures:
            lines.append("### Security Measures")
            for measure in compliance.security_measures:
                lines.append(f"- {measure}")

        return lines


class PDFExporter(BaseExporter):
    """Exporter for PDF format."""

    def __init__(self, page_size: str = "letter"):
        """
        Initialize PDF exporter.

        Args:
            page_size: Page size ('letter' or 'a4').
        """
        if not REPORTLAB_AVAILABLE:
            raise ExportError(
                "reportlab is required for PDF export. "
                "Install it with: pip install reportlab"
            )
        self.page_size = A4 if page_size.lower() == "a4" else letter

    def export(self, bundle: EvidenceBundle, output_path: str) -> str:
        """
        Export bundle to PDF format using reportlab.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the PDF file.

        Returns:
            Path to the exported PDF file.

        Raises:
            ExportError: If export fails.
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Create PDF document
            doc = SimpleDocTemplate(
                str(output_file),
                pagesize=self.page_size,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.75 * inch,
                bottomMargin=0.75 * inch,
            )

            # Build story
            story = self._build_pdf_story(bundle)

            # Build PDF
            doc.build(story)

            logger.info(f"Exported bundle to PDF: {output_file}")
            return str(output_file)
        except Exception as e:
            raise ExportError(f"Failed to export bundle to PDF: {str(e)}") from e

    def _build_pdf_story(self, bundle: EvidenceBundle) -> List[Any]:
        """Build the PDF story (content)."""
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1f4788"),
            spaceAfter=30,
            alignment=1,  # CENTER
        )
        story.append(Paragraph("Evidence Bundle Report", title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Metadata
        story.extend(self._build_metadata_section(bundle.metadata, styles))
        story.append(PageBreak())

        # Model Card
        story.extend(self._build_model_card_section(bundle.model_card, styles))
        story.append(PageBreak())

        # Performance Metrics
        story.extend(
            self._build_performance_metrics_section(
                bundle.performance_metrics, styles
            )
        )
        story.append(PageBreak())

        # Fairness Analysis
        if bundle.fairness_analysis:
            story.extend(
                self._build_fairness_analysis_section(
                    bundle.fairness_analysis, styles
                )
            )
            story.append(PageBreak())

        # Validation Results
        if bundle.validation_results:
            story.extend(
                self._build_validation_results_section(
                    bundle.validation_results, styles
                )
            )
            story.append(PageBreak())

        # Audit Trail
        if bundle.audit_trail:
            story.extend(self._build_audit_trail_section(bundle.audit_trail, styles))
            story.append(PageBreak())

        # Regulatory Compliance
        if bundle.regulatory_compliance:
            story.extend(
                self._build_regulatory_compliance_section(
                    bundle.regulatory_compliance, styles
                )
            )

        return story

    @staticmethod
    def _build_metadata_section(metadata: EvidenceBundleMetadata,
                                 styles) -> List[Any]:
        """Build metadata section."""
        story = []
        story.append(Paragraph("Metadata", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        data = [
            ["Bundle ID", metadata.bundle_id],
            ["Model Name", metadata.model_name],
            ["Model Version", metadata.model_version],
            ["Created At", metadata.created_at.isoformat()],
        ]

        if metadata.created_by:
            data.append(["Created By", metadata.created_by])
        if metadata.organization:
            data.append(["Organization", metadata.organization])
        if metadata.description:
            data.append(["Description", metadata.description])

        table = Table(data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1f5")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)
        return story

    @staticmethod
    def _build_model_card_section(model_card: ModelCard, styles) -> List[Any]:
        """Build model card section."""
        story = []
        story.append(Paragraph("Model Card", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("Basic Information", styles["Heading3"]))
        story.append(Spacer(1, 0.1 * inch))

        data = [
            ["Model Name", model_card.model_name],
            ["Version", model_card.model_version],
            ["Type", model_card.model_type or "Not specified"],
            ["Description", model_card.description],
        ]

        table = Table(data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f1f5")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))

        if model_card.intended_use:
            story.append(Paragraph("Intended Use", styles["Heading3"]))
            story.append(Paragraph(model_card.intended_use, styles["BodyText"]))
            story.append(Spacer(1, 0.2 * inch))

        if model_card.training_data:
            story.append(Paragraph("Training Data", styles["Heading3"]))
            story.append(Paragraph(model_card.training_data, styles["BodyText"]))
            story.append(Spacer(1, 0.2 * inch))

        if model_card.limitations:
            story.append(Paragraph("Limitations", styles["Heading3"]))
            for limitation in model_card.limitations:
                story.append(
                    Paragraph(f"• {limitation}", styles["BodyText"])
                )
            story.append(Spacer(1, 0.2 * inch))

        return story

    @staticmethod
    def _build_performance_metrics_section(metrics: PerformanceMetrics,
                                            styles) -> List[Any]:
        """Build performance metrics section."""
        story = []
        story.append(Paragraph("Performance Metrics", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        story.append(
            Paragraph(
                f"Evaluation Date: {metrics.evaluation_date.isoformat()}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.1 * inch))

        data = [["Metric", "Value"]]
        for metric_name, metric_value in metrics.metrics.items():
            data.append([metric_name, f"{metric_value:.4f}"])

        table = Table(data, colWidths=[2.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)
        return story

    @staticmethod
    def _build_fairness_analysis_section(fairness: FairnessAnalysis,
                                          styles) -> List[Any]:
        """Build fairness analysis section."""
        story = []
        story.append(Paragraph("Fairness Analysis", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        if fairness.protected_attributes:
            story.append(Paragraph("Protected Attributes", styles["Heading3"]))
            for attr in fairness.protected_attributes:
                story.append(Paragraph(f"• {attr}", styles["BodyText"]))
            story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph("Fairness Metrics", styles["Heading3"]))
        data = [["Metric", "Value"]]
        for metric_name, metric_value in fairness.fairness_metrics.items():
            data.append([metric_name, f"{metric_value:.4f}"])

        table = Table(data, colWidths=[2.5 * inch, 2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

        if fairness.bias_assessment:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Overall Bias Assessment", styles["Heading3"]))
            story.append(Paragraph(fairness.bias_assessment, styles["BodyText"]))

        return story

    @staticmethod
    def _build_validation_results_section(validation: ValidationResults,
                                           styles) -> List[Any]:
        """Build validation results section."""
        story = []
        story.append(Paragraph("Validation Results", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        status_text = f"Overall Status: <b>{validation.overall_status.upper()}</b>"
        story.append(Paragraph(status_text, styles["Normal"]))

        if validation.test_coverage:
            story.append(
                Paragraph(
                    f"Test Coverage: {validation.test_coverage:.1f}%",
                    styles["Normal"],
                )
            )

        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Test Suites", styles["Heading3"]))

        data = [["Suite", "Results"]]
        for suite_name, suite_results in validation.test_suites.items():
            data.append([suite_name, str(suite_results)])

        table = Table(data, colWidths=[2 * inch, 3.5 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

        return story

    @staticmethod
    def _build_audit_trail_section(audit: AuditTrail, styles) -> List[Any]:
        """Build audit trail section."""
        story = []
        story.append(Paragraph("Audit Trail", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        if audit.events:
            story.append(Paragraph("Events", styles["Heading3"]))
            for event in audit.events[:10]:  # Limit to first 10 events
                event_text = f"<b>{event['action']}</b> by {event['actor']}"
                story.append(Paragraph(event_text, styles["BodyText"]))
                story.append(
                    Paragraph(
                        f"<i>Timestamp: {event['timestamp']}</i>",
                        styles["Normal"],
                    )
                )
            story.append(Spacer(1, 0.15 * inch))

        return story

    @staticmethod
    def _build_regulatory_compliance_section(compliance: RegulatoryCompliance,
                                              styles) -> List[Any]:
        """Build regulatory compliance section."""
        story = []
        story.append(Paragraph("Regulatory Compliance", styles["Heading2"]))
        story.append(Spacer(1, 0.2 * inch))

        if compliance.applicable_regulations:
            story.append(Paragraph("Applicable Regulations", styles["Heading3"]))
            data = [["Regulation", "Status"]]
            for regulation in compliance.applicable_regulations:
                status = compliance.compliance_status.get(regulation, "Unknown")
                data.append([regulation, status])

            table = Table(data, colWidths=[2.5 * inch, 2 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(table)

        return story


class ZipArchiveExporter(BaseExporter):
    """Exporter for ZIP archive format."""

    def export(self, bundle: EvidenceBundle, output_path: str) -> str:
        """
        Export bundle as a ZIP archive containing multiple formats.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the ZIP file.

        Returns:
            Path to the exported ZIP file.

        Raises:
            ExportError: If export fails.
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            temp_dir = output_file.parent / f".temp_{output_file.stem}"
            temp_dir.mkdir(exist_ok=True)

            try:
                # Export to all formats
                json_exporter = JSONExporter()
                markdown_exporter = MarkdownExporter()

                bundle_id = bundle.metadata.bundle_id
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

                json_path = temp_dir / f"{bundle_id}_evidence_bundle.json"
                markdown_path = temp_dir / f"{bundle_id}_evidence_bundle.md"

                json_exporter.export(bundle, str(json_path))
                markdown_exporter.export(bundle, str(markdown_path))

                # Try to export PDF if reportlab is available
                pdf_path = None
                if REPORTLAB_AVAILABLE:
                    try:
                        pdf_exporter = PDFExporter()
                        pdf_path = temp_dir / f"{bundle_id}_evidence_bundle.pdf"
                        pdf_exporter.export(bundle, str(pdf_path))
                    except Exception as e:
                        logger.warning(f"Could not export PDF: {str(e)}")

                # Create ZIP archive
                with zipfile.ZipFile(
                    output_file, "w", zipfile.ZIP_DEFLATED
                ) as zipf:
                    zipf.write(json_path, arcname=json_path.name)
                    zipf.write(markdown_path, arcname=markdown_path.name)
                    if pdf_path and pdf_path.exists():
                        zipf.write(pdf_path, arcname=pdf_path.name)

                    # Add metadata file
                    metadata_content = f"""Evidence Bundle Archive
Bundle ID: {bundle.metadata.bundle_id}
Model: {bundle.metadata.model_name}
Version: {bundle.metadata.model_version}
Created: {datetime.utcnow().isoformat()}

Contents:
- {json_path.name}: JSON export of the complete bundle
- {markdown_path.name}: Markdown formatted report
"""
                    if pdf_path:
                        metadata_content += f"- {pdf_path.name}: PDF formatted report\n"

                    zipf.writestr("README.txt", metadata_content)

                logger.info(f"Exported bundle to ZIP archive: {output_file}")
                return str(output_file)

            finally:
                # Clean up temp directory
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        except Exception as e:
            raise ExportError(
                f"Failed to export bundle to ZIP archive: {str(e)}"
            ) from e


class EvidenceBundleExporter:
    """
    Main class for exporting evidence bundles to multiple formats.

    This class provides a unified interface for exporting evidence bundles
    to JSON, Markdown, PDF, and ZIP archive formats.
    """

    def __init__(self):
        """Initialize the exporter."""
        self._exporters: Dict[ExportFormat, BaseExporter] = {
            ExportFormat.JSON: JSONExporter(),
            ExportFormat.MARKDOWN: MarkdownExporter(),
        }

        if REPORTLAB_AVAILABLE:
            self._exporters[ExportFormat.PDF] = PDFExporter()

        self._exporters[ExportFormat.ZIP] = ZipArchiveExporter()

    def export_to_json(
        self,
        bundle: EvidenceBundle,
        output_path: str,
    ) -> str:
        """
        Export bundle to JSON format.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the JSON file.

        Returns:
            Path to the exported JSON file.

        Raises:
            ExportError: If export fails.
        """
        return self._exporters[ExportFormat.JSON].export(bundle, output_path)

    def export_to_markdown(
        self,
        bundle: EvidenceBundle,
        output_path: str,
    ) -> str:
        """
        Export bundle to Markdown format.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the Markdown file.

        Returns:
            Path to the exported Markdown file.

        Raises:
            ExportError: If export fails.
        """
        return self._exporters[ExportFormat.MARKDOWN].export(bundle, output_path)

    def export_to_pdf(
        self,
        bundle: EvidenceBundle,
        output_path: str,
        page_size: str = "letter",
    ) -> str:
        """
        Export bundle to PDF format.

        Requires reportlab to be installed. Install with:
        pip install reportlab

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the PDF file.
            page_size: Page size ('letter' or 'a4').

        Returns:
            Path to the exported PDF file.

        Raises:
            ExportError: If reportlab is not available or export fails.
        """
        if not REPORTLAB_AVAILABLE:
            raise ExportError(
                "reportlab is required for PDF export. "
                "Install it with: pip install reportlab"
            )

        exporter = PDFExporter(page_size=page_size)
        return exporter.export(bundle, output_path)

    def export_to_archive(
        self,
        bundle: EvidenceBundle,
        output_path: str,
    ) -> str:
        """
        Export bundle as a ZIP archive containing multiple formats.

        Args:
            bundle: The evidence bundle to export.
            output_path: Path where to save the ZIP file.

        Returns:
            Path to the exported ZIP file.

        Raises:
            ExportError: If export fails.
        """
        return self._exporters[ExportFormat.ZIP].export(bundle, output_path)

    def export_all_formats(
        self,
        bundle: EvidenceBundle,
        output_directory: str,
    ) -> Dict[ExportFormat, str]:
        """
        Export bundle to all available formats.

        Args:
            bundle: The evidence bundle to export.
            output_directory: Directory where to save exported files.

        Returns:
            Dictionary mapping export formats to their file paths.

        Raises:
            ExportError: If any export fails.
        """
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        bundle_id = bundle.metadata.bundle_id
        results = {}

        # JSON
        try:
            json_path = output_dir / f"{bundle_id}_evidence_bundle.json"
            results[ExportFormat.JSON] = self.export_to_json(bundle, str(json_path))
        except ExportError as e:
            logger.error(f"JSON export failed: {str(e)}")
            raise

        # Markdown
        try:
            md_path = output_dir / f"{bundle_id}_evidence_bundle.md"
            results[ExportFormat.MARKDOWN] = self.export_to_markdown(
                bundle, str(md_path)
            )
        except ExportError as e:
            logger.error(f"Markdown export failed: {str(e)}")
            raise

        # PDF
        if REPORTLAB_AVAILABLE:
            try:
                pdf_path = output_dir / f"{bundle_id}_evidence_bundle.pdf"
                results[ExportFormat.PDF] = self.export_to_pdf(bundle, str(pdf_path))
            except ExportError as e:
                logger.warning(f"PDF export failed: {str(e)}")
                # Don't raise, PDF is optional

        # ZIP
        try:
            zip_path = output_dir / f"{bundle_id}_evidence_bundle.zip"
            results[ExportFormat.ZIP] = self.export_to_archive(bundle, str(zip_path))
        except ExportError as e:
            logger.error(f"ZIP export failed: {str(e)}")
            raise

        return results
