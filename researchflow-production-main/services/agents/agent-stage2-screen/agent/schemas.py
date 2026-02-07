from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
from enum import Enum


class Budgets(BaseModel):
    max_output_tokens: int = 1200
    max_context_tokens: int = 6000
    max_escalations: int = 2
    timeout_ms: int = 600000


class GroundingPack(BaseModel):
    """Shared structure for citations and sources (RAG/retrieval grounding)."""

    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents or references")
    citations: List[str] = Field(default_factory=list, description="Citation keys or IDs")
    span_refs: List[Dict[str, Any]] = Field(default_factory=list, description="Optional span references into sources")


class AgentError(BaseModel):
    """Standard error payload when /run returns status != ok."""

    code: str = Field(..., description="Error code, e.g. VALIDATION_ERROR, TASK_FAILED")
    message: str = Field(..., description="Human-readable message (no PHI)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra context")


class AgentRunRequest(BaseModel):
    request_id: str = Field(..., description="Trace/request id")
    task_type: str
    workflow_id: Optional[str] = None
    stage_id: Optional[str] = None
    user_id: Optional[str] = None
    mode: str = "DEMO"
    risk_tier: str = "NON_SENSITIVE"
    domain_id: str = "clinical"
    inputs: Dict[str, Any] = Field(default_factory=dict)
    budgets: Budgets = Field(default_factory=Budgets)


class AgentRunResponse(BaseModel):
    """Unified envelope for POST /agents/run/sync. Always use this shape for success and business errors."""

    status: str = "ok"
    request_id: str
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
    grounding: Optional[GroundingPack] = Field(default=None, description="Optional citations/sources")
    error: Optional[AgentError] = Field(default=None, description="Set when status is not ok")


# Screening-specific schemas

class StudyType(str, Enum):
    """Study type classifications."""
    RANDOMIZED_CONTROLLED_TRIAL = "randomized_controlled_trial"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    COHORT_STUDY = "cohort_study"
    CASE_CONTROL_STUDY = "case_control_study"
    CROSS_SECTIONAL_STUDY = "cross_sectional_study"
    CASE_REPORT = "case_report"
    OBSERVATIONAL_STUDY = "observational_study"
    REVIEW = "review"
    CLINICAL_TRIAL = "clinical_trial"
    UNKNOWN = "unknown"


class ScreeningCriteria(BaseModel):
    """Inclusion and exclusion criteria for screening."""
    inclusion: List[str] = Field(default_factory=list, description="List of inclusion criteria")
    exclusion: List[str] = Field(default_factory=list, description="List of exclusion criteria")
    required_keywords: List[str] = Field(default_factory=list)
    excluded_keywords: List[str] = Field(default_factory=list)
    study_types_required: List[StudyType] = Field(default_factory=list)
    study_types_excluded: List[StudyType] = Field(default_factory=list)
    year_min: Optional[int] = None
    year_max: Optional[int] = None
    require_abstract: bool = True


class PaperScreeningResult(BaseModel):
    """Result of screening a single paper."""
    paper_id: str
    title: str
    verdict: Literal["included", "excluded", "duplicate"]
    reason: str = Field(description="Human-readable reason for verdict")
    study_type: Optional[StudyType] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    matched_criteria: List[str] = Field(default_factory=list)
    duplicate_of: Optional[str] = Field(None, description="ID of original paper if duplicate")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScreeningOutputs(BaseModel):
    """Outputs from the screening agent."""
    included: List[PaperScreeningResult] = Field(default_factory=list)
    excluded: List[PaperScreeningResult] = Field(default_factory=list)
    duplicates: List[PaperScreeningResult] = Field(default_factory=list)
    total_processed: int
    stats: Dict[str, Any] = Field(default_factory=dict)
