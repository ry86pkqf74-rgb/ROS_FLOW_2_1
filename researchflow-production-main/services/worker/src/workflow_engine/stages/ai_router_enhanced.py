"""
Enhanced AI Router Integration for Literature Discovery

Provides sophisticated AI-powered analysis capabilities for literature
review with structured outputs, quality assessment, and PICO-aware processing.
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional
import httpx
from datetime import datetime

from .schemas.literature_schemas import (
    LiteratureCitation, LiteratureTheme, LiteratureGap, 
    LiteratureQualityMetrics, StudyType
)

logger = logging.getLogger("workflow_engine.ai_router_enhanced")


class LiteratureAIRouter:
    """Enhanced AI Router for literature analysis."""
    
    def __init__(self, orchestrator_url: str = None, timeout: float = 120.0):
        """
        Initialize the enhanced AI router.
        
        Args:
            orchestrator_url: Base URL for orchestrator API
            timeout: Request timeout in seconds
        """
        self.orchestrator_url = orchestrator_url or "http://orchestrator:3001"
        self.timeout = timeout
        self._request_count = 0
        self._total_tokens = 0
    
    async def analyze_literature_comprehensive(
        self, 
        papers: List[Dict[str, Any]], 
        research_context: Dict[str, Any],
        governance_mode: str = "DEMO"
    ) -> Dict[str, Any]:
        """
        Comprehensive literature analysis with structured outputs.
        
        Args:
            papers: List of paper data dictionaries
            research_context: Research context including PICO elements
            governance_mode: Current governance mode
            
        Returns:
            Structured literature analysis with themes, gaps, and quality metrics
        """
        try:
            # Prepare literature corpus for analysis
            corpus = self._prepare_literature_corpus(papers, research_context)
            
            # Run parallel analyses
            theme_analysis = await self._analyze_themes(corpus, research_context)
            gap_analysis = await self._identify_research_gaps(corpus, research_context)
            quality_assessment = await self._assess_literature_quality(papers, research_context)
            pico_coverage = await self._analyze_pico_coverage(papers, research_context)
            
            # Combine results
            return {
                "papers_found": len(papers),
                "key_themes": theme_analysis.get("themes", []),
                "research_gaps": gap_analysis.get("gaps", []),
                "citations": [self._format_enhanced_citation(p) for p in papers],
                "quality_metrics": quality_assessment,
                "pico_coverage": pico_coverage,
                "executive_summary": await self._generate_executive_summary(
                    theme_analysis, gap_analysis, quality_assessment, research_context
                ),
                "methodology_summary": self._generate_methodology_summary(papers),
                "ai_analysis_metadata": {
                    "models_used": ["claude-3-haiku", "gpt-4-turbo"],
                    "analysis_timestamp": datetime.utcnow().isoformat(),
                    "governance_mode": governance_mode,
                    "total_tokens_used": self._total_tokens,
                    "request_count": self._request_count
                }
            }
            
        except Exception as e:
            logger.error(f"Comprehensive literature analysis failed: {e}")
            return self._create_fallback_analysis(papers, research_context)
    
    async def _analyze_themes(
        self, 
        corpus: str, 
        research_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify key themes in the literature using AI."""
        prompt = f"""
        Analyze the following literature corpus for key research themes related to: {research_context.get('research_topic', 'the research question')}.

        Literature Corpus:
        {corpus[:4000]}  # Limit for token management

        PICO Context:
        - Population: {research_context.get('pico_elements', {}).get('population', 'Not specified')}
        - Intervention: {research_context.get('pico_elements', {}).get('intervention', 'Not specified')}
        - Outcomes: {research_context.get('pico_elements', {}).get('outcomes', [])}

        Identify 3-7 key themes and provide:
        1. Theme name (max 50 characters)
        2. Description (max 200 characters)
        3. Number of papers addressing this theme
        4. Key findings or consensus points
        5. Any controversies or conflicting evidence

        Respond in JSON format:
        {{
          "themes": [
            {{
              "name": "Theme name",
              "description": "Theme description",
              "paper_count": 5,
              "key_findings": "Main findings",
              "controversies": ["Controversy 1", "Controversy 2"],
              "confidence": 0.85
            }}
          ],
          "thematic_summary": "Overall thematic landscape summary"
        }}
        """
        
        return await self._make_ai_request(prompt, "claude-3-haiku", max_tokens=1000)
    
    async def _identify_research_gaps(
        self, 
        corpus: str, 
        research_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify research gaps using AI analysis."""
        prompt = f"""
        Analyze this literature corpus to identify research gaps and future research directions:

        Literature Corpus:
        {corpus[:4000]}

        Research Context:
        - Topic: {research_context.get('research_topic', 'Unknown')}
        - Study Type: {research_context.get('detected_study_type', 'Various')}

        Identify 3-5 specific research gaps including:
        1. Gap type (methodological, population, intervention, outcome, temporal, geographic)
        2. Description of what's missing
        3. Why this gap is important
        4. Suggested study design to address the gap
        5. Priority level (high/medium/low)

        Respond in JSON format:
        {{
          "gaps": [
            {{
              "type": "methodological",
              "description": "Gap description",
              "importance": "Why this matters",
              "suggested_study": "Recommended study design",
              "priority": "high"
            }}
          ],
          "gap_summary": "Overall assessment of research landscape completeness"
        }}
        """
        
        return await self._make_ai_request(prompt, "gpt-4-turbo", max_tokens=800)
    
    async def _assess_literature_quality(
        self, 
        papers: List[Dict[str, Any]], 
        research_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess overall literature quality using AI."""
        # Calculate basic metrics
        total_papers = len(papers)
        papers_with_abstracts = sum(1 for p in papers if p.get('abstract'))
        recent_papers = sum(1 for p in papers if self._is_recent_paper(p))
        high_impact_papers = sum(1 for p in papers if self._is_high_impact(p))
        
        quality_prompt = f"""
        Assess the quality of this literature set for research on: {research_context.get('research_topic', 'the topic')}

        Literature Statistics:
        - Total papers: {total_papers}
        - Papers with abstracts: {papers_with_abstracts}
        - Recent papers (2020+): {recent_papers}
        - High-impact papers: {high_impact_papers}

        Sample Papers:
        {self._format_papers_for_quality_assessment(papers[:10])}

        Provide a quality assessment including:
        1. Overall quality score (1-10)
        2. Strengths of the literature base
        3. Weaknesses or limitations
        4. Representativeness assessment
        5. Recommendations for improvement

        Respond in JSON format:
        {{
          "overall_quality_score": 7.5,
          "strengths": ["Good recent coverage", "Diverse methodologies"],
          "weaknesses": ["Limited geographic diversity", "Few long-term studies"],
          "representativeness": "Good for developed countries, limited for developing regions",
          "recommendations": ["Include more RCTs", "Seek longer follow-up studies"]
        }}
        """
        
        ai_assessment = await self._make_ai_request(quality_prompt, "claude-3-haiku", max_tokens=600)
        
        # Combine AI assessment with calculated metrics
        return {
            "ai_quality_score": ai_assessment.get("overall_quality_score", 0),
            "total_papers_included": total_papers,
            "papers_with_abstracts_rate": papers_with_abstracts / max(total_papers, 1),
            "recent_papers_rate": recent_papers / max(total_papers, 1),
            "high_impact_papers": high_impact_papers,
            "strengths": ai_assessment.get("strengths", []),
            "weaknesses": ai_assessment.get("weaknesses", []),
            "recommendations": ai_assessment.get("recommendations", [])
        }
    
    async def _analyze_pico_coverage(
        self, 
        papers: List[Dict[str, Any]], 
        research_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze how well the literature covers PICO elements."""
        pico_elements = research_context.get('pico_elements', {})
        
        if not pico_elements:
            return {"coverage_score": 0, "note": "No PICO elements provided"}
        
        prompt = f"""
        Analyze how well this literature set covers the PICO elements:

        Target PICO:
        - Population: {pico_elements.get('population', 'Not specified')}
        - Intervention: {pico_elements.get('intervention', 'Not specified')}
        - Comparator: {pico_elements.get('comparator', 'Not specified')}
        - Outcomes: {pico_elements.get('outcomes', [])}

        Literature Sample:
        {self._format_papers_for_pico_analysis(papers[:15])}

        Assess coverage for each PICO element:
        1. Population coverage (0-100%)
        2. Intervention coverage (0-100%)
        3. Comparator coverage (0-100%)
        4. Outcome coverage (0-100%)
        5. Overall PICO alignment score (0-100%)

        Respond in JSON format:
        {{
          "population_coverage": 85,
          "intervention_coverage": 90,
          "comparator_coverage": 60,
          "outcome_coverage": 80,
          "overall_pico_score": 79,
          "coverage_gaps": ["Limited pediatric studies", "Few head-to-head comparisons"],
          "well_covered_areas": ["Primary efficacy outcomes", "Adult populations"]
        }}
        """
        
        return await self._make_ai_request(prompt, "gpt-4-turbo", max_tokens=500)
    
    async def _generate_executive_summary(
        self, 
        theme_analysis: Dict[str, Any], 
        gap_analysis: Dict[str, Any],
        quality_assessment: Dict[str, Any],
        research_context: Dict[str, Any]
    ) -> str:
        """Generate executive summary of literature analysis."""
        prompt = f"""
        Create a concise executive summary (max 300 words) for this literature review:

        Research Topic: {research_context.get('research_topic', 'Literature Review')}

        Key Findings:
        - Themes Identified: {len(theme_analysis.get('themes', []))}
        - Research Gaps: {len(gap_analysis.get('gaps', []))}
        - Quality Score: {quality_assessment.get('ai_quality_score', 'Not assessed')}/10

        Major Themes:
        {[t.get('name', 'Unnamed') for t in theme_analysis.get('themes', [])[:3]]}

        Primary Research Gaps:
        {[g.get('description', 'Not specified')[:50] for g in gap_analysis.get('gaps', [])[:2]]}

        Write a professional executive summary that:
        1. States the scope and purpose
        2. Highlights key findings and themes
        3. Identifies major research gaps
        4. Comments on literature quality
        5. Provides brief recommendations

        Write in academic tone, past tense, third person.
        """
        
        response = await self._make_ai_request(prompt, "claude-3-haiku", max_tokens=400)
        return response.get("summary", "Executive summary generation failed")
    
    def _prepare_literature_corpus(
        self, 
        papers: List[Dict[str, Any]], 
        research_context: Dict[str, Any]
    ) -> str:
        """Prepare literature corpus for AI analysis."""
        corpus_parts = []
        
        # Add research context
        corpus_parts.append(f"RESEARCH CONTEXT: {research_context.get('research_topic', 'Unknown topic')}")
        
        # Add paper summaries (limited for token management)
        for i, paper in enumerate(papers[:20]):  # Limit to first 20 papers
            title = paper.get('title', 'No title')
            abstract = paper.get('abstract', 'No abstract')[:300]  # Limit abstract length
            year = paper.get('year', 'Unknown year')
            journal = paper.get('journal', 'Unknown journal')
            
            corpus_parts.append(f"\nPAPER {i+1}:")
            corpus_parts.append(f"Title: {title}")
            corpus_parts.append(f"Journal: {journal} ({year})")
            corpus_parts.append(f"Abstract: {abstract}")
        
        return "\n".join(corpus_parts)
    
    def _format_enhanced_citation(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """Format paper as enhanced citation with additional metadata."""
        return {
            "pmid": paper.get("pmid"),
            "title": paper.get("title"),
            "authors": paper.get("authors", []),
            "journal": paper.get("journal"),
            "year": paper.get("year"),
            "doi": paper.get("doi"),
            "abstract": paper.get("abstract", "")[:200] + "..." if paper.get("abstract") else "",
            "source": paper.get("source", "unknown"),
            "keywords": paper.get("keywords", []),
            "mesh_terms": paper.get("mesh_terms", []),
            "study_type": self._infer_study_type(paper),
            "quality_indicators": self._assess_paper_quality(paper)
        }
    
    def _infer_study_type(self, paper: Dict[str, Any]) -> Optional[str]:
        """Infer study type from paper metadata."""
        title = (paper.get('title', '') + ' ' + paper.get('abstract', '')).lower()
        
        if 'randomized controlled trial' in title or 'rct' in title:
            return "randomized_controlled_trial"
        elif 'systematic review' in title:
            return "systematic_review"
        elif 'meta-analysis' in title:
            return "meta_analysis"
        elif 'cohort' in title:
            return "cohort_study"
        elif 'case-control' in title:
            return "case_control"
        elif 'cross-sectional' in title:
            return "cross_sectional"
        else:
            return "observational"
    
    def _assess_paper_quality(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """Assess basic quality indicators for a paper."""
        quality = {}
        
        # Check for complete metadata
        if paper.get('doi'):
            quality['has_doi'] = 'yes'
        if paper.get('abstract') and len(paper.get('abstract', '')) > 100:
            quality['substantial_abstract'] = 'yes'
        if paper.get('authors') and len(paper.get('authors', [])) > 0:
            quality['has_authors'] = 'yes'
        
        # Check recency
        year = paper.get('year')
        if year and int(year) >= 2020:
            quality['recent_publication'] = 'yes'
        
        return quality
    
    def _is_recent_paper(self, paper: Dict[str, Any]) -> bool:
        """Check if paper is recent (2020 or later)."""
        year = paper.get('year')
        try:
            return int(year) >= 2020 if year else False
        except (ValueError, TypeError):
            return False
    
    def _is_high_impact(self, paper: Dict[str, Any]) -> bool:
        """Check if paper is high impact (simple heuristic)."""
        # High impact: recent paper with DOI and substantial abstract
        return (
            self._is_recent_paper(paper) and
            paper.get('doi') and
            paper.get('abstract') and
            len(paper.get('abstract', '')) > 200
        )
    
    def _format_papers_for_quality_assessment(self, papers: List[Dict[str, Any]]) -> str:
        """Format papers for quality assessment prompt."""
        formatted = []
        for i, paper in enumerate(papers[:5], 1):
            formatted.append(f"{i}. {paper.get('title', 'No title')} "
                           f"({paper.get('year', 'No year')}) - "
                           f"{paper.get('journal', 'No journal')}")
        return "\n".join(formatted)
    
    def _format_papers_for_pico_analysis(self, papers: List[Dict[str, Any]]) -> str:
        """Format papers for PICO coverage analysis."""
        formatted = []
        for paper in papers:
            title = paper.get('title', 'No title')
            abstract = paper.get('abstract', 'No abstract')[:150]
            formatted.append(f"Title: {title}\nAbstract: {abstract}\n")
        return "\n".join(formatted)
    
    def _generate_methodology_summary(self, papers: List[Dict[str, Any]]) -> str:
        """Generate methodology summary based on paper types."""
        study_types = {}
        total_papers = len(papers)
        
        for paper in papers:
            study_type = self._infer_study_type(paper)
            study_types[study_type] = study_types.get(study_type, 0) + 1
        
        summary_parts = [f"Literature base of {total_papers} papers includes:"]
        for study_type, count in study_types.items():
            percentage = (count / total_papers) * 100
            summary_parts.append(f"- {study_type}: {count} papers ({percentage:.1f}%)")
        
        return " ".join(summary_parts)
    
    async def _make_ai_request(
        self, 
        prompt: str, 
        model: str = "claude-3-haiku", 
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Make request to AI Router with error handling."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.orchestrator_url}/api/ai/generate",
                    json={
                        "prompt": prompt,
                        "model": model,
                        "max_tokens": max_tokens,
                        "temperature": 0.3  # Lower temperature for more consistent analysis
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                
                ai_response = response.json()
                self._request_count += 1
                self._total_tokens += ai_response.get("tokens_used", 0)
                
                # Try to parse JSON response
                try:
                    return json.loads(ai_response.get("response", "{}"))
                except json.JSONDecodeError:
                    # If not JSON, return the raw response
                    return {"summary": ai_response.get("response", "")}
                    
        except Exception as e:
            logger.error(f"AI Router request failed: {e}")
            return {"error": str(e), "fallback": True}
    
    def _create_fallback_analysis(
        self, 
        papers: List[Dict[str, Any]], 
        research_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fallback analysis when AI Router fails."""
        return {
            "papers_found": len(papers),
            "key_themes": [
                "Treatment efficacy and effectiveness",
                "Safety and adverse events", 
                "Patient outcomes and quality of life"
            ],
            "research_gaps": [
                "Long-term follow-up studies needed",
                "Diverse population representation required",
                "Comparative effectiveness research gaps"
            ],
            "citations": [self._format_enhanced_citation(p) for p in papers],
            "quality_metrics": {
                "total_papers_included": len(papers),
                "ai_quality_score": 6.0,  # Conservative fallback score
                "recent_papers_rate": sum(1 for p in papers if self._is_recent_paper(p)) / max(len(papers), 1)
            },
            "executive_summary": f"Literature review identified {len(papers)} relevant papers on {research_context.get('research_topic', 'the research topic')}. Analysis suggests consistent evidence with opportunities for further research.",
            "fallback_analysis": True
        }
    
    def get_router_stats(self) -> Dict[str, Any]:
        """Get router performance statistics."""
        return {
            "total_requests": self._request_count,
            "total_tokens_used": self._total_tokens,
            "avg_tokens_per_request": self._total_tokens / max(self._request_count, 1),
            "router_url": self.orchestrator_url,
            "timeout_seconds": self.timeout
        }