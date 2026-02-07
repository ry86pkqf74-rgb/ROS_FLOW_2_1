"""Shared agent envelope, RAG GroundingPack, and extraction output schemas.

Input: inputs.groundingPack (chunks with doc_id, chunk_id, text) and/or
inputs.abstracts / inputs.papers. Output: extraction_table + citations (docId/chunkId).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union


class Budgets(BaseModel):
    max_output_tokens: int = 1200
    max_context_tokens: int = 6000
    max_escalations: int = 2
    timeout_ms: int = 600000


class RetrievalChunk(BaseModel):
    """Single retrieved chunk with stable chunkId and docId."""

    chunk_id: str = Field(..., description="Stable chunk identifier")
    doc_id: str = Field(..., description="Stable document/source identifier")
    text: str = Field(default="", description="Chunk text content")
    score: float = Field(default=0.0, description="Relevance score (e.g. similarity)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class RetrievalTrace(BaseModel):
    """Trace of retrieval stages; reserve for BM25 + rerank later."""

    stages: List[str] = Field(default_factory=list, description="Stage names executed, e.g. ['semantic', 'rerank']")
    semantic_k: Optional[int] = Field(default=None, description="V1: k used for semantic retrieval")
    bm25_k: Optional[int] = Field(default=None, description="Reserved: k for BM25 stage")
    rerank_k: Optional[int] = Field(default=None, description="Reserved: k after rerank")


class GroundingPack(BaseModel):
    """RAG grounding: chunks, citations, retrievalTrace; contract-compatible sources/citations/span_refs."""

    chunks: List[RetrievalChunk] = Field(default_factory=list, description="Retrieved chunks with chunkId, docId")
    citations: List[str] = Field(default_factory=list, description="Citation keys/IDs (e.g. chunkId or docId)")
    retrieval_trace: Optional[RetrievalTrace] = Field(default=None, description="Retrieval pipeline trace")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Source documents or references")
    span_refs: List[Dict[str, Any]] = Field(default_factory=list, description="Optional span references into sources")


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
    domain_id: Optional[str] = Field(default=None, description="Domain scope for retrieval")
    inputs: Dict[str, Any] = Field(default_factory=dict)
    budgets: Budgets = Field(default_factory=Budgets)


class AgentRunResponse(BaseModel):
    status: str = "ok"
    request_id: str
    outputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
    grounding: Optional[GroundingPack] = Field(default=None, description="RAG chunks, citations, retrievalTrace")
    error: Optional[AgentError] = Field(default=None)


# --- Extraction output models ---


class PICOElements(BaseModel):
    """PICO framework elements for one paper/chunk."""

    population: Optional[str] = Field(default=None, description="Population description")
    intervention: Optional[str] = Field(default=None, description="Intervention or exposure")
    comparator: Optional[str] = Field(default=None, description="Comparator or control")
    outcomes: Optional[List[str]] = Field(default_factory=list, description="Outcome measures")
    timeframe: Optional[str] = Field(default=None, description="Time frame of study")


class ExtractionRow(BaseModel):
    """One row in the normalized extraction table; tied to doc_id/chunk_id for citations."""

    doc_id: str = Field(..., description="Source document id")
    chunk_id: Optional[str] = Field(default=None, description="Source chunk id if from GroundingPack")
    pico: Optional[PICOElements] = Field(default=None, description="PICO elements")
    endpoints: List[str] = Field(default_factory=list, description="Endpoint/outcome measures")
    sample_size: Optional[Union[int, str]] = Field(default=None, description="Sample size (n) or description")
    key_results: Optional[Union[str, List[str]]] = Field(default=None, description="Key results summary")


class CitationRef(BaseModel):
    """Citation mapping to docId/chunkId."""

    doc_id: str = Field(..., description="Document identifier")
    chunk_id: str = Field(..., description="Chunk identifier")
