"""
Enhanced Reference Management API Endpoints (Production Ready)

RESTful API endpoints for the enhanced reference management system with
full AI Integration Hub support and production-ready error handling.

Linear Issues: ROS-XXX
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import uvicorn

# Core services
from .reference_management_service import get_reference_service
from .integration_hub import get_integration_hub
from .collaborative_references import get_collaborative_manager, ReferenceEdit
from .journal_intelligence import get_journal_intelligence
from .monitoring import get_system_monitor
from .deployment_setup import deploy_enhanced_reference_system, validate_system_deployment
from .reference_types import ReferenceState, CitationStyle, Reference

logger = logging.getLogger(__name__)

# API Models
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

class CollaborationSessionRequest(BaseModel):
    """Request model for collaboration session."""
    study_id: str = Field(..., description="Study identifier")
    editor_id: str = Field(..., description="Editor identifier")
    editor_name: str = Field(..., description="Editor name")

class ReferenceEditRequest(BaseModel):
    """Request model for reference edit."""
    session_id: str = Field(..., description="Session identifier")
    reference_id: str = Field(..., description="Reference identifier")
    field_name: str = Field(..., description="Field being edited")
    old_value: str = Field(..., description="Previous value")
    new_value: str = Field(..., description="New value")
    edit_type: str = Field(..., description="Edit type: add, modify, delete")
    editor_id: str = Field(..., description="Editor identifier")
    editor_name: str = Field(..., description="Editor name")

class JournalRecommendationRequest(BaseModel):
    """Request model for journal recommendations."""
    references: List[Dict[str, Any]] = Field(..., description="Reference list")
    manuscript_abstract: str = Field(default="", description="Manuscript abstract")
    research_field: str = Field(default="general", description="Research field")
    target_impact_range: List[float] = Field(default=[1.0, 100.0], description="Impact factor range")
    open_access_preference: bool = Field(default=False, description="Open access preference")

class JournalFitAnalysisRequest(BaseModel):
    """Request model for journal fit analysis."""
    journal_name: str = Field(..., description="Target journal name")
    references: List[Dict[str, Any]] = Field(..., description="Reference list")
    manuscript_abstract: str = Field(default="", description="Manuscript abstract")

class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    system_status: Dict[str, Any]
    ai_engines_status: Optional[Dict[str, str]] = None
    error_details: Optional[str] = None

# Circuit breaker for AI services
class AICircuitBreaker:
    """Simple circuit breaker for AI services."""
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def is_open(self) -> bool:
        if self.state == "open":
            if datetime.utcnow().timestamp() - self.last_failure_time > self.timeout:
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
ai_circuit_breaker = AICircuitBreaker()

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Reference Management API",
    description="Advanced reference management system with AI-powered features",
    version="2.0.0"
)

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint with AI engine status."""
    try:
        monitor = await get_system_monitor()
        status = await monitor.get_system_status_summary()
        
        # Check AI engines status
        ai_engines_status = {}
        
        try:
            integration_hub = await get_integration_hub()
            ai_engines_status["integration_hub"] = "healthy"
            
            # Check individual engines
            hub_stats = await integration_hub.get_integration_stats()
            for engine_name, engine_stats in hub_stats.items():
                if isinstance(engine_stats, dict) and "error" in engine_stats:
                    ai_engines_status[engine_name] = "unhealthy"
                else:
                    ai_engines_status[engine_name] = "healthy"
                    
        except Exception as e:
            ai_engines_status["integration_hub"] = f"error: {str(e)[:100]}"
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            system_status=status,
            ai_engines_status=ai_engines_status
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get("/health/comprehensive")
async def comprehensive_health_check():
    """Comprehensive health check endpoint."""
    try:
        monitor = await get_system_monitor()
        health_result = await monitor.comprehensive_health_check()
        
        # Add AI engines health check
        try:
            integration_hub = await get_integration_hub()
            ai_stats = await integration_hub.get_integration_stats()
            health_result["ai_engines"] = ai_stats
        except Exception as e:
            health_result["ai_engines"] = {"error": str(e)}
        
        return health_result
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.post("/references/process")
async def process_references(request: ReferenceProcessingRequest):
    """Process references with enhanced AI features and fallback handling."""
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
        
        # Determine processing mode
        processing_mode = "basic"
        fallback_reason = None
        result_data = {}
        
        # Try AI-enhanced processing first if enabled and circuit breaker allows
        if request.enable_ai_processing and not ai_circuit_breaker.is_open():
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
                ai_circuit_breaker.record_success()
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
                        "citation_validations": [
                            val.model_dump() if hasattr(val, 'model_dump') else val 
                            for val in enhanced_result.citation_validations
                        ],
                        "quality_metrics": [
                            qm.model_dump() if hasattr(qm, 'model_dump') else qm 
                            for qm in enhanced_result.quality_metrics
                        ]
                    },
                    
                    # Intelligence Insights
                    "journal_recommendations": enhanced_result.journal_recommendations,
                    "citation_impact_analysis": enhanced_result.citation_impact_analysis,
                    
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
                    
                    # Metadata
                    "processing_time_seconds": enhanced_result.processing_time_seconds,
                    "ai_features_used": {
                        "semantic_matching": request.enable_semantic_matching,
                        "gap_detection": request.enable_gap_detection,
                        "context_analysis": request.enable_context_analysis,
                        "quality_metrics": request.enable_quality_metrics,
                        "journal_intelligence": request.enable_journal_recommendations
                    }
                }
                
            except Exception as ai_error:
                # Record AI failure for circuit breaker
                ai_circuit_breaker.record_failure()
                
                logger.warning(f"AI-enhanced processing failed: {ai_error}")
                
                if not request.ai_fallback_on_error:
                    if request.strict_mode:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"AI processing failed and fallback disabled: {str(ai_error)}"
                        )
                
                fallback_reason = str(ai_error)[:200]  # Truncate long errors
                
        # Fallback to basic processing
        if not result_data:
            logger.info("Using basic reference processing")
            processing_mode = "basic"
            
            ref_service = await get_reference_service()
            result = await ref_service.process_references(ref_state)
            
            # Add basic journal recommendations if requested
            journal_recommendations = []
            citation_impact_analysis = {}
            
            if request.enable_journal_recommendations:
                try:
                    journal_intel = await get_journal_intelligence()
                    journal_recommendations = await journal_intel.recommend_target_journals(
                        result.references,
                        request.manuscript_text,
                        request.research_field or "general"
                    )
                    
                    citation_impact_analysis = await journal_intel.analyze_citation_impact(
                        result.references
                    )
                except Exception as e:
                    logger.warning(f"Journal recommendations failed: {e}")
            
            # Convert result to JSON serializable format (basic)
            result_data = {
                "success": True,
                "processing_mode": processing_mode,
                "study_id": result.study_id,
                "references": [ref.model_dump() for ref in result.references],
                "citations": [citation.model_dump() for citation in result.citations],
                "bibliography": result.bibliography,
                "citation_map": result.citation_map,
                "quality_scores": [score.model_dump() for score in result.quality_scores],
                "warnings": [warning.model_dump() for warning in result.warnings],
                "total_references": result.total_references,
                "style_compliance_score": result.style_compliance_score,
                "processing_time_seconds": result.processing_time_seconds,
                "journal_recommendations": journal_recommendations,
                "citation_impact_analysis": citation_impact_analysis
            }
            
            if fallback_reason:
                result_data["ai_fallback_reason"] = fallback_reason
                result_data["ai_circuit_breaker_status"] = ai_circuit_breaker.state
        
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

# Enhanced endpoint for AI insights
@app.post("/references/insights")
async def get_reference_insights(
    references: List[Dict[str, Any]],
    manuscript_text: str = "",
    research_field: str = "general"
):
    """Get AI insights for existing references."""
    try:
        if ai_circuit_breaker.is_open():
            raise HTTPException(
                status_code=503, 
                detail="AI services temporarily unavailable"
            )
        
        integration_hub = await get_integration_hub()
        ref_objects = [Reference(**ref_data) for ref_data in references]
        
        insights = await integration_hub.suggest_reference_improvements(
            ref_objects, manuscript_text, research_field
        )
        
        ai_circuit_breaker.record_success()
        
        return {
            "success": True,
            "insights": insights,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        ai_circuit_breaker.record_failure()
        logger.error(f"Reference insights failed: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")

@app.post("/references/optimize")
async def optimize_citation_strategy(
    references: List[Dict[str, Any]],
    target_journal: Optional[str] = None,
    manuscript_abstract: str = ""
):
    """Optimize citation strategy for target journal."""
    try:
        if ai_circuit_breaker.is_open():
            raise HTTPException(
                status_code=503, 
                detail="AI services temporarily unavailable"
            )
        
        integration_hub = await get_integration_hub()
        ref_objects = [Reference(**ref_data) for ref_data in references]
        
        optimization = await integration_hub.optimize_citation_strategy(
            ref_objects, target_journal, manuscript_abstract
        )
        
        ai_circuit_breaker.record_success()
        
        return {
            "success": True,
            "optimization": optimization,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        ai_circuit_breaker.record_failure()
        logger.error(f"Citation optimization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")

# Collaboration endpoints (existing functionality maintained)
@app.post("/collaboration/session/start")
async def start_collaboration_session(request: CollaborationSessionRequest):
    """Start a collaborative editing session."""
    try:
        collab_manager = await get_collaborative_manager()
        session_id = await collab_manager.start_session(
            request.study_id,
            request.editor_id,
            request.editor_name
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "study_id": request.study_id,
            "started_by": request.editor_name
        }
        
    except Exception as e:
        logger.error(f"Failed to start collaboration session: {e}")
        raise HTTPException(status_code=500, detail=f"Session start failed: {str(e)}")

# Additional endpoints for monitoring and stats
@app.get("/monitoring/ai-status")
async def get_ai_status():
    """Get AI engines status and circuit breaker state."""
    try:
        integration_hub = await get_integration_hub()
        ai_stats = await integration_hub.get_integration_stats()
        
        return {
            "ai_stats": ai_stats,
            "circuit_breaker": {
                "state": ai_circuit_breaker.state,
                "failure_count": ai_circuit_breaker.failure_count,
                "last_failure_time": ai_circuit_breaker.last_failure_time
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "circuit_breaker": {
                "state": ai_circuit_breaker.state,
                "failure_count": ai_circuit_breaker.failure_count,
                "last_failure_time": ai_circuit_breaker.last_failure_time
            },
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/stats")
async def get_comprehensive_stats():
    """Get comprehensive system statistics."""
    try:
        stats = {"timestamp": datetime.utcnow().isoformat()}
        
        # Reference service stats
        try:
            ref_service = await get_reference_service()
            stats['reference_service'] = await ref_service.get_stats()
        except Exception as e:
            stats['reference_service'] = {'error': str(e)}
        
        # AI integration stats
        try:
            integration_hub = await get_integration_hub()
            stats['ai_integration'] = await integration_hub.get_integration_stats()
        except Exception as e:
            stats['ai_integration'] = {'error': str(e)}
        
        # System monitor stats
        try:
            monitor = await get_system_monitor()
            stats['system_status'] = await monitor.get_system_status_summary()
        except Exception as e:
            stats['system_status'] = {'error': str(e)}
        
        # Circuit breaker status
        stats['circuit_breaker'] = {
            'state': ai_circuit_breaker.state,
            'failure_count': ai_circuit_breaker.failure_count
        }
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(status_code=500, detail=f"Stats collection failed: {str(e)}")

if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api_endpoints_enhanced:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )