"""
Example usage of the Evidence Bundle Exporter module.

This file demonstrates how to create evidence bundles and export them
to various formats (JSON, Markdown, PDF, and ZIP archives).
"""

from datetime import datetime
from export.evidence_bundle_exporter import (
    EvidenceBundleExporter,
    EvidenceBundle,
    EvidenceBundleMetadata,
    ModelCard,
    PerformanceMetrics,
    FairnessAnalysis,
    ValidationResults,
    AuditTrail,
    RegulatoryCompliance,
)


def create_example_bundle() -> EvidenceBundle:
    """Create an example evidence bundle for demonstration."""

    # Create metadata
    metadata = EvidenceBundleMetadata(
        bundle_id="BUNDLE_2024_001",
        model_name="Clinical Risk Predictor",
        model_version="1.2.3",
        created_at=datetime.utcnow(),
        created_by="Data Science Team",
        organization="Healthcare Systems Inc.",
        description="Comprehensive evidence bundle for clinical risk prediction model",
    )

    # Create model card
    model_card = ModelCard(
        model_name="Clinical Risk Predictor",
        model_version="1.2.3",
        description="A machine learning model that predicts patient risk scores for various conditions",
        intended_use="Clinical decision support for patient risk stratification",
        training_data="Electronic health records from 500,000+ patients across 10 healthcare systems",
        model_type="Gradient Boosted Trees",
        architecture="XGBoost with 200 trees, max depth 8",
        parameters={
            "learning_rate": 0.1,
            "n_estimators": 200,
            "max_depth": 8,
            "min_child_weight": 1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
        },
        limitations=[
            "Model performance may vary in understudied populations",
            "Requires preprocessed input data in specific format",
            "Not intended for diagnosis, only for risk assessment",
            "Performance degrades with extreme patient characteristics",
        ],
        ethical_considerations=(
            "Model decisions should be reviewed by clinical staff. "
            "Transparency about model limitations is essential. "
            "Regular audits for bias across demographic groups recommended."
        ),
    )

    # Create performance metrics
    performance_metrics = PerformanceMetrics(
        metrics={
            "accuracy": 0.8742,
            "precision": 0.8621,
            "recall": 0.8945,
            "f1_score": 0.8781,
            "auc_roc": 0.9234,
            "specificity": 0.8523,
        },
        evaluation_dataset="Hold-out test set: 50,000 patients",
        evaluation_date=datetime.utcnow(),
        confidence_intervals={
            "accuracy": (0.8712, 0.8772),
            "auc_roc": (0.9201, 0.9267),
        },
        confidence_level=0.95,
    )

    # Create fairness analysis
    fairness_analysis = FairnessAnalysis(
        fairness_metrics={
            "demographic_parity_difference": 0.0234,
            "equalized_odds_difference": 0.0312,
            "calibration_gap": 0.0187,
        },
        protected_attributes=["age_group", "gender", "ethnicity", "socioeconomic_status"],
        disparate_impact_ratio={
            "age_group": 0.987,
            "gender": 0.992,
            "ethnicity": 0.954,
        },
        bias_assessment=(
            "Model shows generally good fairness metrics across demographics. "
            "Slight disparities noted in ethnicity (96.2% CI: 0.94-0.97). "
            "Continuous monitoring and rebalancing recommended."
        ),
        mitigation_strategies=[
            "Class weight rebalancing to address underrepresented groups",
            "Regular fairness audits on demographic subgroups",
            "Threshold adjustment for different risk groups",
            "Transparent documentation of model limitations",
        ],
    )

    # Create validation results
    validation_results = ValidationResults(
        test_suites={
            "unit_tests": {"passed": 245, "failed": 0, "coverage": 92},
            "integration_tests": {"passed": 78, "failed": 0},
            "performance_tests": {"passed": 15, "failed": 0, "avg_latency_ms": 45},
            "adversarial_tests": {"passed": 32, "failed": 2},
        },
        overall_status="passed",
        test_coverage=92.0,
        failure_cases=[
            {
                "scenario": "Extreme feature values",
                "description": "Model output becomes unreliable with extreme feature combinations",
                "mitigation": "Input validation and bounds checking implemented",
            },
            {
                "scenario": "Missing data patterns",
                "description": "Systematic missing data in certain features affects predictions",
                "mitigation": "Imputation strategy documented; warnings generated for high-missingness",
            },
        ],
        validation_date=datetime.utcnow(),
    )

    # Create audit trail
    audit_trail = AuditTrail()
    audit_trail.add_event(
        action="model_creation",
        actor="Dr. Jane Smith",
        details={"framework": "XGBoost", "python_version": "3.9"},
    )
    audit_trail.add_event(
        action="training_completed",
        actor="ML Pipeline",
        details={"training_time_hours": 12.5, "final_auc": 0.9234},
    )
    audit_trail.add_event(
        action="validation_passed",
        actor="QA Team",
        details={"tests_passed": 370, "tests_failed": 2},
    )
    audit_trail.add_event(
        action="approved_for_deployment",
        actor="Chief Data Officer",
        details={"approval_date": datetime.utcnow().isoformat()},
    )
    audit_trail.chain_of_custody = [
        "Model artifact: model_v1.2.3.pkl (SHA256: abc123...)",
        "Training data: ehr_dataset_q4_2023.parquet (Access: Restricted)",
        "Validation report: validation_results_q4_2023.json",
    ]

    # Create regulatory compliance
    regulatory_compliance = RegulatoryCompliance(
        applicable_regulations=[
            "HIPAA",
            "FDA Software as Medical Device Guidance",
            "GDPR",
            "State Data Privacy Laws",
        ],
        compliance_status={
            "HIPAA": "Compliant",
            "FDA Software as Medical Device Guidance": "Compliant",
            "GDPR": "Compliant",
            "State Data Privacy Laws": "Compliant",
        },
        certifications=[
            "ISO 13485 (Medical Devices)",
            "SOC 2 Type II",
            "HITRUST CSF Certified",
        ],
        data_governance={
            "data_retention_policy": "24 months",
            "data_deletion_procedure": "Secure purge with certificate of destruction",
            "access_control": "Role-based access control (RBAC) with audit logging",
        },
        privacy_measures=[
            "De-identification of PII before model training",
            "Encrypted storage of training data",
            "Differential privacy techniques applied",
            "Regular privacy impact assessments",
        ],
        security_measures=[
            "End-to-end encryption for data in transit",
            "Hardware security modules for key storage",
            "Regular penetration testing",
            "24/7 security monitoring and alerting",
            "Incident response procedures in place",
        ],
    )

    # Create the complete evidence bundle
    bundle = EvidenceBundle(
        metadata=metadata,
        model_card=model_card,
        performance_metrics=performance_metrics,
        fairness_analysis=fairness_analysis,
        validation_results=validation_results,
        audit_trail=audit_trail,
        regulatory_compliance=regulatory_compliance,
    )

    return bundle


def main():
    """Demonstrate evidence bundle creation and export."""
    print("Creating example evidence bundle...")
    bundle = create_example_bundle()

    print("Initializing exporter...")
    exporter = EvidenceBundleExporter()

    output_dir = "/tmp/evidence_bundles"

    # Export to JSON
    print("Exporting to JSON...")
    json_path = exporter.export_to_json(
        bundle,
        f"{output_dir}/example_bundle.json",
    )
    print(f"  Saved to: {json_path}")

    # Export to Markdown
    print("Exporting to Markdown...")
    md_path = exporter.export_to_markdown(
        bundle,
        f"{output_dir}/example_bundle.md",
    )
    print(f"  Saved to: {md_path}")

    # Export to PDF (if reportlab available)
    try:
        print("Exporting to PDF...")
        pdf_path = exporter.export_to_pdf(
            bundle,
            f"{output_dir}/example_bundle.pdf",
        )
        print(f"  Saved to: {pdf_path}")
    except Exception as e:
        print(f"  PDF export skipped: {e}")

    # Export to ZIP archive
    print("Exporting to ZIP archive...")
    zip_path = exporter.export_to_archive(
        bundle,
        f"{output_dir}/example_bundle.zip",
    )
    print(f"  Saved to: {zip_path}")

    # Export all formats
    print("\nExporting to all available formats...")
    results = exporter.export_all_formats(
        bundle,
        output_dir,
    )
    print("Export results:")
    for format_type, path in results.items():
        print(f"  {format_type.value}: {path}")

    print("\nAll exports completed successfully!")


if __name__ == "__main__":
    main()
