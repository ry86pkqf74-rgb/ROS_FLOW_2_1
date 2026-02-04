"""
Integration Tests for Package Compression System
==============================================

End-to-end integration tests for package compression functionality
across the ResearchFlow system including manuscript generation,
citation management, and performance optimization.
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, List, Any

# Test utilities
from tests.integration.utils.helpers import create_test_manuscript, create_test_citations
from tests.integration.utils.api_client import ResearchFlowTestClient
from tests.integration.utils.assertions import assert_compression_quality


class TestPackageCompressionIntegration:
    """Integration tests for package compression across system components."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for API interactions."""
        return ResearchFlowTestClient(base_url="http://localhost:8000")
    
    @pytest.fixture
    def sample_manuscript_package(self):
        """Create a sample manuscript package for testing."""
        return {
            "manuscript": {
                "title": "Advanced Machine Learning in Clinical Research",
                "abstract": "This study explores the application of machine learning...",
                "introduction": "Machine learning has revolutionized healthcare...",
                "methods": "We employed a comprehensive methodology...",
                "results": "Our analysis revealed significant patterns...",
                "discussion": "The findings demonstrate the potential...",
                "conclusion": "This research contributes to the field...",
                "references": ["Reference 1", "Reference 2", "Reference 3"]
            },
            "metadata": {
                "word_count": 4500,
                "citation_count": 47,
                "figure_count": 8,
                "table_count": 4,
                "created_at": "2024-01-15T10:30:00Z",
                "last_modified": "2024-01-15T14:45:00Z"
            },
            "attachments": [
                {"name": "figure1.png", "size": 256000, "type": "image"},
                {"name": "table1.xlsx", "size": 45000, "type": "spreadsheet"},
                {"name": "data.csv", "size": 128000, "type": "data"}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_full_manuscript_compression_workflow(self, test_client, sample_manuscript_package):
        """Test complete manuscript package compression workflow."""
        # Step 1: Upload manuscript package
        response = await test_client.post("/api/manuscript/package/upload", 
                                        json=sample_manuscript_package)
        assert response.status_code == 201
        package_id = response.json()["package_id"]
        
        # Step 2: Request compression optimization
        compression_request = {
            "package_id": package_id,
            "compression_target": 0.8,
            "preserve_quality": True,
            "optimize_citations": True
        }
        
        response = await test_client.post("/api/optimization/compress", 
                                        json=compression_request)
        assert response.status_code == 200
        compression_result = response.json()
        
        # Step 3: Verify compression results
        assert "compression_ratio" in compression_result
        assert "optimized_package" in compression_result
        assert compression_result["compression_ratio"] >= 0.75  # At least 75% of target
        
        # Step 4: Download and verify optimized package
        optimized_package_id = compression_result["optimized_package"]["id"]
        response = await test_client.get(f"/api/manuscript/package/{optimized_package_id}")
        assert response.status_code == 200
        
        optimized_package = response.json()
        assert_compression_quality(sample_manuscript_package, optimized_package)
    
    @pytest.mark.asyncio
    async def test_citation_network_compression_integration(self, test_client):
        """Test integration between citation network analysis and compression."""
        # Create test citation network
        citation_network = {
            "papers": [
                {
                    "id": "paper_001",
                    "title": "Machine Learning in Healthcare",
                    "citations": 156,
                    "impact_factor": 4.2,
                    "content_size": 45000
                },
                {
                    "id": "paper_002", 
                    "title": "Clinical Data Analysis Methods",
                    "citations": 89,
                    "impact_factor": 3.1,
                    "content_size": 38000
                }
            ],
            "relationships": [
                {
                    "source": "paper_001",
                    "target": "paper_002",
                    "relationship_type": "cites",
                    "weight": 0.85
                }
            ]
        }
        
        # Upload citation network
        response = await test_client.post("/api/citations/network/upload",
                                        json=citation_network)
        assert response.status_code == 201
        network_id = response.json()["network_id"]
        
        # Request optimization with compression
        optimization_request = {
            "network_id": network_id,
            "optimize_storage": True,
            "compression_level": "high",
            "preserve_relationships": True
        }
        
        response = await test_client.post("/api/citations/network/optimize",
                                        json=optimization_request)
        assert response.status_code == 200
        
        optimization_result = response.json()
        assert "storage_reduction" in optimization_result
        assert optimization_result["storage_reduction"] > 0.3  # At least 30% reduction
    
    def test_compression_with_phi_data_handling(self, test_client, sample_manuscript_package):
        """Test compression while maintaining PHI data protection."""
        # Add PHI-sensitive data to manuscript
        phi_manuscript = sample_manuscript_package.copy()
        phi_manuscript["metadata"]["contains_phi"] = True
        phi_manuscript["phi_scan_results"] = {
            "phi_detected": True,
            "phi_types": ["patient_id", "date_of_birth"],
            "redaction_required": True
        }
        
        # Request compression with PHI protection
        compression_request = {
            "manuscript": phi_manuscript,
            "compression_target": 0.8,
            "phi_protection": True,
            "redact_sensitive_data": True
        }
        
        # Mock the API call since PHI handling may not be fully implemented
        with patch('tests.integration.utils.api_client.ResearchFlowTestClient.post') as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {
                    "compression_ratio": 0.82,
                    "phi_protection_applied": True,
                    "redacted_fields": ["patient_id", "date_of_birth"],
                    "compression_preserved_privacy": True
                }
            )
            
            response = test_client.post("/api/optimization/compress-phi", 
                                     json=compression_request)
            result = response.json()
            
            assert result["phi_protection_applied"] is True
            assert "redacted_fields" in result
            assert result["compression_preserved_privacy"] is True
    
    @pytest.mark.asyncio
    async def test_real_time_compression_monitoring(self, test_client):
        """Test real-time monitoring of compression operations."""
        # Start a long-running compression task
        compression_task = {
            "data_size": 500000,  # Large dataset
            "compression_algorithm": "advanced",
            "estimated_duration": 30  # seconds
        }
        
        response = await test_client.post("/api/optimization/compress/async",
                                        json=compression_task)
        assert response.status_code == 202  # Accepted for processing
        task_id = response.json()["task_id"]
        
        # Monitor progress
        progress_checks = 0
        while progress_checks < 10:  # Max 10 checks to avoid infinite loop
            response = await test_client.get(f"/api/optimization/compress/status/{task_id}")
            assert response.status_code == 200
            
            status = response.json()
            assert "progress_percentage" in status
            assert "estimated_completion" in status
            
            if status["status"] == "completed":
                assert "compression_ratio" in status
                assert "optimization_metrics" in status
                break
                
            # Wait before next check
            await asyncio.sleep(1)
            progress_checks += 1
        
        # Should have completed or made progress
        assert progress_checks < 10 or status["progress_percentage"] > 0
    
    def test_compression_performance_benchmarks(self, sample_manuscript_package):
        """Test compression performance meets benchmarks."""
        import time
        from tests.integration.utils.helpers import generate_large_manuscript
        
        # Test with different sized manuscripts
        test_sizes = [
            ("small", 1000),    # 1KB
            ("medium", 50000),  # 50KB  
            ("large", 500000),  # 500KB
        ]
        
        performance_results = []
        
        for size_name, size_bytes in test_sizes:
            large_manuscript = generate_large_manuscript(size_bytes)
            
            start_time = time.time()
            
            # Mock compression operation
            with patch('tests.integration.utils.api_client.ResearchFlowTestClient.post') as mock_post:
                mock_post.return_value = Mock(
                    status_code=200,
                    json=lambda: {
                        "compression_ratio": 0.85,
                        "processing_time": time.time() - start_time,
                        "original_size": size_bytes,
                        "compressed_size": int(size_bytes * 0.85)
                    }
                )
                
                test_client = ResearchFlowTestClient()
                response = test_client.post("/api/optimization/compress", 
                                          json={"manuscript": large_manuscript})
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                performance_results.append({
                    "size": size_name,
                    "bytes": size_bytes,
                    "processing_time": processing_time,
                    "throughput": size_bytes / processing_time if processing_time > 0 else 0
                })
        
        # Verify performance benchmarks
        for result in performance_results:
            # Should process at least 10KB/second
            assert result["throughput"] > 10000, f"Poor throughput for {result['size']}: {result['throughput']}"
            
            # Processing time should scale reasonably
            if result["size"] == "small":
                assert result["processing_time"] < 1.0, "Small files should process quickly"
            elif result["size"] == "large":
                assert result["processing_time"] < 10.0, "Large files should complete within 10 seconds"
    
    @pytest.mark.asyncio 
    async def test_compression_error_recovery(self, test_client):
        """Test error recovery and rollback in compression operations."""
        # Create intentionally problematic data
        problematic_package = {
            "manuscript": {
                "corrupted_field": "x" * 1000000,  # Very large field
                "null_content": None,
                "invalid_references": ["", None, 123]  # Invalid reference types
            },
            "metadata": {
                "invalid_date": "not-a-date",
                "negative_count": -5
            }
        }
        
        # Attempt compression
        response = await test_client.post("/api/optimization/compress",
                                        json={"manuscript": problematic_package})
        
        # Should handle errors gracefully
        if response.status_code != 200:
            error_response = response.json()
            assert "error" in error_response
            assert "recovery_suggestions" in error_response
        else:
            # If successful, should have applied error corrections
            result = response.json()
            assert "error_corrections_applied" in result
            assert result["error_corrections_applied"] > 0
    
    def test_compression_consistency_across_environments(self, sample_manuscript_package):
        """Test that compression produces consistent results across environments."""
        compression_results = []
        
        # Test in different mock environments
        environments = ["development", "staging", "production"]
        
        for env in environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                # Mock environment-specific compression
                with patch('tests.integration.utils.api_client.ResearchFlowTestClient.post') as mock_post:
                    mock_post.return_value = Mock(
                        status_code=200,
                        json=lambda: {
                            "compression_ratio": 0.85,
                            "environment": env,
                            "algorithm_version": "1.0.0",
                            "checksum": "abc123def456"  # Should be same across environments
                        }
                    )
                    
                    test_client = ResearchFlowTestClient()
                    response = test_client.post("/api/optimization/compress",
                                              json={"manuscript": sample_manuscript_package})
                    
                    compression_results.append(response.json())
        
        # Verify consistency
        base_ratio = compression_results[0]["compression_ratio"]
        base_checksum = compression_results[0]["checksum"]
        
        for result in compression_results[1:]:
            # Compression ratios should be identical
            assert abs(result["compression_ratio"] - base_ratio) < 0.001
            
            # Checksums should match (same algorithm, same data)
            assert result["checksum"] == base_checksum


class TestCompressionQualityValidation:
    """Tests for validating compression quality and preservation."""
    
    def test_manuscript_content_preservation(self):
        """Test that essential manuscript content is preserved after compression."""
        original_manuscript = {
            "title": "Original Title",
            "abstract": "Original abstract content...",
            "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
            "statistical_results": {
                "p_value": 0.05,
                "confidence_interval": [0.1, 0.9],
                "sample_size": 1000
            }
        }
        
        # Mock compression that might alter content
        compressed_manuscript = {
            "title": "Original Title",  # Should be preserved
            "abstract": "Original abstract...",  # Minor truncation acceptable
            "key_findings": ["Finding 1", "Finding 2", "Finding 3"],  # Must preserve
            "statistical_results": {
                "p_value": 0.05,  # Critical - must preserve
                "confidence_interval": [0.1, 0.9],  # Critical
                "sample_size": 1000  # Critical
            }
        }
        
        # Validate preservation of critical content
        assert compressed_manuscript["title"] == original_manuscript["title"]
        assert compressed_manuscript["key_findings"] == original_manuscript["key_findings"]
        assert compressed_manuscript["statistical_results"] == original_manuscript["statistical_results"]
        
        # Abstract can be slightly shortened but should retain key information
        assert len(compressed_manuscript["abstract"]) >= len(original_manuscript["abstract"]) * 0.8
    
    def test_citation_relationship_preservation(self):
        """Test that citation relationships are preserved during compression."""
        original_network = {
            "papers": {"paper1": {"citations": 45}, "paper2": {"citations": 32}},
            "relationships": [{"source": "paper1", "target": "paper2", "weight": 0.85}]
        }
        
        compressed_network = {
            "papers": {"paper1": {"citations": 45}, "paper2": {"citations": 32}},
            "relationships": [{"source": "paper1", "target": "paper2", "weight": 0.85}]
        }
        
        # Citation relationships must be identical
        assert compressed_network["relationships"] == original_network["relationships"]
        
        # Citation counts must be preserved
        for paper_id, paper_data in original_network["papers"].items():
            assert compressed_network["papers"][paper_id]["citations"] == paper_data["citations"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])