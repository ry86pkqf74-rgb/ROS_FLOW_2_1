"""
Pydantic schemas for agent-rag-retrieve.

Follows the standard agent HTTP contract:
    POST /agents/run/sync   → AgentRunRequest → AgentRunResponse
    POST /agents/run/stream  → SSE
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ── Standard agent envelope ──────────────────────────────────────────

class Budgets(BaseModel):
    max_output_tokens: int = 1200
    max_context_tokens: int = 6000
    max_escalations: int = 2
    timeout_ms: int = 600000


class AgentRunRequest(BaseModel):
    request_id: str = Field(..., description="Trace/request id")
    task_type: str = "RAG_RETRIEVE"
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


# ── Retrieval-specific models ────────────────────────────────────────

class RetrievalChunk(BaseModel):
    """A single retrieved chunk with scores."""
    chunk_id: str
    doc_id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalTrace(BaseModel):
    """Audit trace of retrieval stages applied."""
    stages: List[str] = Field(default_factory=list)
    semantic_k: Optional[int] = None
    bm25_k: Optional[int] = None
    rerank_k: Optional[int] = None
