"""
PRISMA Reporting Type Definitions

Type definitions for PRISMA 2020 systematic review reporting including:
- PRISMA flowchart stages
- PRISMA checklist items
- Search documentation
- Risk of bias summaries

Linear Issues: ROS-XXX (Stage 12 - PRISMA Reporting Agent)
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Enumerations
# =============================================================================

class PRISMAStage(str, Enum):
    """PRISMA 2020 flowchart stages."""
    IDENTIFICATION = "identification"
    SCREENING = "screening"
    ELIGIBILITY = "eligibility"
    INCLUDED = "included"


class SearchDatabase(str, Enum):
    """Common databases for systematic reviews."""
    PUBMED = "PubMed"
    EMBASE = "Embase"
    COCHRANE = "Cochrane Library"
    WEB_OF_SCIENCE = "Web of Science"
    SCOPUS = "Scopus"
    CINAHL = "CINAHL"
    PSYCHINFO = "PsycINFO"


# =============================================================================
# PRISMA Flowchart Data
# =============================================================================

class PRISMAFlowchartData(BaseModel):
    """Data for PRISMA 2020 flowchart."""
    
    # Identification stage
    records_identified_databases: int = Field(..., description="Records identified from databases")
    records_identified_registers: int = Field(default=0, description="Records from registers")
    records_identified_other: int = Field(default=0, description="Records from other sources")
    
    # Before screening
    records_removed_before_screening: int = Field(default=0, description="Duplicates removed")
    records_marked_ineligible: int = Field(default=0, description="Records marked ineligible by automation tools")
    records_removed_other_reasons: int = Field(default=0, description="Records removed for other reasons")
    
    # Screening
    records_screened: int = Field(..., description="Records screened")
    records_excluded: int = Field(..., description="Records excluded at screening")
    
    # Eligibility
    reports_sought_retrieval: int = Field(..., description="Reports sought for retrieval")
    reports_not_retrieved: int = Field(default=0, description="Reports not retrieved")
    reports_assessed_eligibility: int = Field(..., description="Reports assessed for eligibility")
    reports_excluded: int = Field(..., description="Reports excluded with reasons")
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict, description="Exclusion reasons and counts")
    
    # Included
    new_studies_included: int = Field(..., description="New studies included in review")
    total_studies_included: int = Field(..., description="Total studies included in review")
    
    @property
    def total_identified(self) -> int:
        """Total records identified."""
        return (self.records_identified_databases + 
                self.records_identified_registers + 
                self.records_identified_other)


# =============================================================================
# Search Strategy Documentation
# =============================================================================

class SearchStrategy(BaseModel):
    """Documented search strategy for a single database."""
    database: str = Field(..., description="Database name")
    search_date: str = Field(..., description="Date of search (YYYY-MM-DD)")
    date_range: Optional[str] = Field(None, description="Date limits (e.g., '2015-2024')")
    
    search_string: str = Field(..., description="Complete search strategy")
    filters_applied: List[str] = Field(default_factory=list, description="Filters (e.g., 'Humans', 'English')")
    
    results_count: int = Field(..., description="Number of results retrieved")
    
    # Optional: field-specific searches
    field_searches: Dict[str, str] = Field(default_factory=dict, description="Field-specific search strings")


# =============================================================================
# PRISMA Checklist
# =============================================================================

class PRISMAChecklistItem(BaseModel):
    """Single PRISMA 2020 checklist item."""
    section: str = Field(..., description="Checklist section (e.g., 'Title', 'Methods')")
    item_number: str = Field(..., description="Item number (e.g., '1', '5a')")
    item_description: str = Field(..., description="Checklist item description")
    
    reported: bool = Field(default=False, description="Whether item is reported")
    location: Optional[str] = Field(None, description="Page number or section where reported")
    notes: Optional[str] = Field(None, description="Additional notes")


# =============================================================================
# Risk of Bias Summary
# =============================================================================

class RiskOfBiasSummary(BaseModel):
    """Summary of risk of bias across studies."""
    tool_used: str = Field(..., description="Assessment tool (e.g., 'RoB 2.0', 'ROBINS-I')")
    
    # Domain-level summaries
    domains: List[str] = Field(..., description="Bias domains assessed")
    
    # Study x Domain matrix
    study_judgments: Dict[str, Dict[str, str]] = Field(
        ..., 
        description="study_id -> {domain -> judgment}"
    )
    
    # Overall summary
    low_risk_studies: int = Field(..., description="Number of studies with low risk")
    some_concerns_studies: int = Field(..., description="Number with some concerns")
    high_risk_studies: int = Field(..., description="Number with high risk")
    
    # Percentage summaries per domain
    domain_percentages: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="domain -> {low/some_concerns/high -> percentage}"
    )


# =============================================================================
# Complete PRISMA Report
# =============================================================================

@dataclass
class PRISMAReport:
    """Complete PRISMA 2020 report package."""
    
    # Core components
    flowchart_data: PRISMAFlowchartData
    search_strategies: List[SearchStrategy] = field(default_factory=list)
    checklist: List[PRISMAChecklistItem] = field(default_factory=list)
    rob_summary: Optional[RiskOfBiasSummary] = None
    
    # Additional documentation
    inclusion_criteria: List[str] = field(default_factory=list)
    exclusion_criteria: List[str] = field(default_factory=list)
    data_extraction_items: List[str] = field(default_factory=list)
    
    # GRADE summary of findings (if applicable)
    sof_table: Optional[str] = None
    
    # Metadata
    review_title: str = ""
    authors: List[str] = field(default_factory=list)
    registration_number: Optional[str] = None  # PROSPERO, OSF, etc.
    protocol_doi: Optional[str] = None
    
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def generate_flowchart_mermaid(self) -> str:
        """Generate Mermaid diagram code for PRISMA flowchart."""
        data = self.flowchart_data
        
        mermaid = f"""
flowchart TD
    A["Records identified from:<br/>Databases: {data.records_identified_databases}<br/>Registers: {data.records_identified_registers}"] 
    B["Records screened<br/>(n = {data.records_screened})"]
    C["Reports sought for retrieval<br/>(n = {data.reports_sought_retrieval})"]
    D["Reports assessed for eligibility<br/>(n = {data.reports_assessed_eligibility})"]
    E["Studies included in review<br/>(n = {data.total_studies_included})"]
    
    A -->|"Duplicates removed: {data.records_removed_before_screening}"| B
    B -->|"Excluded: {data.records_excluded}"| C
    C -->|"Not retrieved: {data.reports_not_retrieved}"| D
    D -->|"Excluded: {data.reports_excluded}"| E
"""
        return mermaid
    
    def generate_checklist_table(self) -> str:
        """Generate HTML table for PRISMA checklist."""
        if not self.checklist:
            return ""
        
        html = """
<table>
<thead>
<tr><th>Section</th><th>Item #</th><th>Checklist Item</th><th>Reported</th><th>Location</th></tr>
</thead>
<tbody>
"""
        for item in self.checklist:
            reported_mark = "✓" if item.reported else "✗"
            location = item.location or "—"
            html += f"<tr><td>{item.section}</td><td>{item.item_number}</td><td>{item.item_description}</td><td>{reported_mark}</td><td>{location}</td></tr>\n"
        
        html += "</tbody>\n</table>"
        return html
    
    def generate_search_appendix(self) -> str:
        """Generate formatted search strategy appendix."""
        if not self.search_strategies:
            return ""
        
        sections = []
        for idx, strategy in enumerate(self.search_strategies, 1):
            section = f"""
### Database {idx}: {strategy.database}

**Search Date:** {strategy.search_date}
**Date Range:** {strategy.date_range or 'No limit'}
**Results:** {strategy.results_count} records

**Search Strategy:**
```
{strategy.search_string}
```

**Filters Applied:** {', '.join(strategy.filters_applied) if strategy.filters_applied else 'None'}
"""
            sections.append(section)
        
        return "\n\n".join(sections)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "flowchart_data": self.flowchart_data.model_dump(),
            "search_strategies": [s.model_dump() for s in self.search_strategies],
            "checklist_completion": {
                "total_items": len(self.checklist),
                "reported_items": sum(1 for item in self.checklist if item.reported),
                "completion_percentage": (sum(1 for item in self.checklist if item.reported) / len(self.checklist) * 100) if self.checklist else 0,
            },
            "rob_summary": self.rob_summary.model_dump() if self.rob_summary else None,
            "review_metadata": {
                "title": self.review_title,
                "authors": self.authors,
                "registration": self.registration_number,
                "protocol_doi": self.protocol_doi,
            },
            "generated_at": self.generated_at,
        }
