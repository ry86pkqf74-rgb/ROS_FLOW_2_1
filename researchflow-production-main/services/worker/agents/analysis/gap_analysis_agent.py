"""
GapAnalysisAgent - Stage 10: Gap Analysis & Future Directions (Part 1)

Identifies gaps in current research, compares to existing literature,
and suggests prioritized future research directions.

Features:
- Multi-model API integration (Claude, Grok, Mercury, OpenAI)
- Semantic literature comparison using embeddings
- PICO-based research question formulation
- Impact vs Feasibility prioritization matrix
- Manuscript-ready narrative generation

Linear Issues: ROS-XXX (Stage 10 - Gap Analysis Agent)
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from agents.base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# Import types and utilities
from .gap_analysis_types import *
from .gap_analysis_utils import LiteratureComparator, PICOExtractor, GapCategorizer
from .lit_search_agent import StudyContext, Paper

logger = logging.getLogger(__name__)


# =============================================================================
# GapAnalysisAgent
# =============================================================================

class GapAnalysisAgent(BaseAgent):
    """
    Agent for comprehensive gap analysis and future research planning.
    
    Architecture:
    - Planning: Claude Sonnet 4 (superior reasoning)
    - Literature Comparison: Grok-2 (fast semantic analysis)
    - Structured Analysis: Mercury (specialized data processing)
    - Embeddings: OpenAI text-embedding-3-large
    
    Workflow:
    1. Compare current findings to literature
    2. Identify gaps across 6 dimensions
    3. Prioritize gaps (impact vs feasibility)
    4. Generate PICO-based research suggestions
    5. Create manuscript-ready narratives
    """

    def __init__(self):
        config = AgentConfig(
            name="GapAnalysisAgent",
            description="Identify research gaps and suggest future directions",
            stages=[10],
            rag_collections=["research_methods", "gap_analysis_methods"],
            max_iterations=3,
            quality_threshold=0.80,
            timeout_seconds=300,
            phi_safe=True,
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",
        )
        super().__init__(config)
        
        # Initialize specialized LLM clients
        self._init_specialized_llms()
        
        # Initialize utilities
        self.comparator = LiteratureComparator()
        self.pico_extractor = PICOExtractor()
        self.gap_categorizer = GapCategorizer()

    def _init_specialized_llms(self):
        """Initialize multiple LLM clients for specialized tasks."""
        
        # Grok-2 for fast literature comparison
        xai_key = os.getenv("XAI_API_KEY")
        xai_base = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")
        if xai_key:
            self.grok_llm = ChatOpenAI(
                model="grok-2-latest",
                base_url=xai_base,
                api_key=xai_key,
                temperature=0.3,
                max_tokens=2048
            )
            logger.info("[GapAnalysisAgent] Grok-2 initialized for literature comparison")
        else:
            self.grok_llm = None
            logger.warning("[GapAnalysisAgent] XAI_API_KEY not set, using Claude fallback")
        
        # Mercury for structured analysis
        mercury_key = (
            os.getenv("MERCURY_API_KEY") 
            or os.getenv("INCEPTION_API_KEY")
            or os.getenv("INCEPTIONLABS_API_KEY")
        )
        mercury_base = os.getenv("MERCURY_BASE_URL", "https://api.inceptionlabs.ai/v1")
        if mercury_key:
            self.mercury_llm = ChatOpenAI(
                model="mercury-coder-medium",
                base_url=mercury_base,
                api_key=mercury_key,
                temperature=0.2,
                max_tokens=2048
            )
            logger.info("[GapAnalysisAgent] Mercury initialized for structured analysis")
        else:
            self.mercury_llm = None
            logger.warning("[GapAnalysisAgent] Mercury API key not set")

    # =========================================================================
    # BaseAgent Abstract Methods Implementation
    # =========================================================================

    def _get_system_prompt(self) -> str:
        """System prompt for gap analysis expertise."""
        return """You are a Gap Analysis Expert specialized in systematic reviews and meta-analyses.

Your expertise includes:
- Identifying research gaps across multiple dimensions (theoretical, empirical, methodological, population, temporal, geographic)
- GRADE framework for assessing evidence quality
- Comparing study findings to existing literature
- Formulating PICO-based research questions
- Prioritizing research directions based on impact and feasibility
- Understanding research methodology limitations
- Recognizing underrepresented populations and settings
- Writing manuscript-ready "Future Directions" sections

Key principles:
1. Be comprehensive yet specific in gap identification
2. Ground all gaps in evidence from the literature
3. Consider both theoretical and practical implications
4. Prioritize gaps that are both impactful and addressable
5. Formulate clear, answerable research questions
6. Link gaps to specific citations
7. Assess feasibility realistically
8. Consider ethical and resource constraints

Output Style:
- Academic but accessible
- Evidence-based and well-cited
- Actionable and specific
- Balanced between ambition and feasibility"""

    def _get_planning_prompt(self, state: AgentState) -> str:
        """Planning prompt for gap analysis strategy."""
        task_data = json.loads(state["messages"][0].content)
        
        return f"""Plan a comprehensive gap analysis:

Study Context: {json.dumps(task_data.get('study_context', {}), indent=2)}
Literature Available: {len(task_data.get('literature', []))} papers
Findings Available: {len(task_data.get('findings', []))} findings

Your plan should include:
1. Strategy for comparing findings to literature
   - Identify key themes for comparison
   - Determine similarity assessment approach
   
2. Gap identification strategy
   - Which gap types to prioritize (theoretical, empirical, methodological, population, temporal, geographic)
   - Criteria for gap validation
   - Evidence requirements
   
3. Prioritization approach
   - Impact assessment criteria
   - Feasibility assessment criteria
   - Weighting scheme
   
4. Research suggestion strategy
   - Number of suggestions to generate
   - Study designs to consider
   - PICO formulation approach
   
5. RAG retrieval needs
   - What guidelines to retrieve
   - What examples to look for

Output as JSON:
{{
    "steps": ["step1", "step2", "step3"],
    "gap_types_to_analyze": ["empirical", "methodological", "population"],
    "comparison_strategy": "semantic_embeddings",
    "prioritization_method": "impact_feasibility_matrix",
    "num_suggestions": 5,
    "initial_query": "gap analysis methodology systematic reviews",
    "primary_collection": "gap_analysis_methods"
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        """Execution prompt with RAG context."""
        task_data = json.loads(state["messages"][0].content)
        plan = state.get("plan", {})
        
        return f"""Execute gap analysis:

Plan: {json.dumps(plan, indent=2)}

Study Context: {json.dumps(task_data.get('study_context', {}), indent=2)}

Findings: {json.dumps(task_data.get('findings', []), indent=2)}

Literature Summary:
{self._format_literature_summary(task_data.get('literature', []))}

Gap Analysis Guidelines:
{context}

Tasks:
1. Compare findings to literature
   - Identify consistent findings
   - Identify contradictions
   - Identify novel contributions
   - Identify extensions of existing work
   
2. Identify gaps across dimensions:
   - Knowledge gaps (what we don't know)
   - Methodological gaps (design limitations)
   - Population gaps (underrepresented groups)
   - Temporal gaps (outdated evidence)
   - Geographic gaps (limited settings)
   - Theoretical gaps (missing frameworks)
   
3. Assess each gap:
   - Evidence level (strong/moderate/weak)
   - Impact score (1-5)
   - Feasibility score (1-5)
   - Related citations
   
4. Generate 5 research suggestions with:
   - Clear research question
   - Study design
   - PICO framework
   - Expected contribution
   - Priority scores
   
5. Create prioritization matrix (2x2: impact vs feasibility)

6. Generate manuscript-ready narrative

Return JSON:
{{
    "comparisons": {{
        "consistent_with": [...],
        "contradicts": [...],
        "novel_findings": [...],
        "extends": [...]
    }},
    "gaps": {{
        "knowledge": [...],
        "methodological": [...],
        "population": [...],
        "temporal": [...],
        "geographic": [...]
    }},
    "prioritized_gaps": [...],
    "research_suggestions": [...],
    "prioritization_matrix": {{...}},
    "narrative": "..."
}}"""
"""
GapAnalysisAgent - Part 2: Core Methods
"""

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured gap analysis result."""
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
            logger.error(f"Failed to parse gap analysis result: {e}")
            return {
                "comparisons": {},
                "gaps": {},
                "prioritized_gaps": [],
                "research_suggestions": []
            }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Enhanced quality check for gap analysis."""
        result = state.get("execution_result", {})
        criteria_scores = {}
        feedback_parts = []
        
        # 1. Gap diversity (20%)
        gaps = result.get("prioritized_gaps", [])
        if gaps:
            gap_types = set(g.get("gap", {}).get("gap_type") for g in gaps)
            criteria_scores["diversity"] = len(gap_types) / len(GapType)
            if len(gap_types) < 3:
                feedback_parts.append("Identify more diverse gap types (currently {})".format(len(gap_types)))
        else:
            criteria_scores["diversity"] = 0.0
            feedback_parts.append("No gaps identified")
        
        # 2. PICO completeness (20%)
        suggestions = result.get("research_suggestions", [])
        if suggestions:
            pico_complete = sum(1 for s in suggestions if s.get("pico_framework"))
            criteria_scores["pico_completeness"] = pico_complete / len(suggestions)
            if pico_complete < len(suggestions):
                feedback_parts.append("Complete PICO framework for all research suggestions")
        else:
            criteria_scores["pico_completeness"] = 0.0
            feedback_parts.append("No research suggestions generated")
        
        # 3. Literature grounding (25%)
        total_citations = 0
        for gap in gaps:
            related = gap.get("gap", {}).get("related_papers", [])
            total_citations += len(related)
        
        if gaps:
            avg_citations = total_citations / len(gaps)
            criteria_scores["literature_grounding"] = min(1.0, avg_citations / 2.0)  # Target 2+ citations per gap
            if avg_citations < 1.0:
                feedback_parts.append("Provide more literature citations for gaps")
        else:
            criteria_scores["literature_grounding"] = 0.0
        
        # 4. Prioritization clarity (20%)
        has_matrix = "prioritization_matrix" in result
        has_scores = all(
            g.get("gap", {}).get("impact_score") is not None 
            and g.get("gap", {}).get("feasibility_score") is not None 
            for g in gaps
        )
        criteria_scores["prioritization"] = 1.0 if (has_matrix and has_scores) else 0.5 if has_scores else 0.2
        if not has_matrix:
            feedback_parts.append("Generate prioritization matrix")
        
        # 5. Narrative quality (15%)
        narrative = result.get("narrative", "")
        narrative_words = len(narrative.split())
        criteria_scores["narrative"] = min(1.0, narrative_words / 300.0)  # Target 300+ words
        if narrative_words < 200:
            feedback_parts.append("Expand narrative (currently {} words, target 300+)".format(narrative_words))
        
        # Weighted average
        weights = {
            "diversity": 0.20,
            "pico_completeness": 0.20,
            "literature_grounding": 0.25,
            "prioritization": 0.20,
            "narrative": 0.15
        }
        
        overall = sum(criteria_scores.get(k, 0) * weights[k] for k in weights)
        feedback = "; ".join(feedback_parts) if feedback_parts else "Gap analysis meets quality standards"
        
        return QualityCheckResult(
            passed=overall >= self.config.quality_threshold,
            score=overall,
            feedback=feedback,
            criteria_scores=criteria_scores
        )

    # =========================================================================
    # Core Gap Analysis Methods
    # =========================================================================

    async def execute(
        self,
        study: StudyContext,
        literature: List[Paper],
        findings: Optional[List[Finding]] = None
    ) -> GapAnalysisResult:
        """
        Execute complete gap analysis workflow.
        
        Args:
            study: Study context with metadata
            literature: List of papers from literature search
            findings: Optional list of findings from statistical analysis
        
        Returns:
            GapAnalysisResult with comprehensive gap analysis
        """
        logger.info(f"[GapAnalysisAgent] Starting gap analysis for: {study.title}")
        
        # Prepare input data
        input_data = {
            "study_context": study.model_dump(),
            "literature": [p.model_dump() for p in literature[:50]],  # Limit to 50 papers
            "findings": [f.model_dump() for f in (findings or [])]
        }
        
        # Run agent workflow
        agent_result = await self.run(
            task_id=f"gap_analysis_{datetime.utcnow().timestamp()}",
            stage_id=10,
            research_id=study.title,
            input_data=input_data
        )
        
        if not agent_result.success:
            logger.error(f"Gap analysis failed: {agent_result.error}")
            return GapAnalysisResult(
                comparisons=ComparisonResult(overall_similarity_score=0.0)
            )
        
        # Parse result into structured output
        exec_result = agent_result.result or {}
        return self._build_gap_analysis_result(exec_result, literature)

    def _build_gap_analysis_result(
        self,
        exec_result: Dict[str, Any],
        literature: List[Paper]
    ) -> GapAnalysisResult:
        """Build GapAnalysisResult from execution output."""
        
        # Build comparisons
        comp_data = exec_result.get("comparisons", {})
        comparisons = ComparisonResult(
            consistent_with=[LiteratureAlignment(**a) for a in comp_data.get("consistent_with", [])],
            contradicts=[LiteratureAlignment(**a) for a in comp_data.get("contradicts", [])],
            novel_findings=[LiteratureAlignment(**a) for a in comp_data.get("novel_findings", [])],
            extends=[LiteratureAlignment(**a) for a in comp_data.get("extends", [])],
            overall_similarity_score=comp_data.get("overall_similarity_score", 0.5),
            summary=comp_data.get("summary", "")
        )
        
        # Build gaps
        gaps_data = exec_result.get("gaps", {})
        knowledge_gaps = [KnowledgeGap(**g) for g in gaps_data.get("knowledge", [])]
        method_gaps = [MethodGap(**g) for g in gaps_data.get("methodological", [])]
        population_gaps = [PopulationGap(**g) for g in gaps_data.get("population", [])]
        temporal_gaps = [TemporalGap(**g) for g in gaps_data.get("temporal", [])]
        geographic_gaps = [GeographicGap(**g) for g in gaps_data.get("geographic", [])]
        
        # Build prioritized gaps
        prioritized = []
        for pg_data in exec_result.get("prioritized_gaps", []):
            try:
                gap = Gap(**pg_data.get("gap", {}))
                prioritized.append(PrioritizedGap(
                    gap=gap,
                    priority_score=pg_data.get("priority_score", 5.0),
                    priority_level=GapPriority(pg_data.get("priority_level", "medium")),
                    rationale=pg_data.get("rationale", ""),
                    feasibility=pg_data.get("feasibility", ""),
                    expected_impact=pg_data.get("expected_impact", "")
                ))
            except Exception as e:
                logger.warning(f"Failed to parse prioritized gap: {e}")
        
        # Build research suggestions
        suggestions = []
        for s_data in exec_result.get("research_suggestions", []):
            try:
                pico_data = s_data.get("pico_framework")
                pico = PICOFramework(**pico_data) if pico_data else None
                
                suggestions.append(ResearchSuggestion(
                    research_question=s_data.get("research_question", ""),
                    study_design=s_data.get("study_design", ""),
                    target_population=s_data.get("target_population", ""),
                    expected_contribution=s_data.get("expected_contribution", ""),
                    pico_framework=pico,
                    impact_score=s_data.get("impact_score", 3.0),
                    feasibility_score=s_data.get("feasibility_score", 3.0),
                    urgency_score=s_data.get("urgency_score", 3.0)
                ))
            except Exception as e:
                logger.warning(f"Failed to parse research suggestion: {e}")
        
        # Build prioritization matrix
        matrix_data = exec_result.get("prioritization_matrix")
        matrix = PrioritizationMatrix(**matrix_data) if matrix_data else None
        
        # Build complete result
        result = GapAnalysisResult(
            comparisons=comparisons,
            knowledge_gaps=knowledge_gaps,
            method_gaps=method_gaps,
            population_gaps=population_gaps,
            temporal_gaps=temporal_gaps,
            geographic_gaps=geographic_gaps,
            prioritized_gaps=prioritized,
            prioritization_matrix=matrix,
            research_suggestions=suggestions,
            narrative=exec_result.get("narrative", ""),
            future_directions_section=self.generate_future_directions_section(suggestions),
            literature_coverage=min(1.0, len(literature) / 30.0)  # Assume 30+ is good coverage
        )
        
        result.calculate_summary_stats()
        return result

    def generate_future_directions_section(
        self,
        suggestions: List[ResearchSuggestion]
    ) -> str:
        """Generate manuscript-ready Future Directions section."""
        if not suggestions:
            return ""
        
        sections = ["## Future Research Directions\n"]
        
        for i, suggestion in enumerate(suggestions[:5], 1):
            sections.append(f"\n### {i}. {suggestion.research_question}\n")
            sections.append(f"{suggestion.expected_contribution} ")
            sections.append(f"A {suggestion.study_design} study design would be most appropriate. ")
            sections.append(f"The target population should include {suggestion.target_population}. ")
            
            if suggestion.pico_framework:
                sections.append(f"\n**PICO Framework:**\n")
                sections.append(f"- Population: {suggestion.pico_framework.population}\n")
                sections.append(f"- Intervention: {suggestion.pico_framework.intervention}\n")
                sections.append(f"- Comparison: {suggestion.pico_framework.comparison}\n")
                sections.append(f"- Outcome: {suggestion.pico_framework.outcome}\n")
        
        return "".join(sections)

    def _format_literature_summary(self, literature: List[Dict]) -> str:
        """Format literature for LLM context."""
        if not literature:
            return "No literature available."
        
        summary_lines = []
        for i, paper in enumerate(literature[:20], 1):  # Limit to 20 for context
            title = paper.get("title", "Unknown")
            authors = paper.get("authors", [])
            year = paper.get("year", "n.d.")
            abstract = paper.get("abstract", "")[:200]  # Truncate abstracts
            
            author_str = authors[0] if authors else "Unknown"
            summary_lines.append(f"{i}. {author_str} et al. ({year}). {title}\n   {abstract}...")
        
        return "\n".join(summary_lines)


# =============================================================================
# Factory Function
# =============================================================================

def create_gap_analysis_agent() -> GapAnalysisAgent:
    """Factory function for creating GapAnalysisAgent."""
    return GapAnalysisAgent()
