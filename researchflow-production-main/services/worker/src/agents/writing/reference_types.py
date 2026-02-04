"""
Reference Management Type Definitions

Core types for the reference management system.

Linear Issues: ROS-XXX  
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class CitationStyle(str, Enum):
    """Supported citation styles."""
    APA = "apa"
    AMA = "ama"
    VANCOUVER = "vancouver"
    HARVARD = "harvard"
    CHICAGO = "chicago"
    NATURE = "nature"
    CELL = "cell"
    JAMA = "jama"
    MLA = "mla"
    IEEE = "ieee"


class ReferenceType(str, Enum):
    """Types of references."""
    JOURNAL_ARTICLE = "journal_article"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    CONFERENCE_PAPER = "conference_paper"
    THESIS = "thesis"
    REPORT = "report"
    WEBSITE = "website"
    PREPRINT = "preprint"
    PATENT = "patent"
    OTHER = "other"


class QualityLevel(str, Enum):
    """Reference quality levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    PROBLEMATIC = "problematic"


class Reference(BaseModel):
    """Core reference data structure."""
    
    id: str = Field(..., description="Unique reference identifier")
    title: str = Field(..., description="Reference title")
    authors: List[str] = Field(default_factory=list, description="Author names")
    year: Optional[int] = Field(None, description="Publication year")
    journal: Optional[str] = Field(None, description="Journal name")
    volume: Optional[str] = Field(None, description="Volume number")
    issue: Optional[str] = Field(None, description="Issue number")
    pages: Optional[str] = Field(None, description="Page range")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    pmid: Optional[str] = Field(None, description="PubMed ID")
    url: Optional[str] = Field(None, description="URL")
    abstract: Optional[str] = Field(None, description="Abstract text")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    reference_type: ReferenceType = Field(ReferenceType.JOURNAL_ARTICLE, description="Type of reference")
    
    # Metadata
    source_database: Optional[str] = Field(None, description="Source database")
    citation_count: Optional[int] = Field(None, description="Citation count")
    impact_factor: Optional[float] = Field(None, description="Journal impact factor")
    is_retracted: bool = Field(False, description="Whether paper is retracted")
    is_preprint: bool = Field(False, description="Whether this is a preprint")
    
    # Processing metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator('doi')
    def validate_doi(cls, v):
        """Validate DOI format."""
        if v and not v.startswith(('10.', 'doi:', 'DOI:')):
            # Attempt to normalize DOI
            if v.startswith('http'):
                # Extract DOI from URL
                if '10.' in v:
                    v = v[v.find('10.'):]
            elif not v.startswith('10.'):
                return None
        return v.lower() if v else v
    
    @field_validator('pmid')
    def validate_pmid(cls, v):
        """Validate PMID format."""
        if v:
            # Remove any non-numeric characters
            numeric_only = ''.join(c for c in str(v) if c.isdigit())
            return numeric_only if numeric_only else None
        return v


class Citation(BaseModel):
    """Formatted citation with metadata."""
    
    reference_id: str = Field(..., description="Reference ID this citation represents")
    formatted_text: str = Field(..., description="Formatted citation text")
    style: CitationStyle = Field(..., description="Citation style used")
    in_text_markers: List[str] = Field(default_factory=list, description="In-text citation markers")
    bibtex: Optional[str] = Field(None, description="BibTeX representation")
    
    # Quality indicators
    is_complete: bool = Field(True, description="Whether all required fields are present")
    completeness_score: float = Field(1.0, description="Completeness score (0-1)")
    format_compliance: bool = Field(True, description="Whether formatting follows style guide")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QualityScore(BaseModel):
    """Reference quality assessment."""
    
    reference_id: str = Field(..., description="Reference ID")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    quality_level: QualityLevel = Field(..., description="Quality level category")
    
    # Individual dimension scores
    credibility_score: float = Field(..., ge=0.0, le=1.0, description="Source credibility")
    recency_score: float = Field(..., ge=0.0, le=1.0, description="Publication recency relevance")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Topic relevance")
    impact_score: float = Field(..., ge=0.0, le=1.0, description="Citation impact")
    methodology_score: float = Field(..., ge=0.0, le=1.0, description="Methodological rigor")
    
    # Detailed feedback
    strengths: List[str] = Field(default_factory=list, description="Reference strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Reference weaknesses")
    recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")
    
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class QualityWarning(BaseModel):
    """Warning about reference quality issues."""
    
    reference_id: str = Field(..., description="Reference ID")
    warning_type: Literal[
        "retracted_paper",
        "predatory_journal", 
        "very_old",
        "low_citation_count",
        "preprint_misuse",
        "self_citation_excess",
        "circular_citation",
        "incomplete_metadata",
        "broken_link",
        "duplicate_reference"
    ] = Field(..., description="Type of warning")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Warning severity")
    message: str = Field(..., description="Warning message")
    recommendation: Optional[str] = Field(None, description="Recommended action")
    auto_fixable: bool = Field(False, description="Whether warning can be auto-fixed")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReferenceState(BaseModel):
    """State for reference management processing."""
    
    study_id: str = Field(..., description="Study identifier")
    manuscript_text: str = Field(..., description="Full manuscript text")
    literature_results: List[Dict[str, Any]] = Field(default_factory=list, description="Literature search results")
    existing_references: List[Reference] = Field(default_factory=list, description="Existing references")
    target_style: CitationStyle = Field(CitationStyle.AMA, description="Target citation style")
    
    # Processing options
    enable_doi_validation: bool = Field(True, description="Enable DOI validation")
    enable_duplicate_detection: bool = Field(True, description="Enable duplicate detection")
    enable_quality_assessment: bool = Field(True, description="Enable quality assessment")
    max_references: Optional[int] = Field(None, description="Maximum number of references")
    
    # Context
    manuscript_type: Optional[str] = Field(None, description="Type of manuscript")
    target_journal: Optional[str] = Field(None, description="Target journal")
    research_field: Optional[str] = Field(None, description="Research field")


class ReferenceResult(BaseModel):
    """Result of reference management processing."""
    
    study_id: str = Field(..., description="Study identifier")
    
    # Core outputs
    references: List[Reference] = Field(default_factory=list, description="Processed references")
    citations: List[Citation] = Field(default_factory=list, description="Formatted citations")
    bibliography: str = Field("", description="Formatted bibliography")
    citation_map: Dict[str, str] = Field(default_factory=dict, description="In-text marker to reference ID mapping")
    
    # Quality assessments
    quality_scores: List[QualityScore] = Field(default_factory=list, description="Quality assessments")
    warnings: List[QualityWarning] = Field(default_factory=list, description="Quality warnings")
    
    # Processing metadata
    total_references: int = Field(0, description="Total number of references")
    style_compliance_score: float = Field(1.0, description="Overall style compliance score")
    missing_citations: List[str] = Field(default_factory=list, description="Missing citation markers")
    duplicate_references: List[str] = Field(default_factory=list, description="Duplicate reference IDs")
    doi_verified: Dict[str, bool] = Field(default_factory=dict, description="DOI verification results")
    
    # Processing statistics
    processing_time_seconds: float = Field(0.0, description="Total processing time")
    api_calls_made: int = Field(0, description="Number of API calls made")
    cache_hits: int = Field(0, description="Number of cache hits")
    cache_misses: int = Field(0, description="Number of cache misses")
    
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class DOIValidationResult(BaseModel):
    """Result of DOI validation."""
    
    doi: str = Field(..., description="DOI that was validated")
    is_valid: bool = Field(..., description="Whether DOI is valid")
    is_resolvable: bool = Field(..., description="Whether DOI resolves to a resource")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata from DOI resolution")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class DuplicateGroup(BaseModel):
    """Group of duplicate references."""
    
    group_id: str = Field(..., description="Unique group identifier")
    reference_ids: List[str] = Field(..., description="Reference IDs in this duplicate group")
    primary_reference_id: str = Field(..., description="Primary reference ID to keep")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    match_criteria: List[str] = Field(..., description="Criteria that matched")
    
    # Duplicate resolution
    auto_resolvable: bool = Field(False, description="Whether duplicates can be auto-resolved")
    resolution_strategy: Optional[str] = Field(None, description="How duplicates should be resolved")
    
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class CitationNeed(BaseModel):
    """Identified need for a citation in the manuscript."""
    
    id: str = Field(..., description="Unique citation need identifier")
    text_snippet: str = Field(..., description="Text that needs citation")
    context: str = Field(..., description="Surrounding context")
    position: int = Field(..., description="Character position in manuscript")
    section: str = Field(..., description="Manuscript section")
    
    # Classification
    claim_type: Literal[
        "statistical_fact",
        "prior_research",
        "methodology",
        "clinical_guideline", 
        "definition",
        "background_info",
        "other"
    ] = Field(..., description="Type of claim needing citation")
    
    urgency: Literal["low", "medium", "high", "critical"] = Field("medium", description="Citation urgency")
    
    # Suggested citations
    suggested_references: List[str] = Field(default_factory=list, description="Suggested reference IDs")
    
    identified_at: datetime = Field(default_factory=datetime.utcnow)


class ReferenceAnalytics(BaseModel):
    """Analytics for reference usage and patterns."""
    
    study_id: str = Field(..., description="Study identifier")
    
    # Basic statistics
    total_references: int = Field(0, description="Total number of references")
    unique_journals: int = Field(0, description="Number of unique journals")
    year_range: tuple[int, int] = Field((0, 0), description="Year range of references")
    
    # Distribution metrics
    references_by_year: Dict[int, int] = Field(default_factory=dict, description="References by publication year")
    references_by_journal: Dict[str, int] = Field(default_factory=dict, description="References by journal")
    references_by_type: Dict[str, int] = Field(default_factory=dict, description="References by type")
    references_by_section: Dict[str, int] = Field(default_factory=dict, description="References by manuscript section")
    
    # Quality metrics
    average_impact_factor: float = Field(0.0, description="Average journal impact factor")
    average_citation_count: float = Field(0.0, description="Average citation count")
    quality_distribution: Dict[str, int] = Field(default_factory=dict, description="Quality level distribution")
    
    # Pattern analysis
    self_citation_rate: float = Field(0.0, description="Self-citation rate")
    recent_references_rate: float = Field(0.0, description="Rate of recent references (last 5 years)")
    preprint_rate: float = Field(0.0, description="Rate of preprint usage")
    
    generated_at: datetime = Field(default_factory=datetime.utcnow)