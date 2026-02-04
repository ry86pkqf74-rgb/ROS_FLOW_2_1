"""
Type definitions for Table and Figure Legend Agent

Defines the data models and enums used for generating publication-ready
captions, legends, and descriptions for tables and figures.

Linear Issues: TableFigureLegendAgent Implementation
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class LegendType(str, Enum):
    """Types of legends supported."""
    TABLE_TITLE = "table_title"
    TABLE_FOOTNOTE = "table_footnote"
    FIGURE_CAPTION = "figure_caption"
    PANEL_DESCRIPTION = "panel_description"
    ACCESSIBILITY_TEXT = "accessibility_text"


class JournalStyleEnum(str, Enum):
    """Supported journal styles for legend formatting."""
    NATURE = "nature"
    SCIENCE = "science"
    CELL = "cell"
    JAMA = "jama"
    NEJM = "nejm"
    LANCET = "lancet"
    BMJ = "bmj"
    PLOS = "plos"
    APA = "apa"
    DEFAULT = "default"


class PanelLabelStyle(str, Enum):
    """Panel labeling styles for multi-panel figures."""
    UPPERCASE = "A, B, C"
    LOWERCASE = "a, b, c"
    ROMAN_UPPER = "I, II, III"
    ROMAN_LOWER = "i, ii, iii"
    NUMERIC = "1, 2, 3"


class AbbreviationPlacement(str, Enum):
    """Where to place abbreviation definitions."""
    INLINE_LEGEND = "inline_legend"
    SEPARATE_LIST = "separate_list"
    FOOTNOTES = "footnotes"
    BOTH = "both"


# =============================================================================
# Data Models
# =============================================================================

class TableLegend(BaseModel):
    """Complete table legend with title and footnotes."""
    
    table_id: str = Field(description="Unique identifier for the table")
    title: str = Field(description="Table title/caption")
    footnotes: List[str] = Field(default_factory=list, description="Table footnotes")
    abbreviations: Dict[str, str] = Field(default_factory=dict, description="Abbreviations used in table")
    data_description: str = Field(default="", description="Description of data presented")
    statistical_notes: List[str] = Field(default_factory=list, description="Statistical method notes")
    word_count: int = Field(default=0, description="Total word count")
    
    # Metadata
    table_number: Optional[int] = Field(default=None, description="Table number in manuscript")
    journal_compliant: bool = Field(default=False, description="Meets journal requirements")
    accessibility_notes: List[str] = Field(default_factory=list, description="Accessibility improvements")
    
    def get_formatted_title(self) -> str:
        """Get formatted title with table number."""
        if self.table_number:
            return f"Table {self.table_number}. {self.title}"
        return f"Table. {self.title}"
    
    def get_complete_legend(self) -> str:
        """Get complete legend text including footnotes."""
        legend_parts = [self.get_formatted_title()]
        
        if self.data_description:
            legend_parts.append(self.data_description)
        
        if self.footnotes:
            legend_parts.extend(self.footnotes)
        
        if self.statistical_notes:
            legend_parts.extend([f"Statistical note: {note}" for note in self.statistical_notes])
        
        return " ".join(legend_parts)


class FigureLegend(BaseModel):
    """Complete figure legend with caption and panel descriptions."""
    
    figure_id: str = Field(description="Unique identifier for the figure")
    caption: str = Field(description="Main figure caption")
    panel_descriptions: Dict[str, str] = Field(default_factory=dict, description="Panel-specific descriptions")
    abbreviations: Dict[str, str] = Field(default_factory=dict, description="Abbreviations used in figure")
    methods_summary: str = Field(default="", description="Brief methods description")
    statistical_info: str = Field(default="", description="Statistical information")
    accessibility_description: str = Field(default="", description="Accessibility alt-text")
    word_count: int = Field(default=0, description="Total word count")
    
    # Metadata
    figure_number: Optional[int] = Field(default=None, description="Figure number in manuscript")
    panel_label_style: PanelLabelStyle = Field(default=PanelLabelStyle.UPPERCASE, description="Panel labeling style")
    journal_compliant: bool = Field(default=False, description="Meets journal requirements")
    has_multiple_panels: bool = Field(default=False, description="Multi-panel figure")
    
    def get_formatted_caption(self) -> str:
        """Get formatted caption with figure number."""
        if self.figure_number:
            return f"Figure {self.figure_number}. {self.caption}"
        return f"Figure. {self.caption}"
    
    def get_complete_legend(self) -> str:
        """Get complete legend text including all components."""
        legend_parts = [self.get_formatted_caption()]
        
        # Add panel descriptions
        if self.panel_descriptions:
            for panel, description in self.panel_descriptions.items():
                legend_parts.append(f"({panel}) {description}")
        
        # Add methods if present
        if self.methods_summary:
            legend_parts.append(self.methods_summary)
        
        # Add statistical information
        if self.statistical_info:
            legend_parts.append(self.statistical_info)
        
        return " ".join(legend_parts)


class Table(BaseModel):
    """Table data structure for legend generation."""
    
    id: str = Field(description="Unique table identifier")
    title: Optional[str] = Field(default=None, description="Existing title if any")
    headers: List[str] = Field(default_factory=list, description="Column headers")
    rows: List[List[Any]] = Field(default_factory=list, description="Table data rows")
    caption: Optional[str] = Field(default=None, description="Existing caption")
    footnotes: List[str] = Field(default_factory=list, description="Existing footnotes")
    data_types: Dict[str, str] = Field(default_factory=dict, description="Data type per column")
    source_description: str = Field(default="", description="Description of data source")
    
    # Analysis metadata
    contains_statistics: bool = Field(default=False, description="Contains statistical results")
    statistical_methods: List[str] = Field(default_factory=list, description="Statistical methods used")
    sample_size: Optional[int] = Field(default=None, description="Sample size represented")
    
    def get_data_preview(self, max_rows: int = 5) -> Dict[str, Any]:
        """Get preview of table data for legend generation."""
        preview_rows = self.rows[:max_rows] if self.rows else []
        return {
            "headers": self.headers,
            "preview_rows": preview_rows,
            "total_rows": len(self.rows),
            "columns": len(self.headers),
            "data_types": self.data_types,
        }


class Figure(BaseModel):
    """Figure data structure for legend generation."""
    
    id: str = Field(description="Unique figure identifier")
    title: Optional[str] = Field(default=None, description="Existing title if any")
    caption: Optional[str] = Field(default=None, description="Existing caption")
    alt_text: Optional[str] = Field(default=None, description="Existing alt text")
    figure_type: str = Field(description="Type of figure (bar_chart, scatter_plot, etc.)")
    
    # Multi-panel information
    has_panels: bool = Field(default=False, description="Multi-panel figure")
    panel_info: Dict[str, Any] = Field(default_factory=dict, description="Panel-specific information")
    
    # Data and methods
    data_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of underlying data")
    analysis_methods: List[str] = Field(default_factory=list, description="Analysis methods used")
    statistical_tests: List[str] = Field(default_factory=list, description="Statistical tests performed")
    
    # Visual elements
    shows_significance: bool = Field(default=False, description="Shows statistical significance")
    includes_error_bars: bool = Field(default=False, description="Has error bars/confidence intervals")
    color_coding: Optional[str] = Field(default=None, description="Color coding scheme")
    
    def get_content_summary(self) -> Dict[str, Any]:
        """Get summary of figure content for legend generation."""
        return {
            "figure_type": self.figure_type,
            "has_panels": self.has_panels,
            "panel_count": len(self.panel_info) if self.panel_info else 1,
            "data_summary": self.data_summary,
            "analysis_methods": self.analysis_methods,
            "statistical_tests": self.statistical_tests,
            "visual_elements": {
                "shows_significance": self.shows_significance,
                "includes_error_bars": self.includes_error_bars,
                "color_coding": self.color_coding,
            }
        }


class JournalSpec(BaseModel):
    """Journal-specific requirements for legends."""
    
    name: str = Field(description="Journal name")
    max_legend_words: int = Field(description="Maximum words in legend")
    abbreviations_in_legend: bool = Field(default=True, description="Allow abbreviations in legend")
    abbreviation_placement: AbbreviationPlacement = Field(default=AbbreviationPlacement.INLINE_LEGEND)
    requires_footnotes: bool = Field(default=False, description="Requires footnote format")
    panel_label_style: PanelLabelStyle = Field(default=PanelLabelStyle.UPPERCASE)
    methods_in_legend: bool = Field(default=True, description="Include methods in legend")
    statistical_info_required: bool = Field(default=True, description="Require statistical information")
    sample_size_required: bool = Field(default=True, description="Require sample size mention")
    
    # Style preferences
    prefers_active_voice: bool = Field(default=True, description="Prefers active voice")
    concise_style: bool = Field(default=False, description="Prefers very concise style")
    methods_minimal: bool = Field(default=False, description="Minimal methods description")


class TableFigureLegendState(BaseModel):
    """
    Pydantic model for TableFigureLegendAgent state.
    
    This represents the complete state passed through the legend generation workflow,
    including inputs from previous stages and generated outputs.
    """
    
    # Inputs
    study_id: str = Field(description="Unique study identifier")
    tables: List[Table] = Field(default_factory=list, description="Tables from analysis")
    figures: List[Figure] = Field(default_factory=list, description="Figures from visualization")
    manuscript_context: str = Field(default="", description="Manuscript context and background")
    target_journal: Optional[str] = Field(default=None, description="Target journal for submission")
    
    # Processing context
    study_design: Optional[str] = Field(default=None, description="Study design type")
    primary_outcome: Optional[str] = Field(default=None, description="Primary outcome measure")
    sample_size: Optional[int] = Field(default=None, description="Study sample size")
    
    # Outputs
    table_legends: Dict[str, TableLegend] = Field(default_factory=dict, description="Generated table legends")
    figure_legends: Dict[str, FigureLegend] = Field(default_factory=dict, description="Generated figure legends")
    abbreviation_list: List[str] = Field(default_factory=list, description="Master abbreviation list")
    footnotes: Dict[str, List[str]] = Field(default_factory=dict, description="Footnotes by visual ID")
    accessibility_descriptions: Dict[str, str] = Field(default_factory=dict, description="Alt text for figures")
    
    # Quality metrics
    legend_word_counts: Dict[str, int] = Field(default_factory=dict, description="Word counts by legend")
    journal_compliance: Dict[str, bool] = Field(default_factory=dict, description="Journal compliance status")
    cross_references: Dict[str, str] = Field(default_factory=dict, description="Figure/table numbering")
    
    # Metadata
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings about quality")
    processing_notes: List[str] = Field(default_factory=list, description="Processing notes")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
        }
    
    def add_table_legend(self, table_id: str, legend: TableLegend) -> None:
        """Add a table legend to the state."""
        self.table_legends[table_id] = legend
        self.legend_word_counts[f"table_{table_id}"] = legend.word_count
    
    def add_figure_legend(self, figure_id: str, legend: FigureLegend) -> None:
        """Add a figure legend to the state."""
        self.figure_legends[figure_id] = legend
        self.legend_word_counts[f"figure_{figure_id}"] = legend.word_count
    
    def add_abbreviation(self, abbreviation: str, definition: str) -> None:
        """Add an abbreviation to the master list."""
        abbrev_entry = f"{abbreviation}: {definition}"
        if abbrev_entry not in self.abbreviation_list:
            self.abbreviation_list.append(abbrev_entry)
    
    def get_total_word_count(self) -> int:
        """Get total word count across all legends."""
        return sum(self.legend_word_counts.values())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of legend generation results."""
        return {
            "study_id": self.study_id,
            "tables_processed": len(self.tables),
            "figures_processed": len(self.figures),
            "table_legends_generated": len(self.table_legends),
            "figure_legends_generated": len(self.figure_legends),
            "total_abbreviations": len(self.abbreviation_list),
            "total_word_count": self.get_total_word_count(),
            "journal_compliance_rate": (
                sum(self.journal_compliance.values()) / len(self.journal_compliance)
                if self.journal_compliance else 0
            ),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "target_journal": self.target_journal,
            "created_at": self.created_at,
        }
    
    def validate_completeness(self) -> List[str]:
        """Validate that legend generation is complete."""
        issues = []
        
        # Check that all tables have legends
        table_ids = {table.id for table in self.tables}
        legend_table_ids = set(self.table_legends.keys())
        missing_table_legends = table_ids - legend_table_ids
        if missing_table_legends:
            issues.append(f"Missing table legends for: {', '.join(missing_table_legends)}")
        
        # Check that all figures have legends
        figure_ids = {figure.id for figure in self.figures}
        legend_figure_ids = set(self.figure_legends.keys())
        missing_figure_legends = figure_ids - legend_figure_ids
        if missing_figure_legends:
            issues.append(f"Missing figure legends for: {', '.join(missing_figure_legends)}")
        
        # Check journal compliance if target journal specified
        if self.target_journal and not all(self.journal_compliance.values()):
            non_compliant = [
                visual_id for visual_id, compliant in self.journal_compliance.items()
                if not compliant
            ]
            issues.append(f"Non-compliant legends for {self.target_journal}: {', '.join(non_compliant)}")
        
        # Check for errors
        if self.errors:
            issues.append(f"{len(self.errors)} errors present in legend generation")
        
        return issues


# =============================================================================
# Request/Response Models
# =============================================================================

class LegendGenerationRequest(BaseModel):
    """Request for legend generation."""
    
    study_id: str
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    figures: List[Dict[str, Any]] = Field(default_factory=list)
    manuscript_context: str = ""
    target_journal: Optional[str] = None
    generation_options: Dict[str, Any] = Field(default_factory=dict)


class LegendGenerationResponse(BaseModel):
    """Response from legend generation."""
    
    success: bool
    study_id: str
    legend_state: Optional[TableFigureLegendState] = None
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    processing_time_ms: int
    
    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Utility Functions
# =============================================================================

def extract_abbreviations_from_text(text: str) -> List[str]:
    """Extract potential abbreviations from text."""
    import re
    
    # Pattern for abbreviations (uppercase letters, possibly with numbers)
    abbrev_pattern = r'\b[A-Z]{2,}(?:\d+)?\b'
    
    # Common non-abbreviation words to exclude
    exclude_words = {
        'AND', 'OR', 'NOT', 'THE', 'FOR', 'WITH', 'FROM', 'TO', 'OF', 'IN', 'ON', 
        'BY', 'AT', 'IS', 'ARE', 'WAS', 'WERE', 'BE', 'BEEN', 'HAVE', 'HAS', 'HAD',
        'DO', 'DOES', 'DID', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'MAY', 'MIGHT',
        'ALL', 'ANY', 'SOME', 'EACH', 'EVERY', 'NO', 'YES', 'TRUE', 'FALSE'
    }
    
    abbreviations = re.findall(abbrev_pattern, text)
    # Filter out common non-abbreviation words and very long strings
    return [
        abbr for abbr in set(abbreviations) 
        if abbr not in exclude_words and 2 <= len(abbr) <= 10
    ]


def count_words(text: str) -> int:
    """Count words in text, handling various formats."""
    if not text:
        return 0
    
    import re
    # Remove extra whitespace and split on word boundaries
    words = re.findall(r'\b\w+\b', text)
    return len(words)


def format_panel_label(panel_id: str, style: PanelLabelStyle) -> str:
    """Format panel label according to style."""
    try:
        # Convert panel_id to integer index
        if panel_id.isdigit():
            index = int(panel_id)
        else:
            # Try to extract number from string like "panel_1"
            import re
            match = re.search(r'(\d+)', panel_id)
            index = int(match.group(1)) if match else 1
    except (ValueError, AttributeError):
        index = 1
    
    if style == PanelLabelStyle.UPPERCASE:
        return chr(ord('A') + index - 1)  # A, B, C...
    elif style == PanelLabelStyle.LOWERCASE:
        return chr(ord('a') + index - 1)  # a, b, c...
    elif style == PanelLabelStyle.ROMAN_UPPER:
        romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
        return romans[index - 1] if index <= len(romans) else f'#{index}'
    elif style == PanelLabelStyle.ROMAN_LOWER:
        romans = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']
        return romans[index - 1] if index <= len(romans) else f'#{index}'
    elif style == PanelLabelStyle.NUMERIC:
        return str(index)
    
    return str(index)  # Default fallback