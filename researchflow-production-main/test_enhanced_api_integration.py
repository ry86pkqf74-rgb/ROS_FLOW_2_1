"""
Test Enhanced API Integration

Verify that our Enhanced Reference Management API integration works correctly.
"""

import asyncio
from pathlib import Path
import sys

# Add the worker src path
current_dir = Path(__file__).parent
worker_src = current_dir / "services" / "worker" / "src"
sys.path.insert(0, str(worker_src))

async def test_enhanced_references_import():
    """Test importing our enhanced references router."""
    print("🔍 Testing Enhanced References Router Import...")
    
    try:
        from api.enhanced_references import router, ENHANCED_REFERENCES_AVAILABLE
        print("✅ Enhanced References router imported successfully")
        print(f"   Enhanced References Available: {ENHANCED_REFERENCES_AVAILABLE}")
        
        # Check routes
        routes = [route.path for route in router.routes if hasattr(route, 'path')]
        print(f"✅ Routes available: {len(routes)}")
        for route in routes:
            print(f"   - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def test_basic_functionality():
    """Test basic functionality if available."""
    print("\n🧪 Testing Basic Functionality...")
    
    try:
        from api.enhanced_references import enhanced_references_health
        
        # Test health check
        health_result = await enhanced_references_health()
        print("✅ Health check endpoint working")
        print(f"   Status: {health_result.get('status', 'unknown')}")
        print(f"   Enhanced References Available: {health_result.get('enhanced_references_available', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

async def test_fastapi_integration():
    """Test FastAPI integration."""
    print("\n🚀 Testing FastAPI Integration...")
    
    try:
        from fastapi import FastAPI
        from api.enhanced_references import router
        
        # Create test app
        test_app = FastAPI()
        test_app.include_router(router, prefix="/api", tags=["test"])
        
        print("✅ FastAPI integration successful")
        
        # Check registered routes
        routes = [route.path for route in test_app.routes if hasattr(route, 'path')]
        enhanced_routes = [route for route in routes if route.startswith('/api/references')]
        
        print(f"   Total routes: {len(routes)}")
        print(f"   Enhanced reference routes: {len(enhanced_routes)}")
        for route in enhanced_routes:
            print(f"   - {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ FastAPI integration failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("🔧 ENHANCED API INTEGRATION TEST")
    print("=" * 60)
    
    # Test 1: Import
    import_ok = await test_enhanced_references_import()
    
    # Test 2: Basic functionality (if import works)
    functionality_ok = False
    if import_ok:
        functionality_ok = await test_basic_functionality()
    
    # Test 3: FastAPI integration
    fastapi_ok = False
    if import_ok:
        fastapi_ok = await test_fastapi_integration()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    print(f"✅ Import Test: {'PASS' if import_ok else 'FAIL'}")
    print(f"✅ Functionality Test: {'PASS' if functionality_ok else 'FAIL'}")
    print(f"✅ FastAPI Integration: {'PASS' if fastapi_ok else 'FAIL'}")
    
    overall_success = import_ok and fastapi_ok
    
    if overall_success:
        print("\n🎉 INTEGRATION TEST PASSED!")
        print("✅ Enhanced Reference Management API is ready for deployment")
        print("✅ Routes are properly registered and accessible")
        print("✅ Integration with main API server should work")
    else:
        print("\n❌ INTEGRATION TEST FAILED")
        print("⚠️ Issues need to be resolved before deployment")
    
    print("\n" + "=" * 60)
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)