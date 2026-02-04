"""
Tests for Citation Network Analyzer

Comprehensive test suite covering:
- Network construction
- Graph algorithms 
- Centrality analysis
- Community detection
- Research gap detection
- Performance validation
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from typing import Dict, List

# Import the analyzer
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services/worker/src'))

from analysis.citation_network_analyzer import (
    CitationNetworkAnalyzer,
    CitationNode,
    CitationEdge,
    NetworkAnalysisResult,
    get_citation_analyzer
)

class TestCitationNetworkAnalyzer:
    """Test suite for citation network analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create test analyzer instance."""
        return CitationNetworkAnalyzer(cache_dir="./test_cache")
    
    @pytest.fixture
    def sample_papers(self):
        """Sample paper data for testing."""
        return [
            {
                'id': 'paper1',
                'title': 'Machine Learning in Healthcare',
                'authors': ['Smith, J.', 'Doe, A.'],
                'year': 2022,
                'journal': 'Nature Medicine',
                'doi': '10.1038/s41591-022-01234-5',
                'keywords': ['machine learning', 'healthcare', 'AI'],
                'abstract': 'This paper explores ML applications in healthcare...',
                'citation_count': 15,
                'citations': ['paper2', 'paper3']
            },
            {
                'id': 'paper2',
                'title': 'Deep Learning for Medical Imaging',
                'authors': ['Johnson, B.'],
                'year': 2021,
                'journal': 'Medical Image Analysis',
                'doi': '10.1016/j.media.2021.12345',
                'keywords': ['deep learning', 'medical imaging', 'CNN'],
                'abstract': 'Deep learning techniques for medical image analysis...',
                'citation_count': 32,
                'citations': ['paper4']
            },
            {
                'id': 'paper3',
                'title': 'AI Ethics in Clinical Practice',
                'authors': ['Brown, C.', 'Wilson, D.'],
                'year': 2023,
                'journal': 'AI Ethics',
                'keywords': ['AI ethics', 'clinical practice', 'healthcare'],
                'abstract': 'Ethical considerations for AI in healthcare...',
                'citation_count': 8,
                'citations': ['paper1']
            },
            {
                'id': 'paper4',
                'title': 'Computer Vision in Radiology',
                'authors': ['Davis, E.'],
                'year': 2020,
                'journal': 'Radiology',
                'keywords': ['computer vision', 'radiology', 'imaging'],
                'abstract': 'Computer vision applications in radiology...',
                'citation_count': 24,
                'citations': []
            }
        ]
    
    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
        assert analyzer.citation_graph is not None
        assert analyzer.nodes == {}
        assert analyzer.edges == []
        assert analyzer.min_citations_threshold == 1
        assert analyzer.max_network_size == 10000
    
    def test_create_node_from_paper(self, analyzer, sample_papers):
        """Test node creation from paper data."""
        paper = sample_papers[0]
        node = analyzer._create_node_from_paper(paper)
        
        assert node.paper_id == 'paper1'
        assert node.title == 'Machine Learning in Healthcare'
        assert len(node.authors) == 2
        assert node.year == 2022
        assert node.journal == 'Nature Medicine'
        assert node.doi == '10.1038/s41591-022-01234-5'
        assert 'machine learning' in node.keywords
        assert node.citation_count == 15
    
    @pytest.mark.asyncio
    async def test_build_network_from_papers(self, analyzer, sample_papers):
        """Test network construction from paper data."""
        await analyzer.build_network_from_papers(sample_papers)
        
        # Check nodes created
        assert len(analyzer.nodes) == 4
        assert 'paper1' in analyzer.nodes
        assert 'paper2' in analyzer.nodes
        
        # Check graph structure
        assert analyzer.citation_graph.number_of_nodes() == 4
        assert analyzer.citation_graph.number_of_edges() > 0
        
        # Check citation relationships
        assert analyzer.citation_graph.has_edge('paper1', 'paper2')
        assert analyzer.citation_graph.has_edge('paper1', 'paper3')
        assert analyzer.citation_graph.has_edge('paper3', 'paper1')
    
    @pytest.mark.asyncio
    async def test_network_analysis(self, analyzer, sample_papers):
        """Test comprehensive network analysis."""
        await analyzer.build_network_from_papers(sample_papers)
        
        result = await analyzer.analyze_network()
        
        # Check result structure
        assert isinstance(result, NetworkAnalysisResult)
        assert result.node_count == 4
        assert result.edge_count > 0
        assert 0 <= result.density <= 1
        assert result.clustering_coefficient >= 0
        
        # Check top papers lists
        assert len(result.top_central_papers) <= 10
        assert len(result.top_pagerank_papers) <= 10
        assert len(result.top_cited_papers) <= 10
        
        # Check communities
        assert isinstance(result.communities, dict)
        assert result.modularity >= 0
        
        # Check gap analysis
        assert isinstance(result.research_gaps, list)
        assert isinstance(result.emerging_topics, list)
        
        # Check export data
        assert 'nodes' in result.network_data
        assert 'edges' in result.network_data
        assert 'nodes' in result.visualization_data
        assert 'edges' in result.visualization_data
    
    def test_co_citation_computation(self, analyzer, sample_papers):
        """Test co-citation analysis."""
        # Set up minimal network
        analyzer.nodes = {
            'paper1': CitationNode('paper1', 'Title 1', [], 2021, 'Journal', citations={'ref1', 'ref2'}),
            'paper2': CitationNode('paper2', 'Title 2', [], 2021, 'Journal', citations={'ref1', 'ref3'}),
            'paper3': CitationNode('paper3', 'Title 3', [], 2021, 'Journal', citations={'ref2', 'ref3'})
        }
        
        co_citations = analyzer._compute_co_citations()
        
        # Should find co-citations between references
        assert len(co_citations) > 0
        # ref1 and ref2 are co-cited by paper1
        # ref1 and ref3 are co-cited by paper2
        # ref2 and ref3 are co-cited by paper3
    
    def test_bibliographic_coupling(self, analyzer):
        """Test bibliographic coupling computation."""
        # Set up test network
        analyzer.nodes = {
            'paper1': CitationNode('paper1', 'Title 1', [], 2021, 'Journal', citations={'ref1', 'ref2'}),
            'paper2': CitationNode('paper2', 'Title 2', [], 2021, 'Journal', citations={'ref1', 'ref3'}),
            'paper3': CitationNode('paper3', 'Title 3', [], 2021, 'Journal', citations={'ref4'})
        }
        
        coupling = analyzer._compute_bibliographic_coupling()
        
        # paper1 and paper2 should be coupled (both cite ref1)
        pair = tuple(sorted(['paper1', 'paper2']))
        assert pair in coupling
        assert coupling[pair] == 1  # One common reference
    
    @pytest.mark.asyncio
    async def test_centrality_computation(self, analyzer, sample_papers):
        """Test centrality metrics computation."""
        await analyzer.build_network_from_papers(sample_papers)
        
        centrality_results = await analyzer._compute_centrality_metrics()
        
        assert 'betweenness' in centrality_results
        assert 'pagerank' in centrality_results
        assert 'citations' in centrality_results
        
        # Check that results are sorted (highest first)
        betweenness_scores = [score for _, score in centrality_results['betweenness']]
        assert betweenness_scores == sorted(betweenness_scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_community_detection(self, analyzer, sample_papers):
        """Test community detection."""
        await analyzer.build_network_from_papers(sample_papers)
        
        communities, modularity = await analyzer._detect_communities()
        
        assert isinstance(communities, dict)
        assert modularity >= 0  # Modularity should be non-negative
        
        # Check that all nodes are assigned to communities
        all_assigned_nodes = []
        for community_nodes in communities.values():
            all_assigned_nodes.extend(community_nodes)
        
        assert len(set(all_assigned_nodes)) <= len(analyzer.nodes)
    
    @pytest.mark.asyncio
    async def test_research_gap_detection(self, analyzer, sample_papers):
        """Test research gap detection."""
        await analyzer.build_network_from_papers(sample_papers)
        
        gaps = await analyzer._detect_research_gaps()
        
        assert isinstance(gaps, list)
        
        for gap in gaps:
            assert 'gap_type' in gap
            assert 'severity' in gap
            assert gap['severity'] in ['low', 'medium', 'high']
    
    @pytest.mark.asyncio
    async def test_emerging_topics_detection(self, analyzer, sample_papers):
        """Test emerging topics detection."""
        await analyzer.build_network_from_papers(sample_papers)
        
        emerging = await analyzer._detect_emerging_topics()
        
        assert isinstance(emerging, list)
        
        for topic in emerging:
            if 'trend_strength' in topic:
                assert topic['trend_strength'] in ['low', 'medium', 'high']
    
    def test_network_data_preparation(self, analyzer, sample_papers):
        """Test network data preparation for export."""
        # Set up minimal network
        analyzer.nodes = {
            'paper1': CitationNode('paper1', 'Title 1', ['Author 1'], 2021, 'Journal 1')
        }
        analyzer.edges = [
            CitationEdge('paper1', 'paper2', citation_type='direct', strength=1.0)
        ]
        
        network_data = analyzer._prepare_network_data()
        
        assert 'nodes' in network_data
        assert 'edges' in network_data
        assert len(network_data['nodes']) == 1
        assert len(network_data['edges']) == 1
        
        node = network_data['nodes'][0]
        assert node['id'] == 'paper1'
        assert node['title'] == 'Title 1'
        assert node['year'] == 2021
    
    def test_visualization_data_preparation(self, analyzer):
        """Test visualization data preparation."""
        # Set up test network
        analyzer.nodes = {
            f'paper{i}': CitationNode(
                f'paper{i}', f'Title {i}', [f'Author {i}'], 
                2020 + i, f'Journal {i}', citation_count=i*5, cluster_id=i%2
            )
            for i in range(10)
        }
        analyzer.edges = [
            CitationEdge(f'paper{i}', f'paper{i+1}', strength=1.0)
            for i in range(9)
        ]
        
        viz_data = analyzer._prepare_visualization_data()
        
        assert 'nodes' in viz_data
        assert 'edges' in viz_data
        assert 'metadata' in viz_data
        
        # Check node format
        node = viz_data['nodes'][0]
        assert 'id' in node
        assert 'label' in node
        assert 'size' in node
        assert 'color' in node
        
        # Check metadata
        metadata = viz_data['metadata']
        assert 'total_nodes' in metadata
        assert 'displayed_nodes' in metadata
        assert metadata['total_nodes'] == 10
    
    def test_network_summary(self, analyzer, sample_papers):
        """Test network summary generation."""
        # Test empty network
        summary = analyzer.get_network_summary()
        assert summary['status'] == 'empty'
        
        # Test with data
        analyzer.nodes = {
            'paper1': CitationNode('paper1', 'Test Paper', ['Author'], 2022, 'Test Journal', citation_count=10),
            'paper2': CitationNode('paper2', 'Another Paper', ['Author'], 2021, 'Another Journal', citation_count=5)
        }
        
        summary = analyzer.get_network_summary()
        assert summary['status'] == 'active'
        assert summary['node_count'] == 2
        assert 'most_cited_paper' in summary
        assert 'year_range' in summary
        assert summary['year_range'] == (2021, 2022)
    
    def test_save_and_load_network(self, analyzer, tmp_path):
        """Test network serialization and deserialization."""
        # Create test network
        analyzer.nodes = {
            'paper1': CitationNode('paper1', 'Test Paper', ['Author'], 2022, 'Journal')
        }
        analyzer.edges = [
            CitationEdge('paper1', 'paper2', citation_type='direct')
        ]
        
        # Save network
        filepath = tmp_path / "test_network.pkl"
        analyzer.save_network(str(filepath))
        
        assert filepath.exists()
        
        # Create new analyzer and load
        new_analyzer = CitationNetworkAnalyzer()
        new_analyzer.load_network(str(filepath))
        
        # Verify loaded data
        assert len(new_analyzer.nodes) == 1
        assert 'paper1' in new_analyzer.nodes
        assert new_analyzer.nodes['paper1'].title == 'Test Paper'
        assert len(new_analyzer.edges) == 1
    
    def test_global_analyzer_instance(self):
        """Test global analyzer instance."""
        analyzer1 = get_citation_analyzer()
        analyzer2 = get_citation_analyzer()
        
        # Should be the same instance
        assert analyzer1 is analyzer2
    
    @pytest.mark.asyncio
    async def test_error_handling_empty_network(self, analyzer):
        """Test error handling for empty networks."""
        with pytest.raises(ValueError, match="Network is empty"):
            await analyzer.analyze_network()
    
    @pytest.mark.asyncio
    async def test_large_network_handling(self, analyzer):
        """Test handling of large networks."""
        # Create large dataset
        large_papers = [
            {
                'id': f'paper{i}',
                'title': f'Paper {i}',
                'authors': [f'Author {i}'],
                'year': 2000 + (i % 25),
                'journal': f'Journal {i % 5}',
                'keywords': [f'keyword{i%10}', f'topic{i%15}'],
                'citation_count': i % 50,
                'citations': [f'paper{j}' for j in range(max(0, i-3), i)]
            }
            for i in range(100)  # 100 papers
        ]
        
        # Should handle without errors
        await analyzer.build_network_from_papers(large_papers)
        result = await analyzer.analyze_network()
        
        assert result.node_count == 100
        assert result.edge_count > 0
    
    def test_performance_metrics(self, analyzer):
        """Test performance characteristics."""
        import time
        
        # Test node creation performance
        start_time = time.time()
        
        test_papers = [
            {
                'id': f'paper{i}',
                'title': f'Test Paper {i}',
                'authors': [f'Author {i}'],
                'year': 2020,
                'journal': 'Test Journal',
                'keywords': ['test'],
                'citations': []
            }
            for i in range(1000)
        ]
        
        # Create nodes
        for paper in test_papers:
            analyzer._create_node_from_paper(paper)
        
        creation_time = time.time() - start_time
        
        # Should complete in reasonable time (< 1 second for 1000 nodes)
        assert creation_time < 1.0
        
    @pytest.mark.parametrize("paper_count,expected_edges", [
        (10, 9),  # Linear chain
        (50, 49), # Linear chain
        (100, 99) # Linear chain
    ])
    @pytest.mark.asyncio
    async def test_network_scaling(self, analyzer, paper_count, expected_edges):
        """Test network scaling with different sizes."""
        # Create linear citation chain
        papers = [
            {
                'id': f'paper{i}',
                'title': f'Paper {i}',
                'authors': [f'Author {i}'],
                'year': 2020 + i,
                'journal': 'Test Journal',
                'keywords': ['test'],
                'citations': [f'paper{i+1}'] if i < paper_count - 1 else []
            }
            for i in range(paper_count)
        ]
        
        await analyzer.build_network_from_papers(papers)
        
        assert analyzer.citation_graph.number_of_nodes() == paper_count
        # Note: actual edges may be more due to secondary relationships
        assert analyzer.citation_graph.number_of_edges() >= expected_edges

@pytest.mark.integration
class TestCitationNetworkIntegration:
    """Integration tests for citation network analyzer."""
    
    @pytest.mark.asyncio
    async def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline."""
        analyzer = CitationNetworkAnalyzer()
        
        # Sample realistic literature dataset
        papers = [
            {
                'id': 'doi:10.1038/nature12345',
                'title': 'Machine Learning Applications in Genomics',
                'authors': ['Smith, J.', 'Johnson, A.', 'Williams, B.'],
                'year': 2023,
                'journal': 'Nature',
                'doi': '10.1038/nature12345',
                'keywords': ['machine learning', 'genomics', 'bioinformatics', 'deep learning'],
                'abstract': 'We present novel machine learning approaches for genomic data analysis...',
                'citation_count': 45,
                'citations': ['doi:10.1016/j.cell.2022.54321', 'doi:10.1126/science.abc123']
            },
            {
                'id': 'doi:10.1016/j.cell.2022.54321',
                'title': 'Deep Learning for Protein Structure Prediction',
                'authors': ['Davis, C.', 'Brown, D.'],
                'year': 2022,
                'journal': 'Cell',
                'doi': '10.1016/j.cell.2022.54321',
                'keywords': ['deep learning', 'protein structure', 'AlphaFold', 'structural biology'],
                'abstract': 'Advanced deep learning models for accurate protein structure prediction...',
                'citation_count': 123,
                'citations': ['doi:10.1126/science.abc123']
            },
            {
                'id': 'doi:10.1126/science.abc123',
                'title': 'Computational Biology in the AI Era',
                'authors': ['Taylor, E.', 'Anderson, F.'],
                'year': 2021,
                'journal': 'Science',
                'doi': '10.1126/science.abc123',
                'keywords': ['computational biology', 'artificial intelligence', 'systems biology'],
                'abstract': 'The intersection of AI and computational biology opens new frontiers...',
                'citation_count': 89,
                'citations': []
            }
        ]
        
        # Build network
        await analyzer.build_network_from_papers(papers)
        
        # Analyze network
        result = await analyzer.analyze_network()
        
        # Validate comprehensive results
        assert result.node_count == 3
        assert result.density > 0
        assert len(result.top_cited_papers) == 3
        assert result.top_cited_papers[0][1] == 123  # Most cited paper
        
        # Check network data export
        network_data = result.network_data
        assert len(network_data['nodes']) == 3
        assert len(network_data['edges']) > 0
        
        # Check visualization data
        viz_data = result.visualization_data
        assert len(viz_data['nodes']) == 3
        assert viz_data['metadata']['total_nodes'] == 3
        
        # Verify network summary
        summary = analyzer.get_network_summary()
        assert summary['status'] == 'active'
        assert summary['node_count'] == 3
        assert 'Deep Learning for Protein Structure' in summary['most_cited_paper']

if __name__ == "__main__":
    # Run specific tests
    pytest.main([__file__, "-v", "--tb=short"])