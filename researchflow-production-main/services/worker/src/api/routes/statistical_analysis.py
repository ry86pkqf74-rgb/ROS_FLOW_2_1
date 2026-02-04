"""
Statistical Analysis API Route - Stage 7

FastAPI routes for StatisticalAnalysisAgent integration.
Handles statistical analysis requests from the orchestrator.

Linear Issues: ROS-XXX (Stage 7)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Import the statistical analysis agent
try:
    import sys
    from pathlib import Path
    # Add agents directory to path
    agents_dir = Path(__file__).parent.parent.parent.parent / "agents"
    sys.path.insert(0, str(agents_dir))
    
    from analysis.statistical_analysis_agent import (
        create_statistical_analysis_agent,
        StatisticalAnalysisAgent,
    )
    from analysis.statistical_types import (
        StudyData,
        StatisticalResult,
    )
    AGENT_AVAILABLE = True
except ImportError as e:
    AGENT_AVAILABLE = False
    logging.warning(f"StatisticalAnalysisAgent not available: {e}")

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class StudyDataRequest(BaseModel):
    """Study data for statistical analysis"""
    groups: Optional[List[str]] = Field(None, description="Group labels")
    outcomes: Dict[str, List[float]] = Field(..., description="Outcome variables")
    covariates: Optional[Dict[str, List[Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnalysisOptions(BaseModel):
    """Optional analysis configuration"""
    test_type: Optional[str] = None
    confidence_level: float = 0.95
    alpha: float = 0.05
    calculate_effect_size: bool = True
    check_assumptions: bool = True
    generate_visualizations: bool = True


class StatisticalAnalysisRequest(BaseModel):
    """Complete statistical analysis request"""
    study_data: StudyDataRequest
    options: Optional[AnalysisOptions] = None


class StatisticalAnalysisResponse(BaseModel):
    """Statistical analysis response"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int
    agent_iterations: int
    quality_score: float


# =============================================================================
# Routes
# =============================================================================

@router.post("/api/analysis/statistical")
async def run_statistical_analysis(request: StatisticalAnalysisRequest):
    """
    Execute statistical analysis using StatisticalAnalysisAgent.
    
    This is the primary endpoint for Stage 7 statistical analysis.
    Called by the orchestrator service.
    
    Args:
        request: Statistical analysis request with study data and options
    
    Returns:
        Statistical analysis result with descriptive stats, inferential tests,
        effect sizes, assumption checks, and APA-formatted tables
    """
    start_time = datetime.utcnow()
    
    if not AGENT_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="StatisticalAnalysisAgent not available. Check dependencies."
        )
    
    try:
        # Create agent instance
        agent = create_statistical_analysis_agent()
        
        # Convert request to StudyData
        study_data = StudyData(
            groups=request.study_data.groups,
            outcomes=request.study_data.outcomes,
            covariates=request.study_data.covariates,
            metadata=request.study_data.metadata,
        )
        
        logger.info(f"Running statistical analysis for research: {study_data.metadata.get('research_id')}")
        
        # Execute analysis
        result = await agent.execute(study_data)
        
        # Calculate duration
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        logger.info(f"Statistical analysis completed in {duration_ms}ms")
        
        return StatisticalAnalysisResponse(
            success=True,
            result=result.to_dict() if result else None,
            error=None,
            duration_ms=duration_ms,
            agent_iterations=0,  # TODO: Track from agent
            quality_score=0.0,   # TODO: Get from agent result
        )
    
    except Exception as e:
        logger.error(f"Statistical analysis failed: {e}")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return StatisticalAnalysisResponse(
            success=False,
            result=None,
            error=str(e),
            duration_ms=duration_ms,
            agent_iterations=0,
            quality_score=0.0,
        )


@router.get("/api/analysis/statistical/capabilities")
async def get_capabilities():
    """
    Get statistical analysis capabilities.
    
    Returns:
        Information about available tests, assumptions, and features
    """
    if not AGENT_AVAILABLE:
        return {
            "available": False,
            "error": "StatisticalAnalysisAgent not loaded",
        }
    
    return {
        "available": True,
        "agent": "StatisticalAnalysisAgent",
        "version": "1.0.0",
        "capabilities": {
            "hypothesis_tests": [
                "t_test_independent",
                "t_test_paired",
                "mann_whitney",
                "wilcoxon",
                "anova_oneway",
                "kruskal_wallis",
                "chi_square",
            ],
            "effect_sizes": [
                "cohens_d",
                "hedges_g",
                "eta_squared",
            ],
            "assumption_checks": [
                "normality",
                "homogeneity",
                "independence",
            ],
            "outputs": [
                "descriptive_statistics",
                "hypothesis_test_results",
                "effect_sizes",
                "confidence_intervals",
                "apa_formatted_tables",
                "visualization_specifications",
                "remediation_suggestions",
            ],
        },
        "features": {
            "multiple_groups": True,
            "assumption_remediation": True,
            "visualization_specs": True,
            "apa_formatting": True,
            "quality_gates": True,
        },
    }


@router.get("/api/analysis/statistical/health")
async def health_check():
    """
    Health check for statistical analysis service.
    
    Returns:
        Service status and dependencies
    """
    status = {
        "service": "statistical-analysis",
        "status": "healthy" if AGENT_AVAILABLE else "unavailable",
        "agent_loaded": AGENT_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # Check dependencies
    dependencies = {}
    try:
        import scipy
        dependencies["scipy"] = scipy.__version__
    except ImportError:
        dependencies["scipy"] = "not installed"
    
    try:
        import statsmodels
        dependencies["statsmodels"] = statsmodels.__version__
    except ImportError:
        dependencies["statsmodels"] = "not installed"
    
    try:
        import pandas
        dependencies["pandas"] = pandas.__version__
    except ImportError:
        dependencies["pandas"] = "not installed"
    
    try:
        import numpy
        dependencies["numpy"] = numpy.__version__
    except ImportError:
        dependencies["numpy"] = "not installed"
    
    status["dependencies"] = dependencies
    
    return status
