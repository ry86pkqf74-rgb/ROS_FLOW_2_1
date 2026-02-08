"""Literature Ranking and Prioritization Worker"""
from __future__ import annotations
from typing import List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel
from workers.search_worker import SearchResult


PriorityTier = Literal["Must Read", "Should Read", "Optional"]


class ScoredPaper(BaseModel):
    """Paper with multi-criteria scoring"""
    # Original paper data
    title: str
    authors: List[str] | None = None
    journal: str | None = None
    publication_date: str | None = None
    abstract: str | None = None
    url: str | None = None
    doi: str | None = None
    citation_count: int | None = None
    
    # Scoring data
    rank: int
    recency_score: float
    relevance_score: float
    journal_score: float
    author_score: float
    citation_score: float
    composite_score: float
    tier: PriorityTier
    rationale: str


class RankingCriteria(BaseModel):
    """Weights for multi-criteria scoring"""
    recency_weight: float = 0.20
    relevance_weight: float = 0.30
    journal_weight: float = 0.20
    author_weight: float = 0.15
    citation_weight: float = 0.15


class LiteratureRankingWorker:
    """
    Ranks and prioritizes papers using multi-criteria scoring.
    
    Based on the LangSmith agent configuration, applies a composite scoring model:
    - Recency (20%): Publication date
    - Keyword Relevance (30%): Match to user query
    - Journal Impact (20%): Journal reputation
    - Author Reputation (15%): Author credentials
    - Citation Count (15%): Citation impact
    """
    
    def __init__(self, criteria: RankingCriteria | None = None):
        self.criteria = criteria or RankingCriteria()
        
    def rank_papers(
        self,
        papers: List[SearchResult],
        query: str,
        user_priorities: Dict[str, Any] | None = None
    ) -> List[ScoredPaper]:
        """
        Rank papers using multi-criteria scoring
        
        Args:
            papers: List of papers to rank
            query: Original user query for relevance scoring
            user_priorities: Optional user-specified priorities
            
        Returns:
            List of ScoredPaper objects sorted by composite score (highest first)
        """
        scored_papers = []
        
        for paper in papers:
            scores = self._calculate_scores(paper, query)
            composite = self._calculate_composite_score(scores)
            tier = self._assign_tier(composite)
            rationale = self._generate_rationale(paper, scores, composite)
            
            scored_papers.append(ScoredPaper(
                # Paper data
                title=paper.title,
                authors=paper.authors,
                journal=paper.journal,
                publication_date=paper.publication_date,
                abstract=paper.abstract,
                url=paper.url,
                doi=paper.doi,
                citation_count=paper.citation_count,
                # Scoring data
                rank=0,  # Will be set after sorting
                recency_score=scores["recency"],
                relevance_score=scores["relevance"],
                journal_score=scores["journal"],
                author_score=scores["author"],
                citation_score=scores["citation"],
                composite_score=composite,
                tier=tier,
                rationale=rationale
            ))
        
        # Sort by composite score (highest first)
        scored_papers.sort(key=lambda p: p.composite_score, reverse=True)
        
        # Assign ranks
        for i, paper in enumerate(scored_papers, 1):
            paper.rank = i
            
        return scored_papers
    
    def _calculate_scores(
        self,
        paper: SearchResult,
        query: str
    ) -> Dict[str, float]:
        """Calculate individual dimension scores (1-10 scale)"""
        return {
            "recency": self._score_recency(paper.publication_date),
            "relevance": self._score_relevance(paper, query),
            "journal": self._score_journal(paper.journal),
            "author": self._score_author(paper.authors),
            "citation": self._score_citations(paper.citation_count, paper.publication_date)
        }
    
    def _score_recency(self, publication_date: str | None) -> float:
        """
        Score paper recency (1-10 scale)
        
        - 10: Last month
        - 8: Last 3 months
        - 6: Last 6 months
        - 4: Last year
        - 2: Last 2 years
        - 1: Older
        """
        if not publication_date:
            return 1.0
            
        try:
            pub_date = datetime.fromisoformat(publication_date.replace('Z', '+00:00'))
            days_old = (datetime.now().astimezone() - pub_date).days
            
            if days_old < 30:
                return 10.0
            elif days_old < 90:
                return 8.0
            elif days_old < 180:
                return 6.0
            elif days_old < 365:
                return 4.0
            elif days_old < 730:
                return 2.0
            else:
                return 1.0
        except:
            return 1.0
    
    def _score_relevance(self, paper: SearchResult, query: str) -> float:
        """
        Score keyword relevance (1-10 scale)
        
        - 10: Directly addresses exact research question
        - 7: Highly related topic
        - 4: Tangentially related
        - 1: Weak connection
        """
        query_terms = set(query.lower().split())
        title_text = (paper.title or "").lower()
        abstract_text = (paper.abstract or "").lower()
        
        # Count matching terms
        title_matches = sum(1 for term in query_terms if term in title_text)
        abstract_matches = sum(1 for term in query_terms if term in abstract_text)
        
        # Weight title matches more heavily
        match_score = (title_matches * 2) + abstract_matches
        total_terms = len(query_terms)
        
        if total_terms == 0:
            return 5.0
            
        # Normalize to 1-10 scale
        match_ratio = match_score / (total_terms * 3)  # Title can contribute 2x
        
        if match_ratio >= 0.8:
            return 10.0
        elif match_ratio >= 0.5:
            return 7.0
        elif match_ratio >= 0.2:
            return 4.0
        else:
            return max(1.0, match_ratio * 10)
    
    def _score_journal(self, journal: str | None) -> float:
        """
        Score journal impact (1-10 scale)
        
        - 10: Top-tier (NEJM, Lancet, JAMA, Nature, Science, BMJ, Nature Medicine)
        - 8: High-impact specialty journals
        - 6: Solid peer-reviewed journals
        - 4: Regional or niche journals
        - 2: Preprint servers
        - 1: Unknown
        """
        if not journal:
            return 1.0
            
        journal_lower = journal.lower()
        
        # Top-tier journals
        top_tier = [
            "new england journal of medicine", "nejm",
            "lancet", "jama", "nature", "science",
            "bmj", "british medical journal", "nature medicine"
        ]
        if any(tier in journal_lower for tier in top_tier):
            return 10.0
            
        # High-impact specialty
        high_impact = [
            "annals of internal medicine", "circulation",
            "journal of clinical oncology", "jco",
            "cell", "plos medicine", "bmj open"
        ]
        if any(journal_name in journal_lower for journal_name in high_impact):
            return 8.0
            
        # Preprint servers
        preprints = ["biorxiv", "medrxiv", "arxiv"]
        if any(preprint in journal_lower for preprint in preprints):
            return 2.0
            
        # Default to solid peer-reviewed
        return 6.0
    
    def _score_author(self, authors: List[str] | None) -> float:
        """
        Score author reputation (1-10 scale)
        
        In production, this would check:
        - H-index
        - Institutional affiliations
        - Prior publication record
        
        For now, uses heuristics based on author count and format
        """
        if not authors or len(authors) == 0:
            return 1.0
            
        # More authors often indicates institutional backing
        if len(authors) >= 10:
            return 7.0
        elif len(authors) >= 5:
            return 6.0
        elif len(authors) >= 3:
            return 5.0
        else:
            return 4.0
    
    def _score_citations(
        self,
        citation_count: int | None,
        publication_date: str | None
    ) -> float:
        """
        Score citation impact (1-10 scale)
        
        Adjusts for recency - newer papers have less time to accumulate citations
        """
        if citation_count is None:
            return 1.0
            
        # Adjust expectations based on paper age
        try:
            if publication_date:
                pub_date = datetime.fromisoformat(publication_date.replace('Z', '+00:00'))
                years_old = (datetime.now().astimezone() - pub_date).days / 365.25
            else:
                years_old = 1.0
        except:
            years_old = 1.0
            
        # Expected citations per year for different tiers
        citations_per_year = citation_count / max(years_old, 0.1)
        
        if citations_per_year >= 100:
            return 10.0
        elif citations_per_year >= 50:
            return 7.0
        elif citations_per_year >= 10:
            return 4.0
        else:
            return max(1.0, citations_per_year / 10)
    
    def _calculate_composite_score(self, scores: Dict[str, float]) -> float:
        """
        Calculate weighted composite score (0-100 scale)
        
        Composite = (Recency × 0.20) + (Relevance × 0.30) + (Journal × 0.20) 
                    + (Author × 0.15) + (Citations × 0.15)
        """
        composite = (
            scores["recency"] * self.criteria.recency_weight +
            scores["relevance"] * self.criteria.relevance_weight +
            scores["journal"] * self.criteria.journal_weight +
            scores["author"] * self.criteria.author_weight +
            scores["citation"] * self.criteria.citation_weight
        )
        
        # Scale to 0-100
        return composite * 10.0
    
    def _assign_tier(self, composite_score: float) -> PriorityTier:
        """
        Assign priority tier based on composite score
        
        - Tier 1 (Must Read): Score ≥ 75
        - Tier 2 (Should Read): Score 50-74
        - Tier 3 (Optional): Score < 50
        """
        if composite_score >= 75:
            return "Must Read"
        elif composite_score >= 50:
            return "Should Read"
        else:
            return "Optional"
    
    def _generate_rationale(
        self,
        paper: SearchResult,
        scores: Dict[str, float],
        composite_score: float
    ) -> str:
        """Generate 1-2 sentence rationale for ranking"""
        strengths = []
        
        if scores["relevance"] >= 7:
            strengths.append("highly relevant to query")
        if scores["journal"] >= 8:
            strengths.append("published in top-tier journal")
        if scores["recency"] >= 6:
            strengths.append("recent publication")
        if scores["citation"] >= 7:
            strengths.append("highly cited")
            
        if strengths:
            return f"This paper scored {composite_score:.1f}/100 due to: {', '.join(strengths)}."
        else:
            return f"This paper scored {composite_score:.1f}/100 with moderate relevance and impact."
