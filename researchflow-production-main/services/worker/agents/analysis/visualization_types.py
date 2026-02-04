"""
Data Visualization Type Definitions

Comprehensive type definitions for data visualization including:
- Visualization types and configurations
- Figure metadata structures
- Journal style presets
- Color palettes
- Export formats

Linear Issues: ROS-XXX (Stage 8 - Data Visualization Agent)
"""

from typing import List, Optional, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field


# =============================================================================
# Enumerations
# =============================================================================

class VizType(str, Enum):
    """Supported visualization types."""
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    SCATTER_PLOT = "scatter_plot"
    BOX_PLOT = "box_plot"
    VIOLIN_PLOT = "violin_plot"
    HISTOGRAM = "histogram"
    HEATMAP = "heatmap"
    KAPLAN_MEIER = "kaplan_meier"
    FOREST_PLOT = "forest_plot"
    FUNNEL_PLOT = "funnel_plot"
    FLOWCHART = "flowchart"
    CONSORT_DIAGRAM = "consort_diagram"
    PRISMA_DIAGRAM = "prisma_diagram"


class ExportFormat(str, Enum):
    """Supported export formats."""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    EPS = "eps"
    WEBP = "webp"


class JournalStyle(str, Enum):
    """Journal-specific style presets."""
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


class ColorPalette(str, Enum):
    """Color palette options."""
    DEFAULT = "default"
    COLORBLIND_SAFE = "colorblind_safe"
    GRAYSCALE = "grayscale"
    VIRIDIS = "viridis"
    PASTEL = "pastel"
    BOLD = "bold"
    JOURNAL_NATURE = "journal_nature"
    JOURNAL_JAMA = "journal_jama"


class Orientation(str, Enum):
    """Chart orientation."""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


# =============================================================================
# Configuration Classes
# =============================================================================

@dataclass
class BaseChartConfig:
    """Base configuration for all chart types."""
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    width: int = 800
    height: int = 600
    dpi: int = 300
    font_size: int = 12
    font_family: str = "Arial"
    color_palette: ColorPalette = ColorPalette.COLORBLIND_SAFE
    journal_style: JournalStyle = JournalStyle.DEFAULT
    show_grid: bool = True
    show_legend: bool = True
    legend_position: str = "best"
    transparent_background: bool = False


@dataclass
class BarChartConfig(BaseChartConfig):
    """Configuration for bar charts."""
    orientation: Orientation = Orientation.VERTICAL
    show_error_bars: bool = True
    error_bar_type: str = "std"  # "std", "sem", "ci"
    bar_width: float = 0.8
    show_values: bool = True
    value_format: str = ".2f"
    group_spacing: float = 0.2
    colors: Optional[List[str]] = None


@dataclass
class LineChartConfig(BaseChartConfig):
    """Configuration for line charts."""
    show_markers: bool = True
    marker_size: int = 6
    line_width: float = 2.0
    line_style: str = "solid"  # "solid", "dashed", "dotted", "dashdot"
    show_confidence_bands: bool = False
    confidence_level: float = 0.95
    fill_between: bool = False
    colors: Optional[List[str]] = None


@dataclass
class ScatterConfig(BaseChartConfig):
    """Configuration for scatter plots."""
    marker_size: int = 50
    marker_alpha: float = 0.6
    show_trendline: bool = False
    trendline_type: str = "linear"  # "linear", "polynomial", "lowess"
    show_correlation: bool = True
    show_point_labels: bool = False
    color_by_group: bool = False
    colors: Optional[List[str]] = None


@dataclass
class BoxPlotConfig(BaseChartConfig):
    """Configuration for box plots."""
    orientation: Orientation = Orientation.VERTICAL
    show_outliers: bool = True
    show_means: bool = True
    show_notch: bool = False
    box_width: float = 0.5
    colors: Optional[List[str]] = None
    show_individual_points: bool = False
    point_alpha: float = 0.3


@dataclass
class KMConfig(BaseChartConfig):
    """Configuration for Kaplan-Meier survival curves."""
    time_label: str = "Time (months)"
    event_label: str = "Survival probability"
    show_risk_table: bool = True
    show_confidence_intervals: bool = True
    confidence_level: float = 0.95
    show_censored_marks: bool = True
    censored_marker: str = "+"
    show_median_survival: bool = True
    risk_table_position: str = "below"  # "below", "right"
    colors: Optional[List[str]] = None


@dataclass
class ForestConfig(BaseChartConfig):
    """Configuration for forest plots (meta-analysis)."""
    effect_measure: str = "OR"  # "OR", "RR", "HR", "MD", "SMD"
    show_weights: bool = True
    show_diamond_summary: bool = True
    show_heterogeneity: bool = True
    null_line_value: float = 1.0  # 1.0 for ratios, 0.0 for differences
    x_scale: str = "log"  # "log", "linear"
    x_label: Optional[str] = None
    study_label_column: str = "study"
    sort_by_weight: bool = False


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class VizRequest:
    """Request for creating a visualization."""
    viz_type: VizType
    data_columns: Dict[str, str]
    title: Optional[str] = None
    config: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "viz_type": self.viz_type.value,
            "data_columns": self.data_columns,
            "title": self.title,
            "config": self.config.__dict__ if self.config else None,
        }


@dataclass
class Figure:
    """Representation of a generated figure."""
    figure_id: str
    viz_type: VizType
    image_bytes: Optional[bytes] = None
    format: ExportFormat = ExportFormat.PNG
    width: int = 800
    height: int = 600
    dpi: int = 300
    caption: str = ""
    alt_text: str = ""
    data_summary: Dict[str, Any] = field(default_factory=dict)
    rendering_info: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without binary data)."""
        return {
            "figure_id": self.figure_id,
            "viz_type": self.viz_type.value,
            "format": self.format.value,
            "width": self.width,
            "height": self.height,
            "dpi": self.dpi,
            "caption": self.caption,
            "alt_text": self.alt_text,
            "data_summary": self.data_summary,
            "rendering_info": self.rendering_info,
            "created_at": self.created_at,
        }


@dataclass
class FlowStage:
    """Stage in a study flowchart (CONSORT/PRISMA)."""
    name: str
    n: int
    description: Optional[str] = None
    reasons_excluded: Optional[Dict[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "n": self.n,
            "description": self.description,
            "reasons_excluded": self.reasons_excluded or {},
        }


@dataclass
class EffectSize:
    """Effect size for forest plot."""
    study_id: str
    study_label: str
    effect_estimate: float
    ci_lower: float
    ci_upper: float
    weight: float
    n_treatment: Optional[int] = None
    n_control: Optional[int] = None
    year: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "study_id": self.study_id,
            "study_label": self.study_label,
            "effect_estimate": self.effect_estimate,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "weight": self.weight,
            "n_treatment": self.n_treatment,
            "n_control": self.n_control,
            "year": self.year,
        }


@dataclass
class StudyContext:
    """Context information for generating figure captions."""
    study_title: str
    research_question: Optional[str] = None
    outcome_variable: Optional[str] = None
    sample_size: Optional[int] = None
    study_design: Optional[str] = None
    key_findings: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "study_title": self.study_title,
            "research_question": self.research_question,
            "outcome_variable": self.outcome_variable,
            "sample_size": self.sample_size,
            "study_design": self.study_design,
            "key_findings": self.key_findings,
        }


@dataclass
class VizResult:
    """Complete result from visualization generation."""
    figures: List[Figure] = field(default_factory=list)
    captions: List[str] = field(default_factory=list)
    suggested_order: Optional[List[str]] = None
    total_figures: int = 0
    journal_style: JournalStyle = JournalStyle.DEFAULT
    warnings: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "figures": [f.to_dict() for f in self.figures],
            "captions": self.captions,
            "suggested_order": self.suggested_order,
            "total_figures": self.total_figures,
            "journal_style": self.journal_style.value,
            "warnings": self.warnings,
            "generated_at": self.generated_at,
        }
