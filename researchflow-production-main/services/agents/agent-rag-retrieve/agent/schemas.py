"""Shared agent envelope and RAG GroundingPack with chunks, citations, retrievalTrace.

Canonical JSON Schema (contract checker and this agent): docs/agent_response_schema.json.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


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
    # Contract-compatible fields (populated from chunks for envelope compatibility)
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
