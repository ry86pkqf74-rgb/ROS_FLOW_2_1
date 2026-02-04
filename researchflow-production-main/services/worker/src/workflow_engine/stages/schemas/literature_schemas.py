"""
Pydantic schemas for Literature Discovery Stage data validation.

This module provides data validation schemas for Stage 2 Literature Discovery Agent,
ensuring proper type checking and validation of literature search and review data.
"""

from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum
from datetime import datetime


class LiteratureSource(str, Enum):
    """Supported literature sources."""
    PUBMED = "pubmed"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"
    CROSSREF = "crossref"


class StudyType(str, Enum):
    """Study type classifications for literature filtering."""
    RCT = "randomized_controlled_trial"
    SYSTEMATIC_REVIEW = "systematic_review"
    META_ANALYSIS = "meta_analysis"
    COHORT = "cohort_study"
    CASE_CONTROL = "case_control"
    CROSS_SECTIONAL = "cross_sectional"
    OBSERVATIONAL = "observational"
    CLINICAL_TRIAL = "clinical_trial"
    REVIEW = "review"
    CASE_REPORT = "case_report"


class LiteratureAuthor(BaseModel):
    """Schema for literature author information."""
    last_name: str = Field(..., min_length=1, max_length=50)
    first_name: Optional[str] = Field(None, max_length=50)
    initials: Optional[str] = Field(None, max_length=10)
    affiliation: Optional[str] = Field(None, max_length=200)
    orcid: Optional[str] = Field(None, regex=r"^\d{4}-\d{4}-\d{4}-\d{3}[0-9X]$")

    class Config:
        extra = "allow"


class LiteratureCitation(BaseModel):
    """Schema for individual literature citations."""
    
    # Identifiers
    pmid: Optional[str] = Field(None, description="PubMed ID")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    pii: Optional[str] = Field(None, description="Publisher Item Identifier")
    pmc: Optional[str] = Field(None, description="PubMed Central ID")
    semantic_scholar_id: Optional[str] = Field(None, description="Semantic Scholar Paper ID")
    arxiv_id: Optional[str] = Field(None, description="ArXiv ID")
    
    # Core metadata
    title: str = Field(..., min_length=5, max_length=500, description="Article title")
    authors: List[Union[str, LiteratureAuthor]] = Field(
        default_factory=list, 
        description="List of authors"
    )
    journal: Optional[str] = Field(None, max_length=200, description="Journal name")
    year: Optional[Union[str, int]] = Field(None, description="Publication year")
    volume: Optional[str] = Field(None, max_length=20)
    issue: Optional[str] = Field(None, max_length=20)
    pages: Optional[str] = Field(None, max_length=50)
    
    # Content
    abstract: Optional[str] = Field(None, max_length=5000, description="Abstract text")
    keywords: List[str] = Field(default_factory=list, description="Article keywords")
    mesh_terms: List[str] = Field(default_factory=list, description="MeSH terms")
    
    # Classification
    study_type: Optional[StudyType] = Field(None, description="Inferred study type")
    publication_type: Optional[str] = Field(None, description="Publication type")
    language: Optional[str] = Field("en", description="Publication language")
    
    # Quality metrics
    citation_count: Optional[int] = Field(None, ge=0, description="Number of citations")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Relevance score")
    quality_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Quality score")
    impact_factor: Optional[float] = Field(None, ge=0.0, description="Journal impact factor")
    
    # Source metadata
    source: LiteratureSource = Field(..., description="Literature source")
    source_url: Optional[str] = Field(None, description="Source URL")
    retrieved_at: Optional[datetime] = Field(None, description="Retrieval timestamp")
    
    # PICO elements (if extracted)
    pico_population: Optional[str] = Field(None, description="PICO Population")
    pico_intervention: Optional[str] = Field(None, description="PICO Intervention")
    pico_comparator: Optional[str] = Field(None, description="PICO Comparator")
    pico_outcome: Optional[List[str]] = Field(None, description="PICO Outcomes")

    @validator('year')
    def validate_year(cls, v):
        """Validate publication year."""
        if v is None:
            return None
        
        year_int = int(v) if isinstance(v, str) else v
        current_year = datetime.now().year
        
        if year_int < 1800 or year_int > current_year + 1:
            raise ValueError(f"Invalid publication year: {year_int}")
        return str(year_int)

    @validator('doi')
    def validate_doi(cls, v):
        """Validate DOI format."""
        if v is None:
            return None
        
        # Basic DOI validation
        if not v.startswith("10."):
            raise ValueError("DOI must start with '10.'")
        return v.strip()

    @validator('pmid')
    def validate_pmid(cls, v):
        """Validate PMID format."""
        if v is None:
            return None
            
        # PMID should be numeric
        if not v.isdigit():
            raise ValueError("PMID must be numeric")
        return v

    @root_validator
    def validate_identifiers(cls, values):
        """Ensure at least one identifier is present."""
        identifiers = [
            values.get('pmid'),
            values.get('doi'), 
            values.get('semantic_scholar_id'),
            values.get('arxiv_id')
        ]
        
        if not any(identifiers):
            raise ValueError("At least one identifier (PMID, DOI, etc.) must be provided")
        return values

    class Config:
        extra = "allow"
        use_enum_values = True


class LiteratureSearchQuery(BaseModel):
    """Schema for literature search queries."""
    
    # Core search terms
    research_topic: Optional[str] = Field(None, max_length=500, description="Main research topic")
    keywords: List[str] = Field(default_factory=list, description="Search keywords")
    mesh_terms: List[str] = Field(default_factory=list, description="MeSH terms")
    boolean_query: Optional[str] = Field(None, max_length=1000, description="Boolean search query")
    
    # PICO-based search
    pico_population: Optional[str] = Field(None, description="PICO Population")
    pico_intervention: Optional[str] = Field(None, description="PICO Intervention") 
    pico_comparator: Optional[str] = Field(None, description="PICO Comparator")
    pico_outcomes: List[str] = Field(default_factory=list, description="PICO Outcomes")
    pico_search_query: Optional[str] = Field(None, description="PICO-generated search query")
    
    # Search constraints
    study_types: List[StudyType] = Field(default_factory=list, description="Target study types")
    languages: List[str] = Field(default_factory=lambda: ["en"], description="Publication languages")
    date_range: Optional[Dict[str, str]] = Field(None, description="Date range filter")
    max_results: int = Field(50, ge=1, le=1000, description="Maximum results per source")
    
    # Source selection
    sources: List[LiteratureSource] = Field(
        default_factory=lambda: [LiteratureSource.PUBMED], 
        description="Literature sources to search"
    )
    
    # Advanced options
    include_reviews: bool = Field(True, description="Include systematic reviews")
    include_meta_analyses: bool = Field(True, description="Include meta-analyses")
    min_citation_count: Optional[int] = Field(None, ge=0, description="Minimum citation count")
    min_quality_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="Minimum quality score")

    @validator('date_range')
    def validate_date_range(cls, v):
        """Validate date range format."""
        if v is None:
            return None
            
        if 'start' not in v and 'end' not in v:
            raise ValueError("Date range must include 'start' or 'end'")
            
        # Validate date format (basic validation)
        for key in ['start', 'end']:
            if key in v:
                date_str = v[key]
                if not isinstance(date_str, str) or len(date_str) < 4:
                    raise ValueError(f"Invalid {key} date format: {date_str}")
                    
        return v

    class Config:
        extra = "allow"
        use_enum_values = True


class LiteratureTheme(BaseModel):
    """Schema for literature theme clustering."""
    theme_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    citations: List[str] = Field(default_factory=list, description="Citation IDs in this theme")
    keywords: List[str] = Field(default_factory=list, description="Theme keywords")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    paper_count: int = Field(0, ge=0, description="Number of papers in theme")
    
    class Config:
        extra = "allow"


class LiteratureGap(BaseModel):
    """Schema for identified research gaps."""
    gap_description: str = Field(..., min_length=5, max_length=500)
    gap_type: Literal["methodological", "population", "intervention", "outcome", "temporal", "geographic"] = Field(
        ..., description="Type of research gap"
    )
    priority: Literal["high", "medium", "low"] = Field("medium", description="Gap priority")
    supporting_evidence: Optional[str] = Field(None, max_length=1000, description="Evidence for the gap")
    related_citations: List[str] = Field(default_factory=list, description="Related citation IDs")
    suggested_study_design: Optional[str] = Field(None, description="Suggested study design to address gap")
    
    class Config:
        extra = "allow"


class LiteratureQualityMetrics(BaseModel):
    """Schema for literature review quality metrics."""
    total_papers_searched: int = Field(0, ge=0)
    total_papers_included: int = Field(0, ge=0)
    inclusion_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Study type distribution
    study_type_distribution: Dict[StudyType, int] = Field(default_factory=dict)
    
    # Quality indicators
    avg_citation_count: Optional[float] = Field(None, ge=0.0)
    avg_publication_year: Optional[float] = Field(None, ge=1800.0)
    high_impact_papers: int = Field(0, ge=0, description="Papers with >100 citations")
    systematic_reviews_count: int = Field(0, ge=0)
    meta_analyses_count: int = Field(0, ge=0)
    
    # Source distribution
    source_distribution: Dict[LiteratureSource, int] = Field(default_factory=dict)
    
    # Search performance
    search_execution_time: Optional[float] = Field(None, ge=0.0, description="Search time in seconds")
    api_calls_made: int = Field(0, ge=0)
    
    class Config:
        extra = "allow"
        use_enum_values = True


class LiteratureReview(BaseModel):
    """Schema for complete literature review artifact."""
    
    # Required fields (as per specification)
    papers_found: int = Field(..., ge=0, description="Total number of papers found")
    key_themes: List[Union[str, LiteratureTheme]] = Field(
        default_factory=list, 
        description="Key themes identified in literature"
    )
    research_gaps: List[Union[str, LiteratureGap]] = Field(
        default_factory=list, 
        description="Research gaps identified"
    )
    citations: List[LiteratureCitation] = Field(
        default_factory=list, 
        description="Literature citations"
    )
    
    # Enhanced metadata
    search_query: Optional[LiteratureSearchQuery] = Field(None, description="Original search query")
    search_strategy: Optional[str] = Field(None, description="Search strategy used")
    quality_metrics: Optional[LiteratureQualityMetrics] = Field(None, description="Quality metrics")
    
    # Review metadata
    review_date: Optional[datetime] = Field(None, description="Review completion date")
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")
    governance_mode: Optional[str] = Field(None, description="Governance mode used")
    
    # Summary and conclusions
    executive_summary: Optional[str] = Field(None, max_length=2000, description="Executive summary")
    methodology_summary: Optional[str] = Field(None, max_length=1000, description="Methodology summary")
    limitations: List[str] = Field(default_factory=list, description="Review limitations")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    # PICO integration
    pico_coverage: Optional[Dict[str, Any]] = Field(None, description="PICO element coverage analysis")
    stage1_integration_status: Optional[str] = Field(None, description="Stage 1 integration status")

    @validator('papers_found')
    def validate_papers_found(cls, v, values):
        """Validate papers_found matches citations length."""
        citations = values.get('citations', [])
        if citations and v != len(citations):
            # Allow slight discrepancy (some papers might not have full citations)
            if abs(v - len(citations)) > 5:
                raise ValueError(f"papers_found ({v}) significantly differs from citations count ({len(citations)})")
        return v

    @root_validator
    def validate_consistency(cls, values):
        """Validate consistency between fields."""
        papers_found = values.get('papers_found', 0)
        citations = values.get('citations', [])
        
        # Basic consistency checks
        if papers_found > 0 and not citations:
            raise ValueError("If papers_found > 0, citations list cannot be empty")
            
        # Quality metrics consistency
        quality_metrics = values.get('quality_metrics')
        if quality_metrics and quality_metrics.total_papers_included != papers_found:
            if abs(quality_metrics.total_papers_included - papers_found) > 1:
                raise ValueError("Quality metrics total_papers_included must match papers_found")
                
        return values

    class Config:
        extra = "allow"
        use_enum_values = True


class LiteratureValidationResult(BaseModel):
    """Result of literature review validation."""
    
    is_valid: bool = Field(..., description="Whether validation passed")
    
    errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    
    warnings: List[str] = Field(
        default_factory=list, 
        description="List of validation warnings"
    )
    
    literature_review: Optional[LiteratureReview] = Field(
        None,
        description="Validated literature review if validation passed"
    )
    
    quality_score: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=10.0, 
        description="Overall quality score"
    )
    
    recommendations: List[str] = Field(
        default_factory=list,
        description="Recommendations for improvement"
    )

    class Config:
        extra = "allow"


def validate_literature_review(
    review_data: Dict[str, Any],
    governance_mode: str = "DEMO"
) -> LiteratureValidationResult:
    """
    Validate literature review data with mode-specific behavior.
    
    Args:
        review_data: Literature review data dictionary
        governance_mode: Current governance mode (DEMO, STAGING, PRODUCTION)
        
    Returns:
        LiteratureValidationResult with validation status and details
    """
    errors = []
    warnings = []
    recommendations = []
    quality_score = 0.0
    
    try:
        # Create literature review object
        literature_review = LiteratureReview(**review_data)
        
        # Mode-specific validation
        if governance_mode in ["STAGING", "PRODUCTION"]:
            # Strict validation for production modes
            if literature_review.papers_found == 0:
                errors.append("No papers found - search may need refinement")
            elif literature_review.papers_found < 5:
                warnings.append(f"Low paper count ({literature_review.papers_found})")
                recommendations.append("Consider broadening search terms or date range")
            
            if not literature_review.key_themes:
                errors.append("No key themes identified - manual curation required")
            elif len(literature_review.key_themes) < 2:
                warnings.append("Few key themes identified")
                recommendations.append("Consider manual theme refinement")
                
            if not literature_review.research_gaps:
                warnings.append("No research gaps identified")
                recommendations.append("Manual gap analysis recommended")
                
        else:  # DEMO mode
            if literature_review.papers_found == 0:
                warnings.append("No papers found in DEMO mode")
            if not literature_review.key_themes:
                warnings.append("No key themes identified in DEMO mode")
                
        # Calculate quality score
        quality_score = _calculate_quality_score(literature_review)
        
        # Quality-based recommendations
        if quality_score < 5.0:
            recommendations.append("Low quality score - consider expanding search strategy")
        if quality_score < 3.0:
            errors.append(f"Quality score too low: {quality_score:.1f}/10.0")
            
        is_valid = len(errors) == 0
        
        return LiteratureValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            literature_review=literature_review if is_valid else None,
            quality_score=quality_score,
            recommendations=recommendations
        )
        
    except Exception as e:
        return LiteratureValidationResult(
            is_valid=False,
            errors=[f"Validation failed: {str(e)}"],
            warnings=warnings,
            literature_review=None,
            quality_score=0.0,
            recommendations=recommendations
        )


def _calculate_quality_score(review: LiteratureReview) -> float:
    """Calculate quality score for literature review."""
    score = 0.0
    
    # Papers found (0-3 points)
    if review.papers_found >= 20:
        score += 3.0
    elif review.papers_found >= 10:
        score += 2.0
    elif review.papers_found >= 5:
        score += 1.0
    
    # Key themes (0-2 points)
    if len(review.key_themes) >= 5:
        score += 2.0
    elif len(review.key_themes) >= 3:
        score += 1.5
    elif len(review.key_themes) >= 1:
        score += 1.0
        
    # Research gaps (0-2 points)
    if len(review.research_gaps) >= 3:
        score += 2.0
    elif len(review.research_gaps) >= 1:
        score += 1.0
        
    # Citation quality (0-2 points)
    valid_citations = sum(1 for c in review.citations if c.title and len(c.title) > 10)
    if valid_citations >= review.papers_found * 0.9:  # 90% valid
        score += 2.0
    elif valid_citations >= review.papers_found * 0.7:  # 70% valid
        score += 1.0
        
    # Quality metrics (0-1 point)
    if review.quality_metrics:
        if review.quality_metrics.high_impact_papers > 0:
            score += 0.5
        if review.quality_metrics.systematic_reviews_count > 0:
            score += 0.5
            
    return min(score, 10.0)  # Cap at 10.0