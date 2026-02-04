#!/usr/bin/env python3
"""
Minimal AI API Server for ResearchFlow
=====================================

A lightweight FastAPI server that serves only the AI endpoints for testing
and development purposes. This bypasses the complex dependency issues
in the main application.

Usage:
    python3 api_ai_server.py

Then test with:
    curl http://localhost:8000/api/v1/ai/health
"""

import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import only the AI endpoints
from api.ai_endpoints import router as ai_router

# Create minimal FastAPI app
app = FastAPI(
    title="ResearchFlow AI API",
    description="AI-enhanced processing endpoints for ResearchFlow",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include AI router
app.include_router(ai_router)

# Basic health check
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ResearchFlow AI API",
        "version": "0.1.0",
        "ai_endpoints": "/api/v1/ai",
        "documentation": "/docs"
    }

@app.get("/health")
async def health():
    """Basic health check"""
    return {"status": "healthy", "service": "ai-api"}

if __name__ == "__main__":
    print("🚀 Starting ResearchFlow AI API Server...")
    print("📍 AI endpoints will be available at:")
    print("   - Health: http://localhost:8000/api/v1/ai/health")
    print("   - Models: http://localhost:8000/api/v1/ai/models")
    print("   - Embeddings: http://localhost:8000/api/v1/ai/embeddings")
    print("   - Search: http://localhost:8000/api/v1/ai/search")
    print("   - Entities: http://localhost:8000/api/v1/ai/entities")
    print("   - Literature: http://localhost:8000/api/v1/ai/literature/match")
    print("📚 Documentation: http://localhost:8000/docs")
    print("")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        access_log=True
    )