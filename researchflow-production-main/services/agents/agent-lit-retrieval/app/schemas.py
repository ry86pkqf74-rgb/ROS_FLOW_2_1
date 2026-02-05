from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Mode = Literal["DEMO", "LIVE"]
RiskTier = Literal["PHI", "SENSITIVE", "NON_SENSITIVE"]


class LitRetrievalInputs(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    max_results: int = Field(default=25, ge=1, le=200)
    databases: List[str] = Field(default_factory=lambda: ["pubmed"])


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
