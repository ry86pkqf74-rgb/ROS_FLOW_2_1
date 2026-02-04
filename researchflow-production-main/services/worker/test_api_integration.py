#!/usr/bin/env python3
"""
Quick Smoke Test for Enhanced References API Integration
Tests the unified API server with AI-enhanced endpoints
"""

import asyncio
import aiohttp
import json
import time
import sys
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000"

async def test_health_check():
    """Test basic health endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Health check passed")
                    print(f"   Service: {data.get('service')}")
                    mode_data = data.get('mode')
                    if isinstance(mode_data, dict):
                        print(f"   Mode: {mode_data.get('ros_mode')}")
                    else:
                        print(f"   Mode: {mode_data}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False

async def test_enhanced_references_health():
    """Test enhanced references health endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/api/references/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Enhanced References health check passed")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Available: {data.get('enhanced_references_available')}")
                    return True
                else:
                    print(f"❌ Enhanced References health failed: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}...")
                    return False
        except Exception as e:
            print(f"❌ Enhanced References health failed: {e}")
            return False

async def test_enhanced_references_capabilities():
    """Test enhanced references capabilities endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/api/references/capabilities") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Enhanced References capabilities check passed")
                    print(f"   Available: {data.get('enhanced_references_available')}")
                    if data.get('features'):
                        print("   Features:")
                        for feature, enabled in data['features'].items():
                            print(f"     - {feature}: {enabled}")
                    return True
                else:
                    print(f"❌ Enhanced References capabilities failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Enhanced References capabilities failed: {e}")
            return False

async def test_enhanced_references_processing():
    """Test enhanced references processing endpoint"""
    async with aiohttp.ClientSession() as session:
        try:
            test_payload = {
                "study_id": "smoke_test_001",
                "manuscript_text": "Recent studies show benefits of early intervention [citation needed]. Multiple trials have demonstrated efficacy [citation needed].",
                "enable_ai_processing": True,
                "enable_semantic_matching": True,
                "enable_gap_detection": True,
                "target_style": "ama"
            }
            
            async with session.post(
                f"{API_BASE_URL}/api/references/process", 
                json=test_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Enhanced References processing test passed")
                    print(f"   Processing mode: {data.get('processing_mode')}")
                    print(f"   Success: {data.get('success')}")
                    print(f"   Study ID: {data.get('study_id')}")
                    if data.get('processing_time_seconds'):
                        print(f"   Processing time: {data.get('processing_time_seconds'):.2f}s")
                    return True
                else:
                    print(f"❌ Enhanced References processing failed: {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:300]}...")
                    return False
        except Exception as e:
            print(f"❌ Enhanced References processing failed: {e}")
            return False

async def run_smoke_tests():
    """Run all smoke tests"""
    print("🔥 Starting Enhanced References API Smoke Test")
    print("=" * 60)
    
    start_time = time.time()
    
    tests = [
        ("Basic Health Check", test_health_check),
        ("Enhanced References Health", test_enhanced_references_health),
        ("Enhanced References Capabilities", test_enhanced_references_capabilities),
        ("Enhanced References Processing", test_enhanced_references_processing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = await test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    total_time = time.time() - start_time
    
    print("\n" + "=" * 60)
    print(f"🏁 Smoke Test Results: {passed}/{total} tests passed")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"📅 Timestamp: {datetime.utcnow().isoformat()}Z")
    
    if passed == total:
        print("🎉 All tests passed! API integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run_smoke_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Smoke test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Smoke test crashed: {e}")
        sys.exit(1)