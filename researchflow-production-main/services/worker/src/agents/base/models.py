"""
Pydantic data models for ResearchFlow agents.

Comprehensive data structures for:
- Evidence bundle management
- Compliance checklist tracking
- AI governance and risk management
- Model cards and dataset cards

@author Claude
@created 2026-01-30
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ComplianceStatus(str, Enum):
    """Compliance status enumeration."""
    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ChecklistItemStatus(str, Enum):
    """Checklist item completion status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class FAVESGate(str, Enum):
    """FAVES gate dimensions."""
    FAIR = "FAIR"
    APPROPRIATE = "APPROPRIATE"
    VALID = "VALID"
    EFFECTIVE = "EFFECTIVE"
    SAFE = "SAFE"


class RiskLevel(str, Enum):
    """Risk assessment level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Evidence Bundle Models
# ============================================================================

class EvidencePack(BaseModel):
    """Container for research evidence and compliance artifacts."""

    id: str = Field(..., description="Unique evidence pack identifier")
    research_id: str = Field(..., description="Associated research project ID")
    organization: Optional[str] = Field(None, description="Organization")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None, description="Creator user ID")

    # Evidence content
    title: str = Field(..., description="Evidence pack title")
    description: Optional[str] = Field(None, description="Detailed description")
    sources: List[str] = Field(default_factory=list, description="Data source references")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="Artifact URIs")

    # Compliance tracking
    faves_scores: Optional[Dict[str, float]] = Field(None, description="FAVES dimension scores")
    regulatory_frameworks: List[str] = Field(default_factory=list)

    # Audit trail
    audit_trail: List[Dict[str, Any]] = Field(default_factory=list)

    class Config:
        use_enum_values = True


# ============================================================================
# TRIPOD+AI Checklist Models
# ============================================================================

class TRIPODChecklistItem(BaseModel):
    """Individual TRIPOD+AI checklist item."""

    item_id: str = Field(..., description="Unique item identifier (e.g., T1, M7)")
    category: str = Field(..., description="Item category")
    subcategory: str = Field(..., description="Item subcategory")
    description: str = Field(..., description="Item description")
    required: bool = Field(True, description="Whether item is required")
    evidence_types: List[str] = Field(default_factory=list)
    validation_rules: List[str] = Field(default_factory=list)


class TRIPODAIChecklistCompletion(BaseModel):
    """TRIPOD+AI checklist completion tracking."""

    id: str = Field(..., description="Completion record ID")
    research_id: str = Field(..., description="Associated research ID")
    checklist_version: str = Field(default="1.0")

    # Item completions
    items: Dict[str, ChecklistItemStatus] = Field(default_factory=dict)
    item_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    item_notes: Dict[str, str] = Field(default_factory=dict)

    # Overall tracking
    total_items: int = Field(27, description="Total TRIPOD+AI items")
    completed_items: int = Field(default=0)
    completion_percentage: float = Field(default=0.0)

    # Validation
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = Field(False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ============================================================================
# CONSORT-AI Checklist Models
# ============================================================================

class CONSORTAIChecklistItem(BaseModel):
    """Individual CONSORT-AI checklist item."""

    item_id: str = Field(..., description="Unique item identifier (e.g., CONSORT-AI-1)")
    category: str = Field(..., description="Item category")
    subcategory: str = Field(..., description="Item subcategory")
    description: str = Field(..., description="Item description")
    required: bool = Field(True)
    cross_reference: Optional[Dict[str, str]] = None
    evidence_types: List[str] = Field(default_factory=list)
    validation_rules: List[str] = Field(default_factory=list)


class CONSORTAIChecklistCompletion(BaseModel):
    """CONSORT-AI checklist completion tracking."""

    id: str = Field(..., description="Completion record ID")
    research_id: str = Field(..., description="Associated research ID")
    trial_id: Optional[str] = Field(None, description="Trial identifier")
    checklist_version: str = Field(default="1.0")

    # Item completions
    items: Dict[str, ChecklistItemStatus] = Field(default_factory=dict)
    item_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    item_notes: Dict[str, str] = Field(default_factory=dict)

    # Overall tracking
    total_items: int = Field(12, description="Total CONSORT-AI items")
    completed_items: int = Field(default=0)
    completion_percentage: float = Field(default=0.0)

    # Validation
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = Field(False)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


# ============================================================================
# FAVES Assessment Models
# ============================================================================

class FAVESAssessment(BaseModel):
    """FAVES compliance gate assessment."""

    id: str = Field(..., description="Assessment ID")
    research_id: str = Field(..., description="Associated research ID")

    # Individual dimension scores (0-100)
    fair_score: float = Field(..., ge=0, le=100)
    appropriate_score: float = Field(..., ge=0, le=100)
    valid_score: float = Field(..., ge=0, le=100)
    effective_score: float = Field(..., ge=0, le=100)
    safe_score: float = Field(..., ge=0, le=100)

    # Overall assessment
    overall_score: float = Field(default=0.0)
    status: ComplianceStatus = Field(ComplianceStatus.NOT_APPLICABLE)
    passed: bool = Field(False, description="Whether all gates passed (score >= 80)")

    # Detailed findings
    findings_by_dimension: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Reviewer information
    reviewed_by: Optional[str] = Field(None)
    review_date: Optional[datetime] = None

    class Config:
        use_enum_values = True

    @validator('overall_score', pre=True, always=True)
    def compute_overall_score(cls, v, values):
        """Compute overall score from dimension scores."""
        if 'fair_score' in values:
            scores = [
                values.get('fair_score', 0),
                values.get('appropriate_score', 0),
                values.get('valid_score', 0),
                values.get('effective_score', 0),
                values.get('safe_score', 0),
            ]
            return sum(scores) / len(scores) if scores else 0.0
        return v


# ============================================================================
# AI Invocation & Logging Models
# ============================================================================

class AIInvocationLog(BaseModel):
    """Log of AI agent invocations and executions."""

    id: str = Field(..., description="Log entry ID")
    agent_type: str = Field(..., description="Type of agent (compliance, analysis, etc.)")
    research_id: str = Field(..., description="Associated research ID")

    # Invocation details
    invoked_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Input/output
    input_prompt: str = Field(...)
    output: Optional[str] = None

    # Model information
    model_name: Optional[str] = None
    model_version: Optional[str] = None

    # Performance metrics
    tokens_used: Optional[Dict[str, int]] = None
    cost_usd: Optional[float] = None

    # Status
    status: str = Field(default="pending")  # pending, running, completed, failed
    error: Optional[str] = None

    class Config:
        use_enum_values = True


# ============================================================================
# Risk Management Models
# ============================================================================

class RiskRegisterEntry(BaseModel):
    """Entry in the AI risk register."""

    id: str = Field(..., description="Risk ID")
    research_id: str = Field(..., description="Associated research ID")

    # Risk identification
    risk_category: str = Field(...)  # Model risk, data risk, deployment risk, etc.
    risk_description: str = Field(...)

    # Risk assessment
    likelihood: RiskLevel = Field(...)
    impact: RiskLevel = Field(...)
    risk_score: float = Field(..., ge=0, le=100)

    # Mitigation
    mitigation_strategy: Optional[str] = None
    owner: Optional[str] = None

    # Tracking
    identified_date: datetime = Field(default_factory=datetime.utcnow)
    target_resolution_date: Optional[datetime] = None
    resolved_date: Optional[datetime] = None
    status: str = Field(default="open")  # open, mitigated, resolved, closed

    class Config:
        use_enum_values = True


# ============================================================================
# Deployment & Monitoring Models
# ============================================================================

class DeploymentRecord(BaseModel):
    """Record of model deployment event."""

    id: str = Field(..., description="Deployment ID")
    research_id: str = Field(..., description="Associated research ID")
    model_id: str = Field(..., description="Model identifier")

    # Deployment info
    deployment_date: datetime = Field(default_factory=datetime.utcnow)
    environment: str = Field(...)  # development, staging, production
    version: str = Field(...)

    # Deployment details
    deployed_by: Optional[str] = None
    approval_status: ComplianceStatus = Field(ComplianceStatus.NOT_APPLICABLE)
    approver: Optional[str] = None

    # Monitoring setup
    monitoring_enabled: bool = Field(False)
    alert_thresholds: Dict[str, float] = Field(default_factory=dict)

    # Decommissioning
    decommissioned_date: Optional[datetime] = None
    decommission_reason: Optional[str] = None

    class Config:
        use_enum_values = True


# ============================================================================
# Incident & Monitoring Models
# ============================================================================

class IncidentReport(BaseModel):
    """Report of model or deployment incident."""

    id: str = Field(..., description="Incident ID")
    research_id: str = Field(..., description="Associated research ID")

    # Incident info
    title: str = Field(...)
    description: str = Field(...)
    reported_date: datetime = Field(default_factory=datetime.utcnow)

    # Severity
    severity: RiskLevel = Field(...)
    impact_type: str = Field(...)  # data quality, model performance, deployment, etc.

    # Investigation
    investigated_by: Optional[str] = None
    root_cause: Optional[str] = None
    findings: Optional[str] = None

    # Resolution
    resolution_action: Optional[str] = None
    resolved_date: Optional[datetime] = None
    status: str = Field(default="reported")  # reported, investigating, resolved, closed

    class Config:
        use_enum_values = True


# ============================================================================
# Dataset & Model Cards
# ============================================================================

class DatasetCard(BaseModel):
    """Machine Learning Dataset Card documentation."""

    id: str = Field(..., description="Dataset card ID")
    dataset_id: str = Field(..., description="Dataset identifier")
    research_id: str = Field(..., description="Associated research ID")

    # Basic info
    name: str = Field(...)
    description: str = Field(...)
    version: str = Field(default="1.0")

    # Dataset composition
    total_records: int = Field(...)
    features: List[Dict[str, str]] = Field(default_factory=list)
    target_variable: Optional[str] = None

    # Data source
    source_url: Optional[str] = None
    collection_method: str = Field(...)
    collection_date: Optional[datetime] = None

    # Metadata
    license: Optional[str] = None
    temporal_coverage_start: Optional[datetime] = None
    temporal_coverage_end: Optional[datetime] = None

    # Ethical considerations
    sensitive_attributes: List[str] = Field(default_factory=list)
    bias_assessment: Optional[str] = None
    privacy_considerations: Optional[str] = None

    class Config:
        use_enum_values = True


class ModelCard(BaseModel):
    """Machine Learning Model Card documentation."""

    id: str = Field(..., description="Model card ID")
    model_id: str = Field(..., description="Model identifier")
    research_id: str = Field(..., description="Associated research ID")

    # Basic info
    name: str = Field(...)
    description: str = Field(...)
    version: str = Field(default="1.0")
    model_type: str = Field(...)  # classifier, regressor, etc.

    # Model details
    architecture: str = Field(...)
    training_data_id: Optional[str] = None
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)

    # Performance
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    training_dataset_size: int = Field(...)
    evaluation_dataset_size: int = Field(...)

    # Intended use
    intended_use: str = Field(...)
    target_population: str = Field(...)
    out_of_scope_uses: List[str] = Field(default_factory=list)

    # Ethical considerations
    fairness_assessment: Optional[str] = None
    bias_mitigation: Optional[str] = None
    interpretability_approach: Optional[str] = None

    # Limitations
    known_limitations: List[str] = Field(default_factory=list)
    recommended_monitoring: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


# ============================================================================
# Compliance Report Models
# ============================================================================

class ComplianceReport(BaseModel):
    """Comprehensive compliance report combining all assessments."""

    id: str = Field(..., description="Report ID")
    research_id: str = Field(..., description="Associated research ID")

    # Report metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None
    report_period_start: Optional[datetime] = None
    report_period_end: Optional[datetime] = None

    # Compliance summaries
    faves_assessment: Optional[FAVESAssessment] = None
    tripod_completion: Optional[TRIPODAIChecklistCompletion] = None
    consort_completion: Optional[CONSORTAIChecklistCompletion] = None

    # Risk analysis
    risk_register: List[RiskRegisterEntry] = Field(default_factory=list)
    incidents: List[IncidentReport] = Field(default_factory=list)

    # Overall status
    overall_compliance_status: ComplianceStatus = Field(ComplianceStatus.NOT_APPLICABLE)
    compliance_score: float = Field(default=0.0, ge=0, le=100)

    # Recommendations
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True
