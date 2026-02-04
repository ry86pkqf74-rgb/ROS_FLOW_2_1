"""
Manuscript Agent - Stages 14-20: Full manuscript drafting and conference preparation.

This agent handles the manuscript creation phases of the research workflow:
- Stage 14: Full Manuscript Draft - Generate complete IMRaD manuscript in one pass
- Stage 15: Introduction Refinement - Background, literature review, objectives
- Stage 16: Methods Refinement - Study design, procedures, analysis
- Stage 17: Results Refinement - Findings, tables, figures
- Stage 18: Discussion Refinement - Interpretation, limitations, implications
- Stage 19: Abstract - Structured abstract generation
- Stage 20: Conference Prep - Submission materials, formatting

All LLM calls route through the orchestrator's AI Router for PHI compliance.

See: Linear ROS-67 (Phase D: Remaining Agents)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from langgraph.graph import StateGraph, END

from ..base.langgraph_base import LangGraphBaseAgent
from ..base.state import AgentState, Message

logger = logging.getLogger(__name__)


class ManuscriptAgent(LangGraphBaseAgent):
    """
    Manuscript Agent for Stages 15-20 of the research workflow.

    Handles:
    - IMRaD manuscript section drafting
    - Citation and reference management
    - Abstract generation with word limits
    - Conference submission preparation
    - Journal formatting compliance
    """

    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        """
        Initialize the Manuscript agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls
            checkpointer: Optional LangGraph checkpointer
        """
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[14, 15, 16, 17, 18, 19, 20],  # Stage 14 = full manuscript draft
            agent_id='manuscript',
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for Manuscript agent.

        Returns:
            Dict of criterion name to threshold
        """
        return {
            'introduction_complete': True,  # Introduction section drafted
            'methods_complete': True,  # Methods section drafted
            'results_complete': True,  # Results section drafted
            'discussion_complete': True,  # Discussion section drafted
            'citation_count': 10,  # Minimum citations
            'word_limit': 5000,  # Maximum words (configurable)
            'abstract_word_limit': 300,  # Abstract max words
            'imrad_structure': True,  # Follows IMRaD format
        }

    def build_graph(self) -> StateGraph:
        """
        Build the Manuscript agent's LangGraph.

        Graph structure:
        start -> draft_introduction -> draft_methods -> draft_results ->
        draft_discussion -> generate_abstract -> format_citations ->
        final_review -> quality_gate -> (improve or END)
        """
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("draft_introduction", self.draft_introduction_node)
        graph.add_node("draft_methods", self.draft_methods_node)
        graph.add_node("draft_results", self.draft_results_node)
        graph.add_node("draft_discussion", self.draft_discussion_node)
        graph.add_node("generate_abstract", self.generate_abstract_node)
        graph.add_node("format_citations", self.format_citations_node)
        graph.add_node("conference_prep", self.conference_prep_node)
        graph.add_node("final_review", self.final_review_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)

        # Define edges
        graph.set_entry_point("draft_introduction")

        graph.add_edge("draft_introduction", "draft_methods")
        graph.add_edge("draft_methods", "draft_results")
        graph.add_edge("draft_results", "draft_discussion")
        graph.add_edge("draft_discussion", "generate_abstract")
        graph.add_edge("generate_abstract", "format_citations")
        graph.add_edge("format_citations", "conference_prep")
        graph.add_edge("conference_prep", "final_review")
        graph.add_edge("final_review", "quality_gate")

        # Conditional routing after quality gate
        graph.add_conditional_edges(
            "quality_gate",
            self._route_after_quality_gate,
            {
                "human_review": "human_review",
                "save_version": "save_version",
                "end": END,
            }
        )

        graph.add_edge("human_review", "save_version")

        # Conditional routing after save_version (improvement loop)
        graph.add_conditional_edges(
            "save_version",
            self.should_continue_improvement,
            {
                "continue": "improve",
                "complete": END,
            }
        )

        # Improvement can target specific sections
        graph.add_conditional_edges(
            "improve",
            self._route_improvement,
            {
                "introduction": "draft_introduction",
                "methods": "draft_methods",
                "results": "draft_results",
                "discussion": "draft_discussion",
                "abstract": "generate_abstract",
                "full": "draft_introduction",
            }
        )

        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')
        governance_mode = state.get('governance_mode', 'DEMO')

        if governance_mode == 'LIVE' and gate_status in ['passed', 'needs_human']:
            return "human_review"

        if gate_status == 'needs_human':
            return "human_review"

        if gate_status == 'passed':
            return "save_version"

        return "save_version"

    def _route_improvement(self, state: AgentState) -> str:
        """Route improvement to specific section based on feedback."""
        feedback = state.get('feedback', '').lower()
        gate_result = state.get('gate_result', {})
        failed_criteria = gate_result.get('criteria_failed', [])

        # Check feedback for section-specific keywords
        if 'introduction' in feedback or 'background' in feedback:
            return "introduction"
        if 'method' in feedback:
            return "methods"
        if 'result' in feedback or 'table' in feedback or 'figure' in feedback:
            return "results"
        if 'discussion' in feedback or 'limitation' in feedback:
            return "discussion"
        if 'abstract' in feedback:
            return "abstract"

        # Check failed criteria
        if 'introduction_complete' in failed_criteria:
            return "introduction"
        if 'methods_complete' in failed_criteria:
            return "methods"
        if 'results_complete' in failed_criteria:
            return "results"
        if 'discussion_complete' in failed_criteria:
            return "discussion"

        return "full"

    # =========================================================================
    # Node Implementations
    # =========================================================================

    async def draft_introduction_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 15: Draft Introduction section.

        Creates background, literature review, rationale, and objectives.
        """
        logger.info(f"[Manuscript] Stage 15: Drafting introduction", extra={'run_id': state.get('run_id')})

        messages = state.get('messages', [])
        previous_output = state.get('current_output', '')
        input_artifacts = state.get('input_artifact_ids', [])

        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Draft the Introduction section for a scientific manuscript:

Previous Analysis/Results:
{previous_output}

Research Context:
{user_context}

Structure the Introduction with these components:

1. OPENING PARAGRAPH
   - Broad context of the research area
   - Why this topic matters (clinical/scientific significance)
   - Current state of knowledge

2. LITERATURE REVIEW
   - Key prior studies (cite appropriately)
   - What is known about the topic
   - Methodological approaches used
   - Findings from previous research

3. GAP IN KNOWLEDGE
   - What remains unknown
   - Limitations of previous studies
   - Why additional research is needed

4. STUDY RATIONALE
   - Why this specific study was conducted
   - What makes this approach novel or valuable
   - How it addresses the gap

5. OBJECTIVES/HYPOTHESES
   - Primary objective clearly stated
   - Secondary objectives if applicable
   - Specific hypotheses being tested

Writing Guidelines:
- Funnel structure (broad → specific)
- Present tense for established knowledge
- Past tense for specific prior studies
- Formal academic tone
- Active voice when appropriate
- Include [Citation needed] markers for claims requiring references
- Target approximately 500-800 words
"""

        introduction_result = await self.call_llm(
            prompt=prompt,
            task_type='introduction_drafting',
            state=state,
            model_tier='STANDARD',
        )

        message = self.add_assistant_message(
            state,
            f"I've drafted the Introduction section:\n\n{introduction_result}"
        )

        return {
            'current_stage': 15,
            'introduction': introduction_result,
            'current_output': introduction_result,
            'messages': [message],
        }

    async def draft_methods_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 16: Draft Methods section.

        Details study design, participants, procedures, and analysis.
        """
        logger.info(f"[Manuscript] Stage 16: Drafting methods", extra={'run_id': state.get('run_id')})

        introduction = state.get('introduction', '')
        previous_output = state.get('current_output', '')

        prompt = f"""Draft the Methods section for a scientific manuscript:

Introduction:
{introduction}

Previous Analysis Documentation:
{previous_output}

Structure the Methods with these subsections:

1. STUDY DESIGN
   - Type of study (cohort, case-control, cross-sectional, etc.)
   - Prospective or retrospective
   - Single/multi-center
   - Observational or interventional

2. SETTING AND PARTICIPANTS
   - Study setting description
   - Inclusion criteria
   - Exclusion criteria
   - Recruitment procedures
   - Sample size justification

3. DATA SOURCES
   - Where data came from
   - Time period of data collection
   - Data quality measures

4. VARIABLES
   - Outcome variables (primary, secondary)
   - Exposure/predictor variables
   - Covariates and confounders
   - How variables were defined/measured

5. STATISTICAL ANALYSIS
   - Descriptive statistics approach
   - Main analytical methods
   - Handling of missing data
   - Sensitivity analyses planned
   - Software used
   - Significance threshold

6. ETHICAL CONSIDERATIONS
   - IRB approval (with number)
   - Consent procedures
   - Data protection measures

Writing Guidelines:
- Past tense throughout
- Sufficient detail for replication
- Justify methodological choices
- Reference established methods
- STROBE/CONSORT compliance
- Target approximately 800-1200 words
"""

        methods_result = await self.call_llm(
            prompt=prompt,
            task_type='methods_drafting',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 16,
            'methods': methods_result,
            'current_output': methods_result,
        }

    async def draft_results_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 17: Draft Results section.

        Presents findings with tables and figures.
        """
        logger.info(f"[Manuscript] Stage 17: Drafting results", extra={'run_id': state.get('run_id')})

        methods = state.get('methods', '')
        previous_output = state.get('current_output', '')

        prompt = f"""Draft the Results section for a scientific manuscript:

Methods:
{methods}

Analysis Results:
{previous_output}

Structure the Results with these components:

1. PARTICIPANT FLOW
   - Number screened
   - Number eligible
   - Number enrolled
   - Numbers analyzed
   - Reasons for exclusion at each stage

2. BASELINE CHARACTERISTICS
   - Demographics (Table 1)
   - Clinical characteristics
   - Comparison between groups (if applicable)

3. PRIMARY OUTCOME
   - Main finding stated clearly
   - Effect estimate with 95% CI
   - P-value
   - Reference to Table/Figure

4. SECONDARY OUTCOMES
   - Each secondary outcome
   - Effect estimates and CIs
   - Appropriate tables

5. SENSITIVITY ANALYSES
   - Results of pre-specified sensitivity analyses
   - How results compare to main analysis

6. SUBGROUP ANALYSES
   - Pre-specified subgroup results
   - Interaction p-values

Writing Guidelines:
- Past tense
- Report findings objectively (no interpretation)
- Lead with the most important finding
- All numbers with appropriate precision
- Reference tables and figures in text
- Ensure text matches table values
- STROBE flow diagram reference
- Target approximately 600-1000 words

TABLE/FIGURE PLACEHOLDERS:
[Table 1: Baseline Characteristics]
[Table 2: Primary and Secondary Outcomes]
[Figure 1: Participant Flow]
[Figure 2: Main Results Visualization]
"""

        results_result = await self.call_llm(
            prompt=prompt,
            task_type='results_drafting',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 17,
            'results': results_result,
            'current_output': results_result,
        }

    async def draft_discussion_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 18: Draft Discussion section.

        Interprets findings, addresses limitations, and draws conclusions.
        """
        logger.info(f"[Manuscript] Stage 18: Drafting discussion", extra={'run_id': state.get('run_id')})

        introduction = state.get('introduction', '')
        results = state.get('results', '')

        prompt = f"""Draft the Discussion section for a scientific manuscript:

Introduction (for context):
{introduction}

Results:
{results}

Structure the Discussion with these components:

1. KEY FINDINGS SUMMARY
   - Restate main findings (1-2 sentences)
   - How findings address the research question
   - Novel contribution

2. COMPARISON WITH LITERATURE
   - How findings compare to prior studies
   - Explain agreements with existing evidence
   - Explain disagreements with existing evidence
   - Why differences might exist

3. BIOLOGICAL/CLINICAL PLAUSIBILITY
   - Potential mechanisms
   - Biological rationale
   - Clinical significance of findings

4. STRENGTHS
   - Methodological strengths
   - Novel aspects
   - Data quality

5. LIMITATIONS
   - Study design limitations
   - Potential biases
   - Generalizability concerns
   - Missing data/variables
   - How limitations might affect conclusions

6. IMPLICATIONS
   - Clinical implications
   - Policy implications
   - Future research directions

7. CONCLUSIONS
   - Brief summary of what was found
   - What this means
   - Key takeaway message

Writing Guidelines:
- Mix of present tense (interpretations) and past tense (study findings)
- Do not repeat results in detail
- Balanced interpretation (avoid overclaiming)
- Address alternative explanations
- Be transparent about limitations
- Target approximately 1000-1500 words
"""

        discussion_result = await self.call_llm(
            prompt=prompt,
            task_type='discussion_drafting',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 18,
            'discussion': discussion_result,
            'current_output': discussion_result,
        }

    async def generate_abstract_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 19: Generate structured abstract.

        Creates a word-limited abstract with all required elements.
        """
        logger.info(f"[Manuscript] Stage 19: Generating abstract", extra={'run_id': state.get('run_id')})

        introduction = state.get('introduction', '')
        methods = state.get('methods', '')
        results = state.get('results', '')
        discussion = state.get('discussion', '')

        prompt = f"""Generate a structured abstract for this manuscript:

Introduction:
{introduction[:1000]}

Methods:
{methods[:1000]}

Results:
{results[:1000]}

Discussion:
{discussion[:1000]}

Create a STRUCTURED ABSTRACT with these sections:

BACKGROUND (2-3 sentences)
- Why the study was done
- Current gap in knowledge

OBJECTIVES (1-2 sentences)
- Primary objective
- Specific aims

METHODS (3-4 sentences)
- Study design
- Setting and participants
- Main measures
- Statistical approach

RESULTS (4-5 sentences)
- Number of participants
- Main findings with specific numbers
- Effect estimates with 95% CI
- P-values for key findings

CONCLUSIONS (2-3 sentences)
- Main conclusion
- Clinical/scientific implications
- Future directions (optional)

WORD LIMIT: Maximum 300 words total

Guidelines:
- Include specific numbers (N, effect sizes, CIs, p-values)
- No references in abstract
- No abbreviations not defined
- Self-contained summary
- Past tense for methods and results
- Present tense for conclusions
"""

        abstract_result = await self.call_llm(
            prompt=prompt,
            task_type='abstract_generation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 19,
            'abstract': abstract_result,
            'current_output': abstract_result,
        }

    async def format_citations_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Format citations and create reference list using enhanced reference management.

        Identifies citation needs, validates references, and formats bibliography.
        """
        logger.info(f"[Manuscript] Formatting citations with enhanced system", extra={'run_id': state.get('run_id')})

        # Try enhanced reference management first
        try:
            from ..writing.reference_management_service import get_reference_service
            from ..writing.types import ReferenceState, CitationStyle
            
            # Compile full manuscript text
            manuscript_sections = {
                'abstract': state.get('abstract', ''),
                'introduction': state.get('introduction', ''),
                'methods': state.get('methods', ''),
                'results': state.get('results', ''),
                'discussion': state.get('discussion', '')
            }
            
            full_manuscript = '\n\n'.join([
                f"{section.upper()}\n{content}" 
                for section, content in manuscript_sections.items() 
                if content
            ])
            
            # Get literature search results from previous stages
            literature_results = state.get('literature_search_results', [])
            
            # Create reference state
            ref_state = ReferenceState(
                study_id=state.get('run_id', 'manuscript'),
                manuscript_text=full_manuscript,
                literature_results=literature_results,
                target_style=CitationStyle.AMA,  # Medical manuscripts typically use AMA
                enable_doi_validation=True,
                enable_duplicate_detection=True,
                enable_quality_assessment=True,
                manuscript_type=state.get('manuscript_type', 'research_article'),
                target_journal=state.get('target_journal'),
                research_field=state.get('research_field', 'medical')
            )
            
            # Get enhanced reference service
            ref_service = await get_reference_service()
            
            # Process references
            ref_result = await ref_service.process_references(ref_state)
            
            # Update manuscript text with proper citation markers
            updated_manuscript = self._update_citations_in_text(full_manuscript, ref_result.citation_map)
            
            # Create enhanced output
            enhanced_output = {
                'formatted_manuscript': updated_manuscript,
                'bibliography': ref_result.bibliography,
                'total_references': ref_result.total_references,
                'quality_summary': {
                    'average_quality': sum(score.overall_score for score in ref_result.quality_scores) / len(ref_result.quality_scores) if ref_result.quality_scores else 0,
                    'high_quality_count': len([score for score in ref_result.quality_scores if score.overall_score >= 0.8]),
                    'warnings_count': len(ref_result.warnings)
                },
                'processing_metadata': {
                    'processing_time': ref_result.processing_time_seconds,
                    'doi_verified_count': len([verified for verified in ref_result.doi_verified.values() if verified]),
                    'duplicates_removed': len(ref_result.duplicate_references),
                    'style_compliance': ref_result.style_compliance_score
                }
            }
            
            # Generate summary message
            summary_parts = [
                f"Citations formatted with enhanced system.",
                f"{ref_result.total_references} references processed.",
                f"Style compliance: {ref_result.style_compliance_score:.1%}."
            ]
            
            if ref_result.warnings:
                summary_parts.append(f"{len(ref_result.warnings)} quality warnings identified.")
            
            if ref_result.duplicate_references:
                summary_parts.append(f"{len(ref_result.duplicate_references)} duplicate groups resolved.")
            
            if ref_result.missing_citations:
                summary_parts.append(f"{len(ref_result.missing_citations)} citations still needed.")
            
            return {
                **enhanced_output,
                'current_output': ' '.join(summary_parts),
                'enhanced_citations': True
            }
            
        except ImportError:
            logger.warning("Enhanced reference management not available, using legacy citation formatting")
        except Exception as e:
            logger.error(f"Enhanced citation processing failed: {e}")
        
        # Fallback to legacy citation formatting
        return await self._format_citations_legacy(state)
    
    async def _format_citations_legacy(self, state: AgentState) -> Dict[str, Any]:
        """
        Legacy citation formatting method.
        """
        introduction = state.get('introduction', '')
        methods = state.get('methods', '')
        discussion = state.get('discussion', '')

        prompt = f"""Format citations and create a reference list:

Introduction:
{introduction}

Methods:
{methods}

Discussion:
{discussion}

Tasks:
1. Identify all [Citation needed] markers
2. Suggest appropriate references for each
3. Create numbered reference list

For each citation needed:
- Suggest the type of reference (original research, review, guideline)
- Provide example citation format
- Note if specific study should be cited

Reference Format (Vancouver/ICMJE style):
1. Author AA, Author BB. Title of article. Journal Name. Year;Volume(Issue):Pages.

Create:
1. List of all citations with their locations
2. Suggested references for each
3. Complete reference list in order of appearance
4. Check for citation-text consistency

Note: These are placeholder references. Actual references should be
verified against the literature by the research team.
"""

        citations_result = await self.call_llm(
            prompt=prompt,
            task_type='citation_formatting',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'citations': citations_result,
            'current_output': citations_result,
            'enhanced_citations': False
        }
    
    def _update_citations_in_text(self, text: str, citation_map: Dict[str, str]) -> str:
        """
        Update citation markers in text with proper formatted citations.
        
        Args:
            text: Original text with citation markers
            citation_map: Mapping from markers to citation numbers
            
        Returns:
            Updated text with formatted citations
        """
        updated_text = text
        
        # Replace citation markers with proper numbers
        for marker, citation_number in citation_map.items():
            # Handle different citation marker formats
            patterns = [
                marker,  # Exact match
                f"[{marker}]",  # Bracketed
                f"({marker})",  # Parenthesized
                marker.replace('[', '\\[').replace(']', '\\]')  # Escaped brackets
            ]
            
            for pattern in patterns:
                if pattern in updated_text:
                    updated_text = updated_text.replace(pattern, f"[{citation_number}]")
                    break
        
        return updated_text

    async def conference_prep_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 20: Prepare conference submission materials.

        Creates materials for conference submission.
        """
        logger.info(f"[Manuscript] Stage 20: Conference prep", extra={'run_id': state.get('run_id')})

        abstract = state.get('abstract', '')
        results = state.get('results', '')

        prompt = f"""Prepare conference submission materials:

Abstract:
{abstract}

Results Summary:
{results[:1500]}

Create the following:

1. CONFERENCE ABSTRACT (250 words max)
   - More concise version of manuscript abstract
   - Key findings highlighted
   - Clinical impact emphasized

2. PRESENTATION TITLE
   - Informative, engaging
   - Under 20 words
   - Includes key finding

3. KEY TALKING POINTS (5-7 bullets)
   - Main messages for presentation
   - Clinical significance points
   - Novel contributions

4. POSTER OUTLINE
   - Suggested sections
   - Content for each section
   - Visual recommendations

5. DISCLOSURE STATEMENT
   - Funding sources template
   - Conflict of interest template

6. AUTHOR CONTRIBUTIONS (CRediT format)
   - Conceptualization
   - Methodology
   - Formal analysis
   - Writing - original draft
   - Writing - review & editing

7. KEYWORDS (5-7)
   - MeSH terms if applicable
   - For indexing purposes

Ensure all materials are consistent with manuscript content.
"""

        conference_result = await self.call_llm(
            prompt=prompt,
            task_type='discussion_drafting',  # Re-use similar tier
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 20,
            'conference_prep': conference_result,
            'current_output': conference_result,
        }

    async def final_review_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Final manuscript review.

        Comprehensive review of all sections.
        """
        logger.info(f"[Manuscript] Final review", extra={'run_id': state.get('run_id')})

        introduction = state.get('introduction', '')
        methods = state.get('methods', '')
        results = state.get('results', '')
        discussion = state.get('discussion', '')
        abstract = state.get('abstract', '')

        prompt = f"""Conduct final review of this manuscript:

ABSTRACT:
{abstract}

INTRODUCTION:
{introduction[:1000]}

METHODS:
{methods[:1000]}

RESULTS:
{results[:1000]}

DISCUSSION:
{discussion[:1000]}

Review checklist:

1. CONSISTENCY CHECK
   - Numbers match between abstract and text
   - Tables referenced correctly
   - Figures referenced correctly
   - Citation numbers sequential

2. STRUCTURE CHECK
   - IMRaD format followed
   - Each section complete
   - Logical flow
   - Appropriate length

3. LANGUAGE CHECK
   - Grammar and spelling
   - Tense consistency
   - Active vs passive voice
   - Jargon minimized

4. SCIENTIFIC ACCURACY
   - Claims supported by data
   - Interpretation appropriate
   - Limitations acknowledged
   - Conclusions justified

5. FORMATTING CHECK
   - Word count within limits
   - Abstract word count
   - Reference format consistent
   - Tables and figures labeled

6. STROBE/CONSORT CHECK
   - Required elements present
   - Checklist items addressed

Provide:
- Issues identified
- Specific corrections needed
- Overall readiness assessment (Ready/Minor revisions/Major revisions)
"""

        review_result = await self.call_llm(
            prompt=prompt,
            task_type='final_review',
            state=state,
            model_tier='PREMIUM',  # Important final pass
        )

        message = self.add_assistant_message(
            state,
            f"Manuscript complete. Here's my final review:\n\n{review_result}"
        )

        return {
            'final_review': review_result,
            'current_output': review_result,
            'messages': [message],
        }

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improvement node for iterating on feedback.
        """
        logger.info(f"[Manuscript] Improving based on feedback", extra={'run_id': state.get('run_id')})

        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})

        prompt = f"""Improve this manuscript section based on feedback:

Current Content:
{current_output}

Feedback:
{feedback}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Provide revised content addressing:
1. Specific issues mentioned in feedback
2. Failed quality criteria
3. Writing quality improvements
4. Scientific accuracy
"""

        improved_result = await self.call_llm(
            prompt=prompt,
            task_type='methods_drafting',  # Generic section improvement
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_output': improved_result,
            'feedback': None,
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _evaluate_criterion(
        self,
        criterion: str,
        threshold: Any,
        output: str,
        state: AgentState,
    ) -> tuple[bool, float]:
        """Evaluate Manuscript-specific criteria."""
        output_lower = output.lower()

        if criterion == 'introduction_complete':
            intro_elements = ['background', 'objective', 'hypothesis', 'rationale', 'literature']
            has_intro = sum(1 for elem in intro_elements if elem in output_lower) >= 3
            return has_intro or bool(state.get('introduction')), 1.0 if has_intro else 0.5

        if criterion == 'methods_complete':
            methods_elements = ['design', 'participant', 'outcome', 'analysis', 'statistical']
            has_methods = sum(1 for elem in methods_elements if elem in output_lower) >= 3
            return has_methods or bool(state.get('methods')), 1.0 if has_methods else 0.5

        if criterion == 'results_complete':
            results_elements = ['finding', 'table', 'figure', 'participant', 'outcome']
            has_results = sum(1 for elem in results_elements if elem in output_lower) >= 3
            return has_results or bool(state.get('results')), 1.0 if has_results else 0.5

        if criterion == 'discussion_complete':
            discussion_elements = ['limitation', 'implication', 'conclusion', 'comparison', 'strength']
            has_discussion = sum(1 for elem in discussion_elements if elem in output_lower) >= 3
            return has_discussion or bool(state.get('discussion')), 1.0 if has_discussion else 0.5

        if criterion == 'citation_count':
            import re
            # Count citation markers and consider enhanced citations
            citation_markers = len(re.findall(r'\[\d+\]|\[Citation', output))
            
            # Boost score if enhanced citation system was used
            enhanced_citations = state.get('enhanced_citations', False)
            if enhanced_citations:
                citation_markers *= 1.2  # 20% bonus for enhanced citations
            
            passed = citation_markers >= threshold
            score = min(1.0, citation_markers / threshold) if threshold > 0 else 1.0
            return passed, score

        if criterion == 'word_limit':
            word_count = len(output.split())
            passed = word_count <= threshold
            score = 1.0 if passed else max(0, 1 - (word_count - threshold) / threshold)
            return passed, score

        if criterion == 'abstract_word_limit':
            abstract = state.get('abstract', '')
            word_count = len(abstract.split())
            passed = word_count <= threshold
            score = 1.0 if passed else max(0, 1 - (word_count - threshold) / threshold)
            return passed, score

        if criterion == 'imrad_structure':
            has_intro = bool(state.get('introduction'))
            has_methods = bool(state.get('methods'))
            has_results = bool(state.get('results'))
            has_discussion = bool(state.get('discussion'))
            all_sections = has_intro and has_methods and has_results and has_discussion
            section_count = sum([has_intro, has_methods, has_results, has_discussion])
            return all_sections, section_count / 4

        return super()._evaluate_criterion(criterion, threshold, output, state)
