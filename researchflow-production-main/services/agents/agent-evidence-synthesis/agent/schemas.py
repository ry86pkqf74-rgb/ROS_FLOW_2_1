"""Schemas for Evidence Synthesis Agent"""
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class PICOFramework(BaseModel):
    """PICO framework for clinical questions"""
    population: Optional[str] = None
    intervention: Optional[str] = None
    comparator: Optional[str] = None
    outcome: Optional[str] = None


class AgentTask(BaseModel):
    """Standard agent task input"""
    task_type: str
    request_id: str
    workflow_id: Optional[str] = None
    user_id: Optional[str] = None
    mode: Literal["DEMO", "LIVE"] = "DEMO"
    inputs: Dict[str, Any]


class EvidenceSynthesisInputs(BaseModel):
    """Input schema for evidence synthesis"""
    research_question: str = Field(..., description="The research question to synthesize evidence for")
    inclusion_criteria: Optional[List[str]] = Field(default=None, description="Inclusion criteria for evidence")
    exclusion_criteria: Optional[List[str]] = Field(default=None, description="Exclusion criteria for evidence")
    pico: Optional[PICOFramework] = Field(default=None, description="PICO framework for clinical questions")
    sources: Optional[List[str]] = Field(default=None, description="User-provided URLs or sources")
    max_papers: int = Field(default=30, description="Maximum number of papers to retrieve")


class EvidenceChunk(BaseModel):
    """Individual evidence chunk"""
    source: str
    study_type: str
    sample_size: Optional[str] = None
    population: Optional[str] = None
    key_findings: str
    limitations: Optional[str] = None
    relevance: Literal["High", "Medium", "Low"]
    grade: Literal["High", "Moderate", "Low", "Very Low"]
    url: Optional[str] = None


class ConflictAnalysis(BaseModel):
    """Conflict analysis result"""
    conflict_description: str
    positions: List[Dict[str, Any]]
    methodological_assessment: Dict[str, Any]
    heterogeneity_sources: List[str]
    neutral_presentation: str
    interpretive_conclusion: str
    confidence_level: str


class EvidenceSynthesisOutputs(BaseModel):
    """Output schema for evidence synthesis"""
    executive_summary: str
    overall_certainty: Literal["High", "Moderate", "Low", "Very Low"]
    evidence_table: List[EvidenceChunk]
    synthesis_by_subquestion: Dict[str, str]
    conflicting_evidence: Optional[ConflictAnalysis] = None
    limitations: List[str]
    methodology_note: Dict[str, Any]


class AgentResponse(BaseModel):
    """Standard agent response"""
    ok: bool
    request_id: str
    task_type: str
    outputs: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)
