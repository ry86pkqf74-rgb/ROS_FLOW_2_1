from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


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


# --- RAG Ingest task-specific input/output (inside inputs / outputs) ---

class ChunkConfig(BaseModel):
    """Optional chunk config overrides. Defaults from RAG_PIPELINE.md."""

    chunk_size: int = Field(default=512, alias="chunkSize", description="Characters per chunk")
    chunk_overlap: int = Field(default=50, alias="chunkOverlap", description="Overlap between chunks")
    separators: List[str] = Field(
        default_factory=lambda: ["\n\n", "\n", ". ", " "],
        description="Split points (paragraph, sentence, word)",
    )

    class Config:
        populate_by_name = True


class IngestDocument(BaseModel):
    """Single document for ingestion."""

    doc_id: str = Field(..., alias="docId", description="Unique document id")
    title: Optional[str] = None
    source: Optional[str] = None
    text: str = Field(..., description="Full document text to chunk and embed")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class RAGIngestOutput(BaseModel):
    """Strict JSON output for RAG ingest task (inside AgentRunResponse.outputs)."""

    ingested_count: int = Field(..., alias="ingestedCount")
    chunk_count: int = Field(..., alias="chunkCount")
    collection: str
    doc_ids: List[str] = Field(..., alias="docIds")
    chunk_ids: List[str] = Field(..., alias="chunkIds")
    errors: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
