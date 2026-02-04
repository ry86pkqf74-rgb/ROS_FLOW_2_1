#!/usr/bin/env python3

import sys
from pathlib import Path

# Add ros-backend/src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    print("Attempting to import enhanced_references...")
    from api.enhanced_references import router, ENHANCED_REFERENCES_AVAILABLE
    print(f'SUCCESS: Enhanced references loaded, available: {ENHANCED_REFERENCES_AVAILABLE}')
    
    print("Testing router endpoints...")
    print(f"Router has {len(router.routes)} routes")
    for route in router.routes:
        print(f"  - {route.methods} {route.path}")
        
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()