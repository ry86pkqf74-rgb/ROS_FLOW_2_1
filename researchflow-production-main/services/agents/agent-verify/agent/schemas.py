from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


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


# --- Claim verify task-specific input/output (inside inputs / outputs) ---

VerdictKind = Literal["pass", "fail", "unclear"]


class EvidenceQuote(BaseModel):
    """Evidence supporting or contradicting a claim, pointing to a chunk."""

    chunk_id: str = Field(..., alias="chunkId", description="Id of the source chunk in GroundingPack")
    quote: str = Field(..., description="Exact or near-exact quote from the chunk")

    class Config:
        populate_by_name = True


class ClaimVerdict(BaseModel):
    """Per-claim verification result."""

    claim: str = Field(..., description="The claim that was verified")
    verdict: VerdictKind = Field(..., description="pass | fail | unclear")
    evidence: List[EvidenceQuote] = Field(default_factory=list, description="Quotes and chunkIds supporting the verdict")


class VerifyInputs(BaseModel):
    """Inputs for CLAIM_VERIFY task."""

    claims: List[str] = Field(..., description="Claims to verify against the grounding pack")
    grounding_pack: Optional[Dict[str, Any]] = Field(default=None, alias="groundingPack", description="GroundingPack (sources with chunk ids, etc.)")
    governance_mode: str = Field(default="DEMO", alias="governanceMode")
    strictness: str = Field(default="normal", description="e.g. strict, normal, lenient")

    class Config:
        populate_by_name = True


class VerifyOutputs(BaseModel):
    """Outputs for CLAIM_VERIFY task (inside AgentRunResponse.outputs)."""

    claim_verdicts: List[ClaimVerdict] = Field(..., description="Per-claim verdict with evidence")
    overall_pass: bool = Field(..., alias="overallPass", description="True iff all claims are pass")

    class Config:
        populate_by_name = True
