#!/usr/bin/env python3
"""
Complete Stage 2 Flow Test

Tests the complete end-to-end flow:
1. TypeScript orchestrator endpoint
2. BullMQ job dispatch
3. Python worker stage execution
4. Job status polling

This validates the complete integration between services.
"""

import requests
import json
import time
import uuid
import asyncio
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
ORCHESTRATOR_BASE_URL = "http://localhost:3001"
WORKER_BASE_URL = "http://localhost:8000"
TEST_WORKFLOW_ID = str(uuid.uuid4())
TEST_RESEARCH_QUESTION = "What are the cardiovascular effects of intermittent fasting in adults with metabolic syndrome?"

# Auth headers
TEST_HEADERS = {
    "Content-Type": "application/json",
    "X-Dev-User-Id": "test-user-001",  # Development auth
    "Authorization": "Bearer test-jwt-token"
}

def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_result(test_name: str, success: bool, details: str = "", response: Dict = None):
    """Print formatted test results."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   Details: {details}")
    if response and not success:
        print(f"   Response: {json.dumps(response, indent=2)}")
    print()

async def test_services_health():
    """Test that both services are running."""
    print_section("HEALTH CHECKS")
    
    # Test orchestrator
    try:
        response = requests.get(f"{ORCHESTRATOR_BASE_URL}/health", timeout=10)
        orch_healthy = response.status_code == 200
        orch_data = response.json() if orch_healthy else {}
        print_result(
            "Orchestrator Health", 
            orch_healthy, 
            f"Status: {orch_data.get('status', 'unknown')}, Mode: {orch_data.get('governanceMode', 'unknown')}"
        )
    except Exception as e:
        print_result("Orchestrator Health", False, f"Connection failed: {str(e)}")
        return False
    
    # Test worker
    try:
        response = requests.get(f"{WORKER_BASE_URL}/health", timeout=10)
        worker_healthy = response.status_code == 200
        worker_data = response.json() if worker_healthy else {}
        print_result(
            "Worker Health", 
            worker_healthy, 
            f"Status: {worker_data.get('status', 'unknown')}, Service: {worker_data.get('service', 'unknown')}"
        )
    except Exception as e:
        print_result("Worker Health", False, f"Connection failed: {str(e)}")
        return False
    
    return orch_healthy and worker_healthy

async def test_stage_2_direct():
    """Test calling Stage 2 directly on the worker."""
    print_section("DIRECT WORKER TEST")
    
    payload = {
        "workflow_id": TEST_WORKFLOW_ID,
        "research_question": TEST_RESEARCH_QUESTION,
        "user_id": "test-user-001",
        "job_id": str(uuid.uuid4())
    }
    
    try:
        response = requests.post(
            f"{WORKER_BASE_URL}/api/workflow/stages/2/execute",
            json=payload,
            headers=TEST_HEADERS,
            timeout=60  # Stage execution can take time
        )
        
        success = response.status_code == 200
        data = response.json() if success else {}
        
        if success:
            print_result(
                "Direct Stage 2 Execution", 
                True, 
                f"Success: {data.get('success')}, Duration: {data.get('duration_ms')}ms, Artifacts: {len(data.get('artifacts', []))}"
            )
            return data
        else:
            print_result("Direct Stage 2 Execution", False, f"HTTP {response.status_code}", data)
            return None
            
    except Exception as e:
        print_result("Direct Stage 2 Execution", False, f"Request failed: {str(e)}")
        return None

async def test_orchestrator_dispatch():
    """Test the orchestrator job dispatch."""
    print_section("ORCHESTRATOR JOB DISPATCH")
    
    payload = {
        "workflow_id": TEST_WORKFLOW_ID,
        "research_question": TEST_RESEARCH_QUESTION
    }
    
    try:
        response = requests.post(
            f"{ORCHESTRATOR_BASE_URL}/api/workflow/stages/2/execute",
            json=payload,
            headers=TEST_HEADERS,
            timeout=15
        )
        
        success = response.status_code == 202  # Should return 202 Accepted
        data = response.json() if success else {}
        
        if success:
            job_id = data.get('job_id')
            print_result(
                "Job Dispatch", 
                True, 
                f"Job ID: {job_id}, Status: {data.get('status')}, Stage: {data.get('stage')}"
            )
            return job_id
        else:
            print_result("Job Dispatch", False, f"HTTP {response.status_code}", data)
            return None
            
    except Exception as e:
        print_result("Job Dispatch", False, f"Request failed: {str(e)}")
        return None

async def test_job_status_polling(job_id: str, max_wait: int = 120):
    """Test job status polling with timeout."""
    print_section("JOB STATUS POLLING")
    
    if not job_id:
        print_result("Job Status Polling", False, "No job ID provided")
        return False
    
    start_time = time.time()
    last_status = ""
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{ORCHESTRATOR_BASE_URL}/api/workflow/stages/2/jobs/{job_id}/status",
                headers=TEST_HEADERS,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                progress = data.get('progress', 0)
                
                # Log status changes
                if status != last_status:
                    print(f"   Status Update: {status} (Progress: {progress}%)")
                    last_status = status
                
                if status == 'completed':
                    result = data.get('result', {})
                    print_result(
                        "Job Completion", 
                        True, 
                        f"Completed in {time.time() - start_time:.1f}s, Success: {result.get('success')}"
                    )
                    return True
                elif status == 'failed':
                    error = data.get('error', 'Unknown error')
                    print_result("Job Completion", False, f"Job failed: {error}")
                    return False
                
                # Wait before next poll
                await asyncio.sleep(2)
                
            else:
                print_result("Status Polling", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print_result("Status Polling", False, f"Request failed: {str(e)}")
            return False
    
    # Timeout
    print_result("Job Completion", False, f"Timeout after {max_wait}s")
    return False

async def test_validation_scenarios():
    """Test input validation scenarios."""
    print_section("VALIDATION TESTS")
    
    test_cases = [
        {
            "name": "Missing workflow_id",
            "payload": {"research_question": TEST_RESEARCH_QUESTION},
            "expected_status": 400
        },
        {
            "name": "Invalid workflow_id format",
            "payload": {"workflow_id": "invalid-uuid", "research_question": TEST_RESEARCH_QUESTION},
            "expected_status": 400
        },
        {
            "name": "Missing research_question",
            "payload": {"workflow_id": TEST_WORKFLOW_ID},
            "expected_status": 400
        },
        {
            "name": "Short research_question",
            "payload": {"workflow_id": TEST_WORKFLOW_ID, "research_question": "short"},
            "expected_status": 400
        }
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        try:
            response = requests.post(
                f"{ORCHESTRATOR_BASE_URL}/api/workflow/stages/2/execute",
                json=test_case["payload"],
                headers=TEST_HEADERS,
                timeout=10
            )
            
            success = response.status_code == test_case["expected_status"]
            print_result(
                f"Validation: {test_case['name']}",
                success,
                f"Expected {test_case['expected_status']}, got {response.status_code}"
            )
            
            if not success:
                all_passed = False
                
        except Exception as e:
            print_result(f"Validation: {test_case['name']}", False, f"Request failed: {str(e)}")
            all_passed = False
    
    return all_passed

async def main():
    """Run the complete test suite."""
    print("🧪 COMPLETE STAGE 2 FLOW INTEGRATION TEST")
    print("="*60)
    print(f"Testing workflow: {TEST_WORKFLOW_ID}")
    print(f"Research question: {TEST_RESEARCH_QUESTION}")
    print()
    
    # Step 1: Health checks
    if not await test_services_health():
        print("\n❌ Services not healthy. Please start the services and try again.")
        return False
    
    # Step 2: Test direct worker call (bypassing orchestrator)
    direct_result = await test_stage_2_direct()
    direct_success = direct_result is not None
    
    # Step 3: Test validation scenarios
    validation_success = await test_validation_scenarios()
    
    # Step 4: Test orchestrator dispatch and polling
    job_id = await test_orchestrator_dispatch()
    polling_success = False
    if job_id:
        polling_success = await test_job_status_polling(job_id)
    
    # Final summary
    print_section("FINAL SUMMARY")
    
    tests = [
        ("Service Health Checks", True),  # Already passed if we got here
        ("Direct Worker Execution", direct_success),
        ("Input Validation", validation_success),
        ("Orchestrator Job Dispatch", job_id is not None),
        ("Job Status Polling", polling_success)
    ]
    
    passed_count = sum(1 for _, passed in tests if passed)
    total_count = len(tests)
    
    for test_name, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print()
    print(f"Results: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED! Complete Stage 2 flow is working.")
        return True
    else:
        print("⚠️  Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)