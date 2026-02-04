"""
Legend Generation API Routes

FastAPI routes for TableFigureLegendAgent integration.
Handles legend generation requests from the orchestrator.

Phase 2: Stage 1b - API Integration
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import asyncio

# Import the legend generation agent and types
try:
    import sys
    from pathlib import Path
    # Add agents directory to path
    agents_dir = Path(__file__).parent.parent.parent.parent / "agents" / "writing"
    sys.path.insert(0, str(agents_dir))
    
    from table_figure_legend_agent import (
        create_table_figure_legend_agent,
        TableFigureLegendAgent,
    )
    from legend_types import (
        LegendGenerationRequest,
        LegendGenerationResponse,
        TableFigureLegendState,
        Table,
        Figure,
        JournalStyleEnum,
        TableLegend,
        FigureLegend,
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    logging.warning(f"TableFigureLegendAgent not available: {e}")

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TableData(BaseModel):
    """Table data for legend generation"""
    id: str
    title: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    rows: List[List[Any]] = Field(default_factory=list)
    data_types: Dict[str, str] = Field(default_factory=dict)
    contains_statistics: bool = False
    statistical_methods: List[str] = Field(default_factory=list)
    sample_size: Optional[int] = None


class FigureData(BaseModel):
    """Figure data for legend generation"""
    id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    figure_type: str
    has_panels: bool = False
    panel_info: Dict[str, Any] = Field(default_factory=dict)
    data_summary: Dict[str, Any] = Field(default_factory=dict)
    analysis_methods: List[str] = Field(default_factory=list)
    statistical_tests: List[str] = Field(default_factory=list)


class GenerateLegendsRequest(BaseModel):
    """Request to generate legends for tables and figures"""
    study_id: str
    tables: List[TableData] = Field(default_factory=list)
    figures: List[FigureData] = Field(default_factory=list)
    manuscript_context: str = ""
    target_journal: Optional[str] = None
    generation_options: Dict[str, Any] = Field(default_factory=dict)


class GenerateTableLegendRequest(BaseModel):
    """Request to generate a single table legend"""
    table: TableData
    manuscript_context: str = ""
    target_journal: Optional[str] = None


class GenerateFigureLegendRequest(BaseModel):
    """Request to generate a single figure legend"""
    figure: FigureData
    manuscript_context: str = ""
    target_journal: Optional[str] = None


class LegendData(BaseModel):
    """Legend data in response"""
    type: str  # "table" or "figure"
    visual_id: str
    title: Optional[str] = None
    caption: Optional[str] = None
    complete_legend: str
    word_count: int
    journal_compliant: bool
    abbreviations: Dict[str, str] = Field(default_factory=dict)
    accessibility_description: Optional[str] = None
    panel_descriptions: Dict[str, str] = Field(default_factory=dict)


class LegendsResponse(BaseModel):
    """Response from legend generation"""
    success: bool
    study_id: str
    legends: List[LegendData] = Field(default_factory=list)
    master_abbreviations: List[str] = Field(default_factory=list)
    compliance_summary: Dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int
    word_count_total: int
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class LegendResponse(BaseModel):
    """Response from single legend generation"""
    success: bool
    legend: Optional[LegendData] = None
    processing_time_ms: int
    error_message: Optional[str] = None


# =============================================================================
# Utility Functions
# =============================================================================

def convert_table_data_to_table(table_data: TableData) -> Table:
    """Convert API table data to internal Table object"""
    return Table(
        id=table_data.id,
        title=table_data.title,
        headers=table_data.headers,
        rows=table_data.rows,
        data_types=table_data.data_types,
        contains_statistics=table_data.contains_statistics,
        statistical_methods=table_data.statistical_methods,
        sample_size=table_data.sample_size,
    )


def convert_figure_data_to_figure(figure_data: FigureData) -> Figure:
    """Convert API figure data to internal Figure object"""
    return Figure(
        id=figure_data.id,
        title=figure_data.title,
        caption=figure_data.caption,
        figure_type=figure_data.figure_type,
        has_panels=figure_data.has_panels,
        panel_info=figure_data.panel_info,
        data_summary=figure_data.data_summary,
        analysis_methods=figure_data.analysis_methods,
        statistical_tests=figure_data.statistical_tests,
    )


def convert_table_legend_to_legend_data(table_legend: TableLegend) -> LegendData:
    """Convert internal TableLegend to API LegendData"""
    return LegendData(
        type="table",
        visual_id=table_legend.table_id,
        title=table_legend.title,
        complete_legend=table_legend.get_complete_legend(),
        word_count=table_legend.word_count,
        journal_compliant=table_legend.journal_compliant,
        abbreviations=table_legend.abbreviations,
        accessibility_description=table_legend.get_formatted_title(),
    )


def convert_figure_legend_to_legend_data(figure_legend: FigureLegend) -> LegendData:
    """Convert internal FigureLegend to API LegendData"""
    return LegendData(
        type="figure",
        visual_id=figure_legend.figure_id,
        caption=figure_legend.caption,
        complete_legend=figure_legend.get_complete_legend(),
        word_count=figure_legend.word_count,
        journal_compliant=figure_legend.journal_compliant,
        abbreviations=figure_legend.abbreviations,
        accessibility_description=figure_legend.accessibility_description,
        panel_descriptions=figure_legend.panel_descriptions,
    )


# =============================================================================
# Routes
# =============================================================================

@router.post("/api/legends/generate", response_model=LegendsResponse)
async def generate_legends(request: GenerateLegendsRequest):
    """
    Generate legends for all tables and figures.
    
    This is the main endpoint for batch legend generation.
    """
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="TableFigureLegendAgent not available. Check dependencies."
        )
    
    try:
        # Create agent instance
        agent = create_table_figure_legend_agent()
        
        # Convert request data to internal types
        tables = [convert_table_data_to_table(t) for t in request.tables]
        figures = [convert_figure_data_to_figure(f) for f in request.figures]
        
        # Create initial state
        state = TableFigureLegendState(
            study_id=request.study_id,
            tables=tables,
            figures=figures,
            manuscript_context=request.manuscript_context,
            target_journal=request.target_journal,
        )
        
        # Determine target journal
        target_journal = None
        if request.target_journal:
            try:
                target_journal = JournalStyleEnum(request.target_journal.lower())
            except ValueError:
                logger.warning(f"Unknown journal style: {request.target_journal}")
        
        logger.info(f"Generating legends for {len(tables)} tables and {len(figures)} figures")
        
        # Generate all legends
        updated_state = await agent.generate_all_legends(
            state=state,
            target_journal=target_journal,
        )
        
        # Convert results to API format
        legends = []
        for table_id, table_legend in updated_state.table_legends.items():
            legends.append(convert_table_legend_to_legend_data(table_legend))
        
        for figure_id, figure_legend in updated_state.figure_legends.items():
            legends.append(convert_figure_legend_to_legend_data(figure_legend))
        
        # Calculate metrics
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        total_word_count = updated_state.get_total_word_count()
        
        # Compliance summary
        compliance_summary = {
            "overall_compliant": updated_state.journal_compliance.get("overall", False),
            "compliant_count": sum(1 for legend in legends if legend.journal_compliant),
            "total_count": len(legends),
            "target_journal": request.target_journal,
        }
        
        logger.info(f"Legend generation completed in {duration_ms}ms")
        
        return LegendsResponse(
            success=True,
            study_id=request.study_id,
            legends=legends,
            master_abbreviations=updated_state.abbreviation_list,
            compliance_summary=compliance_summary,
            processing_time_ms=duration_ms,
            word_count_total=total_word_count,
            warnings=updated_state.warnings,
        )
    
    except Exception as e:
        logger.error(f"Legend generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return LegendsResponse(
            success=False,
            study_id=request.study_id,
            processing_time_ms=duration_ms,
            word_count_total=0,
            error_message=str(e),
        )


@router.post("/api/legends/table", response_model=LegendResponse)
async def generate_table_legend(request: GenerateTableLegendRequest):
    """
    Generate a legend for a single table.
    
    Useful for individual table legend generation or updates.
    """
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    try:
        agent = create_table_figure_legend_agent()
        table = convert_table_data_to_table(request.table)
        
        # Determine target journal
        target_journal = None
        if request.target_journal:
            try:
                target_journal = JournalStyleEnum(request.target_journal.lower())
            except ValueError:
                target_journal = None
        
        # Generate legend
        table_legend = await agent.generate_table_legend(
            table=table,
            manuscript_context=request.manuscript_context,
            target_journal=target_journal,
        )
        
        # Convert to API format
        legend_data = convert_table_legend_to_legend_data(table_legend)
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return LegendResponse(
            success=True,
            legend=legend_data,
            processing_time_ms=duration_ms,
        )
    
    except Exception as e:
        logger.error(f"Table legend generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return LegendResponse(
            success=False,
            processing_time_ms=duration_ms,
            error_message=str(e),
        )


@router.post("/api/legends/figure", response_model=LegendResponse)
async def generate_figure_legend(request: GenerateFigureLegendRequest):
    """
    Generate a legend for a single figure.
    
    Useful for individual figure legend generation or updates.
    """
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    try:
        agent = create_table_figure_legend_agent()
        figure = convert_figure_data_to_figure(request.figure)
        
        # Determine target journal
        target_journal = None
        if request.target_journal:
            try:
                target_journal = JournalStyleEnum(request.target_journal.lower())
            except ValueError:
                target_journal = None
        
        # Generate legend
        figure_legend = await agent.generate_figure_legend(
            figure=figure,
            manuscript_context=request.manuscript_context,
            target_journal=target_journal,
        )
        
        # Convert to API format
        legend_data = convert_figure_legend_to_legend_data(figure_legend)
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return LegendResponse(
            success=True,
            legend=legend_data,
            processing_time_ms=duration_ms,
        )
    
    except Exception as e:
        logger.error(f"Figure legend generation failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return LegendResponse(
            success=False,
            processing_time_ms=duration_ms,
            error_message=str(e),
        )


@router.get("/api/legends/journal-specs")
async def get_journal_specifications():
    """
    Get available journal specifications.
    
    Returns information about supported journals and their requirements.
    """
    if not AGENT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Agent not available")
    
    try:
        from table_figure_legend_agent import JOURNAL_SPECIFICATIONS
        
        specs = {}
        for journal_enum, spec in JOURNAL_SPECIFICATIONS.items():
            specs[journal_enum.value] = {
                "name": spec.name,
                "max_words": spec.max_legend_words,
                "panel_style": spec.panel_label_style.value,
                "abbreviation_placement": spec.abbreviation_placement.value,
                "requires_footnotes": spec.requires_footnotes,
                "active_voice": spec.prefers_active_voice,
                "concise_style": spec.concise_style,
                "statistical_info_required": spec.statistical_info_required,
            }
        
        return {
            "available": True,
            "journal_specifications": specs,
            "supported_journals": list(specs.keys()),
            "default_journal": "default",
        }
    
    except Exception as e:
        logger.error(f"Failed to get journal specs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/legends/capabilities")
async def get_capabilities():
    """
    Get legend generation capabilities.
    
    Returns information about agent features and status.
    """
    if not AGENT_AVAILABLE:
        return {
            "available": False,
            "error": "TableFigureLegendAgent not loaded",
        }
    
    return {
        "available": True,
        "agent": "TableFigureLegendAgent",
        "version": "1.0.0",
        "features": {
            "table_legends": True,
            "figure_legends": True,
            "multi_panel_support": True,
            "journal_compliance": True,
            "accessibility_descriptions": True,
            "abbreviation_management": True,
            "quality_validation": True,
        },
        "supported_journals": [
            "nature", "jama", "nejm", "lancet", "plos", "default"
        ],
        "panel_label_styles": [
            "A, B, C", "a, b, c", "I, II, III", "i, ii, iii", "1, 2, 3"
        ],
        "max_processing_items": {
            "tables": 50,
            "figures": 100,
            "total_visuals": 150,
        },
    }


@router.get("/api/legends/health")
async def health_check():
    """
    Health check for legend generation service.
    
    Returns service status and dependencies.
    """
    status = {
        "service": "legend-generation",
        "status": "healthy" if AGENT_AVAILABLE else "unavailable",
        "agent_loaded": AGENT_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check dependencies
    dependencies = {}
    try:
        import asyncio
        dependencies["asyncio"] = "available"
    except ImportError:
        dependencies["asyncio"] = "not available"
    
    try:
        from legend_types import TableFigureLegendState
        dependencies["legend_types"] = "available"
    except ImportError:
        dependencies["legend_types"] = "not available"
    
    try:
        import json
        dependencies["json"] = "available"
    except ImportError:
        dependencies["json"] = "not available"
    
    status["dependencies"] = dependencies
    
    # Test agent creation if available
    if AGENT_AVAILABLE:
        try:
            agent = create_table_figure_legend_agent()
            status["agent_creation"] = "success"
        except Exception as e:
            status["agent_creation"] = f"failed: {str(e)}"
            status["status"] = "degraded"
    
    return status


# =============================================================================
# Background Task Routes
# =============================================================================

@router.post("/api/legends/generate-async")
async def generate_legends_async(
    request: GenerateLegendsRequest, 
    background_tasks: BackgroundTasks
):
    """
    Generate legends asynchronously for large datasets.
    
    Returns immediately with a task ID for status checking.
    """
    task_id = f"legend_gen_{request.study_id}_{int(datetime.utcnow().timestamp())}"
    
    # Start background task
    background_tasks.add_task(
        _background_legend_generation,
        task_id,
        request,
    )
    
    return {
        "success": True,
        "task_id": task_id,
        "status": "queued",
        "estimated_duration_seconds": len(request.tables) * 5 + len(request.figures) * 8,
        "message": "Legend generation started in background",
    }


async def _background_legend_generation(task_id: str, request: GenerateLegendsRequest):
    """Background task for legend generation."""
    try:
        logger.info(f"Starting background legend generation: {task_id}")
        
        # This would typically store results in Redis/database for status checking
        # For now, just log the completion
        
        # Simulate the same generation process
        result = await generate_legends(request)
        
        logger.info(f"Background legend generation completed: {task_id}")
        logger.info(f"Generated {len(result.legends)} legends successfully")
        
    except Exception as e:
        logger.error(f"Background legend generation failed: {task_id}, error: {e}")