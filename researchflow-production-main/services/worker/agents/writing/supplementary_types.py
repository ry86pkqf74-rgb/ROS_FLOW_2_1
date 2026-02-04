"""
Type definitions for Supplementary Material Agent

Defines the data models for organizing and packaging supplementary materials
including tables, figures, methods, datasets, and appendices for manuscript submission.

See: Linear ROS-67 (Phase D: Remaining Agents) - Stage 15 Enhancement
"""

from typing import List, Optional, Dict, Any, Union, Literal
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, validator


# =============================================================================
# Enums
# =============================================================================

class SupplementaryItemType(str, Enum):
    """Types of supplementary items."""
    TABLE = "table"
    FIGURE = "figure"
    METHOD = "method"
    DATASET = "dataset"
    APPENDIX = "appendix"
    CHECKLIST = "checklist"
    FORM = "form"
    CODE = "code"


class FileFormat(str, Enum):
    """Supported file formats for supplementary materials."""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    ZIP = "zip"
    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    R = "r"
    PYTHON = "py"
    SAS = "sas"
    STATA = "do"


class JournalFormat(str, Enum):
    """Journal-specific formatting requirements."""
    NEJM = "nejm"
    JAMA = "jama"
    LANCET = "lancet"
    BMJ = "bmj"
    PLOS_ONE = "plos_one"
    NATURE = "nature"
    GENERIC = "generic"


class ChecklistType(str, Enum):
    """Types of reporting checklists."""
    STROBE = "strobe"
    CONSORT = "consort"
    PRISMA = "prisma"
    STARD = "stard"
    SQUIRE = "squire"
    SPIRIT = "spirit"


class PlacementDecision(str, Enum):
    """Where an item should be placed."""
    MAIN_TEXT = "main_text"
    SUPPLEMENT = "supplement"
    ONLINE_ONLY = "online_only"
    EXCLUDE = "exclude"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class SupplementaryTable:
    """Represents a supplementary table with metadata."""
    number: str  # e.g., "S1", "S2"
    title: str
    caption: str
    content: str  # Table data (HTML, CSV, or formatted text)
    source_table_id: Optional[str] = None
    file_path: Optional[str] = None
    page_count: int = 1
    footnotes: List[str] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "caption": self.caption,
            "content": self.content,
            "source_table_id": self.source_table_id,
            "file_path": self.file_path,
            "page_count": self.page_count,
            "footnotes": self.footnotes,
            "cross_references": self.cross_references,
        }


@dataclass
class SupplementaryFigure:
    """Represents a supplementary figure with metadata."""
    number: str  # e.g., "S1", "S2"
    title: str
    caption: str
    file_path: str
    source_figure_id: Optional[str] = None
    format: FileFormat = FileFormat.PDF
    dimensions: Optional[tuple[int, int]] = None
    dpi: Optional[int] = None
    legend: Optional[str] = None
    cross_references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "number": self.number,
            "title": self.title,
            "caption": self.caption,
            "file_path": self.file_path,
            "source_figure_id": self.source_figure_id,
            "format": self.format.value,
            "dimensions": self.dimensions,
            "dpi": self.dpi,
            "legend": self.legend,
            "cross_references": self.cross_references,
        }


@dataclass
class Appendix:
    """Represents an appendix section."""
    id: str  # e.g., "A1", "A2"
    title: str
    content: str
    type: SupplementaryItemType
    file_path: Optional[str] = None
    page_count: int = 1
    subsections: List[Dict[str, str]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "type": self.type.value,
            "file_path": self.file_path,
            "page_count": self.page_count,
            "subsections": self.subsections,
        }


class SupplementaryMaterialState(BaseModel):
    """
    Pydantic model for Supplementary Material Agent state.
    
    Manages the complete state for organizing and packaging supplementary materials
    for manuscript submission.
    """
    
    # Core identifiers
    study_id: str = Field(description="Unique study identifier")
    manuscript_id: str = Field(description="Manuscript identifier")
    project_id: str = Field(description="Research project ID")
    
    # Inputs from previous stages
    main_manuscript: str = Field(default="", description="Main manuscript text")
    manuscript_sections: Dict[str, str] = Field(default_factory=dict, description="Individual manuscript sections")
    all_tables: List[Dict[str, Any]] = Field(default_factory=list, description="All generated tables")
    all_figures: List[Dict[str, Any]] = Field(default_factory=list, description="All generated figures")
    detailed_methods: str = Field(default="", description="Detailed methods from protocol")
    statistical_results: Dict[str, Any] = Field(default_factory=dict, description="Statistical analysis results")
    raw_data_summary: Dict[str, Any] = Field(default_factory=dict, description="Raw data characteristics")
    additional_analyses: List[Dict[str, Any]] = Field(default_factory=list, description="Sensitivity/subgroup analyses")
    
    # Generated outputs
    supplementary_tables: List[SupplementaryTable] = Field(default_factory=list, description="Organized supplementary tables")
    supplementary_figures: List[SupplementaryFigure] = Field(default_factory=list, description="Organized supplementary figures")
    supplementary_methods: str = Field(default="", description="Extended methods section")
    supplementary_results: str = Field(default="", description="Additional results section")
    data_availability_statement: str = Field(default="", description="Data sharing statement")
    appendices: List[Appendix] = Field(default_factory=list, description="Organized appendices")
    
    # Package metadata
    package_manifest: Dict[str, str] = Field(default_factory=dict, description="File manifest with descriptions")
    total_supplement_pages: int = Field(default=0, description="Total page count estimate")
    file_formats: List[str] = Field(default_factory=list, description="List of file formats included")
    package_size_mb: float = Field(default=0.0, description="Estimated package size in MB")
    
    # Configuration
    journal_format: JournalFormat = Field(default=JournalFormat.GENERIC, description="Target journal format")
    include_raw_data: bool = Field(default=False, description="Whether to include raw datasets")
    include_code: bool = Field(default=True, description="Whether to include analysis code")
    max_package_size_mb: float = Field(default=50.0, description="Maximum package size limit")
    
    # Quality control
    placement_decisions: Dict[str, PlacementDecision] = Field(default_factory=dict, description="Content placement decisions")
    cross_reference_map: Dict[str, List[str]] = Field(default_factory=dict, description="Cross-reference relationships")
    validation_results: Dict[str, bool] = Field(default_factory=dict, description="Validation check results")
    
    # Metadata
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    warnings: List[str] = Field(default_factory=list, description="Warnings about content")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    version: str = Field(default="1.0", description="Version of supplementary package")
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            SupplementaryTable: lambda t: t.to_dict(),
            SupplementaryFigure: lambda f: f.to_dict(),
            Appendix: lambda a: a.to_dict(),
        }
    
    @validator('max_package_size_mb')
    def validate_package_size(cls, v):
        """Ensure reasonable package size limits."""
        if v <= 0:
            raise ValueError("Package size must be positive")
        if v > 1000:  # 1GB limit
            raise ValueError("Package size limit too large (max 1000MB)")
        return v
    
    def add_supplementary_table(
        self,
        title: str,
        content: str,
        caption: str,
        source_table_id: Optional[str] = None,
        **kwargs
    ) -> SupplementaryTable:
        """Add a supplementary table."""
        number = f"S{len(self.supplementary_tables) + 1}"
        table = SupplementaryTable(
            number=number,
            title=title,
            content=content,
            caption=caption,
            source_table_id=source_table_id,
            **kwargs
        )
        self.supplementary_tables.append(table)
        return table
    
    def add_supplementary_figure(
        self,
        title: str,
        file_path: str,
        caption: str,
        source_figure_id: Optional[str] = None,
        **kwargs
    ) -> SupplementaryFigure:
        """Add a supplementary figure."""
        number = f"S{len(self.supplementary_figures) + 1}"
        figure = SupplementaryFigure(
            number=number,
            title=title,
            file_path=file_path,
            caption=caption,
            source_figure_id=source_figure_id,
            **kwargs
        )
        self.supplementary_figures.append(figure)
        return figure
    
    def add_appendix(
        self,
        title: str,
        content: str,
        type: SupplementaryItemType,
        **kwargs
    ) -> Appendix:
        """Add an appendix."""
        appendix_id = f"A{len(self.appendices) + 1}"
        appendix = Appendix(
            id=appendix_id,
            title=title,
            content=content,
            type=type,
            **kwargs
        )
        self.appendices.append(appendix)
        return appendix
    
    def get_total_items(self) -> int:
        """Get total count of supplementary items."""
        return len(self.supplementary_tables) + len(self.supplementary_figures) + len(self.appendices)
    
    def validate_completeness(self) -> List[str]:
        """Validate that the supplementary package is complete."""
        issues = []
        
        if not self.data_availability_statement:
            issues.append("Data availability statement missing")
        
        if self.include_raw_data and not any("data" in item.lower() for item in self.package_manifest.values()):
            issues.append("Raw data inclusion requested but no data files in manifest")
        
        if self.include_code and not any("code" in item.lower() for item in self.package_manifest.values()):
            issues.append("Code inclusion requested but no code files in manifest")
        
        # Check for broken cross-references
        for item_id, refs in self.cross_reference_map.items():
            for ref in refs:
                if ref not in self.cross_reference_map and not any(ref in str(table.number) for table in self.supplementary_tables):
                    issues.append(f"Broken cross-reference: {item_id} -> {ref}")
        
        if self.package_size_mb > self.max_package_size_mb:
            issues.append(f"Package size ({self.package_size_mb:.1f}MB) exceeds limit ({self.max_package_size_mb:.1f}MB)")
        
        return issues
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the supplementary package."""
        return {
            "study_id": self.study_id,
            "total_tables": len(self.supplementary_tables),
            "total_figures": len(self.supplementary_figures),
            "total_appendices": len(self.appendices),
            "total_pages": self.total_supplement_pages,
            "package_size_mb": self.package_size_mb,
            "file_formats": self.file_formats,
            "journal_format": self.journal_format.value,
            "has_data_statement": bool(self.data_availability_statement),
            "num_errors": len(self.errors),
            "num_warnings": len(self.warnings),
            "completeness_issues": len(self.validate_completeness()),
            "version": self.version,
            "created_at": self.created_at,
        }


# =============================================================================
# Request/Response Types
# =============================================================================

class SupplementaryMaterialRequest(BaseModel):
    """Request for supplementary material generation."""
    study_id: str
    manuscript_id: str
    main_manuscript: str
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    figures: List[Dict[str, Any]] = Field(default_factory=list)
    methods: str = ""
    statistical_results: Dict[str, Any] = Field(default_factory=dict)
    journal_format: JournalFormat = JournalFormat.GENERIC
    options: Dict[str, Any] = Field(default_factory=dict)


class SupplementaryMaterialResponse(BaseModel):
    """Response from supplementary material generation."""
    success: bool
    study_id: str
    supplementary_state: Optional[SupplementaryMaterialState] = None
    package_manifest: Dict[str, str] = Field(default_factory=dict)
    download_links: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    processing_time_ms: int
    
    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Journal-Specific Configuration
# =============================================================================

@dataclass
class JournalRequirements:
    """Journal-specific requirements for supplementary materials."""
    max_size_mb: float
    preferred_formats: List[FileFormat]
    table_format: str  # "excel", "csv", "pdf"
    figure_format: str  # "pdf", "png", "eps"
    requires_data_statement: bool
    requires_code: bool
    max_supplement_pages: Optional[int]
    naming_convention: str  # Pattern for file naming
    
    @classmethod
    def get_requirements(cls, journal: JournalFormat) -> 'JournalRequirements':
        """Get requirements for specific journal."""
        requirements_map = {
            JournalFormat.NEJM: cls(
                max_size_mb=25.0,
                preferred_formats=[FileFormat.PDF, FileFormat.DOCX],
                table_format="pdf",
                figure_format="pdf",
                requires_data_statement=True,
                requires_code=False,
                max_supplement_pages=50,
                naming_convention="appendix_{number}.pdf"
            ),
            JournalFormat.JAMA: cls(
                max_size_mb=30.0,
                preferred_formats=[FileFormat.PDF, FileFormat.DOCX, FileFormat.XLSX],
                table_format="excel",
                figure_format="pdf",
                requires_data_statement=True,
                requires_code=True,
                max_supplement_pages=None,
                naming_convention="supplement_{number}.{ext}"
            ),
            JournalFormat.PLOS_ONE: cls(
                max_size_mb=100.0,
                preferred_formats=[FileFormat.PDF, FileFormat.DOCX, FileFormat.CSV, FileFormat.ZIP],
                table_format="csv",
                figure_format="pdf",
                requires_data_statement=True,
                requires_code=True,
                max_supplement_pages=None,
                naming_convention="S{number}_{type}.{ext}"
            ),
            JournalFormat.GENERIC: cls(
                max_size_mb=50.0,
                preferred_formats=[FileFormat.PDF, FileFormat.DOCX, FileFormat.ZIP],
                table_format="pdf",
                figure_format="pdf",
                requires_data_statement=True,
                requires_code=True,
                max_supplement_pages=None,
                naming_convention="supplement_{number}.{ext}"
            )
        }
        return requirements_map.get(journal, requirements_map[JournalFormat.GENERIC])


# =============================================================================
# Checklist Definitions
# =============================================================================

STROBE_CHECKLIST = [
    {"item": "1a", "description": "Title and abstract - Indicate study design", "required": True},
    {"item": "1b", "description": "Title and abstract - Provide informative abstract", "required": True},
    {"item": "2", "description": "Background/rationale - Explain scientific background", "required": True},
    {"item": "3", "description": "Objectives - State specific objectives", "required": True},
    {"item": "4", "description": "Study design - Present key design elements early", "required": True},
    {"item": "5", "description": "Setting - Describe study setting", "required": True},
    {"item": "6a", "description": "Participants - Eligibility criteria", "required": True},
    {"item": "6b", "description": "Participants - Sources and selection methods", "required": True},
    {"item": "7", "description": "Variables - Clearly define all outcomes", "required": True},
    {"item": "8", "description": "Data sources/measurement - For each variable", "required": True},
    {"item": "9", "description": "Bias - Describe efforts to address potential bias", "required": True},
    {"item": "10", "description": "Study size - Explain how study size was determined", "required": True},
    {"item": "11", "description": "Quantitative variables - How handled in analyses", "required": True},
    {"item": "12a", "description": "Statistical methods - Describe all statistical methods", "required": True},
    {"item": "12b", "description": "Statistical methods - Methods for subgroups", "required": False},
    {"item": "12c", "description": "Statistical methods - Missing data methods", "required": True},
    {"item": "12d", "description": "Statistical methods - Loss to follow-up handling", "required": False},
    {"item": "12e", "description": "Statistical methods - Sensitivity analyses", "required": False},
]

CONSORT_CHECKLIST = [
    {"item": "1a", "description": "Title - Identification as randomized trial", "required": True},
    {"item": "1b", "description": "Abstract - Structured summary", "required": True},
    {"item": "2a", "description": "Background - Scientific background", "required": True},
    {"item": "2b", "description": "Background - Specific objectives/hypotheses", "required": True},
    {"item": "3a", "description": "Trial design - Description of trial design", "required": True},
    {"item": "3b", "description": "Trial design - Important changes after trial start", "required": True},
    {"item": "4a", "description": "Participants - Eligibility criteria", "required": True},
    {"item": "4b", "description": "Participants - Settings and locations", "required": True},
    {"item": "5", "description": "Interventions - Details of interventions", "required": True},
    {"item": "6a", "description": "Outcomes - Completely defined primary outcomes", "required": True},
    {"item": "6b", "description": "Outcomes - Important secondary outcomes", "required": True},
    {"item": "7a", "description": "Sample size - How determined", "required": True},
    {"item": "7b", "description": "Sample size - Interim analyses and stopping", "required": False},
]