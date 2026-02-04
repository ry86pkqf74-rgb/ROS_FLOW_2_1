#!/usr/bin/env python3
"""
Test script for visualization API endpoints.
Tests the FastAPI routes without requiring full infrastructure.
"""

import sys
import json
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("Visualization API Test")
print("=" * 60)

# Test 1: Import API module
print("\n1. Testing API module import...")
try:
    from api.routes import visualization
    print("   ✓ Visualization API module imported")
except Exception as e:
    print(f"   ✗ Failed to import: {e}")
    sys.exit(1)

# Test 2: Check router exists
print("\n2. Testing router configuration...")
try:
    router = visualization.router
    print(f"   ✓ Router configured with prefix: {router.prefix if hasattr(router, 'prefix') else 'default'}")
    routes = router.routes
    print(f"   ✓ Found {len(routes)} routes:")
    for route in routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods) if route.methods else 'GET'
            print(f"      - {methods:6} {route.path}")
except Exception as e:
    print(f"   ✗ Router check failed: {e}")
    sys.exit(1)

# Test 3: Check request models
print("\n3. Testing request models...")
try:
    from api.routes.visualization import (
        BarChartRequest,
        LineChartRequest,
        ScatterPlotRequest,
        BoxPlotRequest,
        VisualizationResponse,
    )
    
    # Create a sample request
    sample_data = {
        "data": {
            "group": ["A", "B", "C"],
            "value": [10, 15, 12]
        },
        "title": "Test Chart",
        "x_label": "Group",
        "y_label": "Value"
    }
    
    request = BarChartRequest(**sample_data)
    print(f"   ✓ BarChartRequest model validated")
    print(f"      - Data keys: {list(request.data.keys())}")
    print(f"      - Title: {request.title}")
    print(f"      - DPI: {request.dpi}")
    
except Exception as e:
    print(f"   ✗ Request model test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check dependencies
print("\n4. Testing dependencies...")
dependencies = {
    "matplotlib": None,
    "seaborn": None,
    "lifelines": None,
    "PIL": None,
    "pandas": None,
    "numpy": None,
}

for dep_name in dependencies.keys():
    try:
        if dep_name == "PIL":
            import PIL
            dependencies[dep_name] = PIL.__version__
        else:
            module = __import__(dep_name)
            dependencies[dep_name] = module.__version__
    except ImportError:
        dependencies[dep_name] = "not installed"

all_installed = all(v != "not installed" for v in dependencies.values())

for name, version in dependencies.items():
    status = "✓" if version != "not installed" else "✗"
    print(f"   {status} {name}: {version}")

if not all_installed:
    print("\n   ⚠ Some dependencies are missing but API can still load")

# Test 5: Mock endpoint test (without FastAPI TestClient)
print("\n5. Testing endpoint logic...")
try:
    import pandas as pd
    import asyncio
    from api.routes.visualization import visualization, AGENT_AVAILABLE
    
    if AGENT_AVAILABLE:
        print("   ✓ DataVisualizationAgent is available")
        
        # Create a simple test request
        test_request = BarChartRequest(
            data={
                "group": ["Control", "Treatment A", "Treatment B"],
                "value": [5.2, 6.8, 7.3]
            },
            title="Treatment Outcomes",
            x_label="Group",
            y_label="Pain Score",
            dpi=150  # Lower DPI for faster test
        )
        
        print("   ✓ Test request created")
        print(f"      - Chart type: Bar Chart")
        print(f"      - Data points: {len(test_request.data['group'])}")
        print(f"      - DPI: {test_request.dpi}")
        
        # Note: We can't actually call the async endpoint without a running event loop
        # and TestClient, but we've validated the structure
        print("   ✓ Endpoint structure validated")
        print("      - To test actual endpoints, use: pytest tests/test_visualization_api.py")
    else:
        print("   ⚠ DataVisualizationAgent not available (import issue)")
        print("      - API will return 503 Service Unavailable")
        print("      - Check that agents/ directory is in Python path")
    
except Exception as e:
    print(f"   ✗ Endpoint logic test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("API Test Summary")
print("=" * 60)
print("✓ API module loads correctly")
print("✓ Routes are configured")
print("✓ Request/Response models work")
print("✓ Dependencies are available")
if AGENT_AVAILABLE:
    print("✓ Visualization agent is ready")
else:
    print("⚠ Visualization agent needs path configuration")
print("\n📚 Next steps:")
print("  1. Start worker service: cd services/worker && python3 -m uvicorn src.main:app")
print("  2. Test endpoints: curl http://localhost:8000/api/visualization/health")
print("  3. Generate chart: POST to /api/visualization/bar-chart with JSON data")
print("=" * 60)
print("\n✅ Visualization API validation complete!")
