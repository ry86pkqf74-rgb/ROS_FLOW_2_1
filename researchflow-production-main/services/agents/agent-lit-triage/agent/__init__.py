"""Literature Triage Agent - Main orchestrator"""
from __future__ import annotations
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from workers.search_worker import LiteratureSearchWorker
from workers.ranking_worker import LiteratureRankingWorker, ScoredPaper


class TriageRequest(BaseModel):
    """Input for literature triage request"""
    query: str
    date_range_days: int | None = 730  # Default: last 2 years
    min_results: int = 15


class TriageReport(BaseModel):
    """Structured output from literature triage"""
    query: str
    date: str
    papers_found: int
    papers_ranked: int
    executive_summary: str
    tier1_papers: List[ScoredPaper]  # Must Read (score ≥ 75)
    tier2_papers: List[ScoredPaper]  # Should Read (score 50-74)
    tier3_papers: List[ScoredPaper]  # Optional (score < 50)


class LiteratureTriageAgent:
    """
    Main Literature Triage Agent orchestrator.
    
    Implements the three-phase pipeline from the LangSmith agent:
    1. SEARCH: Delegate to Literature_Search_Worker for comprehensive discovery
    2. RANK: Delegate to Literature_Rank_and_Prioritize_Worker for scoring
    3. PRIORITIZE & DELIVER: Format and present final prioritized output
    """
    
    def __init__(self):
        self.search_worker = LiteratureSearchWorker()
        self.ranking_worker = LiteratureRankingWorker()
    
    async def execute_triage(self, request: TriageRequest) -> TriageReport:
        """
        Execute full literature triage pipeline
        
        Args:
            request: TriageRequest with query and parameters
            
        Returns:
            TriageReport with ranked and tiered papers
        """
        # Phase 1: SEARCH
        print(f"[Phase 1] Searching for papers on query: {request.query}")
        
        # Calculate date range
        date_range = None
        if request.date_range_days:
            end_date = datetime.now()
            start_date = end_date.replace(
                day=end_date.day,
                hour=0, minute=0, second=0, microsecond=0
            )
            from datetime import timedelta
            start_date = start_date - timedelta(days=request.date_range_days)
            date_range = (start_date, end_date)
        
        papers = await self.search_worker.search(
            query=request.query,
            date_range=date_range,
            min_results=request.min_results
        )
        
        print(f"[Phase 1] Found {len(papers)} candidate papers")
        
        # Phase 2: RANK
        print(f"[Phase 2] Ranking papers using multi-criteria scoring")
        
        scored_papers = self.ranking_worker.rank_papers(
            papers=papers,
            query=request.query
        )
        
        print(f"[Phase 2] Ranked {len(scored_papers)} papers")
        
        # Phase 3: PRIORITIZE & DELIVER
        print(f"[Phase 3] Organizing into priority tiers")
        
        tier1 = [p for p in scored_papers if p.tier == "Must Read"]
        tier2 = [p for p in scored_papers if p.tier == "Should Read"]
        tier3 = [p for p in scored_papers if p.tier == "Optional"]
        
        print(f"[Phase 3] Tier 1: {len(tier1)}, Tier 2: {len(tier2)}, Tier 3: {len(tier3)}")
        
        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            query=request.query,
            scored_papers=scored_papers
        )
        
        return TriageReport(
            query=request.query,
            date=datetime.now().isoformat(),
            papers_found=len(papers),
            papers_ranked=len(scored_papers),
            executive_summary=executive_summary,
            tier1_papers=tier1,
            tier2_papers=tier2,
            tier3_papers=tier3
        )
    
    def _generate_executive_summary(
        self,
        query: str,
        scored_papers: List[ScoredPaper]
    ) -> str:
        """
        Generate 2-3 paragraph executive summary of key findings
        """
        if not scored_papers:
            return "No papers were found matching the search criteria."
        
        top_papers = scored_papers[:5]
        tier1_count = sum(1 for p in scored_papers if p.tier == "Must Read")
        
        # Identify common themes in top papers
        journals = [p.journal for p in top_papers if p.journal]
        unique_journals = set(journals)
        
        summary_parts = []
        
        # Overview paragraph
        summary_parts.append(
            f"This literature triage identified {len(scored_papers)} relevant papers "
            f"addressing '{query}'. Of these, {tier1_count} papers were classified as "
            f"'Must Read' based on their high relevance, recency, and impact."
        )
        
        # Key findings paragraph
        if top_papers:
            top_paper = top_papers[0]
            summary_parts.append(
                f"The highest-ranked paper (score: {top_paper.composite_score:.1f}/100) "
                f"is '{top_paper.title}' "
                f"{f'published in {top_paper.journal}' if top_paper.journal else ''}. "
                f"{top_paper.rationale}"
            )
        
        # Sources paragraph
        if unique_journals:
            journal_list = ', '.join(list(unique_journals)[:3])
            summary_parts.append(
                f"Key sources include {journal_list}, representing a mix of "
                f"high-impact and specialty publications in the field."
            )
        
        return " ".join(summary_parts)
    
    def format_report_markdown(self, report: TriageReport) -> str:
        """
        Format TriageReport as markdown for human-readable output
        
        Follows the format specified in the LangSmith AGENTS.md
        """
        lines = [
            "# 📋 Literature Triage Report",
            "",
            f"**Query**: {report.query}",
            f"**Date**: {report.date}",
            f"**Papers Found**: {report.papers_found}",
            f"**Papers Ranked**: {report.papers_ranked}",
            "",
            "## Executive Summary",
            "",
            report.executive_summary,
            "",
        ]
        
        # Tier 1 - Must Read
        if report.tier1_papers:
            lines.extend([
                "## Tier 1 — Must Read 🔴",
                "",
                f"*{len(report.tier1_papers)} papers with composite score ≥ 75*",
                ""
            ])
            
            for paper in report.tier1_papers:
                lines.extend(self._format_paper_markdown(paper))
        
        # Tier 2 - Should Read
        if report.tier2_papers:
            lines.extend([
                "## Tier 2 — Should Read 🟡",
                "",
                f"*{len(report.tier2_papers)} papers with composite score 50-74*",
                ""
            ])
            
            for paper in report.tier2_papers:
                lines.extend(self._format_paper_markdown(paper))
        
        # Tier 3 - Optional
        if report.tier3_papers:
            lines.extend([
                "## Tier 3 — Optional 🟢",
                "",
                f"*{len(report.tier3_papers)} papers with composite score < 50*",
                ""
            ])
            
            for paper in report.tier3_papers[:10]:  # Limit to top 10 optional
                lines.extend(self._format_paper_markdown(paper))
        
        return "\n".join(lines)
    
    def _format_paper_markdown(self, paper: ScoredPaper) -> List[str]:
        """Format individual paper as markdown"""
        lines = [
            f"> **{paper.rank}. {paper.title}**",
            f"> - **Authors**: {', '.join(paper.authors) if paper.authors else 'Unknown'}",
            f"> - **Journal**: {paper.journal or 'Unknown'} | **Date**: {paper.publication_date or 'Unknown'}",
            f"> - **Priority Score**: {paper.composite_score:.1f}/100 | **Tier**: {paper.tier}",
        ]
        
        if paper.abstract:
            lines.append(f"> - **Abstract**: {paper.abstract}")
        
        lines.extend([
            f"> - **Score Breakdown**: "
            f"Recency: {paper.recency_score:.1f}/10 | "
            f"Relevance: {paper.relevance_score:.1f}/10 | "
            f"Journal: {paper.journal_score:.1f}/10 | "
            f"Author: {paper.author_score:.1f}/10 | "
            f"Citations: {paper.citation_score:.1f}/10",
            f"> - **Why this matters**: {paper.rationale}",
        ])
        
        if paper.url:
            lines.append(f"> - **Link**: [{paper.url}]({paper.url})")
        
        lines.append("")
        
        return lines
