"""
Citation Network Analysis Engine

This module provides comprehensive citation network analysis including:
- Graph construction from literature data
- Centrality analysis (betweenness, closeness, pagerank)
- Co-citation analysis
- Bibliographic coupling
- Citation impact metrics
- Literature gap detection
- Network visualization data export

Author: Research Analysis Team
"""

import logging
import asyncio
import networkx as nx
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import json
import re
from datetime import datetime
import concurrent.futures
from pathlib import Path
import pickle
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class CitationNode:
    """Represents a publication node in the citation network."""
    
    paper_id: str
    title: str
    authors: List[str]
    year: int
    journal: str
    doi: Optional[str] = None
    
    # Citation metrics
    citation_count: int = 0
    h_index: Optional[int] = None
    
    # Network metrics (computed)
    betweenness_centrality: float = 0.0
    closeness_centrality: float = 0.0
    pagerank_score: float = 0.0
    cluster_id: Optional[int] = None
    
    # Additional metadata
    keywords: List[str] = field(default_factory=list)
    abstract: str = ""
    citations: Set[str] = field(default_factory=set)  # Papers this paper cites
    cited_by: Set[str] = field(default_factory=set)   # Papers that cite this paper

@dataclass
class CitationEdge:
    """Represents a citation relationship between papers."""
    
    source_id: str  # Paper that cites
    target_id: str  # Paper being cited
    context: str = ""  # Citation context from paper
    citation_type: str = "direct"  # direct, co-citation, bibliographic-coupling
    strength: float = 1.0  # Citation strength/weight

@dataclass
class NetworkAnalysisResult:
    """Results from citation network analysis."""
    
    # Network statistics
    node_count: int
    edge_count: int
    density: float
    clustering_coefficient: float
    average_path_length: Optional[float]
    
    # Top nodes by metrics
    top_central_papers: List[Tuple[str, float]]
    top_pagerank_papers: List[Tuple[str, float]]
    top_cited_papers: List[Tuple[str, int]]
    
    # Community detection
    communities: Dict[int, List[str]]
    modularity: float
    
    # Gap analysis
    research_gaps: List[Dict[str, Any]]
    emerging_topics: List[Dict[str, Any]]
    
    # Export data
    network_data: Dict[str, Any]
    visualization_data: Dict[str, Any]

class CitationNetworkAnalyzer:
    """
    Advanced citation network analyzer with graph algorithms.
    
    Provides comprehensive analysis of citation relationships,
    including centrality metrics, community detection, and gap analysis.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize citation network analyzer."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path("./citation_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Network storage
        self.citation_graph = nx.DiGraph()
        self.nodes: Dict[str, CitationNode] = {}
        self.edges: List[CitationEdge] = []
        
        # Analysis cache
        self.analysis_cache: Dict[str, Any] = {}
        
        # Configuration
        self.min_citations_threshold = 1
        self.max_network_size = 10000
        self.community_resolution = 1.0
        
        logger.info("Citation Network Analyzer initialized")
    
    async def build_network_from_papers(self, papers: List[Dict[str, Any]]) -> None:
        """Build citation network from paper data."""
        try:
            logger.info(f"Building citation network from {len(papers)} papers")
            
            # Clear existing network
            self.citation_graph.clear()
            self.nodes.clear()
            self.edges.clear()
            
            # Step 1: Create nodes
            for paper in papers:
                node = self._create_node_from_paper(paper)
                self.nodes[node.paper_id] = node
                self.citation_graph.add_node(node.paper_id, **self._node_to_attrs(node))
            
            # Step 2: Create edges from citations
            for paper in papers:
                paper_id = paper.get('id', paper.get('paper_id', ''))
                citations = paper.get('citations', [])
                
                for cited_paper_id in citations:
                    if cited_paper_id in self.nodes:
                        edge = CitationEdge(
                            source_id=paper_id,
                            target_id=cited_paper_id,
                            context=paper.get('citation_contexts', {}).get(cited_paper_id, ''),
                            strength=1.0
                        )
                        
                        self.edges.append(edge)
                        self.citation_graph.add_edge(
                            paper_id, cited_paper_id,
                            **self._edge_to_attrs(edge)
                        )
                        
                        # Update node citation counts
                        self.nodes[paper_id].citations.add(cited_paper_id)
                        self.nodes[cited_paper_id].cited_by.add(paper_id)
                        self.nodes[cited_paper_id].citation_count += 1
            
            # Step 3: Add co-citation and bibliographic coupling edges
            await self._add_secondary_relationships()
            
            logger.info(f"Citation network built: {len(self.nodes)} nodes, {len(self.edges)} edges")
            
        except Exception as e:
            logger.error(f"Error building citation network: {e}")
            raise
    
    def _create_node_from_paper(self, paper: Dict[str, Any]) -> CitationNode:
        """Create citation node from paper data."""
        return CitationNode(
            paper_id=paper.get('id', paper.get('paper_id', '')),
            title=paper.get('title', ''),
            authors=paper.get('authors', []),
            year=paper.get('year', 0),
            journal=paper.get('journal', ''),
            doi=paper.get('doi'),
            keywords=paper.get('keywords', []),
            abstract=paper.get('abstract', ''),
            citation_count=paper.get('citation_count', 0)
        )
    
    def _node_to_attrs(self, node: CitationNode) -> Dict[str, Any]:
        """Convert node to NetworkX attributes."""
        return {
            'title': node.title,
            'authors': node.authors,
            'year': node.year,
            'journal': node.journal,
            'citation_count': node.citation_count,
            'keywords': node.keywords
        }
    
    def _edge_to_attrs(self, edge: CitationEdge) -> Dict[str, Any]:
        """Convert edge to NetworkX attributes."""
        return {
            'context': edge.context,
            'type': edge.citation_type,
            'strength': edge.strength
        }
    
    async def _add_secondary_relationships(self) -> None:
        """Add co-citation and bibliographic coupling relationships."""
        try:
            # Co-citation analysis: papers cited together
            co_citations = self._compute_co_citations()
            
            for (paper1, paper2), strength in co_citations.items():
                if strength >= 2:  # Minimum co-citation threshold
                    edge = CitationEdge(
                        source_id=paper1,
                        target_id=paper2,
                        citation_type="co-citation",
                        strength=strength
                    )
                    self.edges.append(edge)
                    
                    if not self.citation_graph.has_edge(paper1, paper2):
                        self.citation_graph.add_edge(paper1, paper2, **self._edge_to_attrs(edge))
            
            # Bibliographic coupling: papers that cite the same sources
            bibliographic_coupling = self._compute_bibliographic_coupling()
            
            for (paper1, paper2), strength in bibliographic_coupling.items():
                if strength >= 2:  # Minimum coupling threshold
                    edge = CitationEdge(
                        source_id=paper1,
                        target_id=paper2,
                        citation_type="bibliographic-coupling",
                        strength=strength
                    )
                    self.edges.append(edge)
                    
                    if not self.citation_graph.has_edge(paper1, paper2):
                        self.citation_graph.add_edge(paper1, paper2, **self._edge_to_attrs(edge))
            
            logger.info("Added secondary citation relationships")
            
        except Exception as e:
            logger.error(f"Error adding secondary relationships: {e}")
    
    def _compute_co_citations(self) -> Dict[Tuple[str, str], int]:
        """Compute co-citation matrix."""
        co_citations = defaultdict(int)
        
        for node_id, node in self.nodes.items():
            cited_papers = list(node.citations)
            
            # Find pairs of papers cited together
            for i, paper1 in enumerate(cited_papers):
                for paper2 in cited_papers[i+1:]:
                    pair = tuple(sorted([paper1, paper2]))
                    co_citations[pair] += 1
        
        return dict(co_citations)
    
    def _compute_bibliographic_coupling(self) -> Dict[Tuple[str, str], int]:
        """Compute bibliographic coupling matrix."""
        coupling = defaultdict(int)
        
        papers = list(self.nodes.keys())
        
        for i, paper1 in enumerate(papers):
            for paper2 in papers[i+1:]:
                # Count common citations
                common_citations = len(
                    self.nodes[paper1].citations & 
                    self.nodes[paper2].citations
                )
                
                if common_citations > 0:
                    pair = tuple(sorted([paper1, paper2]))
                    coupling[pair] = common_citations
        
        return dict(coupling)
    
    async def analyze_network(self) -> NetworkAnalysisResult:
        """Perform comprehensive network analysis."""
        try:
            logger.info("Starting comprehensive network analysis")
            
            if len(self.citation_graph.nodes) == 0:
                raise ValueError("Network is empty - build network first")
            
            # Basic network statistics
            node_count = self.citation_graph.number_of_nodes()
            edge_count = self.citation_graph.number_of_edges()
            density = nx.density(self.citation_graph)
            
            # Clustering coefficient
            clustering_coeff = nx.average_clustering(self.citation_graph.to_undirected())
            
            # Average path length (for largest connected component)
            avg_path_length = None
            try:
                if nx.is_connected(self.citation_graph.to_undirected()):
                    avg_path_length = nx.average_shortest_path_length(self.citation_graph.to_undirected())
                else:
                    # Use largest connected component
                    largest_cc = max(nx.connected_components(self.citation_graph.to_undirected()), key=len)
                    subgraph = self.citation_graph.subgraph(largest_cc)
                    avg_path_length = nx.average_shortest_path_length(subgraph.to_undirected())
            except:
                avg_path_length = None
            
            # Centrality analysis
            centrality_results = await self._compute_centrality_metrics()
            
            # Community detection
            communities, modularity = await self._detect_communities()
            
            # Research gap analysis
            research_gaps = await self._detect_research_gaps()
            emerging_topics = await self._detect_emerging_topics()
            
            # Prepare network data for export
            network_data = self._prepare_network_data()
            visualization_data = self._prepare_visualization_data()
            
            result = NetworkAnalysisResult(
                node_count=node_count,
                edge_count=edge_count,
                density=density,
                clustering_coefficient=clustering_coeff,
                average_path_length=avg_path_length,
                top_central_papers=centrality_results['betweenness'][:10],
                top_pagerank_papers=centrality_results['pagerank'][:10],
                top_cited_papers=centrality_results['citations'][:10],
                communities=communities,
                modularity=modularity,
                research_gaps=research_gaps,
                emerging_topics=emerging_topics,
                network_data=network_data,
                visualization_data=visualization_data
            )
            
            logger.info(f"Network analysis complete: {node_count} nodes, {edge_count} edges")
            return result
            
        except Exception as e:
            logger.error(f"Error in network analysis: {e}")
            raise
    
    async def _compute_centrality_metrics(self) -> Dict[str, List[Tuple[str, float]]]:
        """Compute various centrality metrics."""
        try:
            # Use ThreadPoolExecutor for CPU-intensive computations
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # Submit centrality computations
                betweenness_future = executor.submit(
                    nx.betweenness_centrality, self.citation_graph
                )
                closeness_future = executor.submit(
                    nx.closeness_centrality, self.citation_graph
                )
                pagerank_future = executor.submit(
                    nx.pagerank, self.citation_graph
                )
                
                # Get results
                betweenness_centrality = betweenness_future.result()
                closeness_centrality = closeness_future.result()
                pagerank_scores = pagerank_future.result()
            
            # Update node attributes
            for node_id in self.citation_graph.nodes:
                self.nodes[node_id].betweenness_centrality = betweenness_centrality.get(node_id, 0)
                self.nodes[node_id].closeness_centrality = closeness_centrality.get(node_id, 0)
                self.nodes[node_id].pagerank_score = pagerank_scores.get(node_id, 0)
            
            # Sort and return top papers
            top_betweenness = sorted(
                betweenness_centrality.items(), 
                key=lambda x: x[1], reverse=True
            )
            
            top_pagerank = sorted(
                pagerank_scores.items(), 
                key=lambda x: x[1], reverse=True
            )
            
            top_cited = sorted(
                [(node_id, node.citation_count) for node_id, node in self.nodes.items()],
                key=lambda x: x[1], reverse=True
            )
            
            return {
                'betweenness': top_betweenness,
                'pagerank': top_pagerank,
                'citations': top_cited
            }
            
        except Exception as e:
            logger.error(f"Error computing centrality metrics: {e}")
            return {'betweenness': [], 'pagerank': [], 'citations': []}
    
    async def _detect_communities(self) -> Tuple[Dict[int, List[str]], float]:
        """Detect communities in the citation network."""
        try:
            # Convert to undirected for community detection
            undirected_graph = self.citation_graph.to_undirected()
            
            # Use Louvain algorithm for community detection
            communities_dict = nx.community.louvain_communities(
                undirected_graph, 
                resolution=self.community_resolution,
                seed=42
            )
            
            # Convert to dict format
            communities = {}
            for i, community in enumerate(communities_dict):
                communities[i] = list(community)
                
                # Update node cluster assignments
                for node_id in community:
                    if node_id in self.nodes:
                        self.nodes[node_id].cluster_id = i
            
            # Calculate modularity
            modularity = nx.community.modularity(
                undirected_graph, communities_dict
            )
            
            logger.info(f"Detected {len(communities)} communities with modularity {modularity:.3f}")
            
            return communities, modularity
            
        except Exception as e:
            logger.error(f"Error detecting communities: {e}")
            return {}, 0.0
    
    async def _detect_research_gaps(self) -> List[Dict[str, Any]]:
        """Detect potential research gaps in the citation network."""
        try:
            gaps = []
            
            # Find underconnected topic areas
            # Group papers by keywords/topics
            topic_groups = defaultdict(list)
            for node_id, node in self.nodes.items():
                for keyword in node.keywords[:3]:  # Top 3 keywords
                    topic_groups[keyword].append(node_id)
            
            # Analyze connectivity between topic groups
            for topic, papers in topic_groups.items():
                if len(papers) < 3:  # Skip small topics
                    continue
                
                # Calculate internal and external connectivity
                internal_edges = 0
                external_edges = 0
                
                for paper1 in papers:
                    for paper2 in papers:
                        if self.citation_graph.has_edge(paper1, paper2):
                            internal_edges += 1
                    
                    for neighbor in self.citation_graph.neighbors(paper1):
                        if neighbor not in papers:
                            external_edges += 1
                
                # Low internal connectivity suggests gaps
                if internal_edges < len(papers) * 0.5:
                    gaps.append({
                        'topic': topic,
                        'paper_count': len(papers),
                        'internal_connectivity': internal_edges / max(len(papers) ** 2, 1),
                        'external_connectivity': external_edges / max(len(papers), 1),
                        'gap_type': 'internal_fragmentation',
                        'severity': 'medium' if internal_edges == 0 else 'low'
                    })
            
            # Find temporal gaps (years with few publications)
            year_counts = Counter(node.year for node in self.nodes.values() if node.year > 1900)
            if year_counts:
                years = sorted(year_counts.keys())
                for i in range(1, len(years)):
                    if years[i] - years[i-1] > 2:  # Gap > 2 years
                        gaps.append({
                            'topic': 'temporal_gap',
                            'gap_start': years[i-1],
                            'gap_end': years[i],
                            'gap_duration': years[i] - years[i-1],
                            'gap_type': 'temporal',
                            'severity': 'high' if years[i] - years[i-1] > 5 else 'medium'
                        })
            
            return sorted(gaps, key=lambda x: x.get('severity', 'low'), reverse=True)
            
        except Exception as e:
            logger.error(f"Error detecting research gaps: {e}")
            return []
    
    async def _detect_emerging_topics(self) -> List[Dict[str, Any]]:
        """Detect emerging topics and trends."""
        try:
            emerging = []
            
            # Find recent highly-cited papers
            recent_papers = [
                node for node in self.nodes.values() 
                if node.year >= datetime.now().year - 3  # Last 3 years
            ]
            
            if not recent_papers:
                return emerging
            
            # Sort by citation velocity (citations per year since publication)
            current_year = datetime.now().year
            
            for paper in recent_papers:
                years_since_pub = max(current_year - paper.year, 1)
                citation_velocity = paper.citation_count / years_since_pub
                
                if citation_velocity > 2.0:  # Threshold for emerging
                    emerging.append({
                        'paper_id': paper.paper_id,
                        'title': paper.title,
                        'year': paper.year,
                        'citation_velocity': citation_velocity,
                        'total_citations': paper.citation_count,
                        'keywords': paper.keywords,
                        'trend_strength': 'high' if citation_velocity > 5.0 else 'medium'
                    })
            
            # Find keyword trends
            recent_keywords = []
            for paper in recent_papers:
                recent_keywords.extend(paper.keywords)
            
            keyword_counts = Counter(recent_keywords)
            for keyword, count in keyword_counts.most_common(10):
                if count >= 3:  # Minimum frequency
                    emerging.append({
                        'topic': keyword,
                        'paper_count': count,
                        'trend_type': 'keyword_frequency',
                        'trend_strength': 'high' if count > 5 else 'medium'
                    })
            
            return emerging[:20]  # Top 20 emerging topics
            
        except Exception as e:
            logger.error(f"Error detecting emerging topics: {e}")
            return []
    
    def _prepare_network_data(self) -> Dict[str, Any]:
        """Prepare network data for export."""
        return {
            'nodes': [
                {
                    'id': node_id,
                    'title': node.title,
                    'authors': node.authors,
                    'year': node.year,
                    'citation_count': node.citation_count,
                    'betweenness_centrality': node.betweenness_centrality,
                    'pagerank_score': node.pagerank_score,
                    'cluster_id': node.cluster_id,
                    'keywords': node.keywords
                }
                for node_id, node in self.nodes.items()
            ],
            'edges': [
                {
                    'source': edge.source_id,
                    'target': edge.target_id,
                    'type': edge.citation_type,
                    'strength': edge.strength
                }
                for edge in self.edges
            ]
        }
    
    def _prepare_visualization_data(self) -> Dict[str, Any]:
        """Prepare data optimized for network visualization."""
        # Sample nodes for large networks
        max_viz_nodes = 500
        nodes_to_include = list(self.nodes.keys())[:max_viz_nodes]
        
        viz_nodes = []
        viz_edges = []
        
        for node_id in nodes_to_include:
            node = self.nodes[node_id]
            viz_nodes.append({
                'id': node_id,
                'label': node.title[:50] + '...' if len(node.title) > 50 else node.title,
                'size': min(node.citation_count * 2 + 5, 20),
                'color': f"hsl({(node.cluster_id or 0) * 137 % 360}, 70%, 50%)",
                'year': node.year,
                'citations': node.citation_count
            })
        
        for edge in self.edges:
            if edge.source_id in nodes_to_include and edge.target_id in nodes_to_include:
                viz_edges.append({
                    'source': edge.source_id,
                    'target': edge.target_id,
                    'weight': edge.strength
                })
        
        return {
            'nodes': viz_nodes,
            'edges': viz_edges,
            'layout': 'force-directed',
            'metadata': {
                'total_nodes': len(self.nodes),
                'displayed_nodes': len(viz_nodes),
                'total_edges': len(self.edges),
                'displayed_edges': len(viz_edges)
            }
        }
    
    def save_network(self, filepath: str) -> None:
        """Save network to file."""
        try:
            network_data = {
                'nodes': {node_id: node.__dict__ for node_id, node in self.nodes.items()},
                'edges': [edge.__dict__ for edge in self.edges],
                'graph': nx.node_link_data(self.citation_graph)
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(network_data, f)
                
            logger.info(f"Network saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving network: {e}")
            raise
    
    def load_network(self, filepath: str) -> None:
        """Load network from file."""
        try:
            with open(filepath, 'rb') as f:
                network_data = pickle.load(f)
            
            # Restore nodes
            self.nodes = {}
            for node_id, node_dict in network_data['nodes'].items():
                node = CitationNode(**node_dict)
                # Convert sets back from lists if needed
                if isinstance(node.citations, list):
                    node.citations = set(node.citations)
                if isinstance(node.cited_by, list):
                    node.cited_by = set(node.cited_by)
                self.nodes[node_id] = node
            
            # Restore edges
            self.edges = [CitationEdge(**edge_dict) for edge_dict in network_data['edges']]
            
            # Restore graph
            self.citation_graph = nx.node_link_graph(network_data['graph'])
            
            logger.info(f"Network loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading network: {e}")
            raise
    
    def get_network_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the network."""
        if not self.nodes:
            return {'status': 'empty', 'message': 'No network data available'}
        
        return {
            'status': 'active',
            'node_count': len(self.nodes),
            'edge_count': len(self.edges),
            'density': nx.density(self.citation_graph) if self.citation_graph.nodes else 0,
            'most_cited_paper': max(
                self.nodes.items(), 
                key=lambda x: x[1].citation_count,
                default=('', CitationNode('', '', [], 0, ''))
            )[1].title if self.nodes else 'None',
            'year_range': (
                min(node.year for node in self.nodes.values() if node.year > 1900),
                max(node.year for node in self.nodes.values())
            ) if self.nodes else (0, 0),
            'total_journals': len(set(node.journal for node in self.nodes.values() if node.journal)),
            'analysis_cached': bool(self.analysis_cache)
        }

# Global analyzer instance
_citation_analyzer: Optional[CitationNetworkAnalyzer] = None

def get_citation_analyzer() -> CitationNetworkAnalyzer:
    """Get global citation network analyzer instance."""
    global _citation_analyzer
    if _citation_analyzer is None:
        _citation_analyzer = CitationNetworkAnalyzer()
    return _citation_analyzer