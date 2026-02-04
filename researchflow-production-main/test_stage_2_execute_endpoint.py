#!/usr/bin/env python3
"""
Stage 2 Execute Endpoint Integration Test

Tests the newly implemented POST /api/workflow/stages/2/execute endpoint
and the BullMQ job status polling functionality.

Usage: python test_stage_2_execute_endpoint.py
"""

import requests
import json
import time
import uuid
from typing import Dict, Any
import sys

# Test configuration
ORCHESTRATOR_BASE_URL = "http://localhost:3001"
TEST_WORKFLOW_ID = str(uuid.uuid4())
TEST_RESEARCH_QUESTION = "What are the cardiovascular effects of intermittent fasting in adults with metabolic syndrome?"

# Test headers - use dev auth for testing
TEST_HEADERS = {
    "Content-Type": "application/json",
    "X-Dev-User-Id": "test-user-001",  # Development auth header
    "Authorization": "Bearer test-jwt-token"  # Mock JWT for testing
}

def print_test_result(test_name: str, success: bool, details: str = ""):
    """Print formatted test results"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   Details: {details}")
    print()

def test_health_check():
    """Test that orchestrator is running"""
    print("🏥 Testing Orchestrator Health Check...")
    try:
        response = requests.get(f"{ORCHESTRATOR_BASE_URL}/health", timeout=10)
        success = response.status_code == 200
        
        if success:
            data = response.json()
            print_test_result(
                "Health Check", 
                success, 
                f"Status: {data.get('status', 'unknown')}, Environment: {data.get('environment', 'unknown')}"
            )
        else:
            print_test_result("Health Check", False, f"HTTP {response.status_code}")
        
        return success
    except Exception as e:
        print_test_result("Health Check", False, f"Connection failed: {str(e)}")
        return False

def test_stage_2_execute():
    """Test Stage 2 execute endpoint"""
    print("🔬 Testing Stage 2 Execute Endpoint...")
    
    try:
        payload = {
            "workflow_id": TEST_WORKFLOW_ID,
            "research_question": TEST_RESEARCH_QUESTION
        }
        
        response = requests.post(
            f"{ORCHESTRATOR_BASE_URL}/api/workflow/stages/2/execute",
            json=payload,
            headers=TEST_HEADERS,
            timeout=15
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 202:
            data = response.json()
            required_fields = ["success", "job_id", "stage", "workflow_id", "status"]
            has_all_fields = all(field in data for field in required_fields)
            
            if has_all_fields and data["stage"] == 2:
                print_test_result(
                    "Stage 2 Execute Request",
                    True,
                    f"Job ID: {data['job_id']}, Status: {data['status']}"
                )
                return data["job_id"]
            else:
                print_test_result(
                    "Stage 2 Execute Request",
                    False,
                    f"Missing required fields or incorrect stage. Got: {list(data.keys())}"
                )
                return None
        else:
            print_test_result(
                "Stage 2 Execute Request",
                False,
                f"Expected HTTP 202, got {response.status_code}: {response.text}"
            )
            return None
            
    except Exception as e:
        print_test_result("Stage 2 Execute Request", False, f"Request failed: {str(e)}")
        return None

def test_job_status_polling(job_id: str):
    """Test job status polling endpoint"""
    print("📊 Testing Job Status Polling...")
    
    try:
        response = requests.get(
            f"{ORCHESTRATOR_BASE_URL}/api/workflow/stages/2/jobs/{job_id}/status",
            headers=TEST_HEADERS,
            timeout=10
        )
        
        print(f"Status Polling Response: {response.status_code}")
        print(f"Status Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["job_id", "stage", "status"]
            has_required = all(field in data for field in required_fields)
            
            if has_required and data["job_id"] == job_id:
                print_test_result(
                    "Job Status Polling",
                    True,
                    f"Job {job_id} status: {data.get('status', 'unknown')}"
                )
                return True
            else:
                print_test_result(
                    "Job Status Polling",
                    False,
                    f"Invalid response structure or job ID mismatch"
                )
                return False
        else:
            print_test_result(
                "Job Status Polling",
                False,
                f"Expected HTTP 200, got {response.status_code}: {response.text}"
            )
            return False
            
    except Exception as e:
        print_test_result("Job Status Polling", False, f"Request failed: {str(e)}")
        return False

def test_input_validation():
    """Test input validation on Stage 2 execute endpoint"""
    print("🛡️ Testing Input Validation...")
    
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
            print_test_result(
                f"Validation: {test_case['name']}",
                success,
                f"Expected {test_case['expected_status']}, got {response.status_code}"
            )
            
            if not success:
                all_passed = False
                
        except Exception as e:
            print_test_result(f"Validation: {test_case['name']}", False, f"Request failed: {str(e)}")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("🧪 STAGE 2 EXECUTE ENDPOINT INTEGRATION TESTS")
    print("=" * 50)
    print()
    
    # Step 1: Health check
    if not test_health_check():
        print("❌ Orchestrator is not running. Please start the services and try again.")
        sys.exit(1)
    
    # Step 2: Test input validation
    validation_passed = test_input_validation()
    
    # Step 3: Test successful execution
    job_id = test_stage_2_execute()
    
    # Step 4: Test job status polling (if we got a job ID)
    status_polling_passed = False
    if job_id:
        status_polling_passed = test_job_status_polling(job_id)
    
    # Summary
    print("📋 TEST SUMMARY")
    print("=" * 30)
    
    tests = [
        ("Health Check", True),  # Already passed if we got this far
        ("Input Validation", validation_passed),
        ("Stage 2 Execute", job_id is not None),
        ("Job Status Polling", status_polling_passed)
    ]
    
    passed_count = sum(1 for _, passed in tests if passed)
    total_count = len(tests)
    
    for test_name, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print()
    print(f"Results: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED! Stage 2 execute endpoint is working correctly.")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()