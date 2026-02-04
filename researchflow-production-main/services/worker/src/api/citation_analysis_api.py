"""
Citation Network Analysis API

FastAPI endpoints for citation network analysis including:
- Network construction from literature data
- Centrality and impact analysis
- Community detection and clustering
- Research gap identification
- Network visualization data export
- Analysis result caching and retrieval

Author: Research Analysis Team
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
import logging
import json
import asyncio
from datetime import datetime
import traceback

# Import citation network analyzer
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.citation_network_analyzer import (
    CitationNetworkAnalyzer,
    NetworkAnalysisResult,
    get_citation_analyzer
)
from monitoring.performance_dashboard import get_performance_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Citation Network Analysis API",
    description="Advanced citation network analysis and research gap detection",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class PaperInput(BaseModel):
    """Paper data for network construction."""
    
    id: str = Field(..., description="Unique paper identifier")
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    year: int = Field(..., ge=1900, le=2030, description="Publication year")
    journal: str = Field(default="", description="Journal name")
    doi: Optional[str] = Field(None, description="DOI identifier")
    keywords: List[str] = Field(default_factory=list, description="Keywords/topics")
    abstract: str = Field(default="", description="Paper abstract")
    citation_count: int = Field(default=0, ge=0, description="Number of citations")
    citations: List[str] = Field(default_factory=list, description="List of cited paper IDs")
    
    @validator('citations')
    def validate_citations(cls, v):
        """Validate citation list."""
        if len(v) > 1000:  # Reasonable limit
            raise ValueError("Too many citations (max 1000)")
        return v

class NetworkBuildRequest(BaseModel):
    """Request to build citation network."""
    
    papers: List[PaperInput] = Field(..., description="List of papers to analyze")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Analysis configuration options"
    )
    
    @validator('papers')
    def validate_papers(cls, v):
        """Validate paper list."""
        if len(v) == 0:
            raise ValueError("Paper list cannot be empty")
        if len(v) > 10000:
            raise ValueError("Too many papers (max 10000)")
        return v

class AnalysisRequest(BaseModel):
    """Request for network analysis."""
    
    include_communities: bool = Field(default=True, description="Include community detection")
    include_gaps: bool = Field(default=True, description="Include research gap analysis")
    include_trends: bool = Field(default=True, description="Include emerging topic analysis")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results per category")
    cache_results: bool = Field(default=True, description="Cache analysis results")

class NetworkStatsResponse(BaseModel):
    """Network statistics response."""
    
    node_count: int
    edge_count: int
    density: float
    clustering_coefficient: float
    average_path_length: Optional[float]
    most_cited_paper: str
    year_range: tuple
    total_journals: int
    analysis_timestamp: str

class CentralityResponse(BaseModel):
    """Centrality analysis response."""
    
    top_betweenness_centrality: List[Dict[str, Any]]
    top_pagerank_scores: List[Dict[str, Any]]
    top_cited_papers: List[Dict[str, Any]]

class CommunityResponse(BaseModel):
    """Community detection response."""
    
    communities: Dict[int, List[str]]
    modularity: float
    community_count: int
    largest_community_size: int

class ResearchGapsResponse(BaseModel):
    """Research gaps analysis response."""
    
    identified_gaps: List[Dict[str, Any]]
    gap_count: int
    high_priority_gaps: List[Dict[str, Any]]

class EmergingTopicsResponse(BaseModel):
    """Emerging topics analysis response."""
    
    trending_topics: List[Dict[str, Any]]
    high_velocity_papers: List[Dict[str, Any]]
    keyword_trends: List[Dict[str, Any]]

class NetworkVisualizationResponse(BaseModel):
    """Network visualization data response."""
    
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    layout_config: Dict[str, Any]
    metadata: Dict[str, Any]

class FullAnalysisResponse(BaseModel):
    """Complete network analysis response."""
    
    network_stats: NetworkStatsResponse
    centrality_analysis: CentralityResponse
    community_analysis: CommunityResponse
    research_gaps: ResearchGapsResponse
    emerging_topics: EmergingTopicsResponse
    visualization_data: NetworkVisualizationResponse
    analysis_metadata: Dict[str, Any]

# Dependencies
def get_analyzer() -> CitationNetworkAnalyzer:
    """Get citation network analyzer instance."""
    return get_citation_analyzer()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        analyzer = get_analyzer()
        summary = analyzer.get_network_summary()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "network_status": summary.get("status", "unknown"),
            "features": {
                "network_construction": True,
                "centrality_analysis": True,
                "community_detection": True,
                "gap_analysis": True,
                "trend_analysis": True,
                "visualization_export": True
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

@app.post("/api/v1/network/build")
async def build_citation_network(
    request: NetworkBuildRequest,
    background_tasks: BackgroundTasks,
    analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)
):
    """Build citation network from paper data."""
    try:
        performance_monitor = get_performance_monitor()
        
        with performance_monitor.measure_operation(
            "build_citation_network",
            endpoint="/api/v1/network/build",
            estimated_cost=len(request.papers) * 0.001  # Estimate: $0.001 per paper
        ):
            logger.info(f"Building citation network from {len(request.papers)} papers")
            
            # Convert Pydantic models to dicts
            papers_data = [paper.dict() for paper in request.papers]
            
            # Build network
            await analyzer.build_network_from_papers(papers_data)
            
            # Get network summary
            summary = analyzer.get_network_summary()
            
            logger.info(f"Citation network built successfully: {summary['node_count']} nodes")
            
            return {
                "success": True,
                "message": f"Network built with {summary['node_count']} nodes and {summary['edge_count']} edges",
                "network_summary": summary,
                "build_timestamp": datetime.now().isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error building citation network: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/network/stats", response_model=NetworkStatsResponse)
async def get_network_statistics(analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)):
    """Get basic network statistics."""
    try:
        performance_monitor = get_performance_monitor()
        
        with performance_monitor.measure_operation("get_network_stats", endpoint="/api/v1/network/stats"):
            summary = analyzer.get_network_summary()
            
            if summary["status"] == "empty":
                raise HTTPException(status_code=404, detail="No network data available")
            
            return NetworkStatsResponse(
                node_count=summary["node_count"],
                edge_count=summary["edge_count"],
                density=summary["density"],
                clustering_coefficient=0.0,  # Will be computed in full analysis
                average_path_length=None,
                most_cited_paper=summary["most_cited_paper"],
                year_range=summary["year_range"],
                total_journals=summary["total_journals"],
                analysis_timestamp=datetime.now().isoformat()
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting network statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/network/analyze", response_model=FullAnalysisResponse)
async def analyze_citation_network(
    request: AnalysisRequest,
    analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)
):
    """Perform comprehensive citation network analysis."""
    try:
        performance_monitor = get_performance_monitor()
        
        with performance_monitor.measure_operation(
            "analyze_citation_network",
            endpoint="/api/v1/network/analyze",
            estimated_cost=analyzer.citation_graph.number_of_nodes() * 0.002  # $0.002 per node
        ):
            logger.info("Starting comprehensive citation network analysis")
            
            # Check if network exists
            if not analyzer.nodes:
                raise HTTPException(status_code=404, detail="No network data - build network first")
            
            # Perform analysis
            result = await analyzer.analyze_network()
            
            # Format response
            response = FullAnalysisResponse(
                network_stats=NetworkStatsResponse(
                    node_count=result.node_count,
                    edge_count=result.edge_count,
                    density=result.density,
                    clustering_coefficient=result.clustering_coefficient,
                    average_path_length=result.average_path_length,
                    most_cited_paper=result.top_cited_papers[0][0] if result.top_cited_papers else "",
                    year_range=(0, 0),  # Will be computed from analyzer summary
                    total_journals=0,   # Will be computed from analyzer summary
                    analysis_timestamp=datetime.now().isoformat()
                ),
                centrality_analysis=CentralityResponse(
                    top_betweenness_centrality=[
                        {"paper_id": paper_id, "score": score, "title": analyzer.nodes[paper_id].title}
                        for paper_id, score in result.top_central_papers[:request.max_results]
                        if paper_id in analyzer.nodes
                    ],
                    top_pagerank_scores=[
                        {"paper_id": paper_id, "score": score, "title": analyzer.nodes[paper_id].title}
                        for paper_id, score in result.top_pagerank_papers[:request.max_results]
                        if paper_id in analyzer.nodes
                    ],
                    top_cited_papers=[
                        {"paper_id": paper_id, "citations": citations, "title": analyzer.nodes[paper_id].title}
                        for paper_id, citations in result.top_cited_papers[:request.max_results]
                        if paper_id in analyzer.nodes
                    ]
                ),
                community_analysis=CommunityResponse(
                    communities=result.communities,
                    modularity=result.modularity,
                    community_count=len(result.communities),
                    largest_community_size=max(len(community) for community in result.communities.values()) if result.communities else 0
                ),
                research_gaps=ResearchGapsResponse(
                    identified_gaps=result.research_gaps[:request.max_results] if request.include_gaps else [],
                    gap_count=len(result.research_gaps),
                    high_priority_gaps=[
                        gap for gap in result.research_gaps 
                        if gap.get("severity", "low") in ["high", "medium"]
                    ][:10]
                ),
                emerging_topics=EmergingTopicsResponse(
                    trending_topics=result.emerging_topics[:request.max_results] if request.include_trends else [],
                    high_velocity_papers=[
                        topic for topic in result.emerging_topics
                        if "paper_id" in topic and topic.get("citation_velocity", 0) > 3.0
                    ][:10],
                    keyword_trends=[
                        topic for topic in result.emerging_topics
                        if topic.get("trend_type") == "keyword_frequency"
                    ][:10]
                ),
                visualization_data=NetworkVisualizationResponse(
                    nodes=result.visualization_data["nodes"],
                    edges=result.visualization_data["edges"],
                    layout_config={"type": "force-directed", "iterations": 100},
                    metadata=result.visualization_data["metadata"]
                ),
                analysis_metadata={
                    "analysis_timestamp": datetime.now().isoformat(),
                    "request_config": request.dict(),
                    "network_size": result.node_count,
                    "computation_time": "computed_externally"
                }
            )
            
            logger.info("Citation network analysis completed successfully")
            return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in citation network analysis: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/network/communities", response_model=CommunityResponse)
async def get_communities(analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)):
    """Get community detection results."""
    try:
        if not analyzer.nodes:
            raise HTTPException(status_code=404, detail="No network data available")
        
        communities, modularity = await analyzer._detect_communities()
        
        return CommunityResponse(
            communities=communities,
            modularity=modularity,
            community_count=len(communities),
            largest_community_size=max(len(community) for community in communities.values()) if communities else 0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting communities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/network/gaps", response_model=ResearchGapsResponse)
async def get_research_gaps(
    max_gaps: int = Query(default=20, ge=1, le=100),
    analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)
):
    """Get research gap analysis results."""
    try:
        if not analyzer.nodes:
            raise HTTPException(status_code=404, detail="No network data available")
        
        gaps = await analyzer._detect_research_gaps()
        
        return ResearchGapsResponse(
            identified_gaps=gaps[:max_gaps],
            gap_count=len(gaps),
            high_priority_gaps=[
                gap for gap in gaps 
                if gap.get("severity", "low") in ["high", "medium"]
            ][:10]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting research gaps: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/network/visualization", response_model=NetworkVisualizationResponse)
async def get_visualization_data(analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)):
    """Get network visualization data."""
    try:
        if not analyzer.nodes:
            raise HTTPException(status_code=404, detail="No network data available")
        
        viz_data = analyzer._prepare_visualization_data()
        
        return NetworkVisualizationResponse(
            nodes=viz_data["nodes"],
            edges=viz_data["edges"],
            layout_config={"type": "force-directed", "iterations": 100},
            metadata=viz_data["metadata"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visualization data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/network/export")
async def export_network_data(
    format: str = Query(default="json", regex="^(json|pickle)$"),
    analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)
):
    """Export network data in specified format."""
    try:
        if not analyzer.nodes:
            raise HTTPException(status_code=404, detail="No network data available")
        
        if format == "json":
            network_data = analyzer._prepare_network_data()
            return JSONResponse(content=network_data)
        
        elif format == "pickle":
            # For pickle export, we'd typically save to file and return download link
            # This is a simplified version
            raise HTTPException(
                status_code=501, 
                detail="Pickle export not implemented in this endpoint - use save_network method directly"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting network data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/network/clear")
async def clear_network(analyzer: CitationNetworkAnalyzer = Depends(get_analyzer)):
    """Clear current network data."""
    try:
        analyzer.citation_graph.clear()
        analyzer.nodes.clear()
        analyzer.edges.clear()
        analyzer.analysis_cache.clear()
        
        return {
            "success": True,
            "message": "Network data cleared successfully",
            "cleared_timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error clearing network: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting Citation Network Analysis API...")
        
        # Initialize analyzer
        analyzer = get_citation_analyzer()
        logger.info("Citation Network Analyzer initialized")
        
        # Initialize performance monitoring
        performance_monitor = get_performance_monitor()
        logger.info("Performance monitoring initialized")
        
        logger.info("Citation Network Analysis API ready!")
    
    except Exception as e:
        logger.error(f"Failed to initialize API: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down Citation Network Analysis API...")
        
        # Cleanup if needed
        performance_monitor = get_performance_monitor()
        performance_monitor.stop_monitoring()
        
        logger.info("Citation Network Analysis API shutdown complete")
    
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")