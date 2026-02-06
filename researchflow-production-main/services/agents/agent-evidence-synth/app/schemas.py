from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

Mode = Literal["DEMO", "LIVE"]
RiskTier = Literal["PHI", "SENSITIVE", "NON_SENSITIVE"]


class Paper(BaseModel):
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None


class EvidenceSynthInputs(BaseModel):
    query: str = Field(min_length=1)
    papers: List[Paper] = Field(default_factory=list)


class AgentTask(BaseModel):
    request_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    mode: Optional[Mode] = None
    risk_tier: Optional[RiskTier] = None
    domain_id: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    budgets: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    ok: bool
    request_id: str
    task_type: str
    outputs: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
