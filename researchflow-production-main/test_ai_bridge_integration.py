#!/usr/bin/env python3
"""
AI Bridge Integration Test

Tests the integration between Python AI Router Bridge and TypeScript orchestrator.
This validates the complete IRB Agent → AI Bridge → AI Router flow.

Usage: python test_ai_bridge_integration.py
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
ORCHESTRATOR_URL = "http://localhost:3001"
TEST_USER_HEADER = {"X-Dev-User-Id": "test-user-123"}  # For dev auth

class AIBridgeIntegrationTest:
    def __init__(self):
        self.base_url = ORCHESTRATOR_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        self.passed_tests = 0
        self.total_tests = 0

    async def run_all_tests(self):
        """Run all integration tests"""
        print("🔄 Starting AI Bridge Integration Tests...")
        print("=" * 50)
        
        try:
            await self.test_health_check()
            await self.test_capabilities()
            await self.test_invoke()
            await self.test_batch()
            await self.test_streaming()
        except Exception as e:
            print(f"❌ Test suite failed with error: {e}")
            return False
        finally:
            await self.client.aclose()
        
        print("\n" + "=" * 50)
        print(f"✅ Integration Tests Complete: {self.passed_tests}/{self.total_tests} passed")
        
        if self.passed_tests == self.total_tests:
            print("🎉 All tests passed! AI Bridge integration is working!")
            return True
        else:
            print("⚠️  Some tests failed. Check the output above.")
            return False

    async def test_health_check(self):
        """Test bridge health endpoint"""
        self.total_tests += 1
        print("🔍 Testing bridge health check...")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/ai-bridge/health",
                headers=TEST_USER_HEADER
            )
            
            if response.status_code == 200:
                data = response.json()
                assert data["bridge"]["healthy"] is True
                assert "aiRouter" in data["dependencies"]
                print("   ✅ Health check passed")
                self.passed_tests += 1
            else:
                print(f"   ❌ Health check failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Health check error: {e}")

    async def test_capabilities(self):
        """Test bridge capabilities endpoint"""
        self.total_tests += 1
        print("🔍 Testing bridge capabilities...")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/ai-bridge/capabilities",
                headers=TEST_USER_HEADER
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "endpoints" in data
                assert "features" in data
                assert "ECONOMY" in data["features"]["modelTiers"]
                print("   ✅ Capabilities check passed")
                self.passed_tests += 1
            else:
                print(f"   ❌ Capabilities check failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Capabilities error: {e}")

    async def test_invoke(self):
        """Test single LLM invocation"""
        self.total_tests += 1
        print("🔍 Testing LLM invoke...")
        
        request_payload = {
            "prompt": "Test prompt for IRB agent integration.",
            "options": {
                "taskType": "phi_redaction",
                "stageId": 5,
                "modelTier": "STANDARD",
                "governanceMode": "DEMO",
                "requirePhiCompliance": True
            },
            "metadata": {
                "agentId": "irb-agent-test",
                "projectId": "test-project",
                "runId": "test-run-001",
                "threadId": "test-thread",
                "stageRange": [1, 20],
                "currentStage": 5
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/ai-bridge/invoke",
                headers=TEST_USER_HEADER,
                json=request_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "content" in data
                assert "usage" in data
                assert "cost" in data
                assert "model" in data
                assert "tier" in data
                print(f"   ✅ Invoke successful - Model: {data['model']}, Tier: {data['tier']}")
                print(f"   💰 Cost: ${data['cost']['total']:.4f}")
                self.passed_tests += 1
            else:
                print(f"   ❌ Invoke failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Invoke error: {e}")

    async def test_batch(self):
        """Test batch LLM processing"""
        self.total_tests += 1
        print("🔍 Testing batch processing...")
        
        request_payload = {
            "prompts": [
                "Analyze this clinical data for PHI.",
                "Summarize the research findings.",
                "Generate compliance recommendations."
            ],
            "options": {
                "taskType": "summarization",
                "modelTier": "ECONOMY",
                "governanceMode": "DEMO"
            },
            "metadata": {
                "agentId": "batch-test-agent",
                "projectId": "test-project",
                "runId": "batch-test-001",
                "threadId": "batch-thread",
                "stageRange": [10, 15],
                "currentStage": 12
            }
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/ai-bridge/batch",
                headers=TEST_USER_HEADER,
                json=request_payload
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "responses" in data
                assert len(data["responses"]) == 3
                assert "totalCost" in data
                assert "successCount" in data
                print(f"   ✅ Batch successful - {data['successCount']}/{len(data['responses'])} succeeded")
                print(f"   💰 Total cost: ${data['totalCost']:.4f}")
                self.passed_tests += 1
            else:
                print(f"   ❌ Batch failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Batch error: {e}")

    async def test_streaming(self):
        """Test streaming LLM responses"""
        self.total_tests += 1
        print("🔍 Testing streaming...")
        
        request_payload = {
            "prompt": "Generate a detailed analysis of research ethics compliance.",
            "options": {
                "taskType": "ethical_review",
                "modelTier": "PREMIUM",
                "governanceMode": "LIVE"
            },
            "metadata": {
                "agentId": "streaming-test-agent",
                "projectId": "test-project",
                "runId": "stream-test-001",
                "threadId": "stream-thread",
                "stageRange": [15, 20],
                "currentStage": 17
            }
        }
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/ai-bridge/stream",
                headers=TEST_USER_HEADER,
                json=request_payload
            ) as response:
                
                if response.status_code == 200:
                    chunks_received = 0
                    content_chunks = 0
                    
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            chunks_received += 1
                            if 'data: ' in chunk and '"type":"content"' in chunk:
                                content_chunks += 1
                    
                    if chunks_received > 0 and content_chunks > 0:
                        print(f"   ✅ Streaming successful - {chunks_received} chunks, {content_chunks} content chunks")
                        self.passed_tests += 1
                    else:
                        print(f"   ❌ Streaming incomplete - {chunks_received} chunks, {content_chunks} content")
                else:
                    print(f"   ❌ Streaming failed: {response.status_code}")
                    
        except Exception as e:
            print(f"   ❌ Streaming error: {e}")

    async def simulate_irb_agent_flow(self):
        """Simulate a realistic IRB agent workflow"""
        print("\n🤖 Simulating IRB Agent Workflow...")
        print("-" * 30)
        
        # Step 1: PHI Scan
        print("Step 1: PHI Detection...")
        phi_request = {
            "prompt": "Review this text for PHI: 'Patient John Doe (DOB: 1/1/1980) was treated at City Hospital.'",
            "options": {
                "taskType": "phi_redaction",
                "modelTier": "PREMIUM",
                "governanceMode": "LIVE",
                "requirePhiCompliance": True
            },
            "metadata": {
                "agentId": "irb-agent-phi",
                "projectId": "irb-review-001",
                "runId": "phi-scan-001",
                "threadId": "irb-thread-001",
                "stageRange": [1, 20],
                "currentStage": 4
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/ai-bridge/invoke",
            headers=TEST_USER_HEADER,
            json=phi_request
        )
        
        if response.status_code == 200:
            print("   ✅ PHI scan completed")
        else:
            print("   ❌ PHI scan failed")
        
        # Step 2: Risk Assessment
        print("Step 2: Risk Assessment...")
        risk_request = {
            "prompt": "Assess the risk level of this research study involving human subjects.",
            "options": {
                "taskType": "ethical_review",
                "modelTier": "STANDARD",
                "governanceMode": "LIVE"
            },
            "metadata": {
                "agentId": "irb-agent-risk",
                "projectId": "irb-review-001",
                "runId": "risk-assessment-001",
                "threadId": "irb-thread-001",
                "stageRange": [1, 20],
                "currentStage": 8
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/ai-bridge/invoke",
            headers=TEST_USER_HEADER,
            json=risk_request
        )
        
        if response.status_code == 200:
            print("   ✅ Risk assessment completed")
        else:
            print("   ❌ Risk assessment failed")
        
        # Step 3: Compliance Check
        print("Step 3: Compliance Verification...")
        compliance_request = {
            "prompt": "Verify compliance with IRB requirements and federal regulations.",
            "options": {
                "taskType": "claim_verification",
                "modelTier": "PREMIUM",
                "governanceMode": "LIVE"
            },
            "metadata": {
                "agentId": "irb-agent-compliance",
                "projectId": "irb-review-001",
                "runId": "compliance-check-001",
                "threadId": "irb-thread-001",
                "stageRange": [1, 20],
                "currentStage": 15
            }
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/ai-bridge/invoke",
            headers=TEST_USER_HEADER,
            json=compliance_request
        )
        
        if response.status_code == 200:
            print("   ✅ Compliance check completed")
        else:
            print("   ❌ Compliance check failed")
        
        print("🎉 IRB Agent workflow simulation completed!")

async def main():
    """Main test runner"""
    tester = AIBridgeIntegrationTest()
    
    # Run basic integration tests
    success = await tester.run_all_tests()
    
    if success:
        # Run IRB agent simulation
        await tester.simulate_irb_agent_flow()
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        exit(1)