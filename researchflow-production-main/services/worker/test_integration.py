"""
Standalone Integration Test Runner

Runs production integration tests for the Enhanced Reference Management System.
"""

import sys
import os
from pathlib import Path

# Add the src path to sys.path for imports
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

# Now we can import the test modules
from agents.writing.test_production_integration import TestProductionIntegration

if __name__ == "__main__":
    print("🚀 Starting Production Integration Test...")
    
    test_instance = TestProductionIntegration()
    test_instance.setup_method()
    
    try:
        test_instance.test_integration_comprehensive()
        print("\\n✅ Integration tests completed successfully!")
    except Exception as e:
        print(f"\\n❌ Integration tests failed: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)