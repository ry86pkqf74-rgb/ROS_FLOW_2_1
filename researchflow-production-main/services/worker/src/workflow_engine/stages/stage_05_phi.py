"""
Stage 5: PHI Detection and Handling - PHIGuardAgent

This stage scans data for Protected Health Information (PHI) and
ensures proper handling according to HIPAA Safe Harbor requirements.

ROS-147 Enhancement:
- Inherits from BaseStageAgent for consistency with other stages
- HIPAA Safe Harbor compliance validation (18 identifiers)
- Column-level risk assessment (name patterns + value scanning)
- PHI redaction with audit logging
- Safe Harbor compliance validation

Phase 5 Enhancement:
- Supports Dask DataFrame using map_partitions
- Supports chunked iteration for large files
- Integrates with ingestion module configuration

Uses canonical PHI patterns from the generated module for consistency
with Node services.
"""

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from langchain_core.tools import BaseTool
    from langchain_core.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = Any  # type: ignore
    PromptTemplate = Any  # type: ignore

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

# Import enhanced PHI analyzers (Phase 1 enhancements)
try:
    from .phi_analyzers import (
        QuasiIdentifierAnalyzer,
        MLPhiDetector,
        MultiJurisdictionCompliance,
        ComplianceFramework,
        create_ml_phi_detector,
    )
    from ..audit import (
        PHIAuditChain,
        AuditEventType,
        StorageBackend,
    )
    ENHANCED_PHI_AVAILABLE = True
except ImportError:
    ENHANCED_PHI_AVAILABLE = False
    logger.warning("Enhanced PHI analyzers not available - using basic detection only")

# Import generated PHI patterns - single source of truth
from src.validation.phi_patterns_generated import (
    PHI_PATTERNS_HIGH_CONFIDENCE,
    PHI_PATTERNS_OUTPUT_GUARD,
)

# Import ingestion module for large-data support (Phase 5)
try:
    from src.ingestion import (
        IngestionConfig,
        get_ingestion_config,
        ingest_file_large,
        IngestionMetadata,
        DASK_AVAILABLE,
    )
    INGESTION_AVAILABLE = True
except ImportError:
    # Create type aliases to avoid NameError
    IngestionConfig = Optional[Dict[str, Any]]  # type: ignore
    get_ingestion_config = None
    ingest_file_large = None
    IngestionMetadata = None
    DASK_AVAILABLE = False
    INGESTION_AVAILABLE = False

# Import pandas for DataFrame handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

logger = logging.getLogger("workflow_engine.stages.stage_05_phi")

# HIPAA Safe Harbor 18 Identifiers (45 CFR 164.514(b)(2))
HIPAA_SAFE_HARBOR_18 = [
    "names",
    "geographic_subdivisions",
    "dates",
    "phone_numbers",
    "fax_numbers",
    "email_addresses",
    "social_security_numbers",
    "medical_record_numbers",
    "health_plan_beneficiary_numbers",
    "account_numbers",
    "certificate_license_numbers",
    "vehicle_identifiers",
    "device_identifiers",
    "web_urls",
    "ip_addresses",
    "biometric_identifiers",
    "photographs",
    "unique_identifying_numbers",
]

# Column name patterns for PHI risk assessment
PHI_COLUMN_NAME_PATTERNS = {
    "critical": [
        "patient_name", "name", "full_name", "first_name", "last_name",
        "ssn", "social_security", "social_security_number",
        "mrn", "medical_record", "patient_id", "patient_identifier",
    ],
    "high": [
        "dob", "date_of_birth", "birth_date", "birthdate",
        "email", "email_address", "e_mail",
        "phone", "telephone", "phone_number", "mobile", "cell",
        "address", "street_address", "home_address",
        "zip", "zip_code", "postal_code", "postcode",
    ],
    "medium": [
        "age", "age_at", "age_years",
        "account", "account_number", "acct",
        "license", "driver_license", "dl_number",
        "health_plan", "insurance", "policy_number",
    ],
    "low": [
        "date", "timestamp", "datetime",
        "ip", "ip_address",
        "url", "website", "web_address",
    ],
}

# Audit log storage (in-memory for now, can be extended to persist)
_audit_log_entries: List[Dict[str, Any]] = []


def hash_match(text: str) -> str:
    """Compute SHA256 hash of matched text (first 12 chars).

    CRITICAL: Never store raw PHI. Only hashes for deduplication.

    Args:
        text: Matched PHI text

    Returns:
        First 12 characters of SHA256 hash
    """
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def scan_text_for_phi(
    content: str,
    tier: str = "HIGH_CONFIDENCE"
) -> List[Dict[str, Any]]:
    """Scan text content for PHI patterns.

    Args:
        content: Text content to scan
        tier: Pattern tier to use ("HIGH_CONFIDENCE" or "OUTPUT_GUARD")

    Returns:
        List of PHI findings (hash-only, no raw values)
    """
    patterns = (
        PHI_PATTERNS_HIGH_CONFIDENCE
        if tier == "HIGH_CONFIDENCE"
        else PHI_PATTERNS_OUTPUT_GUARD
    )

    findings: List[Dict[str, Any]] = []

    for category, pattern in patterns:
        for match in pattern.finditer(content):
            # CRITICAL: Hash immediately, never store raw match
            match_text = match.group()
            findings.append({
                "category": category,
                "matchHash": hash_match(match_text),
                "matchLength": len(match_text),
                "position": {
                    "start": match.start(),
                    "end": match.end(),
                },
            })

    return findings


def assess_column_risk(
    column_name: str,
    findings_in_column: List[Dict[str, Any]],
    df: Optional["pd.DataFrame"] = None,
) -> Dict[str, Any]:
    """Assess risk level for a column based on name patterns and PHI findings.

    Args:
        column_name: Name of the column
        findings_in_column: List of PHI findings in this column
        df: Optional DataFrame to check for quasi-identifiers

    Returns:
        Risk assessment dict with level, reasons, and recommendations
    """
    col_lower = column_name.lower()
    risk_level = "none"
    reasons: List[str] = []
    categories_found = set(f.get("category") for f in findings_in_column)

    # Check column name patterns
    name_based_risk = None
    for level, patterns in PHI_COLUMN_NAME_PATTERNS.items():
        if any(pattern in col_lower for pattern in patterns):
            name_based_risk = level
            reasons.append(f"Column name matches {level} risk pattern")
            break

    # Check value-based findings
    value_based_risk = None
    if findings_in_column:
        critical_categories = {"SSN", "MRN", "EMAIL", "PHONE"}
        high_categories = {"DOB", "NAME", "ADDRESS", "ZIP_CODE"}
        
        if any(f.get("category") in critical_categories for f in findings_in_column):
            value_based_risk = "critical"
            reasons.append("Critical PHI categories detected in values")
        elif any(f.get("category") in high_categories for f in findings_in_column):
            value_based_risk = "high"
            reasons.append("High-risk PHI categories detected in values")
        elif len(findings_in_column) > 10:
            value_based_risk = "medium"
            reasons.append(f"Multiple PHI findings ({len(findings_in_column)})")
        else:
            value_based_risk = "low"
            reasons.append(f"PHI detected ({len(findings_in_column)} findings)")

    # Determine overall risk (highest of name-based and value-based)
    risk_levels = ["none", "low", "medium", "high", "critical"]
    risk_scores = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    
    max_score = 0
    if name_based_risk:
        max_score = max(max_score, risk_scores.get(name_based_risk, 0))
    if value_based_risk:
        max_score = max(max_score, risk_scores.get(value_based_risk, 0))
    
    risk_level = risk_levels[min(max_score, len(risk_levels) - 1)]

    # Check for quasi-identifiers (date + ZIP + age combinations)
    quasi_identifier_risk = False
    if df is not None and column_name in df.columns:
        # Check if this column is part of a quasi-identifier combination
        date_cols = [c for c in df.columns if any(p in c.lower() for p in ["date", "dob", "birth"])]
        zip_cols = [c for c in df.columns if any(p in c.lower() for p in ["zip", "postal"])]
        age_cols = [c for c in df.columns if any(p in c.lower() for p in ["age"])]
        
        if (column_name in date_cols and zip_cols and age_cols) or \
           (column_name in zip_cols and date_cols and age_cols) or \
           (column_name in age_cols and date_cols and zip_cols):
            quasi_identifier_risk = True
            reasons.append("Part of quasi-identifier combination (date+ZIP+age)")

    recommendations = []
    if risk_level in ("high", "critical"):
        recommendations.append("redact_or_pseudonymize")
    elif risk_level == "medium":
        recommendations.append("generalize_or_redact")
    elif quasi_identifier_risk:
        recommendations.append("generalize_to_safe_level")
    elif risk_level == "low":
        recommendations.append("review_and_consider_redaction")

    return {
        "risk_level": risk_level,
        "name_based_risk": name_based_risk,
        "value_based_risk": value_based_risk,
        "quasi_identifier_risk": quasi_identifier_risk,
        "reasons": reasons,
        "categories_found": list(categories_found),
        "findings_count": len(findings_in_column),
        "recommendations": recommendations,
    }


def scan_dataframe_for_phi(
    df: "pd.DataFrame",
    tier: str = "HIGH_CONFIDENCE",
    chunk_index: Optional[int] = None,
    assess_risk: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Scan a pandas DataFrame for PHI patterns with risk assessment.
    
    Scans all string columns for PHI and optionally assesses column-level risk.
    
    Args:
        df: DataFrame to scan
        tier: Pattern tier to use
        chunk_index: Optional chunk/partition index for tracking
        assess_risk: Whether to perform column-level risk assessment
        
    Returns:
        Tuple of (findings list, column_risk_assessments dict)
    """
    findings: List[Dict[str, Any]] = []
    column_risks: Dict[str, Dict[str, Any]] = {}
    
    # Identify string columns
    string_cols = df.select_dtypes(include=['object', 'string']).columns
    
    for col in string_cols:
        col_findings: List[Dict[str, Any]] = []
        
        for row_idx, value in enumerate(df[col]):
            if pd.isna(value):
                continue
            
            content = str(value)
            cell_findings = scan_text_for_phi(content, tier=tier)
            
            for finding in cell_findings:
                finding["column"] = col
                finding["row"] = row_idx
                if chunk_index is not None:
                    finding["chunk_index"] = chunk_index
                findings.append(finding)
                col_findings.append(finding)
        
        # Assess column-level risk if requested
        if assess_risk:
            column_risks[col] = assess_column_risk(col, col_findings, df)
    
    return findings, column_risks


def scan_dask_dataframe_for_phi(
    ddf: Any,  # dask.dataframe.DataFrame
    tier: str = "HIGH_CONFIDENCE",
    max_partitions: int = 100,
    assess_risk: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Scan a Dask DataFrame for PHI using map_partitions.
    
    Args:
        ddf: Dask DataFrame to scan
        tier: Pattern tier to use
        max_partitions: Maximum partitions to scan (for safety)
        assess_risk: Whether to perform column-level risk assessment
        
    Returns:
        Tuple of (findings, scan_metadata, column_risk_assessments)
    """
    if not DASK_AVAILABLE:
        return [], {"error": "Dask not available"}, {}
    
    all_findings: List[Dict[str, Any]] = []
    partitions_scanned = 0
    total_rows = 0
    all_column_risks: Dict[str, Dict[str, Any]] = {}
    
    num_partitions = min(ddf.npartitions, max_partitions)
    
    # Sample first partition for risk assessment
    sample_df = None
    if assess_risk and num_partitions > 0:
        try:
            sample_df = ddf.get_partition(0).compute()
        except Exception as e:
            logger.warning(f"Could not sample partition for risk assessment: {e}")
    
    for i in range(num_partitions):
        try:
            partition_df = ddf.get_partition(i).compute()
            partition_findings, partition_risks = scan_dataframe_for_phi(
                partition_df, 
                tier=tier, 
                chunk_index=i,
                assess_risk=(i == 0) if assess_risk else False,  # Only assess first partition
            )
            all_findings.extend(partition_findings)
            total_rows += len(partition_df)
            partitions_scanned += 1
            
            # Merge column risks (from first partition)
            if i == 0:
                all_column_risks.update(partition_risks)
        except Exception as e:
            logger.warning(f"Error scanning partition {i}: {e}")
    
    metadata = {
        "partitions_scanned": partitions_scanned,
        "total_partitions": ddf.npartitions,
        "rows_scanned": total_rows,
        "scan_mode": "dask_partitioned",
    }
    
    return all_findings, metadata, all_column_risks


def scan_chunked_iterator_for_phi(
    reader: Any,  # TextFileReader
    tier: str = "HIGH_CONFIDENCE",
    max_chunks: int = 100,
    assess_risk: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Scan a chunked iterator (TextFileReader) for PHI.
    
    Note: This consumes the iterator.
    
    Args:
        reader: Chunked file reader
        tier: Pattern tier to use
        max_chunks: Maximum chunks to scan (for safety)
        assess_risk: Whether to perform column-level risk assessment
        
    Returns:
        Tuple of (findings, scan_metadata, column_risk_assessments)
    """
    all_findings: List[Dict[str, Any]] = []
    chunks_scanned = 0
    total_rows = 0
    all_column_risks: Dict[str, Dict[str, Any]] = {}
    
    for i, chunk_df in enumerate(reader):
        if i >= max_chunks:
            logger.warning(f"Reached max_chunks limit ({max_chunks})")
            break
        
        chunk_findings, chunk_risks = scan_dataframe_for_phi(
            chunk_df,
            tier=tier,
            chunk_index=i,
            assess_risk=(i == 0) if assess_risk else False,  # Only assess first chunk
        )
        all_findings.extend(chunk_findings)
        total_rows += len(chunk_df)
        chunks_scanned += 1
        
        # Merge column risks (from first chunk)
        if i == 0:
            all_column_risks.update(chunk_risks)
    
    metadata = {
        "chunks_scanned": chunks_scanned,
        "rows_scanned": total_rows,
        "scan_mode": "chunked",
    }
    
    return all_findings, metadata, all_column_risks


def redact_phi(
    content: str,
    findings: List[Dict[str, Any]],
    redaction_style: str = "marker",
) -> Tuple[str, Dict[str, Any]]:
    """Redact PHI from content using findings.

    Args:
        content: Original content with PHI
        findings: List of PHI findings (with position info)
        redaction_style: Style of redaction ("marker", "asterisk", "remove")

    Returns:
        Tuple of (redacted_content, redaction_metadata)
    """
    if not findings:
        return content, {
            "redacted": False,
            "original_length": len(content),
            "redacted_length": len(content),
            "redactions_applied": 0,
        }

    # Sort findings by position (descending) to apply from end to start
    sorted_findings = sorted(
        findings,
        key=lambda f: f.get("position", {}).get("start", 0),
        reverse=True,
    )

    redacted_content = content
    redactions_applied = 0
    categories_redacted: Dict[str, int] = {}

    for finding in sorted_findings:
        pos = finding.get("position", {})
        start = pos.get("start", 0)
        end = pos.get("end", 0)
        category = finding.get("category", "UNKNOWN")

        if start >= 0 and end <= len(content) and start < end:
            if redaction_style == "marker":
                replacement = f"[PHI:{category}]"
            elif redaction_style == "asterisk":
                replacement = "*" * (end - start)
            else:  # remove
                replacement = ""

            redacted_content = (
                redacted_content[:start] + replacement + redacted_content[end:]
            )
            redactions_applied += 1
            categories_redacted[category] = categories_redacted.get(category, 0) + 1

    return redacted_content, {
        "redacted": True,
        "original_length": len(content),
        "redacted_length": len(redacted_content),
        "redactions_applied": redactions_applied,
        "categories_redacted": categories_redacted,
        "redaction_style": redaction_style,
    }


def log_phi_redaction(
    job_id: str,
    context: Dict[str, Any],
    redaction_metadata: Dict[str, Any],
    findings_count: int,
) -> str:
    """Log PHI redaction event for audit trail.

    Args:
        job_id: Job identifier
        context: Context information (governance_mode, user_id, etc.)
        redaction_metadata: Metadata from redaction operation
        findings_count: Number of findings that were redacted

    Returns:
        Audit log entry ID
    """
    audit_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat() + "Z"

    entry = {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "event_type": "PHI_REDACTION",
        "job_id": job_id,
        "governance_mode": context.get("governance_mode", "UNKNOWN"),
        "user_id": context.get("user_id"),
        "findings_count": findings_count,
        "redaction_metadata": redaction_metadata,
        "categories_redacted": redaction_metadata.get("categories_redacted", {}),
    }

    _audit_log_entries.append(entry)

    # Log to Python logger as well
    logger.info(
        f"[PHI_REDACTION] {audit_id} - "
        f"Job: {job_id}, Findings: {findings_count}, "
        f"Redactions: {redaction_metadata.get('redactions_applied', 0)}"
    )

    return audit_id


def validate_safe_harbor_compliance(
    findings: List[Dict[str, Any]],
    phi_schema: Dict[str, Any],
    dates_generalized: bool = False,
    zip_generalized: bool = False,
    ages_generalized: bool = False,
) -> Dict[str, Any]:
    """Validate HIPAA Safe Harbor compliance (45 CFR 164.514(b)(2)).

    Args:
        findings: List of PHI findings
        phi_schema: PHI schema with column mappings
        dates_generalized: Whether dates have been generalized to year only
        zip_generalized: Whether ZIP codes have been generalized (first 3 digits)
        ages_generalized: Whether ages over 89 have been generalized

    Returns:
        Compliance validation result with status and violations
    """
    violations: List[str] = []
    categories_found = set(f.get("category") for f in findings)

    # Map detected categories to HIPAA Safe Harbor 18 identifiers
    hipaa_mapping = {
        "SSN": "social_security_numbers",
        "MRN": "medical_record_numbers",
        "EMAIL": "email_addresses",
        "PHONE": "phone_numbers",
        "NAME": "names",
        "DOB": "dates",
        "ZIP_CODE": "geographic_subdivisions",
        "ADDRESS": "geographic_subdivisions",
        "HEALTH_PLAN": "health_plan_beneficiary_numbers",
        "ACCOUNT": "account_numbers",
        "LICENSE": "certificate_license_numbers",
        "DEVICE_ID": "device_identifiers",
        "URL": "web_urls",
        "IP_ADDRESS": "ip_addresses",
        "AGE_OVER_89": "dates",  # Age is part of dates identifier
    }

    detected_identifiers = set()
    for category in categories_found:
        hipaa_id = hipaa_mapping.get(category)
        if hipaa_id:
            detected_identifiers.add(hipaa_id)

    # Check if all 18 identifiers are removed/redacted
    if detected_identifiers:
        violations.append(
            f"HIPAA identifiers detected: {', '.join(sorted(detected_identifiers))}"
        )

    # Check date generalization
    if "DOB" in categories_found and not dates_generalized:
        violations.append(
            "Dates detected but not generalized to year only (Safe Harbor requirement)"
        )

    # Check ZIP generalization
    if "ZIP_CODE" in categories_found and not zip_generalized:
        violations.append(
            "ZIP codes detected but not generalized to first 3 digits (Safe Harbor requirement)"
        )

    # Check age generalization
    if "AGE_OVER_89" in categories_found and not ages_generalized:
        violations.append(
            "Ages over 89 detected but not generalized (Safe Harbor requirement)"
        )

    # Check columns requiring de-identification
    columns_requiring_deid = phi_schema.get("columns_requiring_deidentification", [])
    if columns_requiring_deid:
        violations.append(
            f"Columns requiring de-identification: {', '.join(columns_requiring_deid)}"
        )

    is_compliant = len(violations) == 0

    return {
        "compliant": is_compliant,
        "violations": violations,
        "detected_identifiers": list(detected_identifiers),
        "total_identifiers_detected": len(detected_identifiers),
        "dates_generalized": dates_generalized,
        "zip_generalized": zip_generalized,
        "ages_generalized": ages_generalized,
        "compliance_method": "safe_harbor" if is_compliant else "expert_determination_required",
    }


@register_stage
class PHIGuardAgent(BaseStageAgent):
    """PHI Guard Agent for Stage 5.

    This stage performs comprehensive PHI detection and HIPAA Safe Harbor
    compliance validation. It scans data for Protected Health Information
    and ensures proper handling according to HIPAA requirements.

    Features:
    - HIPAA Safe Harbor 18 identifier detection
    - Column-level risk assessment (name patterns + value scanning)
    - PHI redaction with audit logging
    - Safe Harbor compliance validation
    - Support for large files (Dask/chunked processing)
    
    Enhanced Features (Phase 1):
    - ML-enhanced PHI detection (NER models)
    - Advanced quasi-identifier analysis (k-anonymity)
    - Multi-jurisdiction compliance (GDPR, CCPA, etc.)
    - Cryptographic audit chains
    - Real-time PHI monitoring
    """

    stage_id = 5
    stage_name = "PHI Detection"

    # Categories of PHI to detect (HIPAA Safe Harbor 18)
    PHI_CATEGORIES = HIPAA_SAFE_HARBOR_18
    
    def __init__(self, **kwargs):
        """Initialize PHI Guard Agent with enhanced capabilities."""
        super().__init__(**kwargs)
        
        # Initialize enhanced analyzers if available
        self.quasi_analyzer = None
        self.ml_detector = None
        self.compliance_validator = None
        self.audit_chain = None
        
        if ENHANCED_PHI_AVAILABLE:
            self._initialize_enhanced_analyzers()
    
    def _initialize_enhanced_analyzers(self):
        """Initialize enhanced PHI analysis components."""
        try:
            # Initialize quasi-identifier analyzer
            self.quasi_analyzer = QuasiIdentifierAnalyzer(
                k_threshold=5,
                l_threshold=2,
                t_threshold=0.2
            )
            
            # Initialize ML PHI detector
            self.ml_detector = create_ml_phi_detector(
                confidence_threshold=0.8,
                enable_clinical=True
            )
            
            # Initialize multi-jurisdiction compliance validator
            self.compliance_validator = MultiJurisdictionCompliance()
            
            # Initialize audit chain
            self.audit_chain = PHIAuditChain(
                storage_backend=StorageBackend.FILE_SYSTEM,
                enable_signing=True
            )
            
            logger.info("Enhanced PHI analyzers initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize enhanced analyzers: {e}")
            # Fallback to basic functionality
            self.quasi_analyzer = None
            self.ml_detector = None
            self.compliance_validator = None
            self.audit_chain = None

    def get_enhanced_capabilities(self) -> Dict[str, bool]:
        """Get status of enhanced PHI detection capabilities."""
        return {
            "enhanced_analyzers_available": ENHANCED_PHI_AVAILABLE,
            "quasi_identifier_analysis": self.quasi_analyzer is not None,
            "ml_detection": self.ml_detector is not None,
            "multi_jurisdiction_compliance": self.compliance_validator is not None,
            "cryptographic_audit": self.audit_chain is not None,
        }
    
    def get_tools(self) -> List[BaseTool]:
        """Get LangChain tools for PHI detection.

        Returns:
            List of LangChain tools (empty for now, can be extended)
        """
        if not LANGCHAIN_AVAILABLE:
            return []
        # Future: Could add tools for PHI pattern customization, compliance checking, etc.
        return []

    def get_prompt_template(self) -> PromptTemplate:
        """Get prompt template for PHI detection stage.

        Returns:
            LangChain PromptTemplate for PHI detection
        """
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        return PromptTemplate.from_template(
            "PHI Detection and HIPAA Safe Harbor Compliance Check\n\n"
            "Job ID: {job_id}\n"
            "Governance Mode: {governance_mode}\n"
            "File Path: {file_path}\n"
            "Scan Mode: {scan_mode}\n\n"
            "Task: Scan data for Protected Health Information (PHI) and validate "
            "HIPAA Safe Harbor compliance (45 CFR 164.514(b)(2)).\n\n"
            "PHI Categories to Detect:\n"
            "- Names\n"
            "- Geographic subdivisions\n"
            "- Dates (DOB, admission, discharge, death)\n"
            "- Phone/Fax numbers\n"
            "- Email addresses\n"
            "- Social Security Numbers\n"
            "- Medical Record Numbers\n"
            "- Health Plan Beneficiary Numbers\n"
            "- Account numbers\n"
            "- Certificate/License numbers\n"
            "- Vehicle identifiers\n"
            "- Device identifiers\n"
            "- Web URLs\n"
            "- IP addresses\n"
            "- Biometric identifiers\n"
            "- Photographs\n"
            "- Unique identifying numbers\n\n"
            "Output: PHI detection results with hash-only findings, "
            "column-level risk assessments, and Safe Harbor compliance status."
        )

    async def execute(self, context: StageContext) -> StageResult:
        """Execute PHI detection scan with Safe Harbor validation.

        Args:
            context: StageContext with job configuration

        Returns:
            StageResult with PHI detection results (hash-only, no raw PHI)
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        warnings: List[str] = []
        errors: List[str] = []
        artifacts: List[str] = []

        logger.info(f"Running PHI detection for job {context.job_id}")

        # Get PHI configuration
        phi_config = context.config.get("phi", {})
        scan_mode = phi_config.get("scan_mode", "standard")
        enable_redaction = phi_config.get("enable_redaction", False)
        redaction_style = phi_config.get("redaction_style", "marker")
        validate_compliance = phi_config.get("validate_compliance", True)
        assess_column_risk = phi_config.get("assess_column_risk", True)

        tier = (
            "OUTPUT_GUARD"
            if scan_mode == "strict"
            else "HIGH_CONFIDENCE"
        )

        all_findings: List[Dict[str, Any]] = []
        content_length = 0
        scan_metadata: Dict[str, Any] = {}
        column_risk_assessments: Dict[str, Dict[str, Any]] = {}
        redaction_metadata: Optional[Dict[str, Any]] = None
        redacted_content: Optional[str] = None

        # Get large-file info from stage 04 output if available
        large_file_info = context.config.get("stage_04_output", {}).get("large_file_info", {})
        processing_mode = large_file_info.get("processing_mode", "standard")
        
        # Scan file content if provided
        file_path = context.dataset_pointer
        if file_path and os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
                content_length = file_size
                
                # Check if we should use large-file handling
                use_large_file = False
                if INGESTION_AVAILABLE:
                    config = get_ingestion_config()
                    use_large_file = file_size >= config.large_file_bytes
                
                if use_large_file and file_path.endswith(('.csv', '.tsv')):
                    # Use large-file PHI scanning
                    logger.info(f"Using large-file PHI scanning for {file_path}")
                    
                    file_format = "tsv" if file_path.endswith('.tsv') else "csv"
                    data, ingestion_meta = ingest_file_large(
                        file_path,
                        file_format=file_format,
                        config=config,
                    )
                    
                    if ingestion_meta.is_dask:
                        all_findings, scan_metadata, column_risk_assessments = scan_dask_dataframe_for_phi(
                            data, tier=tier, assess_risk=assess_column_risk
                        )
                    elif ingestion_meta.is_chunked:
                        all_findings, scan_metadata, column_risk_assessments = scan_chunked_iterator_for_phi(
                            data, tier=tier, assess_risk=assess_column_risk
                        )
                    else:
                        # Standard pandas DataFrame
                        all_findings, column_risk_assessments = scan_dataframe_for_phi(
                            data, tier=tier, assess_risk=assess_column_risk
                        )
                        scan_metadata = {"scan_mode": "pandas", "rows_scanned": len(data)}
                    
                elif PANDAS_AVAILABLE and file_path.endswith(('.csv', '.tsv', '.parquet')):
                    # Use pandas for structured data
                    if file_path.endswith('.parquet'):
                        df = pd.read_parquet(file_path)
                    elif file_path.endswith('.tsv'):
                        df = pd.read_csv(file_path, sep='\t')
                    else:
                        df = pd.read_csv(file_path)
                    
                    all_findings, column_risk_assessments = scan_dataframe_for_phi(
                        df, tier=tier, assess_risk=assess_column_risk
                    )
                    scan_metadata = {"scan_mode": "pandas", "rows_scanned": len(df)}
                    
                else:
                    # Fall back to text scanning
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    content_length = len(content)
                    all_findings = scan_text_for_phi(content, tier=tier)
                    scan_metadata = {"scan_mode": "text", "content_length": content_length}
                    
                    # Assess risk for text content (no column structure)
                    if assess_column_risk and all_findings:
                        # Group findings by category for risk assessment
                        categories = set(f.get("category") for f in all_findings)
                        column_risk_assessments["_text_content"] = {
                            "risk_level": "high" if len(all_findings) > 10 else "medium",
                            "reasons": [f"PHI detected in text content ({len(all_findings)} findings)"],
                            "categories_found": list(categories),
                            "findings_count": len(all_findings),
                            "recommendations": ["redact"],
                        }
                
                logger.info(
                    f"Scanned {scan_metadata.get('rows_scanned', content_length)} "
                    f"units, found {len(all_findings)} potential PHI matches"
                )

                # Perform redaction if enabled
                if enable_redaction and all_findings:
                    if file_path.endswith(('.csv', '.tsv', '.parquet')):
                        # For structured data, redaction would need to be applied per cell
                        # For now, log a warning that redaction is not fully implemented for DataFrames
                        warnings.append(
                            "Redaction enabled but not fully implemented for structured data. "
                            "Consider using text-based redaction or manual column removal."
                        )
                    else:
                        # Text-based redaction
                        redacted_content, redaction_metadata = redact_phi(
                            content, all_findings, redaction_style=redaction_style
                        )
                        
                        # Log redaction event
                        log_phi_redaction(
                            job_id=context.job_id,
                            context={
                                "governance_mode": context.governance_mode,
                                "user_id": context.config.get("user_id"),
                            },
                            redaction_metadata=redaction_metadata,
                            findings_count=len(all_findings),
                        )
                        
                        # Save redacted content as artifact if requested
                        if phi_config.get("save_redacted", False):
                            redacted_path = os.path.join(
                                context.artifact_path,
                                f"redacted_{os.path.basename(file_path)}"
                            )
                            with open(redacted_path, "w", encoding="utf-8") as f:
                                f.write(redacted_content)
                            artifacts.append(redacted_path)

            except Exception as e:
                errors.append(f"Failed to read file for PHI scan: {str(e)}")
                logger.error(f"PHI scan error: {e}")

        # Aggregate findings by category (no raw PHI in output)
        categories_found: Dict[str, int] = {}
        for finding in all_findings:
            cat = finding["category"]
            categories_found[cat] = categories_found.get(cat, 0) + 1

        # Determine risk level
        phi_count = len(all_findings)
        if phi_count == 0:
            risk_level = "none"
        elif phi_count <= 5:
            risk_level = "low"
        elif phi_count <= 20:
            risk_level = "medium"
        else:
            risk_level = "high"

        # CRITICAL: Detection results contain NO raw PHI
        # Only hashes, counts, and positions
        detection_results = {
            "scan_mode": scan_mode,
            "tier": tier,
            "content_length": content_length,
            "total_findings": phi_count,
            "categories_found": categories_found,
            "risk_level": risk_level,
            "phi_detected": phi_count > 0,
            "requires_deidentification": risk_level in ("medium", "high"),
            # Store individual findings (hash-only)
            "findings": all_findings,
            # Include scan metadata for diagnostics
            "scan_metadata": scan_metadata,
            # Column-level risk assessments
            "column_risk_assessments": column_risk_assessments,
        }

        # Build PHI schema for downstream stages (cumulative data)
        phi_schema = {
            "version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "source_file": file_path,
            "governance_mode": context.governance_mode,
            "risk_level": risk_level,
            "phi_detected": phi_count > 0,
            # Map of column -> list of PHI categories found
            "column_phi_map": {},
            # List of columns requiring de-identification
            "columns_requiring_deidentification": [],
            # De-identification recommendations
            "deidentification_recommendations": {},
            # Column risk assessments
            "column_risks": column_risk_assessments,
        }

        # Build column-level PHI map from findings
        for finding in all_findings:
            col = finding.get("column", "_text_content")
            cat = finding["category"]

            if col not in phi_schema["column_phi_map"]:
                phi_schema["column_phi_map"][col] = []

            if cat not in phi_schema["column_phi_map"][col]:
                phi_schema["column_phi_map"][col].append(cat)

        # Identify columns requiring de-identification based on risk assessments
        for col, risk_assessment in column_risk_assessments.items():
            risk_level_col = risk_assessment.get("risk_level", "none")
            if risk_level_col in ("high", "critical", "medium"):
                if col not in phi_schema["columns_requiring_deidentification"]:
                    phi_schema["columns_requiring_deidentification"].append(col)
                
                # Add recommendations from risk assessment
                recommendations = risk_assessment.get("recommendations", [])
                if recommendations:
                    phi_schema["deidentification_recommendations"][col] = recommendations

        # Also add columns from findings (backward compatibility)
        for col, categories in phi_schema["column_phi_map"].items():
            if categories and col not in phi_schema["columns_requiring_deidentification"]:
                phi_schema["columns_requiring_deidentification"].append(col)

                # Add de-identification recommendations per category
                recommendations = []
                for cat in categories:
                    if cat in ("SSN", "MRN", "NAME"):
                        recommendations.append("redact_or_pseudonymize")
                    elif cat in ("DOB",):
                        recommendations.append("date_shift")
                    elif cat in ("ZIP_CODE", "ADDRESS"):
                        recommendations.append("generalize_to_region")
                    elif cat in ("PHONE", "EMAIL"):
                        recommendations.append("redact")
                    else:
                        recommendations.append("redact")

                if col not in phi_schema["deidentification_recommendations"]:
                    phi_schema["deidentification_recommendations"][col] = list(set(recommendations))

        # Store PHI schema in detection results
        detection_results["phi_schema"] = phi_schema

        # ENHANCED: Run ML PHI detection if available
        ml_findings = []
        if self.ml_detector and file_path and os.path.exists(file_path):
            try:
                if not file_path.endswith(('.csv', '.tsv', '.parquet')):
                    # Text-based ML detection
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    ml_findings = self.ml_detector.detect_phi(content)
                    detection_results["ml_findings"] = [
                        finding.to_dict() for finding in ml_findings
                    ]
                    logger.info(f"ML PHI detection found {len(ml_findings)} additional findings")
            except Exception as e:
                warnings.append(f"ML PHI detection failed: {str(e)}")

        # ENHANCED: Run quasi-identifier analysis if available
        quasi_analysis = None
        if self.quasi_analyzer and PANDAS_AVAILABLE and file_path and file_path.endswith(('.csv', '.tsv', '.parquet')):
            try:
                # Use the same DataFrame that was scanned for PHI
                if file_path.endswith('.parquet'):
                    df = pd.read_parquet(file_path)
                elif file_path.endswith('.tsv'):
                    df = pd.read_csv(file_path, sep='\t')
                else:
                    df = pd.read_csv(file_path)
                
                quasi_analysis = self.quasi_analyzer.analyze_comprehensive_risk(df)
                detection_results["quasi_identifier_analysis"] = quasi_analysis
                
                # Add k-anonymity warnings
                if not quasi_analysis["k_anonymity"]["is_anonymous"]:
                    warnings.append(
                        f"K-anonymity violation detected: k={quasi_analysis['k_anonymity']['k_value']}, "
                        f"unique individuals: {quasi_analysis['k_anonymity']['unique_individuals']}"
                    )
                
                logger.info(
                    f"Quasi-identifier analysis: k={quasi_analysis['k_anonymity']['k_value']}, "
                    f"risk_level={quasi_analysis['overall_risk']['risk_level']}"
                )
                
            except Exception as e:
                warnings.append(f"Quasi-identifier analysis failed: {str(e)}")

        # Safe Harbor compliance validation
        compliance_result = None
        if validate_compliance:
            compliance_result = validate_safe_harbor_compliance(
                findings=all_findings,
                phi_schema=phi_schema,
                dates_generalized=False,  # Would be set based on actual processing
                zip_generalized=False,    # Would be set based on actual processing
                ages_generalized=False,    # Would be set based on actual processing
            )
            detection_results["safe_harbor_compliance"] = compliance_result

            if not compliance_result["compliant"]:
                if context.governance_mode == "PRODUCTION":
                    errors.extend(compliance_result["violations"])
                else:
                    warnings.extend(
                        f"Safe Harbor violation: {v}" for v in compliance_result["violations"]
                    )
        
        # ENHANCED: Multi-jurisdiction compliance validation
        multi_compliance_results = None
        if self.compliance_validator and validate_compliance:
            try:
                from .phi_analyzers.compliance_validator import ComplianceFramework
                
                # Run HIPAA and GDPR validation
                frameworks = [ComplianceFramework.HIPAA_SAFE_HARBOR, ComplianceFramework.GDPR_ARTICLE_4]
                
                multi_compliance_results = self.compliance_validator.validate_all_frameworks(
                    findings=all_findings,
                    phi_schema=phi_schema,
                    frameworks=frameworks,
                    # GDPR parameters (would come from config in production)
                    gdpr_consent=context.config.get("gdpr_consent", False),
                    gdpr_explicit_consent=context.config.get("gdpr_explicit_consent", False),
                    gdpr_data_portability=context.config.get("gdpr_data_portability", False),
                    gdpr_right_to_erasure=context.config.get("gdpr_right_to_erasure", False)
                )
                
                detection_results["multi_jurisdiction_compliance"] = {
                    framework.value: {
                        "is_compliant": result.is_compliant,
                        "violations_count": len(result.violations),
                        "risk_score": result.risk_score,
                        "compliance_percentage": result.compliance_percentage
                    }
                    for framework, result in multi_compliance_results.items()
                }
                
                # Generate comprehensive compliance summary
                compliance_summary = self.compliance_validator.generate_compliance_summary(multi_compliance_results)
                detection_results["compliance_summary"] = compliance_summary
                
                # Add warnings for non-compliant frameworks
                for framework_name in compliance_summary["non_compliant_frameworks"]:
                    warnings.append(f"{framework_name} compliance violations detected")
                
                logger.info(
                    f"Multi-jurisdiction compliance: {len(compliance_summary['compliant_frameworks'])} compliant, "
                    f"{len(compliance_summary['non_compliant_frameworks'])} non-compliant"
                )
                
            except Exception as e:
                warnings.append(f"Multi-jurisdiction compliance validation failed: {str(e)}")

        # ENHANCED: Log to cryptographic audit chain
        if self.audit_chain:
            try:
                from ..audit import AuditEventType
                
                # Log PHI detection event
                audit_event_id = self.audit_chain.log_phi_event(
                    event_type=AuditEventType.PHI_DETECTION,
                    job_id=context.job_id,
                    stage_id=self.stage_id,
                    governance_mode=context.governance_mode,
                    user_id=context.config.get("user_id"),
                    event_data={
                        "total_findings": phi_count,
                        "risk_level": risk_level,
                        "categories_found_count": len(categories_found),
                        "scan_mode": scan_mode,
                        "file_size_bytes": content_length,
                        "processing_mode": scan_metadata.get("scan_mode", "unknown"),
                        "ml_findings_count": len(ml_findings),
                        "quasi_analysis_available": quasi_analysis is not None,
                    },
                    compliance_context={
                        "safe_harbor_compliant": compliance_result["compliant"] if compliance_result else None,
                        "multi_jurisdiction_compliant": compliance_summary["overall_compliant"] if multi_compliance_results else None,
                    }
                )
                
                detection_results["audit_event_id"] = audit_event_id
                logger.info(f"PHI detection logged to audit chain: {audit_event_id}")
                
            except Exception as e:
                warnings.append(f"Audit chain logging failed: {str(e)}")

        # Add redaction metadata if available
        if redaction_metadata:
            detection_results["redaction"] = redaction_metadata

        # Mode-specific handling
        if context.governance_mode == "DEMO":
            detection_results["demo_mode"] = True
            if phi_count > 0:
                warnings.append("DEMO mode: PHI detected but processing continues")

        if context.governance_mode == "PRODUCTION" and risk_level == "high":
            errors.append("Production mode: High PHI risk requires manual review")

        # Use create_stage_result helper from BaseStageAgent
        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            output=detection_results,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "phi_categories_checked": self.PHI_CATEGORIES,
                "pattern_count": len(PHI_PATTERNS_OUTPUT_GUARD),
                "ingestion_module_available": INGESTION_AVAILABLE,
                "dask_available": DASK_AVAILABLE,
                "processing_mode": scan_metadata.get("scan_mode", "unknown"),
                "column_risk_assessment_enabled": assess_column_risk,
                "redaction_enabled": enable_redaction,
                "compliance_validation_enabled": validate_compliance,
                # Enhanced capabilities metadata
                "enhanced_capabilities": self.get_enhanced_capabilities(),
                "ml_phi_detection_enabled": self.ml_detector is not None,
                "quasi_identifier_analysis_enabled": self.quasi_analyzer is not None,
                "multi_jurisdiction_compliance_enabled": self.compliance_validator is not None,
                "cryptographic_audit_enabled": self.audit_chain is not None,
            },
            started_at=started_at,
        )
