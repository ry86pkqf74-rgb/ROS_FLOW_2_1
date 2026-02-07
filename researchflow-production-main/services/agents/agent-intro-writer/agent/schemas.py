from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Budgets(BaseModel):
    max_output_tokens: int = 4096
    max_context_tokens: int = 6000
    max_escalations: int = 2
    timeout_ms: int = 600000


class GroundingPack(BaseModel):
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    span_refs: List[Dict[str, Any]] = Field(default_factory=list)


class AgentError(BaseModel):
    code: str = Field(..., description="Error code, e.g. VALIDATION_ERROR, TASK_FAILED")
    message: str = Field(..., description="Human-readable message (no PHI)")
    details: Optional[Dict[str, Any]] = Field(default=None)


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
    status: str = "ok"
    request_id: str
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
    grounding: Optional[GroundingPack] = Field(default=None)
    error: Optional[AgentError] = Field(default=None)


# Section writer task-specific (inputs.outline, verifiedClaims, extractionRows, groundingPack, styleParams)
class SectionWriterInputs(BaseModel):
    outline: List[str] = Field(default_factory=list, description="Section headings, e.g. [Introduction, Methods, Results]")
    verified_claims: List[Dict[str, Any]] = Field(default_factory=list, alias="verifiedClaims")
    extraction_rows: List[Dict[str, Any]] = Field(default_factory=list, alias="extractionRows")
    grounding_pack: Optional[Dict[str, Any]] = Field(default=None, alias="groundingPack")
    style_params: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="styleParams")

    class Config:
        populate_by_name = True


# Outputs: section_markdown, claims_with_evidence, warnings, overallPass (optional)
class SectionWriterOutputs(BaseModel):
    section_markdown: str = Field(default="", alias="sectionMarkdown")
    claims_with_evidence: List[Dict[str, Any]] = Field(default_factory=list, alias="claimsWithEvidence")
    warnings: List[str] = Field(default_factory=list)
    overall_pass: bool = Field(default=True, alias="overallPass")

    class Config:
        populate_by_name = True
