"""
Integration Tests for Citation Network Analysis System

Tests the complete citation analysis pipeline including:
- API endpoints integration
- Performance monitoring integration
- Database interactions
- End-to-end workflows
- Error handling and recovery

Author: Integration Test Team
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Any
from unittest.mock import Mock, patch
import httpx
from fastapi.testclient import TestClient

# Import the system components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/worker/src'))

from api.citation_analysis_api import app
from analysis.citation_network_analyzer import CitationNetworkAnalyzer
from monitoring.performance_dashboard import get_performance_monitor

class TestCitationAnalysisIntegration:
    """Integration tests for citation analysis system."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_literature_dataset(self):
        """Sample literature dataset for testing."""
        return [
            {
                "id": "paper_ai_healthcare_2023",
                "title": "Artificial Intelligence in Healthcare: A Comprehensive Review",
                "authors": ["Dr. Sarah Johnson", "Prof. Michael Chen", "Dr. Lisa Wang"],
                "year": 2023,
                "journal": "Nature Medicine",
                "doi": "10.1038/s41591-023-01234-5",
                "keywords": ["artificial intelligence", "healthcare", "machine learning", "medical diagnosis", "clinical decision support"],
                "abstract": "This comprehensive review examines the current state and future prospects of artificial intelligence applications in healthcare, covering diagnostic imaging, treatment planning, drug discovery, and patient monitoring systems.",
                "citation_count": 127,
                "citations": ["paper_ml_diagnosis_2022", "paper_clinical_ai_2021", "paper_drug_discovery_2020"]
            },
            {
                "id": "paper_ml_diagnosis_2022",
                "title": "Machine Learning for Medical Diagnosis: Advances and Challenges",
                "authors": ["Dr. Robert Kim", "Dr. Amanda Rodriguez"],
                "year": 2022,
                "journal": "Journal of Medical Internet Research",
                "doi": "10.2196/28567",
                "keywords": ["machine learning", "medical diagnosis", "deep learning", "computer vision", "medical imaging"],
                "abstract": "An analysis of machine learning techniques applied to medical diagnosis, highlighting recent advances in deep learning and computer vision for medical imaging applications.",
                "citation_count": 89,
                "citations": ["paper_deep_learning_medical_2021", "paper_computer_vision_2020"]
            },
            {
                "id": "paper_clinical_ai_2021",
                "title": "Clinical Decision Support Systems: AI Implementation Strategies",
                "authors": ["Prof. David Thompson", "Dr. Jennifer Martinez"],
                "year": 2021,
                "journal": "Journal of the American Medical Informatics Association",
                "doi": "10.1093/jamia/ocab123",
                "keywords": ["clinical decision support", "artificial intelligence", "electronic health records", "healthcare informatics"],
                "abstract": "This paper presents strategies for implementing AI-powered clinical decision support systems in healthcare environments, addressing integration challenges and workflow optimization.",
                "citation_count": 76,
                "citations": ["paper_ehr_integration_2020", "paper_workflow_optimization_2019"]
            },
            {
                "id": "paper_drug_discovery_2020",
                "title": "AI-Driven Drug Discovery: From Molecules to Medicine",
                "authors": ["Dr. Carlos Mendez", "Dr. Priya Sharma", "Prof. James Wilson"],
                "year": 2020,
                "journal": "Nature Biotechnology",
                "doi": "10.1038/s41587-020-01234-x",
                "keywords": ["drug discovery", "artificial intelligence", "molecular design", "pharmaceutical research", "computational biology"],
                "abstract": "Exploration of AI applications in drug discovery pipelines, from initial molecular design to clinical trial optimization, demonstrating significant improvements in discovery timelines.",
                "citation_count": 156,
                "citations": ["paper_molecular_ai_2019", "paper_clinical_trials_2018"]
            },
            {
                "id": "paper_deep_learning_medical_2021",
                "title": "Deep Learning Applications in Medical Imaging: A Systematic Review",
                "authors": ["Dr. Emily Chang", "Prof. Alex Petrov"],
                "year": 2021,
                "journal": "Medical Image Analysis",
                "doi": "10.1016/j.media.2021.12345",
                "keywords": ["deep learning", "medical imaging", "convolutional neural networks", "radiology", "pathology"],
                "abstract": "Systematic review of deep learning applications in medical imaging, covering radiology, pathology, and dermatology applications with performance analysis.",
                "citation_count": 98,
                "citations": ["paper_cnn_medical_2020", "paper_radiology_ai_2019"]
            },
            {
                "id": "paper_computer_vision_2020",
                "title": "Computer Vision in Healthcare: Current Applications and Future Directions",
                "authors": ["Dr. Mohammed Al-Hassan", "Dr. Rachel Green"],
                "year": 2020,
                "journal": "IEEE Transactions on Medical Imaging",
                "doi": "10.1109/TMI.2020.1234567",
                "keywords": ["computer vision", "healthcare", "medical imaging", "object detection", "image segmentation"],
                "abstract": "Overview of computer vision applications in healthcare settings, including medical imaging analysis, surgical guidance, and patient monitoring systems.",
                "citation_count": 112,
                "citations": ["paper_image_segmentation_2019", "paper_surgical_guidance_2018"]
            }
        ]
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "features" in data
        
        features = data["features"]
        assert features["network_construction"] is True
        assert features["centrality_analysis"] is True
        assert features["community_detection"] is True
    
    def test_build_network_endpoint(self, client, sample_literature_dataset):
        """Test network building endpoint."""
        request_data = {
            "papers": sample_literature_dataset,
            "config": {"min_citations": 1}
        }
        
        response = client.post("/api/v1/network/build", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "network_summary" in data
        assert "build_timestamp" in data
        
        # Validate network was built
        summary = data["network_summary"]
        assert summary["status"] == "active"
        assert summary["node_count"] == 6
        assert summary["edge_count"] > 0
    
    def test_network_statistics_endpoint(self, client, sample_literature_dataset):
        """Test network statistics endpoint."""
        # First build network
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Get statistics
        response = client.get("/api/v1/network/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["node_count"] == 6
        assert data["edge_count"] > 0
        assert 0 <= data["density"] <= 1
        assert "most_cited_paper" in data
        assert "year_range" in data
        assert "analysis_timestamp" in data
    
    def test_full_analysis_endpoint(self, client, sample_literature_dataset):
        """Test comprehensive analysis endpoint."""
        # Build network first
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Request analysis
        analysis_request = {
            "include_communities": True,
            "include_gaps": True,
            "include_trends": True,
            "max_results": 10,
            "cache_results": True
        }
        
        response = client.post("/api/v1/network/analyze", json=analysis_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate response structure
        assert "network_stats" in data
        assert "centrality_analysis" in data
        assert "community_analysis" in data
        assert "research_gaps" in data
        assert "emerging_topics" in data
        assert "visualization_data" in data
        assert "analysis_metadata" in data
        
        # Validate centrality analysis
        centrality = data["centrality_analysis"]
        assert "top_betweenness_centrality" in centrality
        assert "top_pagerank_scores" in centrality
        assert "top_cited_papers" in centrality
        assert len(centrality["top_cited_papers"]) <= 10
        
        # Validate community analysis
        communities = data["community_analysis"]
        assert "communities" in communities
        assert "modularity" in communities
        assert communities["community_count"] > 0
        
        # Validate visualization data
        viz_data = data["visualization_data"]
        assert "nodes" in viz_data
        assert "edges" in viz_data
        assert "metadata" in viz_data
        assert len(viz_data["nodes"]) == 6
    
    def test_communities_endpoint(self, client, sample_literature_dataset):
        """Test community detection endpoint."""
        # Build network
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Get communities
        response = client.get("/api/v1/network/communities")
        assert response.status_code == 200
        
        data = response.json()
        assert "communities" in data
        assert "modularity" in data
        assert "community_count" in data
        assert data["modularity"] >= 0
    
    def test_research_gaps_endpoint(self, client, sample_literature_dataset):
        """Test research gaps analysis endpoint."""
        # Build network
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Get research gaps
        response = client.get("/api/v1/network/gaps?max_gaps=5")
        assert response.status_code == 200
        
        data = response.json()
        assert "identified_gaps" in data
        assert "gap_count" in data
        assert "high_priority_gaps" in data
        assert len(data["identified_gaps"]) <= 5
    
    def test_visualization_endpoint(self, client, sample_literature_dataset):
        """Test visualization data endpoint."""
        # Build network
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Get visualization data
        response = client.get("/api/v1/network/visualization")
        assert response.status_code == 200
        
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "layout_config" in data
        assert "metadata" in data
        
        # Validate node format
        if data["nodes"]:
            node = data["nodes"][0]
            assert "id" in node
            assert "label" in node
            assert "size" in node
            assert "color" in node
    
    def test_export_network_endpoint(self, client, sample_literature_dataset):
        """Test network data export endpoint."""
        # Build network
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Export as JSON
        response = client.post("/api/v1/network/export?format=json")
        assert response.status_code == 200
        
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 6
    
    def test_clear_network_endpoint(self, client, sample_literature_dataset):
        """Test network clearing endpoint."""
        # Build network
        request_data = {"papers": sample_literature_dataset}
        client.post("/api/v1/network/build", json=request_data)
        
        # Clear network
        response = client.delete("/api/v1/network/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # Verify network is cleared
        response = client.get("/api/v1/network/stats")
        assert response.status_code == 404  # No network data
    
    def test_error_handling_no_network(self, client):
        """Test error handling when no network exists."""
        # Try to get stats without building network
        response = client.get("/api/v1/network/stats")
        assert response.status_code == 404
        assert "No network data available" in response.json()["detail"]
        
        # Try to analyze without building network
        analysis_request = {"include_communities": True}
        response = client.post("/api/v1/network/analyze", json=analysis_request)
        assert response.status_code == 404
        assert "build network first" in response.json()["detail"]
    
    def test_validation_errors(self, client):
        """Test input validation errors."""
        # Empty papers list
        request_data = {"papers": []}
        response = client.post("/api/v1/network/build", json=request_data)
        assert response.status_code == 422
        
        # Invalid year
        invalid_paper = {
            "id": "test",
            "title": "Test",
            "authors": [],
            "year": 1800,  # Too old
            "journal": "Test"
        }
        request_data = {"papers": [invalid_paper]}
        response = client.post("/api/v1/network/build", json=request_data)
        assert response.status_code == 422
    
    def test_performance_monitoring_integration(self, client, sample_literature_dataset):
        """Test performance monitoring integration."""
        # Build network (should trigger performance monitoring)
        request_data = {"papers": sample_literature_dataset}
        response = client.post("/api/v1/network/build", json=request_data)
        assert response.status_code == 200
        
        # Perform analysis (should be monitored)
        analysis_request = {"include_communities": True}
        response = client.post("/api/v1/network/analyze", json=analysis_request)
        assert response.status_code == 200
        
        # Check that performance monitoring is working
        # (In a real integration test, you'd check actual metrics)
        monitor = get_performance_monitor()
        assert monitor is not None
        assert len(monitor.metrics) > 0  # Should have recorded some metrics

@pytest.mark.integration
class TestCitationAnalysisWorkflows:
    """Integration tests for complete citation analysis workflows."""
    
    @pytest.fixture
    def large_dataset(self):
        """Larger dataset for workflow testing."""
        papers = []
        for i in range(50):
            paper = {
                "id": f"paper_{i:03d}",
                "title": f"Research Paper {i}: Advanced Topics in AI",
                "authors": [f"Author {i}", f"Co-Author {i}"],
                "year": 2020 + (i % 4),
                "journal": f"Journal {i % 10}",
                "keywords": [f"keyword_{i%15}", f"topic_{i%20}", "artificial intelligence"],
                "citation_count": i * 2 + 10,
                "citations": [f"paper_{j:03d}" for j in range(max(0, i-5), i) if j != i]
            }
            papers.append(paper)
        return papers
    
    @pytest.mark.asyncio
    async def test_large_network_workflow(self, large_dataset):
        """Test complete workflow with larger dataset."""
        analyzer = CitationNetworkAnalyzer()
        
        # Build network
        start_time = time.time()
        await analyzer.build_network_from_papers(large_dataset)
        build_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert build_time < 10.0  # 10 seconds max for 50 papers
        
        # Analyze network
        start_time = time.time()
        result = await analyzer.analyze_network()
        analysis_time = time.time() - start_time
        
        # Should complete analysis in reasonable time
        assert analysis_time < 30.0  # 30 seconds max for analysis
        
        # Validate results
        assert result.node_count == 50
        assert result.edge_count > 0
        assert len(result.top_cited_papers) > 0
        assert len(result.communities) > 0
    
    def test_concurrent_requests(self, client, sample_literature_dataset):
        """Test handling concurrent API requests."""
        import concurrent.futures
        import threading
        
        def make_request():
            """Make a single request."""
            request_data = {"papers": sample_literature_dataset}
            return client.post("/api/v1/network/build", json=request_data)
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [future.result() for future in futures]
        
        # All requests should succeed (or at least not crash)
        success_count = sum(1 for result in results if result.status_code == 200)
        assert success_count >= 1  # At least one should succeed
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, large_dataset):
        """Test memory usage stability during processing."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        analyzer = CitationNetworkAnalyzer()
        
        # Process multiple times to check for memory leaks
        for iteration in range(5):
            await analyzer.build_network_from_papers(large_dataset)
            result = await analyzer.analyze_network()
            
            # Force garbage collection
            gc.collect()
            
            current_memory = process.memory_info().rss
            memory_growth = current_memory - initial_memory
            
            # Memory growth should be reasonable (< 100MB for test dataset)
            assert memory_growth < 100 * 1024 * 1024, f"Memory growth too high: {memory_growth / 1024 / 1024:.2f}MB"
        
        # Clean up
        analyzer.citation_graph.clear()
        analyzer.nodes.clear()
        analyzer.edges.clear()
    
    def test_error_recovery(self, client):
        """Test system recovery from errors."""
        # Cause an error with invalid data
        invalid_request = {"papers": "not a list"}
        response = client.post("/api/v1/network/build", json=invalid_request)
        assert response.status_code == 422
        
        # System should still work after error
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])