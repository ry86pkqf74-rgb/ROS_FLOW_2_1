"""
LitSearchAgent - Stage 6: Automated Literature Search

Automated literature searches across PubMed, Semantic Scholar with:
- PICO framework for structured search
- Multi-database orchestration
- AI-powered relevance ranking
- Multi-style citation generation

Linear Issues: ROS-XXX
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
import httpx

# Import base agent
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

# Import search strategies and formatters
from .search_strategies import (
    PICOFramework,
    SearchQueryBuilder,
    MeSHTermExpander,
    DatabaseType,
    PaperDeduplicator,
)
from .citation_formatters import CitationFormatterFactory

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

class StudyContext(BaseModel):
    """Context about the research study for literature search."""
    title: str = Field(..., description="Title of the research study")
    keywords: List[str] = Field(default_factory=list, description="Key search terms")
    research_question: str = Field(..., description="Primary research question")
    study_type: str = Field(..., description="Type of study")
    population: Optional[str] = Field(None, description="Target population")
    intervention: Optional[str] = Field(None, description="Intervention")
    outcome: Optional[str] = Field(None, description="Primary outcome")


class Paper(BaseModel):
    """Single academic paper."""
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    year: Optional[int] = None
    source: str
    journal: Optional[str] = None
    citation_count: Optional[int] = None
    url: Optional[str] = None


class RankedPaper(BaseModel):
    """Paper with relevance scoring."""
    paper: Paper
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    relevance_reason: str


class Citation(BaseModel):
    """Formatted citation."""
    formatted_citation: str
    bibtex: str
    style: str = "AMA"
    paper_id: str


class LitSearchResult(BaseModel):
    """Complete literature search result."""
    papers: List[RankedPaper] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    search_queries_used: List[str] = Field(default_factory=list)
    total_found: int = 0
    databases_searched: List[str] = Field(default_factory=list)
    search_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# LitSearchAgent
# =============================================================================

class LitSearchAgent(BaseAgent):
    """Agent for automated literature search and citation generation."""

    def __init__(self):
        config = AgentConfig(
            name="LitSearchAgent",
            description="Automated literature search across academic databases",
            stages=[6],
            rag_collections=["guidelines", "research_methods"],
            max_iterations=2,
            quality_threshold=0.75,
            timeout_seconds=180,
            phi_safe=True,
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
        )
        super().__init__(config)
        
        self.pubmed_api_key = os.getenv("NCBI_API_KEY")
        self.semantic_scholar_api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.mesh_expander = MeSHTermExpander()

    def _get_system_prompt(self) -> str:
        return """You are a specialized literature search agent for medical research.

Your role:
1. Construct effective search queries using PICO framework
2. Evaluate paper relevance based on research objectives
3. Identify high-quality evidence sources
4. Generate accurate citations

Key principles:
- Use MeSH terms for PubMed searches
- Prioritize recent, highly-cited papers
- Consider study design hierarchy
- Flag predatory journals or retracted papers
- Maintain objectivity in relevance scoring"""

    def _get_planning_prompt(self, state: AgentState) -> str:
        task_data = json.loads(state["messages"][0].content)
        return f"""Plan a comprehensive literature search:

Study Context: {json.dumps(task_data.get('study_context', {}), indent=2)}

Your plan should include:
1. Primary search terms and MeSH headings
2. Boolean operators strategy
3. Date range filters
4. Databases to search
5. Expected number of results
6. Relevance criteria

Output as JSON:
{{
    "steps": ["step1", "step2"],
    "search_queries": ["query1", "query2"],
    "databases": ["pubmed", "semantic_scholar"],
    "filters": {{"year_from": 2015}},
    "initial_query": "search query for RAG",
    "primary_collection": "research_methods"
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        task_data = json.loads(state["messages"][0].content)
        plan = state.get("plan", {})
        
        return f"""Execute literature search:

Plan: {json.dumps(plan, indent=2)}
Study Context: {json.dumps(task_data.get('study_context', {}), indent=2)}

Search Strategy Context:
{context}

Tasks:
1. Execute searches on configured databases
2. Retrieve paper metadata
3. Rank papers by relevance (0-1 score)
4. Generate citations in AMA style
5. Flag retracted or predatory papers

Return JSON:
{{
    "ranked_papers": [
        {{
            "paper": {{"title": "...", "authors": [...]}},
            "relevance_score": 0.95,
            "relevance_reason": "..."
        }}
    ],
    "total_found": 150,
    "queries_executed": ["query1"],
    "databases_used": ["pubmed"]
}}"""

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
            else:
                raise ValueError("No JSON in response")
        except Exception as e:
            logger.error(f"Failed to parse result: {e}")
            return {"ranked_papers": [], "total_found": 0}

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        result = state.get("execution_result", {})
        criteria_scores = {}
        feedback_parts = []
        
        # Paper count
        papers = result.get("ranked_papers", [])
        if len(papers) >= 10:
            criteria_scores["paper_count"] = 1.0
        elif len(papers) >= 5:
            criteria_scores["paper_count"] = 0.7
            feedback_parts.append("Consider expanding search (5-9 found, target 10+)")
        else:
            criteria_scores["paper_count"] = 0.4
            feedback_parts.append("Insufficient papers. Try broader terms")
        
        # Relevance
        if papers:
            avg_relevance = sum(p.get("relevance_score", 0) for p in papers) / len(papers)
            criteria_scores["relevance"] = avg_relevance
            if avg_relevance < 0.6:
                feedback_parts.append("Low relevance. Refine query")
        else:
            criteria_scores["relevance"] = 0.0
        
        # Database coverage
        dbs = result.get("databases_used", [])
        criteria_scores["database_coverage"] = min(1.0, len(dbs) / 2)
        
        overall = sum(criteria_scores.values()) / len(criteria_scores) if criteria_scores else 0.0
        feedback = "; ".join(feedback_parts) if feedback_parts else "Quality OK"
        
        return QualityCheckResult(
            passed=overall >= self.config.quality_threshold,
            score=overall,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )

    async def execute(self, study_context: StudyContext, max_results: int = 50) -> LitSearchResult:
        """Execute complete literature search workflow."""
        logger.info(f"[LitSearchAgent] Starting search: {study_context.title}")
        
        input_data = {
            "study_context": study_context.model_dump(),
            "max_results": max_results,
        }
        
        agent_result = await self.run(
            task_id=f"lit_search_{datetime.utcnow().timestamp()}",
            stage_id=6,
            research_id=study_context.title,
            input_data=input_data,
        )
        
        if not agent_result.success:
            logger.error(f"Search failed: {agent_result.error}")
            return LitSearchResult()
        
        exec_result = agent_result.result or {}
        ranked_papers = []
        for rp_data in exec_result.get("ranked_papers", [])[:max_results]:
            try:
                paper = Paper(**rp_data.get("paper", {}))
                ranked_paper = RankedPaper(
                    paper=paper,
                    relevance_score=rp_data.get("relevance_score", 0.5),
                    relevance_reason=rp_data.get("relevance_reason", ""),
                )
                ranked_papers.append(ranked_paper)
            except Exception as e:
                logger.warning(f"Failed to parse paper: {e}")
        
        citations = await self.extract_citations([rp.paper for rp in ranked_papers])
        
        return LitSearchResult(
            papers=ranked_papers,
            citations=citations,
            search_queries_used=exec_result.get("queries_executed", []),
            total_found=exec_result.get("total_found", len(ranked_papers)),
            databases_searched=exec_result.get("databases_used", []),
        )

    async def search_pubmed(self, query: str, max_results: int = 20) -> List[Paper]:
        """Search PubMed (TODO: Implement NCBI Entrez API)."""
        logger.info(f"[LitSearchAgent] PubMed search: {query[:100]}")
        # TODO: Implement actual API integration
        return []

    async def search_semantic_scholar(self, query: str, max_results: int = 20) -> List[Paper]:
        """Search Semantic Scholar (TODO: Implement API)."""
        logger.info(f"[LitSearchAgent] Semantic Scholar search: {query[:100]}")
        # TODO: Implement actual API integration
        return []

    async def rank_relevance(self, papers: List[Paper], study_context: StudyContext) -> List[RankedPaper]:
        """Rank papers by relevance using LLM."""
        if not papers:
            return []
        
        from langchain_core.messages import HumanMessage
        ranking_prompt = f"""Rank papers by relevance:

Study: {study_context.research_question}
Papers: {json.dumps([{"title": p.title, "abstract": p.abstract} for p in papers], indent=2)}

Return JSON: [{{"index": 0, "score": 0.95, "reason": "..."}}]"""
        
        response = await self.llm.ainvoke([HumanMessage(content=ranking_prompt)])
        ranking_data = self._parse_execution_result(response.content)
        
        ranked = []
        for rank in ranking_data if isinstance(ranking_data, list) else []:
            idx = rank.get("index", 0)
            if 0 <= idx < len(papers):
                ranked.append(RankedPaper(
                    paper=papers[idx],
                    relevance_score=rank.get("score", 0.5),
                    relevance_reason=rank.get("reason", ""),
                ))
        
        return sorted(ranked, key=lambda x: x.relevance_score, reverse=True)

    async def extract_citations(self, papers: List[Paper]) -> List[Citation]:
        """Generate formatted citations."""
        citations = []
        formatter = CitationFormatterFactory.get_formatter("AMA")
        
        for paper in papers:
            try:
                formatted = formatter.format_journal_article(
                    authors=paper.authors,
                    title=paper.title,
                    journal=paper.journal or "",
                    year=paper.year,
                    doi=paper.doi,
                )
                
                paper_id = paper.doi or paper.pmid or f"paper_{papers.index(paper)}"
                bibtex = f"@article{{{paper_id},\n  title = {{{paper.title}}}\n}}"
                
                citations.append(Citation(
                    formatted_citation=formatted,
                    bibtex=bibtex,
                    style="AMA",
                    paper_id=paper_id,
                ))
            except Exception as e:
                logger.warning(f"Citation failed: {e}")
        
        return citations


def create_lit_search_agent() -> LitSearchAgent:
    """Factory function."""
    return LitSearchAgent()
