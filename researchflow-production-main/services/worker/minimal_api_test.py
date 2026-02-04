#!/usr/bin/env python3
"""
Minimal API Server for Testing Enhanced References Integration
Runs only the core enhanced references endpoints for smoke testing
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add ros-backend/src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import Enhanced Reference Management router
try:
    from api.enhanced_references import router as enhanced_references_router
    ENHANCED_REFERENCES_AVAILABLE = True
    print("[MINIMAL] Enhanced Reference Management router loaded")
except ImportError as e:
    ENHANCED_REFERENCES_AVAILABLE = False
    print(f"[MINIMAL] Enhanced Reference Management router not available: {e}")

app = FastAPI(
    title="Minimal Enhanced References Test API",
    description="Test server for Enhanced References functionality",
    version="1.0.0-test",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Root / service info")
async def root():
    """Return service name, version, and mode."""
    return {
        "service": "Minimal Enhanced References Test API",
        "version": "1.0.0-test",
        "mode": "TEST",
        "enhanced_references_available": ENHANCED_REFERENCES_AVAILABLE,
        "status": "active"
    }

@app.get("/health", summary="Health check")
async def health_check():
    return {
        "status": "healthy",
        "service": "minimal-enhanced-refs-test",
        "version": "1.0.0-test",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "enhanced_references_available": ENHANCED_REFERENCES_AVAILABLE,
        "mode": "TEST"
    }

# Register Enhanced Reference Management router if available
if ENHANCED_REFERENCES_AVAILABLE and enhanced_references_router is not None:
    app.include_router(enhanced_references_router, prefix="/api", tags=["enhanced-references"])
    print("[MINIMAL] Enhanced Reference Management router registered at /api/references/*")
else:
    # Provide fallback endpoints
    @app.get("/api/references/health", summary="Enhanced References Health (Fallback)")
    async def enhanced_references_health_fallback():
        return {
            "status": "unavailable",
            "error": "Enhanced Reference Management components not loaded",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/api/references/capabilities", summary="Enhanced References Capabilities (Fallback)")
    async def enhanced_references_capabilities_fallback():
        return {
            "enhanced_references_available": False,
            "error": "Enhanced Reference Management not loaded",
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    port = int(os.environ.get("TEST_API_PORT", 8000))
    print(f"[MINIMAL] Starting minimal test API server on port {port}")
    print(f"[MINIMAL] Enhanced References available: {ENHANCED_REFERENCES_AVAILABLE}")
    
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")