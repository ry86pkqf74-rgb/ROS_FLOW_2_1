"""
Data Visualization API Routes

FastAPI routes for DataVisualizationAgent integration.
Handles chart generation requests from the orchestrator.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import pandas as pd

# Import the visualization agent
try:
    import sys
    from pathlib import Path
    # Add agents directory to path
    agents_dir = Path(__file__).parent.parent.parent.parent / "agents"
    sys.path.insert(0, str(agents_dir))
    
    from analysis import (
        create_data_visualization_agent,
        VizType, VizRequest, VizResult,
        BarChartConfig, LineChartConfig, ScatterConfig,
        BoxPlotConfig, KMConfig, ForestConfig,
        ColorPalette, JournalStyle, ExportFormat, Orientation,
        FlowStage, VizEffectSize,
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    logging.warning(f"DataVisualizationAgent not available: {e}")

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ChartDataRequest(BaseModel):
    """Chart data payload"""
    data: Dict[str, List[Any]] = Field(..., description="Column-oriented data")
    

class BarChartRequest(BaseModel):
    """Bar chart generation request"""
    data: Dict[str, List[Any]]
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    show_error_bars: bool = False
    error_bar_type: Optional[str] = "std"
    orientation: str = "vertical"
    color_palette: str = "colorblind_safe"
    journal_style: Optional[str] = None
    dpi: int = 300


class LineChartRequest(BaseModel):
    """Line chart generation request"""
    data: Dict[str, List[Any]]
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    show_markers: bool = True
    show_confidence_bands: bool = False
    color_palette: str = "colorblind_safe"
    journal_style: Optional[str] = None
    dpi: int = 300


class ScatterPlotRequest(BaseModel):
    """Scatter plot generation request"""
    data: Dict[str, List[Any]]
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    show_trendline: bool = False
    show_correlation: bool = True
    color_palette: str = "colorblind_safe"
    journal_style: Optional[str] = None
    dpi: int = 300


class BoxPlotRequest(BaseModel):
    """Box plot generation request"""
    data: Dict[str, List[Any]]
    title: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    show_outliers: bool = True
    show_means: bool = True
    color_palette: str = "colorblind_safe"
    journal_style: Optional[str] = None
    dpi: int = 300


class KaplanMeierRequest(BaseModel):
    """Kaplan-Meier curve generation request"""
    data: Dict[str, List[Any]]
    title: Optional[str] = None
    time_col: str = "time"
    event_col: str = "event"
    group_col: Optional[str] = None
    show_risk_table: bool = True
    show_confidence_intervals: bool = True
    journal_style: Optional[str] = None
    dpi: int = 300


class ForestPlotRequest(BaseModel):
    """Forest plot generation request"""
    effects: List[Dict[str, Any]]  # List of effect size objects
    title: Optional[str] = None
    effect_measure: str = "OR"
    show_diamond_summary: bool = True
    journal_style: Optional[str] = None
    dpi: int = 300


class FlowchartRequest(BaseModel):
    """Flowchart generation request"""
    stages: List[Dict[str, Any]]  # List of flow stage objects
    title: Optional[str] = None
    flowchart_type: str = "consort"
    journal_style: Optional[str] = None
    dpi: int = 300


class VisualizationResponse(BaseModel):
    """Visualization generation response"""
    success: bool
    figure_id: Optional[str] = None
    image_base64: Optional[str] = None
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int


# =============================================================================
# Routes
# =============================================================================

@router.post("/api/visualization/bar-chart")
async def create_bar_chart(request: BarChartRequest):
    """
    Generate a bar chart.
    
    Returns:
        Visualization response with base64-encoded image and metadata
    """
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="DataVisualizationAgent not available. Check dependencies."
        )
    
    try:
        # Create agent instance
        agent = create_data_visualization_agent()
        
        # Convert request data to DataFrame
        df = pd.DataFrame(request.data)
        
        # Build configuration
        config = BarChartConfig(
            title=request.title or "",
            x_label=request.x_label or "",
            y_label=request.y_label or "",
            show_error_bars=request.show_error_bars,
            error_bar_type=request.error_bar_type,
            orientation=Orientation(request.orientation),
            color_palette=ColorPalette(request.color_palette),
            journal_style=JournalStyle(request.journal_style) if request.journal_style else None,
            dpi=request.dpi,
        )
        
        logger.info(f"Generating bar chart: {config.title}")
        
        # Generate figure
        figure = agent.create_bar_chart(df, config)
        
        # Convert image bytes to base64
        import base64
        image_base64 = base64.b64encode(figure.image_bytes).decode('utf-8')
        
        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info(f"Bar chart generated in {duration_ms}ms")
        
        return VisualizationResponse(
            success=True,
            figure_id=figure.id,
            image_base64=image_base64,
            caption=figure.caption,
            alt_text=figure.alt_text,
            metadata=figure.to_dict(),
            duration_ms=duration_ms,
        )
    
    except Exception as e:
        logger.error(f"Bar chart generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return VisualizationResponse(
            success=False,
            error=str(e),
            duration_ms=duration_ms,
        )


@router.post("/api/visualization/line-chart")
async def create_line_chart(request: LineChartRequest):
    """Generate a line chart."""
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    try:
        agent = create_data_visualization_agent()
        df = pd.DataFrame(request.data)
        
        config = LineChartConfig(
            title=request.title or "",
            x_label=request.x_label or "",
            y_label=request.y_label or "",
            show_markers=request.show_markers,
            show_confidence_bands=request.show_confidence_bands,
            color_palette=ColorPalette(request.color_palette),
            journal_style=JournalStyle(request.journal_style) if request.journal_style else None,
            dpi=request.dpi,
        )
        
        figure = agent.create_line_chart(df, config)
        
        import base64
        image_base64 = base64.b64encode(figure.image_bytes).decode('utf-8')
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return VisualizationResponse(
            success=True,
            figure_id=figure.id,
            image_base64=image_base64,
            caption=figure.caption,
            alt_text=figure.alt_text,
            metadata=figure.to_dict(),
            duration_ms=duration_ms,
        )
    
    except Exception as e:
        logger.error(f"Line chart generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return VisualizationResponse(success=False, error=str(e), duration_ms=duration_ms)


@router.post("/api/visualization/scatter-plot")
async def create_scatter_plot(request: ScatterPlotRequest):
    """Generate a scatter plot."""
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    try:
        agent = create_data_visualization_agent()
        df = pd.DataFrame(request.data)
        
        config = ScatterConfig(
            title=request.title or "",
            x_label=request.x_label or "",
            y_label=request.y_label or "",
            show_trendline=request.show_trendline,
            show_correlation=request.show_correlation,
            color_palette=ColorPalette(request.color_palette),
            journal_style=JournalStyle(request.journal_style) if request.journal_style else None,
            dpi=request.dpi,
        )
        
        figure = agent.create_scatter_plot(df, config)
        
        import base64
        image_base64 = base64.b64encode(figure.image_bytes).decode('utf-8')
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return VisualizationResponse(
            success=True,
            figure_id=figure.id,
            image_base64=image_base64,
            caption=figure.caption,
            alt_text=figure.alt_text,
            metadata=figure.to_dict(),
            duration_ms=duration_ms,
        )
    
    except Exception as e:
        logger.error(f"Scatter plot generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return VisualizationResponse(success=False, error=str(e), duration_ms=duration_ms)


@router.post("/api/visualization/box-plot")
async def create_box_plot(request: BoxPlotRequest):
    """Generate a box plot."""
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    try:
        agent = create_data_visualization_agent()
        df = pd.DataFrame(request.data)
        
        config = BoxPlotConfig(
            title=request.title or "",
            x_label=request.x_label or "",
            y_label=request.y_label or "",
            show_outliers=request.show_outliers,
            show_means=request.show_means,
            color_palette=ColorPalette(request.color_palette),
            journal_style=JournalStyle(request.journal_style) if request.journal_style else None,
            dpi=request.dpi,
        )
        
        figure = agent.create_box_plot(df, config)
        
        import base64
        image_base64 = base64.b64encode(figure.image_bytes).decode('utf-8')
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return VisualizationResponse(
            success=True,
            figure_id=figure.id,
            image_base64=image_base64,
            caption=figure.caption,
            alt_text=figure.alt_text,
            metadata=figure.to_dict(),
            duration_ms=duration_ms,
        )
    
    except Exception as e:
        logger.error(f"Box plot generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        return VisualizationResponse(success=False, error=str(e), duration_ms=duration_ms)


@router.get("/api/visualization/capabilities")
async def get_capabilities():
    """
    Get visualization capabilities.
    
    Returns:
        Information about available chart types and features
    """
    if not AGENT_AVAILABLE:
        return {
            "available": False,
            "error": "DataVisualizationAgent not loaded",
        }
    
    return {
        "available": True,
        "agent": "DataVisualizationAgent",
        "version": "1.0.0",
        "chart_types": [
            "bar_chart",
            "line_chart",
            "scatter_plot",
            "box_plot",
            "kaplan_meier",
            "forest_plot",
            "flowchart",
        ],
        "features": {
            "journal_styles": [
                "nature", "science", "cell", "jama", "nejm",
                "lancet", "bmj", "plos", "apa"
            ],
            "color_palettes": [
                "colorblind_safe", "grayscale", "viridis",
                "pastel", "bold", "journal_nature", "journal_jama"
            ],
            "export_formats": ["png", "svg", "pdf", "eps", "webp"],
            "accessibility": [
                "colorblind_safe_palettes",
                "alt_text_generation",
                "caption_generation"
            ],
        },
    }


@router.get("/api/visualization/health")
async def health_check():
    """
    Health check for visualization service.
    
    Returns:
        Service status and dependencies
    """
    status = {
        "service": "data-visualization",
        "status": "healthy" if AGENT_AVAILABLE else "unavailable",
        "agent_loaded": AGENT_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check dependencies
    dependencies = {}
    try:
        import matplotlib
        dependencies["matplotlib"] = matplotlib.__version__
    except ImportError:
        dependencies["matplotlib"] = "not installed"
    
    try:
        import seaborn
        dependencies["seaborn"] = seaborn.__version__
    except ImportError:
        dependencies["seaborn"] = "not installed"
    
    try:
        import lifelines
        dependencies["lifelines"] = lifelines.__version__
    except ImportError:
        dependencies["lifelines"] = "not installed"
    
    try:
        import PIL
        dependencies["pillow"] = PIL.__version__
    except ImportError:
        dependencies["pillow"] = "not installed"
    
    status["dependencies"] = dependencies
    
    return status
