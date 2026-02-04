"""
Enhanced Semantic Scholar Integration with Advanced Features

This module provides advanced Semantic Scholar integration including:
- Citation network analysis
- Research trend analysis  
- Author influence scoring
- Paper recommendation engine
- Knowledge gap detection
- Collaboration network mapping

Author: Literature Enhancement Team
"""

import json
import logging
import asyncio
import aiohttp
import networkx as nx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans

from src.online_literature.provider import OnlineLiteratureProvider, PaperMetadata
from src.runtime_config import RuntimeConfig

logger = logging.getLogger(__name__)

@dataclass
class EnhancedPaperMetadata(PaperMetadata):
    """Enhanced paper metadata with additional Semantic Scholar data."""
    
    # Citation metrics
    citation_count: int = 0
    influential_citation_count: int = 0
    h_index: Optional[int] = None
    
    # Publication metrics
    venue_type: Optional[str] = None
    is_open_access: bool = False
    publication_date: Optional[datetime] = None
    
    # Content analysis
    fields_of_study: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    # Network metrics
    citation_velocity: Optional[float] = None  # Citations per year since publication
    influence_score: Optional[float] = None   # PageRank-based influence
    novelty_score: Optional[float] = None     # How unique compared to existing work
    
    # Relationships
    references: List[str] = field(default_factory=list)  # Referenced paper IDs
    citations: List[str] = field(default_factory=list)   # Citing paper IDs
    related_papers: List[str] = field(default_factory=list)
    
    # Quality indicators
    venue_impact_factor: Optional[float] = None
    author_reputation_score: Optional[float] = None

@dataclass  
class AuthorProfile:
    """Enhanced author profile with network metrics."""
    
    author_id: str
    name: str
    
    # Publication metrics
    paper_count: int = 0
    citation_count: int = 0
    h_index: int = 0
    i10_index: int = 0
    
    # Network metrics
    collaboration_network_size: int = 0
    centrality_score: Optional[float] = None
    influence_score: Optional[float] = None
    
    # Research focus
    primary_fields: List[str] = field(default_factory=list)
    research_topics: List[str] = field(default_factory=list)
    
    # Temporal patterns
    publication_timeline: List[Tuple[int, int]] = field(default_factory=list)  # (year, paper_count)
    recent_activity_score: Optional[float] = None

@dataclass
class ResearchTrend:
    """Research trend analysis results."""
    
    topic: str
    
    # Trend metrics
    paper_count_trend: List[Tuple[int, int]] = field(default_factory=list)  # (year, count)
    citation_trend: List[Tuple[int, int]] = field(default_factory=list)
    growth_rate: Optional[float] = None
    momentum_score: Optional[float] = None
    
    # Key contributors
    top_authors: List[str] = field(default_factory=list)
    top_venues: List[str] = field(default_factory=list)
    influential_papers: List[str] = field(default_factory=list)
    
    # Future predictions
    predicted_growth: Optional[float] = None
    emerging_subtopics: List[str] = field(default_factory=list)

@dataclass
class KnowledgeGap:
    """Identified knowledge gap in research."""
    
    gap_id: str
    description: str
    
    # Gap characteristics
    confidence_score: float
    potential_impact: Optional[float] = None
    research_difficulty: Optional[str] = None
    
    # Context
    related_topics: List[str] = field(default_factory=list)
    missing_connections: List[Tuple[str, str]] = field(default_factory=list)
    potential_methodologies: List[str] = field(default_factory=list)
    
    # Recommendations
    suggested_research_directions: List[str] = field(default_factory=list)
    relevant_funding_opportunities: List[str] = field(default_factory=list)

class EnhancedSemanticScholarProvider:
    """
    Enhanced Semantic Scholar provider with advanced analytics capabilities.
    
    Features:
    - Citation network analysis
    - Research trend detection
    - Author influence scoring
    - Paper recommendation engine
    - Knowledge gap identification
    - Collaboration network mapping
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 base_url: str = "https://api.semanticscholar.org/graph/v1",
                 rate_limit_per_second: int = 10):
        """Initialize enhanced Semantic Scholar provider."""
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limit = rate_limit_per_second
        
        # Analytics components
        self.citation_graph = nx.DiGraph()
        self.author_network = nx.Graph()
        self.paper_cache: Dict[str, EnhancedPaperMetadata] = {}
        self.author_cache: Dict[str, AuthorProfile] = {}
        
        # ML models for recommendations
        self.tfidf_vectorizer = TfidfVectorizer(max_features=10000, stop_words='english')
        self.paper_embeddings: Optional[np.ndarray] = None
        self.recommendation_model = None
        
        logger.info("Enhanced Semantic Scholar Provider initialized")
    
    async def search_enhanced(self,
                            topic: str,
                            max_results: int = 50,
                            include_citations: bool = True,
                            include_references: bool = True,
                            analyze_trends: bool = True) -> Dict[str, Any]:
        """
        Enhanced search with comprehensive analysis.
        
        Args:
            topic: Search query
            max_results: Maximum results to return
            include_citations: Whether to fetch citation data
            include_references: Whether to fetch reference data
            analyze_trends: Whether to perform trend analysis
            
        Returns:
            Dictionary containing papers, trends, gaps, and recommendations
        """
        try:
            # Network governance check
            cfg = RuntimeConfig.from_env_and_optional_yaml(None)
            if cfg.no_network:
                raise RuntimeError("NO_NETWORK=1 blocks Semantic Scholar calls")
            
            # Perform base search
            papers = await self._search_papers_advanced(topic, max_results)
            
            # Build citation network if requested
            citation_network = None
            if include_citations or include_references:
                citation_network = await self._build_citation_network(papers)
            
            # Analyze research trends
            trends = None
            if analyze_trends:
                trends = await self._analyze_research_trends(topic, papers)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(papers, topic)
            
            # Identify knowledge gaps
            knowledge_gaps = await self._identify_knowledge_gaps(papers, topic)
            
            # Calculate influence scores
            influence_scores = self._calculate_influence_scores(papers, citation_network)
            
            return {
                "papers": papers,
                "trends": trends,
                "recommendations": recommendations,
                "knowledge_gaps": knowledge_gaps,
                "influence_scores": influence_scores,
                "citation_network": citation_network,
                "search_metadata": {
                    "query": topic,
                    "timestamp": datetime.now().isoformat(),
                    "result_count": len(papers),
                    "analysis_version": "enhanced_v1.0"
                }
            }
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            raise
    
    async def _search_papers_advanced(self, topic: str, max_results: int) -> List[EnhancedPaperMetadata]:
        """Search papers with enhanced metadata."""
        try:
            async with aiohttp.ClientSession() as session:
                # Extended field list for comprehensive data
                fields = [
                    "title", "year", "authors", "doi", "url", "abstract",
                    "citationCount", "influentialCitationCount", "isOpenAccess",
                    "fieldsOfStudy", "s2FieldsOfStudy", "publicationDate",
                    "venue", "references", "citations", "embedding"
                ]
                
                headers = {"Accept": "application/json"}
                if self.api_key:
                    headers["x-api-key"] = self.api_key
                
                url = f"{self.base_url}/paper/search"
                params = {
                    "query": topic,
                    "limit": max_results,
                    "fields": ",".join(fields)
                }
                
                async with session.get(url, headers=headers, params=params) as response:
                    data = await response.json()
                
                papers = []
                for item in data.get("data", []):
                    paper = self._parse_enhanced_paper(item)
                    papers.append(paper)
                    
                    # Cache for later use
                    if paper.doi:
                        self.paper_cache[paper.doi] = paper
                
                logger.info(f"Retrieved {len(papers)} papers for topic: {topic}")
                return papers
                
        except Exception as e:
            logger.error(f"Advanced paper search failed: {e}")
            raise
    
    def _parse_enhanced_paper(self, data: Dict[str, Any]) -> EnhancedPaperMetadata:
        """Parse API response into enhanced paper metadata."""
        try:
            # Basic metadata
            title = data.get("title", "").strip() or "Untitled"
            authors = [
                author.get("name", "").strip() 
                for author in data.get("authors", [])
                if author.get("name", "").strip()
            ]
            year = data.get("year")
            doi = data.get("doi")
            url = data.get("url")
            abstract = data.get("abstract", "").strip()
            
            # Enhanced metadata
            citation_count = data.get("citationCount", 0)
            influential_citation_count = data.get("influentialCitationCount", 0)
            is_open_access = data.get("isOpenAccess", False)
            
            # Parse publication date
            publication_date = None
            if data.get("publicationDate"):
                try:
                    publication_date = datetime.fromisoformat(data["publicationDate"].replace("Z", "+00:00"))
                except:
                    pass
            
            # Fields of study
            fields_of_study = []
            if data.get("fieldsOfStudy"):
                fields_of_study = [field for field in data["fieldsOfStudy"] if field]
            
            # S2 fields (more detailed)
            if data.get("s2FieldsOfStudy"):
                s2_fields = [field.get("category", "") for field in data["s2FieldsOfStudy"]]
                fields_of_study.extend([f for f in s2_fields if f and f not in fields_of_study])
            
            # Venue information
            venue_info = data.get("venue", {}) if data.get("venue") else {}
            venue = venue_info.get("name") if isinstance(venue_info, dict) else str(venue_info)
            venue_type = venue_info.get("type") if isinstance(venue_info, dict) else None
            
            # References and citations (IDs only for now)
            references = []
            if data.get("references"):
                references = [ref.get("paperId") for ref in data["references"] if ref.get("paperId")]
            
            citations = []
            if data.get("citations"):
                citations = [cit.get("paperId") for cit in data["citations"] if cit.get("paperId")]
            
            # Embedding for similarity calculations
            embedding = data.get("embedding", {}).get("vector") if data.get("embedding") else None
            
            # Calculate derived metrics
            citation_velocity = None
            if year and citation_count > 0:
                years_since_publication = max(1, datetime.now().year - int(year))
                citation_velocity = citation_count / years_since_publication
            
            return EnhancedPaperMetadata(
                title=title,
                authors=authors,
                year=int(year) if year else None,
                venue=venue,
                doi=doi,
                url=url,
                abstract=abstract,
                citation_count=citation_count,
                influential_citation_count=influential_citation_count,
                is_open_access=is_open_access,
                publication_date=publication_date,
                fields_of_study=fields_of_study,
                embedding=embedding,
                references=references,
                citations=citations,
                citation_velocity=citation_velocity,
                venue_type=venue_type
            )
            
        except Exception as e:
            logger.error(f"Error parsing enhanced paper data: {e}")
            # Return basic metadata if parsing fails
            return EnhancedPaperMetadata(
                title=data.get("title", "Untitled"),
                authors=[a.get("name", "") for a in data.get("authors", [])],
                year=data.get("year"),
                doi=data.get("doi"),
                url=data.get("url"),
                abstract=data.get("abstract")
            )
    
    async def _build_citation_network(self, papers: List[EnhancedPaperMetadata]) -> nx.DiGraph:
        """Build citation network graph from papers."""
        try:
            G = nx.DiGraph()
            
            # Add nodes (papers)
            for paper in papers:
                paper_id = paper.doi or paper.title
                G.add_node(paper_id, 
                          title=paper.title,
                          year=paper.year,
                          citation_count=paper.citation_count,
                          fields=paper.fields_of_study)
            
            # Add edges (citations)
            for paper in papers:
                paper_id = paper.doi or paper.title
                
                # References (this paper cites others)
                for ref_id in paper.references:
                    if ref_id in [p.doi for p in papers if p.doi]:
                        G.add_edge(paper_id, ref_id, relation="cites")
                
                # Citations (other papers cite this one)
                for cit_id in paper.citations:
                    if cit_id in [p.doi for p in papers if p.doi]:
                        G.add_edge(cit_id, paper_id, relation="cites")
            
            logger.info(f"Built citation network with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            return G
            
        except Exception as e:
            logger.error(f"Error building citation network: {e}")
            return nx.DiGraph()
    
    async def _analyze_research_trends(self, topic: str, papers: List[EnhancedPaperMetadata]) -> ResearchTrend:
        """Analyze research trends for the given topic."""
        try:
            # Group papers by year
            papers_by_year = defaultdict(list)
            for paper in papers:
                if paper.year:
                    papers_by_year[paper.year].append(paper)
            
            # Calculate year-over-year trends
            years = sorted(papers_by_year.keys())
            paper_count_trend = [(year, len(papers_by_year[year])) for year in years]
            
            # Calculate citation trends
            citation_trend = []
            for year in years:
                total_citations = sum(paper.citation_count for paper in papers_by_year[year])
                citation_trend.append((year, total_citations))
            
            # Calculate growth rate
            growth_rate = None
            if len(paper_count_trend) >= 2:
                recent_count = sum(count for year, count in paper_count_trend[-3:])
                earlier_count = sum(count for year, count in paper_count_trend[:3])
                if earlier_count > 0:
                    growth_rate = (recent_count - earlier_count) / earlier_count
            
            # Find top authors
            author_counts = defaultdict(int)
            for paper in papers:
                for author in paper.authors:
                    author_counts[author] += 1
            
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_authors = [author for author, count in top_authors]
            
            # Find top venues
            venue_counts = defaultdict(int)
            for paper in papers:
                if paper.venue:
                    venue_counts[paper.venue] += 1
            
            top_venues = sorted(venue_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_venues = [venue for venue, count in top_venues]
            
            # Find influential papers (by citation count)
            influential_papers = sorted(papers, 
                                      key=lambda p: p.citation_count, 
                                      reverse=True)[:10]
            influential_paper_titles = [p.title for p in influential_papers]
            
            # Calculate momentum score (recent activity relative to historical)
            momentum_score = None
            if len(years) >= 3:
                recent_years = years[-2:]  # Last 2 years
                historical_years = years[:-2]  # Earlier years
                
                if historical_years:
                    recent_avg = sum(papers_by_year[year] for year in recent_years) / len(recent_years) if recent_years else 0
                    historical_avg = sum(papers_by_year[year] for year in historical_years) / len(historical_years)
                    
                    if historical_avg > 0:
                        momentum_score = recent_avg / historical_avg
            
            return ResearchTrend(
                topic=topic,
                paper_count_trend=paper_count_trend,
                citation_trend=citation_trend,
                growth_rate=growth_rate,
                momentum_score=momentum_score,
                top_authors=top_authors,
                top_venues=top_venues,
                influential_papers=influential_paper_titles
            )
            
        except Exception as e:
            logger.error(f"Error analyzing research trends: {e}")
            return ResearchTrend(topic=topic)
    
    async def _generate_recommendations(self, papers: List[EnhancedPaperMetadata], topic: str) -> List[Dict[str, Any]]:
        """Generate paper recommendations using content similarity and network analysis."""
        try:
            if not papers:
                return []
            
            # Prepare text data for similarity analysis
            paper_texts = []
            valid_papers = []
            
            for paper in papers:
                text_content = f"{paper.title} {paper.abstract or ''}"
                if text_content.strip():
                    paper_texts.append(text_content)
                    valid_papers.append(paper)
            
            if len(paper_texts) < 2:
                return []
            
            # Calculate TF-IDF similarity
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(paper_texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            recommendations = []
            
            # For each paper, find most similar papers
            for i, paper in enumerate(valid_papers):
                similarities = similarity_matrix[i]
                # Get top 5 most similar papers (excluding self)
                similar_indices = np.argsort(similarities)[::-1][1:6]
                
                similar_papers = []
                for idx in similar_indices:
                    if similarities[idx] > 0.1:  # Threshold for relevance
                        similar_papers.append({
                            "title": valid_papers[idx].title,
                            "similarity_score": float(similarities[idx]),
                            "citation_count": valid_papers[idx].citation_count,
                            "year": valid_papers[idx].year
                        })
                
                if similar_papers:
                    recommendations.append({
                        "source_paper": {
                            "title": paper.title,
                            "citation_count": paper.citation_count
                        },
                        "recommended_papers": similar_papers
                    })
            
            # Sort recommendations by source paper citation count (most influential first)
            recommendations.sort(key=lambda x: x["source_paper"]["citation_count"], reverse=True)
            
            logger.info(f"Generated {len(recommendations)} recommendation sets")
            return recommendations[:20]  # Return top 20 recommendation sets
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _identify_knowledge_gaps(self, papers: List[EnhancedPaperMetadata], topic: str) -> List[KnowledgeGap]:
        """Identify potential knowledge gaps in the research area."""
        try:
            # Analyze field combinations
            field_combinations = defaultdict(int)
            all_fields = set()
            
            for paper in papers:
                if len(paper.fields_of_study) >= 2:
                    # Count co-occurrence of fields
                    for i, field1 in enumerate(paper.fields_of_study):
                        all_fields.add(field1)
                        for field2 in paper.fields_of_study[i+1:]:
                            all_fields.add(field2)
                            combo = tuple(sorted([field1, field2]))
                            field_combinations[combo] += 1
            
            # Identify under-researched combinations
            gaps = []
            all_fields_list = list(all_fields)
            
            for i, field1 in enumerate(all_fields_list):
                for field2 in all_fields_list[i+1:]:
                    combo = tuple(sorted([field1, field2]))
                    if combo not in field_combinations:
                        # This combination doesn't exist in our dataset
                        gap_id = f"gap_{hash(combo) % 10000}"
                        
                        gaps.append(KnowledgeGap(
                            gap_id=gap_id,
                            description=f"Limited research connecting {field1} and {field2} in {topic}",
                            confidence_score=0.7,  # Medium confidence for missing combinations
                            related_topics=[field1, field2],
                            missing_connections=[(field1, field2)],
                            suggested_research_directions=[
                                f"Investigate applications of {field1} in {field2}",
                                f"Develop {field2} approaches using {field1} principles"
                            ]
                        ))
            
            # Identify temporal gaps (years with few publications)
            year_counts = defaultdict(int)
            for paper in papers:
                if paper.year:
                    year_counts[paper.year] += 1
            
            if year_counts:
                years = sorted(year_counts.keys())
                avg_papers_per_year = sum(year_counts.values()) / len(years)
                
                for year in range(min(years), max(years) + 1):
                    if year_counts[year] < avg_papers_per_year * 0.3:  # Less than 30% of average
                        gaps.append(KnowledgeGap(
                            gap_id=f"temporal_gap_{year}",
                            description=f"Limited research activity in {topic} during {year}",
                            confidence_score=0.6,
                            related_topics=[topic],
                            suggested_research_directions=[
                                f"Investigate why research activity was low in {year}",
                                f"Review developments in {year} that might be relevant today"
                            ]
                        ))
            
            # Sort gaps by confidence score
            gaps.sort(key=lambda x: x.confidence_score, reverse=True)
            
            logger.info(f"Identified {len(gaps)} potential knowledge gaps")
            return gaps[:10]  # Return top 10 gaps
            
        except Exception as e:
            logger.error(f"Error identifying knowledge gaps: {e}")
            return []
    
    def _calculate_influence_scores(self, papers: List[EnhancedPaperMetadata], graph: Optional[nx.DiGraph]) -> Dict[str, float]:
        """Calculate influence scores using PageRank algorithm."""
        try:
            if not graph or graph.number_of_nodes() == 0:
                # Fallback to citation count based scoring
                scores = {}
                max_citations = max((p.citation_count for p in papers), default=1)
                for paper in papers:
                    paper_id = paper.doi or paper.title
                    scores[paper_id] = paper.citation_count / max_citations
                return scores
            
            # Use PageRank for more sophisticated influence scoring
            pagerank_scores = nx.pagerank(graph, alpha=0.85, max_iter=100)
            
            logger.info(f"Calculated influence scores for {len(pagerank_scores)} papers")
            return pagerank_scores
            
        except Exception as e:
            logger.error(f"Error calculating influence scores: {e}")
            return {}
    
    async def get_research_collaboration_network(self, authors: List[str]) -> nx.Graph:
        """Build collaboration network for given authors."""
        try:
            G = nx.Graph()
            
            # This would require additional API calls to get author collaboration data
            # For now, return empty graph
            logger.info("Collaboration network analysis requires extended implementation")
            
            return G
            
        except Exception as e:
            logger.error(f"Error building collaboration network: {e}")
            return nx.Graph()
    
    async def predict_research_trends(self, topic: str, historical_data: ResearchTrend) -> Dict[str, Any]:
        """Predict future research trends based on historical data."""
        try:
            predictions = {
                "topic": topic,
                "predictions": {}
            }
            
            # Simple linear trend prediction
            if historical_data.paper_count_trend and len(historical_data.paper_count_trend) >= 3:
                years = [year for year, count in historical_data.paper_count_trend]
                counts = [count for year, count in historical_data.paper_count_trend]
                
                # Linear regression for simple prediction
                if len(years) >= 2:
                    # Calculate slope
                    n = len(years)
                    sum_x = sum(years)
                    sum_y = sum(counts)
                    sum_xy = sum(x * y for x, y in zip(years, counts))
                    sum_x_squared = sum(x * x for x in years)
                    
                    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x_squared - sum_x * sum_x)
                    intercept = (sum_y - slope * sum_x) / n
                    
                    # Predict next 3 years
                    current_year = max(years)
                    future_years = [current_year + i for i in range(1, 4)]
                    predicted_counts = [slope * year + intercept for year in future_years]
                    
                    predictions["predictions"]["paper_count"] = [
                        (year, max(0, count)) for year, count in zip(future_years, predicted_counts)
                    ]
                    
                    predictions["predictions"]["growth_trend"] = "increasing" if slope > 0 else "decreasing"
                    predictions["predictions"]["confidence"] = 0.6  # Medium confidence for simple model
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting research trends: {e}")
            return {"topic": topic, "predictions": {}}