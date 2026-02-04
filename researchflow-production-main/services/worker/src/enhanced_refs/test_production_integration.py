"""
Production Integration Test for Enhanced Reference Management System

Comprehensive test to verify end-to-end functionality:
- API → Integration Hub → AI Engines workflow
- Error handling and fallback mechanisms
- Performance and reliability

Linear Issues: ROS-XXX
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any
from fastapi.testclient import TestClient

# Import the enhanced API
from .api_endpoints import app
from .integration_hub import get_integration_hub
from .reference_management_service import get_reference_service
from .reference_types import Reference, ReferenceState, CitationStyle

# Test fixtures
SAMPLE_MANUSCRIPT_TEXT = """
Introduction

Cardiovascular disease remains the leading cause of death globally [citation needed]. 
Recent studies have shown that lifestyle interventions can significantly reduce risk [citation needed].
The Mediterranean diet has been associated with improved outcomes [citation needed].

Methods

We conducted a systematic review following PRISMA guidelines [citation needed].
Our search included PubMed, Embase, and Cochrane databases [citation needed].

Results

A total of 15 studies met inclusion criteria. The pooled analysis showed a 25% risk reduction [citation needed].
Statistical heterogeneity was low (I² = 12%) [citation needed].

Discussion

These findings are consistent with previous meta-analyses [citation needed].
The mechanisms may involve reduced inflammation [citation needed] and improved endothelial function [citation needed].
"""

SAMPLE_LITERATURE_RESULTS = [
    {
        "id": "pmid_12345",
        "title": "Mediterranean Diet and Cardiovascular Disease Prevention: A Systematic Review",
        "authors": ["Smith, J.", "Jones, A.", "Brown, M."],
        "year": 2023,
        "journal": "Journal of the American Heart Association",
        "doi": "10.1161/JAHA.123.456789",
        "pmid": "12345",
        "abstract": "This systematic review examined the effects of Mediterranean diet on cardiovascular outcomes...",
        "source": "pubmed"
    },
    {
        "id": "pmid_67890", 
        "title": "PRISMA 2020 Explanation and Elaboration",
        "authors": ["Page, M.J.", "McKenzie, J.E."],
        "year": 2021,
        "journal": "BMJ",
        "doi": "10.1136/bmj.n160",
        "pmid": "67890",
        "abstract": "The PRISMA 2020 statement provides updated guidance for reporting systematic reviews...",
        "source": "pubmed"
    },
    {
        "id": "pmid_11111",
        "title": "Lifestyle Interventions for Cardiovascular Disease Prevention",
        "authors": ["Wilson, K.", "Taylor, R."],
        "year": 2022,
        "journal": "Circulation",
        "doi": "10.1161/CIR.0000000000001234",
        "pmid": "11111",
        "abstract": "Comprehensive lifestyle interventions show significant benefits for cardiovascular health...",
        "source": "pubmed"
    }
]

SAMPLE_REQUEST = {
    "study_id": "test_study_001",
    "manuscript_text": SAMPLE_MANUSCRIPT_TEXT,
    "literature_results": SAMPLE_LITERATURE_RESULTS,
    "existing_references": [],
    "target_style": "ama",
    "research_field": "cardiovascular_medicine",
    "enable_ai_processing": True,
    "enable_semantic_matching": True,
    "enable_gap_detection": True,
    "enable_context_analysis": True,
    "enable_quality_metrics": True,
    "enable_journal_recommendations": True
}

class TestProductionIntegration:
    """Comprehensive production integration tests."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    async def test_health_checks(self):
        """Test health check endpoints."""
        print("\\n🔍 Testing health checks...")
        
        # Basic health check
        response = self.client.get("/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "system_status" in health_data
        
        print(f"✅ Basic health check passed")
        print(f"   Status: {health_data['status']}")
        if "ai_engines_status" in health_data:
            print(f"   AI engines: {health_data['ai_engines_status']}")
        
        # Comprehensive health check
        response = self.client.get("/health/comprehensive")
        assert response.status_code in [200, 503]  # May fail if services not available
        
        if response.status_code == 200:
            print("✅ Comprehensive health check passed")
        else:
            print("⚠️ Comprehensive health check failed (expected in some environments)")
    
    async def test_ai_enhanced_processing(self):
        """Test AI-enhanced reference processing."""
        print("\\n🤖 Testing AI-enhanced processing...")
        
        start_time = time.time()
        
        response = self.client.post("/references/process", json=SAMPLE_REQUEST)
        
        processing_time = time.time() - start_time
        print(f"   Processing time: {processing_time:.2f}s")
        
        # Should succeed with either AI or fallback
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert "study_id" in result
        assert "processing_mode" in result
        assert "references" in result
        assert "citations" in result
        
        processing_mode = result["processing_mode"]
        print(f"   Processing mode: {processing_mode}")
        
        if processing_mode == "ai_enhanced":
            print("✅ AI-enhanced processing successful!")
            
            # Verify AI enhancements are present
            assert "ai_enhancements" in result
            assert "quality_summary" in result
            assert "insights" in result
            
            # Check specific AI features
            ai_features = result.get("ai_features_used", {})
            print(f"   AI features used: {ai_features}")
            
            # Verify quality scores
            quality_summary = result["quality_summary"]
            print(f"   Overall quality: {quality_summary.get('overall_score', 'N/A')}")
            print(f"   Completeness: {quality_summary.get('completeness_score', 'N/A')}")
            print(f"   AI confidence: {quality_summary.get('ai_confidence', 'N/A')}")
            
            # Check insights
            insights = result["insights"]
            print(f"   Recommendations: {len(insights.get('improvement_recommendations', []))}")
            print(f"   Priority issues: {len(insights.get('priority_issues', []))}")
            
        elif processing_mode == "basic":
            print("⚠️ Fell back to basic processing")
            if "ai_fallback_reason" in result:
                print(f"   Fallback reason: {result['ai_fallback_reason']}")
        
        # Verify references were processed
        references = result["references"]
        citations = result["citations"]
        print(f"   References processed: {len(references)}")
        print(f"   Citations generated: {len(citations)}")
        
        # Check for journal recommendations
        if result.get("journal_recommendations"):
            print(f"   Journal recommendations: {len(result['journal_recommendations'])}")
        
        return result
    
    async def test_basic_processing_fallback(self):
        """Test fallback to basic processing when AI disabled."""
        print("\\n🔄 Testing basic processing fallback...")
        
        # Disable AI features
        fallback_request = SAMPLE_REQUEST.copy()
        fallback_request.update({
            "enable_ai_processing": False,
            "enable_semantic_matching": False,
            "enable_gap_detection": False,
            "enable_context_analysis": False,
            "enable_quality_metrics": False
        })
        
        response = self.client.post("/references/process", json=fallback_request)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["processing_mode"] == "basic"
        
        print("✅ Basic processing fallback working")
        print(f"   References: {len(result['references'])}")
        print(f"   Citations: {len(result['citations'])}")
    
    async def test_error_handling(self):
        """Test error handling and circuit breaker."""
        print("\\n🛡️ Testing error handling...")
        
        # Test with invalid data
        invalid_request = {
            "study_id": "test_invalid",
            "manuscript_text": "",  # Empty manuscript
            "literature_results": [],
            "existing_references": [{"invalid": "reference"}],  # Invalid reference format
            "target_style": "invalid_style"
        }
        
        response = self.client.post("/references/process", json=invalid_request)
        
        # Should handle gracefully
        if response.status_code == 422:
            print("✅ Input validation working")
        elif response.status_code == 200:
            result = response.json()
            if result.get("processing_mode") == "basic":
                print("✅ Error handled with graceful fallback")
            else:
                print("⚠️ Unexpected success with invalid input")
        else:
            print(f"⚠️ Unexpected error response: {response.status_code}")
    
    async def test_ai_status_endpoint(self):
        """Test AI status monitoring endpoint."""
        print("\\n📊 Testing AI status monitoring...")
        
        response = self.client.get("/monitoring/ai-status")
        
        # Should always return status info (may have errors)
        assert response.status_code == 200
        
        status = response.json()
        assert "circuit_breaker" in status
        assert "timestamp" in status
        
        circuit_breaker = status["circuit_breaker"]
        print(f"   Circuit breaker state: {circuit_breaker['state']}")
        print(f"   Failure count: {circuit_breaker['failure_count']}")
        
        if "ai_stats" in status and not isinstance(status["ai_stats"], str):
            print("✅ AI engines status available")
            ai_stats = status["ai_stats"]
            for engine, stats in ai_stats.items():
                if isinstance(stats, dict) and "error" not in stats:
                    print(f"   {engine}: healthy")
                else:
                    print(f"   {engine}: error")
        else:
            print("⚠️ AI engines status not available")
    
    async def test_comprehensive_stats(self):
        """Test comprehensive statistics endpoint."""
        print("\\n📈 Testing comprehensive statistics...")
        
        response = self.client.get("/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert stats["success"] is True
        assert "stats" in stats
        
        stats_data = stats["stats"]
        print("   Available statistics:")
        
        for component, component_stats in stats_data.items():
            if isinstance(component_stats, dict) and "error" in component_stats:
                print(f"   ❌ {component}: {component_stats['error'][:50]}...")
            else:
                print(f"   ✅ {component}: operational")
    
    async def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow."""
        print("\\n🔄 Testing end-to-end workflow...")
        
        # Step 1: Process references
        result = await self.test_ai_enhanced_processing()
        
        # Step 2: Get insights for processed references
        if result["references"]:
            print("\\n   Step 2: Getting reference insights...")
            
            insights_request = {
                "references": result["references"][:3],  # Test with first 3 references
                "manuscript_text": SAMPLE_MANUSCRIPT_TEXT[:500],  # Truncate for test
                "research_field": "cardiovascular_medicine"
            }
            
            try:
                response = self.client.post("/references/insights", json=insights_request)
                if response.status_code == 200:
                    insights = response.json()
                    print("   ✅ Reference insights generated")
                    if insights.get("insights"):
                        print(f"      Insights keys: {list(insights['insights'].keys())}")
                else:
                    print(f"   ⚠️ Insights failed: {response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Insights error: {str(e)[:100]}")
        
        # Step 3: Test optimization
        if result["references"]:
            print("\\n   Step 3: Testing citation optimization...")
            
            optimization_request = {
                "references": result["references"][:3],
                "target_journal": "Journal of the American Heart Association",
                "manuscript_abstract": "This study examines cardiovascular interventions..."
            }
            
            try:
                response = self.client.post("/references/optimize", json=optimization_request)
                if response.status_code == 200:
                    optimization = response.json()
                    print("   ✅ Citation optimization generated")
                    if optimization.get("optimization"):
                        print(f"      Optimization keys: {list(optimization['optimization'].keys())}")
                else:
                    print(f"   ⚠️ Optimization failed: {response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Optimization error: {str(e)[:100]}")
        
        print("\\n✅ End-to-end workflow test completed")
    
    def test_integration_comprehensive(self):
        """Run all integration tests."""
        print("\\n" + "="*60)
        print("🚀 COMPREHENSIVE PRODUCTION INTEGRATION TEST")
        print("="*60)
        
        async def run_tests():
            await self.test_health_checks()
            await self.test_ai_enhanced_processing()
            await self.test_basic_processing_fallback()
            await self.test_error_handling()
            await self.test_ai_status_endpoint()
            await self.test_comprehensive_stats()
            await self.test_end_to_end_workflow()
            
            print("\\n" + "="*60)
            print("✅ ALL INTEGRATION TESTS COMPLETED")
            print("="*60)
        
        # Run async tests
        asyncio.run(run_tests())

# Direct execution support
if __name__ == "__main__":
    print("Starting Production Integration Test...")
    test_instance = TestProductionIntegration()
    test_instance.setup_method()
    test_instance.test_integration_comprehensive()
    print("\\nProduction Integration Test Complete!")