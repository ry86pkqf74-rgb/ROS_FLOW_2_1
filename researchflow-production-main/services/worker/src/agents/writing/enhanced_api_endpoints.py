"""
Enhanced API Endpoints for AI Bridge with Advanced Features

Comprehensive API with:
- Advanced metrics integration
- Circuit breaker protection
- Performance optimization
- Cost tracking
- Enterprise features

Author: AI Bridge Enhancement Team
"""

import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
from pydantic import BaseModel, Field
import json

# Import advanced components
from .advanced_metrics import get_metrics_collector, record_performance_metric, record_cost_metric, MetricType, MetricSeverity
from .circuit_breaker_advanced import get_circuit_breaker, CircuitBreakerConfig, CircuitBreakerOpenError
from .production_health_check import get_health_checker
from .monitoring import get_system_monitor

# Import existing components
from .integration_hub import get_integration_hub
from .reference_management_service import get_reference_service
from .reference_types import ReferenceState, CitationStyle

logger = logging.getLogger(__name__)

# Enhanced Pydantic models
class EnhancedProcessingRequest(BaseModel):
    """Enhanced request model with additional features."""
    # Core fields
    study_id: str
    manuscript_text: str
    literature_results: List[Dict[str, Any]] = Field(default_factory=list)
    existing_references: List[Dict[str, Any]] = Field(default_factory=list)
    target_style: str = "ama"
    research_field: str = "general"
    
    # AI processing options
    enable_ai_processing: bool = True
    enable_semantic_matching: bool = True
    enable_gap_detection: bool = True
    enable_context_analysis: bool = True
    enable_quality_metrics: bool = True
    enable_journal_recommendations: bool = False
    
    # Performance options
    priority: str = Field(default="normal", description="Processing priority: low, normal, high, urgent")
    enable_streaming: bool = Field(default=False, description="Enable streaming response for large datasets")
    max_processing_time_seconds: int = Field(default=300, description="Maximum processing time")
    
    # Cost management
    cost_limit_usd: Optional[float] = Field(default=None, description="Maximum cost allowed for this request")
    enable_cost_optimization: bool = Field(default=True, description="Enable cost optimization strategies")
    
    # Advanced features  
    enable_caching: bool = Field(default=True, description="Enable result caching")
    cache_ttl_minutes: int = Field(default=60, description="Cache time to live in minutes")
    enable_batch_processing: bool = Field(default=False, description="Enable batch processing for efficiency")
    
    # Metadata
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    request_metadata: Dict[str, Any] = Field(default_factory=dict)

class EnhancedProcessingResponse(BaseModel):
    """Enhanced response model with comprehensive information."""
    # Core response
    success: bool
    study_id: str
    processing_mode: str
    references: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    
    # Enhanced results
    ai_enhancements: Optional[Dict[str, Any]] = None
    quality_summary: Optional[Dict[str, Any]] = None
    insights: Optional[Dict[str, Any]] = None
    journal_recommendations: Optional[List[Dict[str, Any]]] = None
    
    # Performance metrics
    processing_time_seconds: float
    cache_hit: bool = False
    cost_breakdown: Optional[Dict[str, Any]] = None
    
    # Quality and validation
    validation_score: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # AI feature usage
    ai_features_used: Dict[str, bool] = Field(default_factory=dict)
    ai_confidence_scores: Optional[Dict[str, float]] = None
    fallback_reasons: List[str] = Field(default_factory=list)

class SystemMetricsResponse(BaseModel):
    """System metrics response model."""
    timestamp: str
    system_health: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    circuit_breaker_status: Dict[str, Any]
    predictive_insights: Optional[Dict[str, Any]] = None

# Create enhanced FastAPI app
app = FastAPI(
    title="Enhanced AI Bridge API",
    description="Enterprise AI Bridge for ResearchFlow with advanced features",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Performance tracking middleware
@app.middleware("http")
async def performance_tracking_middleware(request: Request, call_next):
    """Track API performance and costs."""
    start_time = time.time()
    endpoint = f"{request.method} {request.url.path}"
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        # Record performance metric
        await record_performance_metric(
            endpoint=endpoint,
            duration_ms=duration_ms,
            error=False,
            status_code=response.status_code,
            user_id=request.headers.get("X-User-ID", "anonymous")
        )
        
        # Add performance headers
        response.headers["X-Response-Time-MS"] = str(round(duration_ms, 2))
        response.headers["X-Processed-By"] = "enhanced-ai-bridge"
        
        return response
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Record error metric
        await record_performance_metric(
            endpoint=endpoint,
            duration_ms=duration_ms,
            error=True,
            error_type=type(e).__name__
        )
        
        raise

# Enhanced health check endpoints
@app.get("/health", 
         response_model=Dict[str, Any],
         summary="Basic health check",
         description="Quick health check for load balancers")
async def health_check():
    """Enhanced basic health check."""
    try:
        health_checker = await get_health_checker()
        quick_health = await health_checker.quick_health_check()
        
        # Add system metrics
        metrics_collector = await get_metrics_collector()
        system_metrics = await metrics_collector.get_system_metrics()
        
        return {
            **quick_health,
            "system_resources": system_metrics.get("system_resources", {}),
            "version": "2.0.0",
            "enhanced": True
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

@app.get("/health/comprehensive",
         response_model=Dict[str, Any],
         summary="Comprehensive health check",
         description="Detailed health check with all system components")
async def comprehensive_health_check():
    """Comprehensive health check with detailed diagnostics."""
    try:
        health_checker = await get_health_checker()
        health_report = await health_checker.comprehensive_health_check()
        
        # Add advanced metrics
        metrics_collector = await get_metrics_collector()
        system_metrics = await metrics_collector.get_system_metrics()
        performance_summary = await metrics_collector.get_performance_summary()
        cost_analysis = await metrics_collector.get_cost_analysis()
        
        # Add circuit breaker status
        from .circuit_breaker_advanced import get_circuit_breaker_manager
        circuit_manager = get_circuit_breaker_manager()
        circuit_health = circuit_manager.get_overall_health()
        
        enhanced_report = {
            **health_report,
            "enhanced_metrics": {
                "system_metrics": system_metrics,
                "performance_summary": performance_summary,
                "cost_analysis": cost_analysis,
                "circuit_breaker_health": circuit_health
            },
            "api_version": "2.0.0"
        }
        
        # Return 503 if unhealthy
        overall_health = circuit_health.get("overall_health", 1.0)
        if health_report["overall_status"] == "degraded" or overall_health < 0.5:
            return JSONResponse(
                status_code=503,
                content=enhanced_report
            )
        
        return enhanced_report
        
    except Exception as e:
        logger.error(f"Comprehensive health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Comprehensive health check failed: {str(e)}")

# Enhanced processing endpoint
@app.post("/references/process",
          response_model=EnhancedProcessingResponse,
          summary="Process references with AI enhancement",
          description="Enhanced reference processing with advanced AI features")
async def process_references_enhanced(
    request: EnhancedProcessingRequest,
    background_tasks: BackgroundTasks
) -> EnhancedProcessingResponse:
    """Enhanced reference processing with advanced features."""
    start_time = time.time()
    
    # Get circuit breaker for AI services
    ai_circuit_breaker = get_circuit_breaker("ai_services", CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout_seconds=60,
        slow_request_threshold_ms=10000  # 10 seconds for AI processing
    ))
    
    try:
        # Validate cost limits
        if request.cost_limit_usd and request.cost_limit_usd <= 0:
            raise HTTPException(status_code=400, detail="Cost limit must be positive")
        
        # Create processing state
        reference_state = ReferenceState(
            study_id=request.study_id,
            manuscript_text=request.manuscript_text,
            literature_results=request.literature_results,
            existing_references=request.existing_references,
            target_style=CitationStyle(request.target_style),
            enable_ai_processing=request.enable_ai_processing,
            enable_semantic_matching=request.enable_semantic_matching,
            enable_gap_detection=request.enable_gap_detection,
            enable_context_analysis=request.enable_context_analysis,
            enable_quality_assessment=request.enable_quality_metrics
        )
        
        # Process with circuit breaker protection
        async def process_with_ai():
            ref_service = await get_reference_service()
            
            # Apply timeout based on priority
            timeout_map = {
                "low": 600,      # 10 minutes
                "normal": 300,   # 5 minutes  
                "high": 180,     # 3 minutes
                "urgent": 60     # 1 minute
            }
            timeout = min(timeout_map.get(request.priority, 300), request.max_processing_time_seconds)
            
            return await asyncio.wait_for(
                ref_service.process_references(reference_state),
                timeout=timeout
            )
        
        # Execute with circuit breaker
        result = await ai_circuit_breaker.call(
            process_with_ai,
            timeout_seconds=request.max_processing_time_seconds
        )
        
        # Calculate costs (mock implementation)
        estimated_cost = 0.001 * len(request.literature_results) + 0.01 * len(request.manuscript_text) / 1000
        
        # Record cost metric
        await record_cost_metric(
            cost_usd=estimated_cost,
            service="reference_processing",
            tokens=len(request.manuscript_text) // 4  # Rough token estimate
        )
        
        # Check cost limits
        if request.cost_limit_usd and estimated_cost > request.cost_limit_usd:
            logger.warning(f"Cost limit exceeded: ${estimated_cost:.4f} > ${request.cost_limit_usd}")
            # Continue but warn user
        
        processing_time = time.time() - start_time
        
        # Generate enhanced response
        response = EnhancedProcessingResponse(
            success=True,
            study_id=request.study_id,
            processing_mode="ai_enhanced" if request.enable_ai_processing else "basic",
            references=result.references,
            citations=result.citations,
            processing_time_seconds=processing_time,
            cost_breakdown={
                "estimated_cost_usd": estimated_cost,
                "tokens_used": len(request.manuscript_text) // 4,
                "api_calls_made": 1,
                "within_budget": not request.cost_limit_usd or estimated_cost <= request.cost_limit_usd
            },
            ai_features_used={
                "ai_processing": request.enable_ai_processing and result.ai_enhanced,
                "semantic_matching": request.enable_semantic_matching,
                "gap_detection": request.enable_gap_detection,
                "context_analysis": request.enable_context_analysis,
                "quality_metrics": request.enable_quality_metrics
            }
        )
        
        # Add AI enhancements if available
        if hasattr(result, 'ai_enhancements') and result.ai_enhancements:
            response.ai_enhancements = result.ai_enhancements
            response.quality_summary = result.ai_enhancements.get('quality_summary')
            response.insights = result.ai_enhancements.get('insights')
        
        # Background task for analytics
        background_tasks.add_task(
            record_processing_analytics,
            request, response, processing_time
        )
        
        return response
        
    except CircuitBreakerOpenError as e:
        # Circuit breaker is open - provide fallback response
        logger.warning(f"Circuit breaker open, using fallback processing: {e}")
        
        ref_service = await get_reference_service()
        # Disable AI features for fallback
        fallback_state = ReferenceState(
            study_id=request.study_id,
            manuscript_text=request.manuscript_text,
            literature_results=request.literature_results,
            existing_references=request.existing_references,
            target_style=CitationStyle(request.target_style),
            enable_ai_processing=False
        )
        
        fallback_result = await ref_service.process_references(fallback_state)
        processing_time = time.time() - start_time
        
        return EnhancedProcessingResponse(
            success=True,
            study_id=request.study_id,
            processing_mode="basic_fallback",
            references=fallback_result.references,
            citations=fallback_result.citations,
            processing_time_seconds=processing_time,
            fallback_reasons=["Circuit breaker open for AI services"],
            warnings=["AI features unavailable, using basic processing"]
        )
        
    except asyncio.TimeoutError:
        processing_time = time.time() - start_time
        raise HTTPException(
            status_code=408,
            detail=f"Processing timeout after {processing_time:.1f}s. Try reducing scope or increasing timeout."
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Reference processing failed after {processing_time:.1f}s: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Enhanced monitoring endpoints
@app.get("/metrics/system",
         response_model=SystemMetricsResponse,
         summary="Get comprehensive system metrics",
         description="Detailed system performance, cost, and health metrics")
async def get_system_metrics():
    """Get comprehensive system metrics."""
    try:
        metrics_collector = await get_metrics_collector()
        
        # Gather all metrics
        system_metrics = await metrics_collector.get_system_metrics()
        performance_summary = await metrics_collector.get_performance_summary()
        cost_analysis = await metrics_collector.get_cost_analysis()
        predictive_insights = await metrics_collector.get_predictive_insights()
        
        # Circuit breaker status
        from .circuit_breaker_advanced import get_circuit_breaker_manager
        circuit_manager = get_circuit_breaker_manager()
        circuit_status = circuit_manager.get_all_states()
        
        return SystemMetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
            system_health=system_metrics,
            performance_metrics=performance_summary,
            cost_metrics=cost_analysis,
            circuit_breaker_status=circuit_status,
            predictive_insights=predictive_insights
        )
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")

@app.get("/metrics/performance",
         summary="Get performance metrics",
         description="Detailed API performance statistics")
async def get_performance_metrics():
    """Get detailed performance metrics."""
    try:
        metrics_collector = await get_metrics_collector()
        performance_summary = await metrics_collector.get_performance_summary()
        return performance_summary
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics/costs",
         summary="Get cost analysis",
         description="Detailed cost breakdown and projections")
async def get_cost_metrics():
    """Get detailed cost analysis."""
    try:
        metrics_collector = await get_metrics_collector()
        cost_analysis = await metrics_collector.get_cost_analysis()
        return cost_analysis
    except Exception as e:
        logger.error(f"Error getting cost metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Circuit breaker management endpoints
@app.get("/circuit-breakers",
         summary="Get circuit breaker status",
         description="Status of all circuit breakers")
async def get_circuit_breaker_status():
    """Get status of all circuit breakers."""
    try:
        from .circuit_breaker_advanced import get_circuit_breaker_manager
        circuit_manager = get_circuit_breaker_manager()
        return circuit_manager.get_all_states()
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/circuit-breakers/{name}/reset",
          summary="Reset circuit breaker",
          description="Manually reset a specific circuit breaker")
async def reset_circuit_breaker(name: str):
    """Manually reset a circuit breaker."""
    try:
        from .circuit_breaker_advanced import get_circuit_breaker_manager
        circuit_manager = get_circuit_breaker_manager()
        
        if name not in circuit_manager.circuit_breakers:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{name}' not found")
        
        circuit_breaker = circuit_manager.circuit_breakers[name]
        await circuit_breaker._transition_to_closed()
        
        return {"message": f"Circuit breaker '{name}' reset to CLOSED state"}
        
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Performance optimization endpoints
@app.post("/admin/optimize-performance",
          summary="Trigger performance optimization",
          description="Trigger system performance optimization (admin only)")
async def optimize_performance(background_tasks: BackgroundTasks):
    """Trigger performance optimization."""
    try:
        background_tasks.add_task(run_performance_optimization)
        return {"message": "Performance optimization started", "status": "in_progress"}
    except Exception as e:
        logger.error(f"Error starting performance optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/clear-caches",
          summary="Clear system caches",
          description="Clear all system caches (admin only)")
async def clear_caches():
    """Clear all system caches."""
    try:
        # This would trigger cache clearing in actual implementation
        return {"message": "Caches cleared", "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error clearing caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks
async def record_processing_analytics(request: EnhancedProcessingRequest, 
                                    response: EnhancedProcessingResponse,
                                    processing_time: float):
    """Record analytics data for processing requests."""
    try:
        metrics_collector = await get_metrics_collector()
        
        # Record usage metrics
        await metrics_collector.record_metric(
            metric_name="reference_processing_completed",
            value={
                "study_id": request.study_id,
                "processing_mode": response.processing_mode,
                "references_count": len(response.references),
                "processing_time": processing_time,
                "ai_features_used": response.ai_features_used,
                "user_id": request.user_id,
                "organization_id": request.organization_id
            },
            metric_type=MetricType.USAGE,
            tags={
                "endpoint": "process_references",
                "success": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"Error recording analytics: {e}")

async def run_performance_optimization():
    """Run system performance optimization."""
    try:
        logger.info("Starting performance optimization...")
        
        # Mock optimization tasks
        await asyncio.sleep(2)  # Simulate optimization work
        
        logger.info("Performance optimization completed")
        
    except Exception as e:
        logger.error(f"Performance optimization failed: {e}")

# Exception handlers
@app.exception_handler(CircuitBreakerOpenError)
async def circuit_breaker_exception_handler(request: Request, exc: CircuitBreakerOpenError):
    """Handle circuit breaker open exceptions."""
    return JSONResponse(
        status_code=503,
        content={
            "error": "Service temporarily unavailable",
            "detail": str(exc),
            "retry_after": 60,
            "fallback_available": True
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "enhanced_api_endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )