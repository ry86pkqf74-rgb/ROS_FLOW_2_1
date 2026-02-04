"""
Protocol Generation REST API

Provides HTTP endpoints for easy integration with the protocol generation system.
Supports all template types, output formats, and advanced features including
PHI compliance, performance monitoring, and batch processing.

Endpoints:
- POST /api/v1/protocols/generate - Generate single protocol
- GET /api/v1/protocols/templates - List available templates
- POST /api/v1/protocols/validate - Validate template variables
- POST /api/v1/protocols/batch - Batch protocol generation
- GET /api/v1/protocols/health - Health check

Author: Enhancement Team
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import traceback

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# Import enhanced protocol generator
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflow_engine.stages.study_analyzers.protocol_generator import (
    ProtocolFormat,
    TemplateType,
    RegulatoryFramework
)
from enhanced_protocol_generation import (
    EnhancedProtocolGenerator,
    create_enhanced_generator
)
from security.phi_compliance import ComplianceLevel
from config.protocol_config import get_current_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Protocol Generation API",
    description="REST API for clinical study protocol generation with templates and PHI compliance",
    version="1.0.0",
    docs_url="/api/v1/protocols/docs",
    redoc_url="/api/v1/protocols/redoc"
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global enhanced protocol generator instance
enhanced_generator = None


# Pydantic models for request/response
class ProtocolRequest(BaseModel):
    """Request model for protocol generation."""
    template_id: str = Field(..., description="Template ID to use for generation")
    study_data: Dict[str, Any] = Field(..., description="Study parameters and data")
    output_format: str = Field("markdown", description="Output format (markdown, html, json, pdf, docx)")
    
    @validator('output_format')
    def validate_output_format(cls, v):
        valid_formats = ['markdown', 'html', 'json', 'pdf', 'docx', 'xml', 'latex', 'rtf']
        if v.lower() not in valid_formats:
            raise ValueError(f'Invalid output format. Must be one of: {valid_formats}')
        return v.lower()


class ProtocolResponse(BaseModel):
    """Response model for protocol generation."""
    success: bool
    protocol_content: Optional[str] = None
    template_id: str
    output_format: str
    metadata: Optional[Dict[str, Any]] = None
    generated_timestamp: str
    content_length: Optional[int] = None
    error: Optional[str] = None


class TemplateInfo(BaseModel):
    """Template information model."""
    template_id: str
    name: str
    description: str
    type: str
    version: str
    required_variables: List[str]
    sections_count: int


class TemplatesResponse(BaseModel):
    """Response model for templates list."""
    templates: List[TemplateInfo]
    total_count: int


class ValidationRequest(BaseModel):
    """Request model for template validation."""
    template_id: str = Field(..., description="Template ID to validate against")
    variables: Dict[str, Any] = Field(..., description="Variables to validate")


class ValidationResponse(BaseModel):
    """Response model for template validation."""
    valid: bool
    missing_variables: List[str]
    provided_variables: List[str]
    required_variables: List[str]
    error: Optional[str] = None


class BatchRequest(BaseModel):
    """Request model for batch protocol generation."""
    requests: List[ProtocolRequest] = Field(..., description="List of protocol requests")
    parallel_processing: bool = Field(True, description="Process requests in parallel")


class BatchResponse(BaseModel):
    """Response model for batch processing."""
    results: List[ProtocolResponse]
    total_requests: int
    successful_requests: int
    failed_requests: int
    processing_time_seconds: float


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    templates_loaded: int
    system_info: Dict[str, Any]


# Dependency to get enhanced protocol generator
def get_enhanced_protocol_generator() -> EnhancedProtocolGenerator:
    """Get initialized enhanced protocol generator instance."""
    global enhanced_generator
    if enhanced_generator is None:
        enhanced_generator = create_enhanced_generator("default")
    return enhanced_generator


# API Endpoints
@app.get("/api/v1/protocols/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        generator = get_enhanced_protocol_generator()
        health_info = generator.get_system_health()
        
        return HealthResponse(
            status=health_info["status"],
            timestamp=health_info["timestamp"],
            version="1.0.0",
            templates_loaded=health_info["templates"]["total_available"],
            system_info={
                "phi_compliance": health_info["phi_compliance"]["enabled"],
                "regulatory_templates": health_info["configuration"]["regulatory_checking"],
                "supported_formats": ["markdown", "html", "json", "pdf", "docx"],
                "performance_monitoring": True,
                "enhanced_features": True,
                "configuration_management": True
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Service unhealthy")


@app.get("/api/v1/protocols/templates", response_model=TemplatesResponse)
async def get_templates():
    """Get list of available protocol templates with enhanced features."""
    try:
        generator = get_enhanced_protocol_generator()
        templates_info = generator.get_available_templates_enhanced()
        
        templates = []
        for template_id, info in templates_info.items():
            templates.append(TemplateInfo(
                template_id=template_id,
                name=info['name'],
                description=info['description'],
                type=info['type'],
                version=info['version'],
                required_variables=info['required_variables'],
                sections_count=info['sections_count']
            ))
        
        return TemplatesResponse(
            templates=templates,
            total_count=len(templates)
        )
    
    except Exception as e:
        logger.error(f"Error getting templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/protocols/generate", response_model=ProtocolResponse)
async def generate_protocol(request: ProtocolRequest, user_id: Optional[str] = Query(None)):
    """Generate a protocol document with enhanced features including PHI compliance."""
    try:
        logger.info(f"Generating enhanced protocol with template: {request.template_id}")
        
        generator = get_enhanced_protocol_generator()
        
        # Convert string format to enum
        try:
            output_format = ProtocolFormat(request.output_format)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid output format: {request.output_format}"
            )
        
        # Generate protocol with enhanced features
        result = await generator.generate_protocol_enhanced(
            template_id=request.template_id,
            study_data=request.study_data,
            output_format=output_format,
            user_id=user_id,
            phi_check=True
        )
        
        if not result["success"]:
            logger.error(f"Enhanced protocol generation failed: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=400, detail=result.get('error', 'Protocol generation failed'))
        
        return ProtocolResponse(
            success=result["success"],
            protocol_content=result["protocol_content"],
            template_id=result["template_id"],
            output_format=result["output_format"],
            metadata=result.get("metadata", {}),
            generated_timestamp=result["generated_timestamp"],
            content_length=result["content_length"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating enhanced protocol: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/protocols/validate", response_model=ValidationResponse)
async def validate_template_variables(request: ValidationRequest):
    """Validate variables against template requirements with PHI compliance checking."""
    try:
        generator = get_enhanced_protocol_generator()
        
        validation_result = generator.validate_template_variables_enhanced(
            request.template_id, request.variables
        )
        
        if "error" in validation_result:
            raise HTTPException(status_code=400, detail=validation_result["error"])
        
        return ValidationResponse(
            valid=validation_result["valid"],
            missing_variables=validation_result["missing_variables"],
            provided_variables=validation_result["provided_variables"],
            required_variables=validation_result["required_variables"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating template variables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/protocols/batch", response_model=BatchResponse)
async def batch_generate_protocols(request: BatchRequest, background_tasks: BackgroundTasks):
    """Generate multiple protocols in batch with enhanced features."""
    try:
        logger.info(f"Starting enhanced batch generation of {len(request.requests)} protocols")
        
        generator = get_enhanced_protocol_generator()
        
        # Convert requests to enhanced format
        enhanced_requests = []
        for req in request.requests:
            enhanced_requests.append({
                "template_id": req.template_id,
                "study_data": req.study_data,
                "output_format": ProtocolFormat(req.output_format),
                "phi_check": True
            })
        
        # Use enhanced batch processing
        batch_result = await generator.batch_generate_enhanced(
            enhanced_requests,
            parallel_processing=request.parallel_processing
        )
        
        # Convert results to API response format
        api_results = []
        for result in batch_result["results"]:
            api_results.append(ProtocolResponse(
                success=result["success"],
                protocol_content=result.get("protocol_content"),
                template_id=result["template_id"],
                output_format=result["output_format"],
                metadata=result.get("metadata", {}),
                generated_timestamp=result["generated_timestamp"],
                content_length=result.get("content_length"),
                error=result.get("error")
            ))
        
        return BatchResponse(
            results=api_results,
            total_requests=batch_result["batch_statistics"]["total_requests"],
            successful_requests=batch_result["batch_statistics"]["successful_requests"],
            failed_requests=batch_result["batch_statistics"]["failed_requests"],
            processing_time_seconds=batch_result["batch_statistics"]["processing_time_seconds"]
        )
    
    except Exception as e:
        logger.error(f"Error in enhanced batch processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/protocols/template/{template_id}")
async def get_template_details(template_id: str):
    """Get detailed information about a specific template."""
    try:
        generator = get_protocol_generator()
        templates = generator.get_available_templates()
        
        if template_id not in templates:
            raise HTTPException(status_code=404, detail="Template not found")
        
        template_info = templates[template_id]
        
        # Get additional template details
        return {
            "template_id": template_id,
            "info": template_info,
            "sample_variables": {
                "study_title": "Sample Study Title",
                "principal_investigator": "Dr. Sample Name",
                "primary_objective": "Sample primary objective",
                "estimated_sample_size": 100,
                "design_description": "Sample study design"
            },
            "supported_formats": [format.value for format in ProtocolFormat],
            "regulatory_compliance": True,
            "phi_compliant": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize enhanced services on startup."""
    global enhanced_generator
    try:
        logger.info("Starting Enhanced Protocol Generation API...")
        enhanced_generator = create_enhanced_generator("default")
        health_info = enhanced_generator.get_system_health()
        
        logger.info(f"Loaded {health_info['templates']['total_available']} protocol templates")
        logger.info(f"PHI Compliance: {health_info['phi_compliance']['enabled']}")
        logger.info(f"Configuration: {health_info['configuration']['environment']}")
        logger.info("Enhanced Protocol Generation API ready!")
    except Exception as e:
        logger.error(f"Failed to initialize enhanced API: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Protocol Generation API...")


# Development server runner
def run_dev_server(host: str = "0.0.0.0", port: int = 8002):
    """Run development server."""
    uvicorn.run(
        "protocol_api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    run_dev_server()