"""
Gap Analysis Type Definitions - Stage 10

Comprehensive type definitions for gap analysis including:
- Research gap categorization (6 types)
- Literature comparison structures
- PICO framework for research questions
- Prioritization matrices
- Future research suggestions

Linear Issues: ROS-XXX (Stage 10 - Gap Analysis Agent)
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# =============================================================================
# Gap Type Enumerations
# =============================================================================

class GapType(str, Enum):
    """Categories of research gaps identified in systematic reviews."""
    THEORETICAL = "theoretical"          # Missing explanatory frameworks
    EMPIRICAL = "empirical"              # Missing data/evidence
    METHODOLOGICAL = "methodological"    # Design limitations
    POPULATION = "population"            # Underrepresented groups
    TEMPORAL = "temporal"                # Outdated evidence
    GEOGRAPHIC = "geographic"            # Limited settings studied


class EvidenceLevel(str, Enum):
    """Strength of evidence for a gap's existence."""
    STRONG = "strong"          # Clear consensus, multiple sources
    MODERATE = "moderate"      # Some evidence, needs confirmation
    WEAK = "weak"             # Speculative, limited support


class Addressability(str, Enum):
    """How feasible it is to address a gap."""
    FEASIBLE = "feasible"                              # Can be done with current resources
    CHALLENGING = "challenging"                        # Requires additional resources
    REQUIRES_MAJOR_RESOURCES = "requires_major_resources"  # Needs significant investment


class GapPriority(str, Enum):
    """Priority level for addressing gaps."""
    HIGH = "high"          # High impact + high feasibility
    MEDIUM = "medium"      # Mixed impact/feasibility
    LOW = "low"           # Low impact or low feasibility
    STRATEGIC = "strategic"  # High impact but challenging


# =============================================================================
# Finding Structures
# =============================================================================

class Finding(BaseModel):
    """A research finding from the current study."""
    description: str = Field(..., description="Clear statement of the finding")
    effect_size: Optional[float] = Field(None, description="Magnitude of effect (if quantitative)")
    significance: Optional[float] = Field(None, description="P-value or significance measure")
    confidence: str = Field(..., description="Confidence level: low/medium/high")
    supporting_data: Optional[Dict[str, Any]] = Field(None, description="Raw data supporting finding")
    statistical_test: Optional[str] = Field(None, description="Test used (e.g., t-test, ANOVA)")


# =============================================================================
# Literature Comparison
# =============================================================================

class LiteratureAlignment(BaseModel):
    """Alignment between finding and literature."""
    finding: str
    paper_title: str
    paper_id: str
    alignment_type: str = Field(..., description="consistent_with/contradicts/extends/novel")
    similarity_score: float = Field(ge=0.0, le=1.0, description="Semantic similarity (0-1)")
    explanation: str = Field(..., description="Why this alignment was determined")


class ComparisonResult(BaseModel):
    """Complete comparison of findings to literature."""
    consistent_with: List[LiteratureAlignment] = Field(default_factory=list)
    contradicts: List[LiteratureAlignment] = Field(default_factory=list)
    novel_findings: List[LiteratureAlignment] = Field(default_factory=list)
    extends: List[LiteratureAlignment] = Field(default_factory=list)
    overall_similarity_score: float = Field(ge=0.0, le=1.0)
    summary: str = Field("", description="Natural language summary of comparison")


# =============================================================================
# Gap Structures
# =============================================================================

class KnowledgeGap(BaseModel):
    """Gap in current scientific knowledge."""
    topic: str = Field(..., description="What area of knowledge is missing")
    current_evidence: str = Field(..., description="What we currently know")
    what_is_missing: str = Field(..., description="Specific missing information")
    importance: str = Field(..., description="Why this gap matters: low/medium/high")
    related_citations: List[str] = Field(default_factory=list, description="Papers discussing this gap")


class MethodGap(BaseModel):
    """Methodological limitation in current research."""
    aspect: str = Field(..., description="What methodological aspect has limitations")
    current_approach: str = Field(..., description="How it's currently done")
    limitation: str = Field(..., description="Why current approach is limited")
    alternative_approaches: List[str] = Field(..., description="Better methods that could be used")
    impact_on_validity: str = Field(..., description="How this affects study validity")


class PopulationGap(BaseModel):
    """Underrepresented population in research."""
    population_studied: str = Field(..., description="Who has been studied")
    populations_missing: List[str] = Field(..., description="Who is underrepresented")
    generalizability_concern: str = Field(..., description="Why this limits applicability")
    priority_level: str = Field(..., description="Importance of including: low/medium/high")
    barriers: Optional[List[str]] = Field(None, description="Why these populations are underrepresented")


class TemporalGap(BaseModel):
    """Gap due to outdated evidence."""
    topic: str = Field(..., description="Research area with outdated evidence")
    most_recent_year: int = Field(..., description="Year of most recent study")
    years_since_update: int = Field(..., description="How many years since last study")
    paper_count: int = Field(..., description="Number of existing papers")
    urgency: str = Field(..., description="How urgent is update: low/medium/high")
    changes_since_last_study: Optional[str] = Field(None, description="What has changed")


class GeographicGap(BaseModel):
    """Geographic limitation in research."""
    regions_studied: List[str] = Field(..., description="Where studies have been conducted")
    regions_missing: List[str] = Field(..., description="Underrepresented regions")
    generalizability_concern: str = Field(..., description="Why geographic diversity matters")
    cultural_factors: Optional[List[str]] = Field(None, description="Cultural considerations")


class Gap(BaseModel):
    """Generic gap structure with metadata."""
    gap_type: GapType
    description: str = Field(..., description="Clear description of the gap")
    evidence_level: EvidenceLevel = Field(..., description="Strength of evidence for gap")
    addressability: Addressability = Field(..., description="Feasibility of addressing")
    related_papers: List[str] = Field(default_factory=list, description="Citations supporting gap")
    impact_score: Optional[float] = Field(None, ge=1.0, le=5.0, description="Potential impact (1-5)")
    feasibility_score: Optional[float] = Field(None, ge=1.0, le=5.0, description="Feasibility (1-5)")


# =============================================================================
# Prioritization
# =============================================================================

class PrioritizedGap(BaseModel):
    """Gap with priority scoring for decision-making."""
    gap: Gap
    priority_score: float = Field(ge=0.0, le=10.0, description="Overall priority (0-10)")
    priority_level: GapPriority = Field(..., description="Priority category")
    rationale: str = Field(..., description="Why this priority was assigned")
    feasibility: str = Field(..., description="Feasibility assessment")
    expected_impact: str = Field(..., description="Expected impact if addressed")
    estimated_timeline: Optional[str] = Field(None, description="Time to address")
    resource_requirements: Optional[str] = Field(None, description="Resources needed")


class PrioritizationMatrix(BaseModel):
    """2x2 matrix for gap prioritization (Impact vs Feasibility)."""
    high_priority: List[Dict[str, Any]] = Field(default_factory=list, description="High impact, high feasibility")
    strategic: List[Dict[str, Any]] = Field(default_factory=list, description="High impact, low feasibility")
    quick_wins: List[Dict[str, Any]] = Field(default_factory=list, description="Low impact, high feasibility")
    low_priority: List[Dict[str, Any]] = Field(default_factory=list, description="Low impact, low feasibility")
    
    visualization_config: Optional[Dict[str, Any]] = Field(None, description="Config for frontend rendering")


# =============================================================================
# PICO Framework
# =============================================================================

class PICOFramework(BaseModel):
    """PICO framework for formulating research questions."""
    population: str = Field(..., description="P: Population/Problem/Patient")
    intervention: str = Field(..., description="I: Intervention/Exposure")
    comparison: str = Field(..., description="C: Comparison/Control group")
    outcome: str = Field(..., description="O: Outcome of interest")
    study_type: Optional[str] = Field(None, description="Optimal study design (RCT, cohort, etc.)")
    timeframe: Optional[str] = Field(None, description="Time period for outcome assessment")
    
    def format_research_question(self) -> str:
        """Generate natural language research question from PICO."""
        return (
            f"In {self.population}, does {self.intervention} "
            f"compared to {self.comparison} lead to {self.outcome}?"
        )
    
    def generate_pubmed_query(self) -> str:
        """Generate PubMed search query from PICO components."""
        terms = [
            f"({self.population}[MeSH] OR {self.population}[tiab])",
            f"AND ({self.intervention}[MeSH] OR {self.intervention}[tiab])",
            f"AND ({self.outcome}[MeSH] OR {self.outcome}[tiab])"
        ]
        if self.comparison:
            terms.insert(2, f"AND ({self.comparison}[MeSH] OR {self.comparison}[tiab])")
        return " ".join(terms)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "population": self.population,
            "intervention": self.intervention,
            "comparison": self.comparison,
            "outcome": self.outcome,
            "study_type": self.study_type,
            "research_question": self.format_research_question(),
            "pubmed_query": self.generate_pubmed_query()
        }


# =============================================================================
# Research Suggestions
# =============================================================================

class ResearchSuggestion(BaseModel):
    """Future research direction with detailed planning."""
    research_question: str = Field(..., description="Clear, answerable research question")
    study_design: str = Field(..., description="Optimal study design")
    target_population: str = Field(..., description="Who should be studied")
    expected_contribution: str = Field(..., description="What this would add to knowledge")
    
    pico_framework: Optional[PICOFramework] = Field(None, description="Structured PICO formulation")
    estimated_timeline: Optional[str] = Field(None, description="Expected duration")
    resource_requirements: Optional[str] = Field(None, description="Resources needed")
    potential_challenges: Optional[List[str]] = Field(None, description="Anticipated obstacles")
    funding_opportunities: Optional[List[str]] = Field(None, description="Potential funding sources")
    
    # Priority scoring
    impact_score: float = Field(ge=1.0, le=5.0, description="Expected impact (1-5)")
    feasibility_score: float = Field(ge=1.0, le=5.0, description="Feasibility (1-5)")
    urgency_score: float = Field(ge=1.0, le=5.0, description="How urgent (1-5)")
    
    def calculate_priority(self) -> float:
        """Calculate overall priority score."""
        return (self.impact_score * 0.5 + self.feasibility_score * 0.3 + self.urgency_score * 0.2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "research_question": self.research_question,
            "study_design": self.study_design,
            "target_population": self.target_population,
            "expected_contribution": self.expected_contribution,
            "pico": self.pico_framework.to_dict() if self.pico_framework else None,
            "priority_score": self.calculate_priority(),
            "impact": self.impact_score,
            "feasibility": self.feasibility_score,
            "urgency": self.urgency_score
        }


# =============================================================================
# Complete Gap Analysis Result
# =============================================================================

class GapAnalysisResult(BaseModel):
    """Complete output from gap analysis agent."""
    
    # Comparison results
    comparisons: ComparisonResult
    
    # Identified gaps by type
    knowledge_gaps: List[KnowledgeGap] = Field(default_factory=list)
    method_gaps: List[MethodGap] = Field(default_factory=list)
    population_gaps: List[PopulationGap] = Field(default_factory=list)
    temporal_gaps: List[TemporalGap] = Field(default_factory=list)
    geographic_gaps: List[GeographicGap] = Field(default_factory=list)
    
    # Prioritized gaps
    prioritized_gaps: List[PrioritizedGap] = Field(default_factory=list)
    prioritization_matrix: Optional[PrioritizationMatrix] = None
    
    # Future research
    research_suggestions: List[ResearchSuggestion] = Field(default_factory=list)
    
    # Narrative outputs
    narrative: str = Field("", description="Manuscript-ready narrative for Discussion section")
    future_directions_section: str = Field("", description="Structured Future Directions section")
    
    # Metadata
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    total_gaps_identified: int = Field(0, description="Total number of gaps")
    high_priority_count: int = Field(0, description="Number of high-priority gaps")
    
    # Quality indicators
    literature_coverage: float = Field(0.0, ge=0.0, le=1.0, description="% of literature analyzed")
    gap_diversity_score: float = Field(0.0, ge=0.0, le=1.0, description="Diversity of gap types")
    
    def calculate_summary_stats(self):
        """Calculate summary statistics."""
        all_gaps = self.prioritized_gaps
        self.total_gaps_identified = len(all_gaps)
        self.high_priority_count = sum(1 for g in all_gaps if g.priority_level == GapPriority.HIGH)
        
        # Gap diversity
        gap_types = {g.gap.gap_type for g in all_gaps}
        self.gap_diversity_score = len(gap_types) / len(GapType)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        self.calculate_summary_stats()
        
        return {
            "comparisons": self.comparisons.model_dump(),
            "gaps": {
                "knowledge": [g.model_dump() for g in self.knowledge_gaps],
                "methodological": [g.model_dump() for g in self.method_gaps],
                "population": [g.model_dump() for g in self.population_gaps],
                "temporal": [g.model_dump() for g in self.temporal_gaps],
                "geographic": [g.model_dump() for g in self.geographic_gaps],
            },
            "prioritized_gaps": [g.model_dump() for g in self.prioritized_gaps],
            "prioritization_matrix": self.prioritization_matrix.model_dump() if self.prioritization_matrix else None,
            "research_suggestions": [s.to_dict() for s in self.research_suggestions],
            "narrative": self.narrative,
            "future_directions": self.future_directions_section,
            "summary": {
                "total_gaps": self.total_gaps_identified,
                "high_priority": self.high_priority_count,
                "gap_diversity": self.gap_diversity_score,
                "literature_coverage": self.literature_coverage,
            },
            "timestamp": self.timestamp
        }


# =============================================================================
# Study Metadata (for context)
# =============================================================================

class StudyMetadata(BaseModel):
    """Metadata about the current study for gap analysis."""
    study_title: str
    research_question: str
    study_design: str = Field(..., description="RCT, cohort, cross-sectional, etc.")
    population_studied: str
    sample_size: int
    intervention: Optional[str] = None
    comparison: Optional[str] = None
    primary_outcome: str
    secondary_outcomes: Optional[List[str]] = None
    inclusion_criteria: Optional[List[str]] = None
    exclusion_criteria: Optional[List[str]] = None
    study_duration: Optional[str] = None
    geographic_location: Optional[str] = None
    limitations: Optional[List[str]] = None
