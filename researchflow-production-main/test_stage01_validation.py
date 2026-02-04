#!/usr/bin/env python3
"""
Simple validation script for Stage 1 Protocol Design Agent implementation.

Tests basic functionality without full dependencies.
"""

import os
import sys
import json
from pathlib import Path

# Add worker src to Python path
worker_src = Path(__file__).parent / "services" / "worker" / "src"
sys.path.insert(0, str(worker_src))

def test_config_feature_flag():
    """Test the feature flag configuration."""
    print("🔧 Testing feature flag configuration...")
    
    try:
        # Test feature flag disabled
        os.environ['ENABLE_NEW_STAGE_1'] = 'false'
        from config import get_config, reset_config
        reset_config()
        config = get_config()
        assert config.enable_new_stage_1 == False
        print("✅ Feature flag disabled works")
        
        # Test feature flag enabled  
        os.environ['ENABLE_NEW_STAGE_1'] = 'true'
        reset_config()
        config = get_config()
        assert config.enable_new_stage_1 == True
        print("✅ Feature flag enabled works")
        
        print("✅ Config feature flag test PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_pico_basic():
    """Test basic PICO functionality."""
    print("🧪 Testing PICO module basic functionality...")
    
    try:
        # Load PICO module code directly
        pico_file = worker_src / "agents" / "common" / "pico.py"
        with open(pico_file, 'r') as f:
            pico_code = f.read()
        
        # Create namespace and execute PICO code
        namespace = {}
        exec(pico_code, namespace)
        
        PICOElements = namespace['PICOElements']
        PICOValidator = namespace['PICOValidator']
        PICOExtractor = namespace['PICOExtractor']
        
        print("✅ PICO classes loaded successfully")
        
        # Test PICOElements creation
        pico = PICOElements(
            population="Adults aged 40-65 with Type 2 diabetes",
            intervention="Structured exercise program (150 min/week)",
            comparator="Standard diabetes care without exercise",
            outcomes=["HbA1c reduction", "Weight loss"],
            timeframe="12 months"
        )
        print("✅ PICOElements creation successful")
        
        # Test validation
        is_valid, errors = PICOValidator.validate(pico)
        assert is_valid == True, f"PICO should be valid, got errors: {errors}"
        print(f"✅ PICO validation: valid={is_valid}")
        
        # Test quality assessment
        quality = PICOValidator.assess_quality(pico)
        assert quality['score'] > 50, f"Quality score should be > 50, got {quality['score']}"
        print(f"✅ Quality assessment: score={quality['score']}, level={quality['quality_level']}")
        
        # Test search query generation
        search_query = PICOValidator.to_search_query(pico, use_boolean=True)
        assert "AND" in search_query, "Boolean search query should contain AND"
        assert pico.population in search_query, "Search query should contain population"
        print(f"✅ Search query: {search_query[:60]}...")
        
        # Test hypothesis generation - all three styles
        for style in ['null', 'alternative', 'comparative']:
            hypothesis = PICOValidator.to_hypothesis(pico, style=style)
            assert len(hypothesis) > 20, f"Hypothesis should be substantial, got: {hypothesis[:30]}"
            assert pico.population.split()[0].lower() in hypothesis.lower(), "Hypothesis should reference population"
            print(f"✅ {style.capitalize()} hypothesis generated")
        
        print("✅ PICO module test PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ PICO test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stage_registry():
    """Test the stage registry functionality."""
    print("📋 Testing stage registry...")
    
    try:
        # Set feature flag to legacy mode
        os.environ['ENABLE_NEW_STAGE_1'] = 'false'
        
        from workflow_engine.registry import list_stages, get_stage
        
        # Check that stages are registered
        stages = list_stages()
        assert len(stages) > 0, "Should have registered stages"
        print(f"✅ Found {len(stages)} registered stages")
        
        # Check Stage 1 specifically
        stage_1 = get_stage(1)
        assert stage_1 is not None, "Stage 1 should be registered"
        print(f"✅ Stage 1 registered: {stage_1.__name__}")
        
        # Verify it's the legacy stage when flag is disabled
        assert 'Upload' in stage_1.__name__ or 'Intake' in stage_1.__name__, \
            f"Should be legacy upload stage, got {stage_1.__name__}"
        print("✅ Legacy Stage 1 correctly selected with feature flag disabled")
        
        print("✅ Stage registry test PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ Stage registry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_structure():
    """Test that all expected files exist."""
    print("📁 Testing file structure...")
    
    try:
        expected_files = [
            "services/worker/src/agents/common/pico.py",
            "services/worker/src/agents/protocol_design/agent.py", 
            "services/worker/src/agents/protocol_design/__init__.py",
            "services/worker/src/workflow_engine/stages/stage_01_protocol_design.py",
            "tests/unit/agents/common/test_pico.py",
            "tests/unit/agents/protocol_design/test_agent.py",
            "tests/integration/test_pico_pipeline.py",
        ]
        
        missing_files = []
        for file_path in expected_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
            else:
                print(f"✅ {file_path}")
        
        if missing_files:
            print(f"❌ Missing files: {missing_files}")
            return False
        
        print("✅ File structure test PASSED\n")
        return True
        
    except Exception as e:
        print(f"❌ File structure test failed: {e}")
        return False

def main():
    """Run all validation tests."""
    print("🚀 Stage 1 Protocol Design Agent - Implementation Validation")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Config Feature Flag", test_config_feature_flag),
        ("PICO Module", test_pico_basic),
        ("Stage Registry", test_stage_registry),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test PASSED")
            else:
                failed += 1
                print(f"❌ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} test FAILED with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 VALIDATION SUMMARY:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📊 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Stage 1 implementation is ready for deployment.")
        return True
    else:
        print(f"\n⚠️  {failed} tests failed. Please review and fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)