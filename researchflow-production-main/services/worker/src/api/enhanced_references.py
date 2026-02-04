"""
Enhanced Reference Management API Router

FastAPI router module for integrating Enhanced Reference Management System
into the main ROS API server. Provides unified access to AI-powered reference
processing capabilities.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create router for enhanced references endpoints
router = APIRouter()

# Try to import our Enhanced Reference Management components
try:
    # Import from the writing agents module
    import sys
    from pathlib import Path
    
    # Add agents path to import our writing modules
    agents_path = Path(__file__).parent.parent / "agents"
    if str(agents_path) not in sys.path:
        sys.path.insert(0, str(agents_path))
    
    # Use enhanced_refs package to avoid agents import issues
    try:
        from enhanced_refs.integration_hub import get_integration_hub
    except ImportError:
        from enhanced_refs.minimal_integration_hub import get_integration_hub
    
    try:
        from enhanced_refs.reference_management_service import get_reference_service
    except ImportError:
        from enhanced_refs.minimal_reference_service import get_reference_service
    
    from enhanced_refs.reference_types import ReferenceState, CitationStyle, Reference
    
    ENHANCED_REFERENCES_AVAILABLE = True
    logger.info("Enhanced Reference Management components loaded successfully")
    
except Exception as e:
    ENHANCED_REFERENCES_AVAILABLE = False
    logger.warning(f"Enhanced Reference Management not available: {e}")

# Define API models
class ReferenceProcessingRequest(BaseModel):
    """Request model for reference processing with AI controls."""
    study_id: str = Field(..., description="Study identifier")
    manuscript_text: str = Field(..., description="Full manuscript text")
    literature_results: List[Dict[str, Any]] = Field(default=[], description="Literature search results")
    existing_references: List[Dict[str, Any]] = Field(default=[], description="Existing references")
    target_style: str = Field(default="ama", description="Citation style")
    
    # Core processing controls
    enable_doi_validation: bool = Field(default=True, description="Enable DOI validation")
    enable_duplicate_detection: bool = Field(default=True, description="Enable duplicate detection")
    enable_quality_assessment: bool = Field(default=True, description="Enable quality assessment")
    enable_journal_recommendations: bool = Field(default=True, description="Enable journal recommendations")
    
    # AI Enhancement Controls
    enable_ai_processing: bool = Field(default=True, description="Enable AI-enhanced processing")
    enable_semantic_matching: bool = Field(default=True, description="Enable AI semantic matching")
    enable_gap_detection: bool = Field(default=True, description="Enable literature gap detection")
    enable_context_analysis: bool = Field(default=True, description="Enable citation context analysis")
    enable_quality_metrics: bool = Field(default=True, description="Enable advanced quality metrics")
    enable_ai_insights: bool = Field(default=True, description="Enable AI insights and recommendations")
    
    # Limits and configuration
    max_references: Optional[int] = Field(None, description="Maximum references")
    research_field: Optional[str] = Field(None, description="Research field")
    target_journal: Optional[str] = Field(None, description="Target journal")
    
    # Error handling preferences
    ai_fallback_on_error: bool = Field(default=True, description="Fall back to basic processing if AI fails")
    strict_mode: bool = Field(default=False, description="Fail on any error (vs graceful degradation)")

class ReferenceInsightsRequest(BaseModel):
    """Request model for reference insights."""
    references: List[Dict[str, Any]] = Field(..., description="Reference list")
    manuscript_text: str = Field(default="", description="Manuscript text for context")
    research_field: str = Field(default="general", description="Research field")

class CitationOptimizationRequest(BaseModel):
    """Request model for citation optimization."""
    references: List[Dict[str, Any]] = Field(..., description="Reference list")
    target_journal: Optional[str] = Field(None, description="Target journal")
    manuscript_abstract: str = Field(default="", description="Manuscript abstract")

# Circuit breaker for AI services (simplified version)
class SimpleCircuitBreaker:
    """Simplified circuit breaker for AI services."""
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def is_open(self) -> bool:
        if self.state == "open":
            if datetime.utcnow().timestamp() - (self.last_failure_time or 0) > self.timeout:
                self.state = "half-open"
                return False
            return True
        return False
    
    def record_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow().timestamp()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

# Global circuit breaker instance
circuit_breaker = SimpleCircuitBreaker()

@router.get("/references/health", summary="Enhanced References Health Check")
async def enhanced_references_health():
    """Health check for Enhanced Reference Management System."""
    
    if not ENHANCED_REFERENCES_AVAILABLE:
        return {
            "status": "unavailable",
            "error": "Enhanced Reference Management components not loaded",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        # Check Integration Hub
        integration_hub = await get_integration_hub()
        ai_stats = await integration_hub.get_integration_stats()
        
        # Check basic service
        ref_service = await get_reference_service()
        service_stats = await ref_service.get_stats()
        
        return {
            "status": "healthy",
            "enhanced_references_available": True,
            "integration_hub_status": "healthy",
            "circuit_breaker": {
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count
            },
            "ai_engines": len(ai_stats),
            "service_stats": service_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "degraded",
            "enhanced_references_available": True,
            "error": str(e),
            "circuit_breaker": {
                "state": circuit_breaker.state,
                "failure_count": circuit_breaker.failure_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }

@router.post("/references/process", summary="Process References with AI Enhancement")
async def process_references_enhanced(request: ReferenceProcessingRequest):
    """
    Process references with full AI enhancement capabilities.
    
    Features:
    - AI-powered semantic matching
    - Literature gap detection  
    - Citation context analysis
    - Advanced quality metrics
    - Journal intelligence
    - Circuit breaker reliability
    - Graceful fallback to basic processing
    """
    
    if not ENHANCED_REFERENCES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Enhanced Reference Management not available"
        )
    
    start_time = datetime.utcnow()
    
    try:
        # Convert request to ReferenceState
        style_mapping = {
            "ama": CitationStyle.AMA,
            "apa": CitationStyle.APA,
            "vancouver": CitationStyle.VANCOUVER,
            "harvard": CitationStyle.HARVARD,
            "chicago": CitationStyle.CHICAGO,
            "nature": CitationStyle.NATURE,
            "cell": CitationStyle.CELL,
            "jama": CitationStyle.JAMA,
            "mla": CitationStyle.MLA,
            "ieee": CitationStyle.IEEE
        }
        
        citation_style = style_mapping.get(request.target_style.lower(), CitationStyle.AMA)
        
        ref_state = ReferenceState(
            study_id=request.study_id,
            manuscript_text=request.manuscript_text,
            literature_results=request.literature_results,
            existing_references=[Reference(**ref) for ref in request.existing_references],
            target_style=citation_style,
            enable_doi_validation=request.enable_doi_validation,
            enable_duplicate_detection=request.enable_duplicate_detection,
            enable_quality_assessment=request.enable_quality_assessment,
            max_references=request.max_references,
            research_field=request.research_field,
            target_journal=request.target_journal
        )
        
        # Try AI-enhanced processing first
        processing_mode = "basic"
        fallback_reason = None
        result_data = {}
        
        if request.enable_ai_processing and not circuit_breaker.is_open():
            try:
                logger.info("Attempting AI-enhanced processing via Integration Hub")
                integration_hub = await get_integration_hub()
                
                enhanced_result = await integration_hub.process_enhanced_references(
                    ref_state,
                    enable_semantic_matching=request.enable_semantic_matching,
                    enable_gap_detection=request.enable_gap_detection,
                    enable_context_analysis=request.enable_context_analysis,
                    enable_quality_metrics=request.enable_quality_metrics,
                    enable_journal_intelligence=request.enable_journal_recommendations
                )
                
                # Success! Reset circuit breaker
                circuit_breaker.record_success()
                processing_mode = "ai_enhanced"
                
                # Convert enhanced result to API response
                result_data = {
                    "success": True,
                    "processing_mode": processing_mode,
                    "study_id": enhanced_result.study_id,
                    "references": [ref.model_dump() for ref in enhanced_result.references],
                    "citations": [citation.model_dump() for citation in enhanced_result.citations],
                    "bibliography": enhanced_result.bibliography,
                    
                    # AI Enhancements
                    "ai_enhancements": {
                        "semantic_matches": enhanced_result.semantic_matches,
                        "literature_gaps": [
                            gap.model_dump() if hasattr(gap, 'model_dump') else gap 
                            for gap in enhanced_result.literature_gaps
                        ],
                        "citation_contexts": [
                            ctx.model_dump() if hasattr(ctx, 'model_dump') else ctx 
                            for ctx in enhanced_result.citation_contexts
                        ],
                        "quality_metrics": [
                            qm.model_dump() if hasattr(qm, 'model_dump') else qm 
                            for qm in enhanced_result.quality_metrics
                        ]
                    },
                    
                    # Quality Summary
                    "quality_summary": {
                        "overall_score": enhanced_result.overall_quality_score,
                        "completeness_score": enhanced_result.completeness_score,
                        "ai_confidence": enhanced_result.ai_confidence
                    },
                    
                    # Actionable Insights
                    "insights": {
                        "improvement_recommendations": enhanced_result.improvement_recommendations,
                        "priority_issues": enhanced_result.priority_issues,
                        "suggested_actions": enhanced_result.suggested_actions
                    },
                    
                    # Journal Intelligence
                    "journal_recommendations": enhanced_result.journal_recommendations,
                    "citation_impact_analysis": enhanced_result.citation_impact_analysis,
                    
                    "processing_time_seconds": enhanced_result.processing_time_seconds
                }
                
            except Exception as ai_error:
                # Record AI failure for circuit breaker
                circuit_breaker.record_failure()
                
                logger.warning(f"AI-enhanced processing failed: {ai_error}")
                
                if not request.ai_fallback_on_error or request.strict_mode:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"AI processing failed: {str(ai_error)}"
                    )
                
                fallback_reason = str(ai_error)[:200]
        
        # Fallback to basic processing if AI failed or disabled
        if not result_data:
            logger.info("Using basic reference processing")
            processing_mode = "basic"
            
            ref_service = await get_reference_service()
            result = await ref_service.process_references(ref_state)
            
            # Convert result to JSON serializable format (basic)
            result_data = {
                "success": True,
                "processing_mode": processing_mode,
                "study_id": result.study_id,
                "references": [ref.model_dump() for ref in result.references],
                "citations": [citation.model_dump() for citation in result.citations],
                "bibliography": result.bibliography,
                "quality_scores": [score.model_dump() for score in result.quality_scores],
                "warnings": [warning.model_dump() for warning in result.warnings],
                "total_references": result.total_references,
                "processing_time_seconds": result.processing_time_seconds
            }
            
            if fallback_reason:
                result_data["ai_fallback_reason"] = fallback_reason
                result_data["circuit_breaker_status"] = circuit_breaker.state
        
        # Add processing metadata
        total_time = (datetime.utcnow() - start_time).total_seconds()
        result_data.update({
            "api_processing_time_seconds": total_time,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return result_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reference processing failed completely: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/references/insights", summary="Get AI Insights for References")
async def get_reference_insights_enhanced(request: ReferenceInsightsRequest):
    """Get AI-powered insights for existing references."""
    
    if not ENHANCED_REFERENCES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Enhanced Reference Management not available"
        )
    
    try:
        if circuit_breaker.is_open():
            raise HTTPException(
                status_code=503,
                detail="AI services temporarily unavailable"
            )
        
        integration_hub = await get_integration_hub()
        ref_objects = [Reference(**ref_data) for ref_data in request.references]
        
        insights = await integration_hub.suggest_reference_improvements(
            ref_objects,
            request.manuscript_text,
            request.research_field
        )
        
        circuit_breaker.record_success()
        
        return {
            "success": True,
            "insights": insights,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Reference insights failed: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")

@router.post("/references/optimize", summary="Optimize Citation Strategy")
async def optimize_citation_strategy_enhanced(request: CitationOptimizationRequest):
    """Optimize citation strategy for target journal or best practices."""
    
    if not ENHANCED_REFERENCES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Enhanced Reference Management not available"
        )
    
    try:
        if circuit_breaker.is_open():
            raise HTTPException(
                status_code=503,
                detail="AI services temporarily unavailable"
            )
        
        integration_hub = await get_integration_hub()
        ref_objects = [Reference(**ref_data) for ref_data in request.references]
        
        optimization = await integration_hub.optimize_citation_strategy(
            ref_objects,
            request.target_journal,
            request.manuscript_abstract
        )
        
        circuit_breaker.record_success()
        
        return {
            "success": True,
            "optimization": optimization,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Citation optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

@router.get("/references/status", summary="Enhanced References Status")
async def get_enhanced_references_status():
    """Get detailed status of Enhanced Reference Management System."""
    
    if not ENHANCED_REFERENCES_AVAILABLE:
        return {
            "enhanced_references_available": False,
            "error": "Enhanced Reference Management components not loaded",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    try:
        # Collect status from all components
        status = {
            "enhanced_references_available": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Integration Hub status
        try:
            integration_hub = await get_integration_hub()
            ai_stats = await integration_hub.get_integration_stats()
            status["integration_hub"] = {
                "status": "healthy",
                "ai_engines": list(ai_stats.keys()),
                "engine_count": len(ai_stats)
            }
        except Exception as e:
            status["integration_hub"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Reference service status
        try:
            ref_service = await get_reference_service()
            service_stats = await ref_service.get_stats()
            status["reference_service"] = {
                "status": "healthy",
                "stats": service_stats
            }
        except Exception as e:
            status["reference_service"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Circuit breaker status
        status["circuit_breaker"] = {
            "state": circuit_breaker.state,
            "failure_count": circuit_breaker.failure_count,
            "last_failure_time": circuit_breaker.last_failure_time
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get enhanced references status: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

# Add route for capabilities
@router.get("/references/capabilities", summary="Enhanced References Capabilities")
async def get_enhanced_references_capabilities():
    """Get capabilities and feature availability."""
    
    capabilities = {
        "enhanced_references_available": ENHANCED_REFERENCES_AVAILABLE,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if ENHANCED_REFERENCES_AVAILABLE:
        capabilities.update({
            "features": {
                "ai_enhanced_processing": True,
                "semantic_matching": True,
                "literature_gap_detection": True,
                "citation_context_analysis": True,
                "quality_metrics": True,
                "journal_intelligence": True,
                "circuit_breaker_reliability": True,
                "graceful_fallback": True
            },
            "citation_styles": [
                "ama", "apa", "vancouver", "harvard", "chicago",
                "nature", "cell", "jama", "mla", "ieee"
            ],
            "endpoints": [
                "/api/references/process",
                "/api/references/insights", 
                "/api/references/optimize",
                "/api/references/health",
                "/api/references/status",
                "/api/references/capabilities"
            ]
        })
    else:
        capabilities["error"] = "Enhanced Reference Management not loaded"
    
    return capabilities