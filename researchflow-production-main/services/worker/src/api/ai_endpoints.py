"""
AI Enhanced API Endpoints
Provides REST API endpoints for AI-enhanced processing including semantic search,
text embeddings, and entity extraction.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import asyncio
import logging
from datetime import datetime

from ai.enhanced_processing import (
    get_ai_processor, 
    EnhancedAIProcessor,
    EmbeddingResult,
    SimilarityResult
)

logger = logging.getLogger(__name__)

# API Models
class EmbeddingRequest(BaseModel):
    """Request model for text embedding"""
    texts: Union[str, List[str]] = Field(..., description="Single text or list of texts to embed")
    model: Optional[str] = Field(None, description="Optional model override")
    
class EmbeddingResponse(BaseModel):
    """Response model for text embedding"""
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    texts: List[str] = Field(..., description="Input texts")
    model_name: str = Field(..., description="Model used for embedding")
    processing_time: float = Field(..., description="Processing time in seconds")
    success: bool = Field(..., description="Whether operation succeeded")

class SearchRequest(BaseModel):
    """Request model for semantic search"""
    query: str = Field(..., description="Search query")
    documents: List[str] = Field(..., description="Documents to search")
    top_k: int = Field(5, description="Number of top results to return", ge=1, le=50)
    similarity_threshold: float = Field(0.5, description="Minimum similarity score", ge=0.0, le=1.0)

class SearchResponse(BaseModel):
    """Response model for semantic search"""
    query: str = Field(..., description="Original query")
    matches: List[Dict[str, Any]] = Field(..., description="Search results with scores")
    total_matches: int = Field(..., description="Total number of matches")
    processing_time: float = Field(..., description="Processing time in seconds")
    model_name: str = Field(..., description="Model used for search")

class EntityExtractionRequest(BaseModel):
    """Request model for entity extraction"""
    text: str = Field(..., description="Text to extract entities from", max_length=10000)
    model: Optional[str] = Field(None, description="Optional NER model override")

class EntityExtractionResponse(BaseModel):
    """Response model for entity extraction"""
    entities: List[Dict[str, Any]] = Field(..., description="Extracted entities")
    text: str = Field(..., description="Original input text")
    model: str = Field(..., description="Model used for extraction")
    success: bool = Field(..., description="Whether operation succeeded")

class LiteratureMatchRequest(BaseModel):
    """Request model for literature matching"""
    query: str = Field(..., description="Research query")
    literature_database: List[Dict[str, Any]] = Field(..., description="Literature entries to search")
    top_k: int = Field(10, description="Number of top results", ge=1, le=50)

class LiteratureMatchResponse(BaseModel):
    """Response model for literature matching"""
    matches: List[Dict[str, Any]] = Field(..., description="Matched literature with scores")
    query: str = Field(..., description="Original query")
    total: int = Field(..., description="Total matches found")
    processing_time: float = Field(..., description="Processing time in seconds")

class ModelInfoResponse(BaseModel):
    """Response model for model information"""
    ai_packages_available: bool
    initialized: bool
    loaded_models: List[str]
    config: Dict[str, Any]
    torch_info: Optional[Dict[str, Any]] = None

# Router setup
router = APIRouter(prefix="/api/v1/ai", tags=["AI Enhanced Processing"])

async def get_processor() -> EnhancedAIProcessor:
    """Dependency to get AI processor instance"""
    processor = get_ai_processor()
    # Trigger initialization
    await processor._ensure_initialized()
    if not processor.is_ready():
        raise HTTPException(
            status_code=503, 
            detail="AI processing services are not available. Please ensure AI packages are installed."
        )
    return processor

@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint for AI services"""
    processor = get_ai_processor()
    
    # Try to initialize if not already done
    try:
        await processor._ensure_initialized()
        status = "healthy" if processor.is_ready() else "unavailable"
        ai_available = processor.is_ready()
        message = "AI services ready" if processor.is_ready() else "AI initialization failed"
    except Exception as e:
        status = "error"
        ai_available = False
        message = f"AI initialization error: {str(e)}"
    
    return {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "ai_packages_available": ai_available,
        "message": message
    }

@router.get("/models", response_model=ModelInfoResponse)
async def get_model_info():
    """Get information about loaded AI models"""
    processor = get_ai_processor()
    info = processor.get_model_info()
    
    return ModelInfoResponse(
        ai_packages_available=info["ai_packages_available"],
        initialized=info["initialized"],
        loaded_models=info["loaded_models"],
        config=info["config"],
        torch_info=info.get("torch_info")
    )

@router.post("/embeddings", response_model=EmbeddingResponse)
async def generate_embeddings(
    request: EmbeddingRequest,
    processor: EnhancedAIProcessor = Depends(get_processor)
):
    """Generate text embeddings using sentence transformers"""
    try:
        results = await processor.get_embeddings(request.texts)
        
        # Check if any embeddings failed
        failed_results = [r for r in results if not r.success]
        if failed_results:
            error_messages = [r.error_message for r in failed_results if r.error_message]
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate embeddings: {'; '.join(error_messages)}"
            )
        
        return EmbeddingResponse(
            embeddings=[result.embedding.tolist() for result in results],
            texts=[result.text for result in results],
            model_name=results[0].model_name if results else "unknown",
            processing_time=sum(r.processing_time for r in results),
            success=True
        )
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    processor: EnhancedAIProcessor = Depends(get_processor)
):
    """Perform semantic search on documents"""
    try:
        # Update processor config with request parameters
        original_threshold = processor.config.get("similarity_threshold")
        processor.config["similarity_threshold"] = request.similarity_threshold
        
        result = await processor.semantic_search(
            query=request.query,
            documents=request.documents,
            top_k=request.top_k
        )
        
        # Restore original threshold
        if original_threshold is not None:
            processor.config["similarity_threshold"] = original_threshold
        
        return SearchResponse(
            query=result.query,
            matches=result.matches,
            total_matches=len(result.matches),
            processing_time=result.processing_time,
            model_name=result.model_name
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/entities", response_model=EntityExtractionResponse)
async def extract_entities(
    request: EntityExtractionRequest,
    processor: EnhancedAIProcessor = Depends(get_processor)
):
    """Extract named entities from text"""
    try:
        result = await processor.extract_entities(request.text)
        
        if not result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Entity extraction failed: {result.get('error', 'Unknown error')}"
            )
        
        return EntityExtractionResponse(
            entities=result["entities"],
            text=result["text"],
            model=result["model"],
            success=result["success"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")

@router.post("/literature/match", response_model=LiteratureMatchResponse)
async def match_literature(
    request: LiteratureMatchRequest,
    processor: EnhancedAIProcessor = Depends(get_processor)
):
    """Enhanced literature matching using semantic similarity"""
    try:
        result = await processor.enhanced_literature_matching(
            query=request.query,
            literature_db=request.literature_database
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=f"Literature matching failed: {result['error']}"
            )
        
        return LiteratureMatchResponse(
            matches=result["matches"][:request.top_k],  # Limit to requested top_k
            query=result["query"],
            total=result["total"],
            processing_time=result.get("processing_time", 0.0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Literature matching failed: {e}")
        raise HTTPException(status_code=500, detail=f"Literature matching failed: {str(e)}")

@router.post("/batch/embeddings")
async def batch_embeddings(
    background_tasks: BackgroundTasks,
    texts: List[str],
    batch_size: int = 32,
    processor: EnhancedAIProcessor = Depends(get_processor)
):
    """Process embeddings in batches for large datasets"""
    if len(texts) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10,000 texts allowed for batch processing"
        )
    
    try:
        # Process in chunks
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_results = await processor.get_embeddings(batch)
            results.extend(batch_results)
            
            # Allow other coroutines to run
            await asyncio.sleep(0.01)
        
        successful_results = [r for r in results if r.success]
        failed_count = len(results) - len(successful_results)
        
        return {
            "embeddings": [r.embedding.tolist() for r in successful_results],
            "texts": [r.text for r in successful_results],
            "total_processed": len(results),
            "successful": len(successful_results),
            "failed": failed_count,
            "average_processing_time": sum(r.processing_time for r in successful_results) / len(successful_results) if successful_results else 0
        }
        
    except Exception as e:
        logger.error(f"Batch embedding processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")

# Optional: Add to main FastAPI app
def setup_ai_routes(app):
    """Setup AI routes in the main FastAPI application"""
    app.include_router(router)
    logger.info("AI enhanced endpoints registered")