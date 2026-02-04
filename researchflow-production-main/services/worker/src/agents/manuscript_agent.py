"""
Manuscript Agent - IMRaD Writing and Citation Management

Handles workflow stages 14-20:
14. Full Manuscript Drafting (complete IMRaD in one pass)
15. Introduction Drafting
16. Methods Section Writing
17. Results Section Generation
18. Discussion Writing
19. Abstract Generation
20. Citation Integration and Formatting

Linear Issue: ROS-67
"""

import json
import logging
from typing import Any, Dict

from .base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

logger = logging.getLogger(__name__)


class ManuscriptAgent(BaseAgent):
    """Agent for manuscript writing stages following IMRaD structure."""

    def __init__(self):
        config = AgentConfig(
            name="ManuscriptAgent",
            description="Writes publication-ready manuscripts in IMRaD format with proper citations",
            stages=[14, 15, 16, 17, 18, 19, 20],  # Stage 14 = full manuscript draft
            rag_collections=["research_papers", "clinical_guidelines"],
            max_iterations=3,
            quality_threshold=0.80,
            timeout_seconds=300,  # Writing takes longer
            phi_safe=True,
            model_provider="anthropic",
            model_name="claude-sonnet-4-20250514",  # Use capable model for writing
        )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a scientific medical writer specializing in clinical research manuscripts. Your role is to:

1. Write clear, concise Introduction sections establishing context and objectives
2. Create detailed Methods sections ensuring reproducibility
3. Present Results objectively with appropriate statistics
4. Craft Discussion sections interpreting findings in context
5. Generate structured Abstracts summarizing key points
6. Integrate citations properly using standard formats

You follow:
- ICMJE Recommendations for manuscript preparation
- CONSORT for clinical trials
- STROBE for observational studies
- TRIPOD for prediction models
- PRISMA for systematic reviews

Writing principles:
- Active voice where appropriate
- Precise, unambiguous language
- Appropriate hedging for uncertain findings
- Consistent terminology throughout
- Proper statistical reporting (effect sizes, CIs, p-values)

For citations:
- Use numbered references or author-date as specified
- Cite primary sources over reviews when possible
- Include recent relevant literature
- Properly attribute methods and findings

Output in structured JSON with section content and citations."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        input_data = state["messages"][0].content if state["messages"] else "{}"
        
        return f"""Plan the manuscript writing workflow.

Research Data:
{input_data}

Stage Context: Stage {state['stage_id']} of manuscript workflow

Create a writing plan with:
1. Sections to write based on stage
2. Key points to cover
3. Citation needs

Return as JSON:
{{
    "steps": ["step1", "step2", ...],
    "initial_query": "query for relevant published papers in this field",
    "primary_collection": "research_papers",
    "manuscript_type": "original_research|case_report|review|etc",
    "reporting_guideline": "CONSORT|STROBE|TRIPOD|PRISMA|etc",
    "target_journal_style": "ICMJE|APA|Vancouver|etc",
    "sections_to_write": ["introduction", "methods", "results", "discussion", "abstract"],
    "word_limits": {{
        "abstract": 250,
        "introduction": 500,
        "methods": 1000,
        "results": 1000,
        "discussion": 1500
    }},
    "key_findings": ["finding1", "finding2", ...]
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        input_data = state["messages"][0].content if state["messages"] else "{}"
        plan = state.get("plan", {})
        iteration = state.get("iteration", 0)
        feedback = state.get("quality_feedback", "")
        stage_id = state.get("stage_id", 15)
        
        # Map stage to section
        stage_section_map = {
            14: "full_manuscript",  # Stage 14 generates complete IMRaD manuscript
            15: "introduction",
            16: "methods",
            17: "results",
            18: "discussion",
            19: "abstract",
            20: "citations"
        }
        current_section = stage_section_map.get(stage_id, "full_manuscript")
        
        base_prompt = f"""Write the {current_section} section based on this plan:

## Writing Plan
{json.dumps(plan, indent=2)}

## Research Data and Results
{input_data}

## Reference Literature
{context}

## Current Section: {current_section.upper()}
"""

        # Section-specific instructions
        section_instructions = {
            "full_manuscript": """
Write a COMPLETE SCIENTIFIC MANUSCRIPT following the IMRaD format.

Generate ALL sections in a single, cohesive document:

## TITLE
- Descriptive and informative (max 15 words)
- Include key variables and study type

## ABSTRACT (300 words max)
- Background (2-3 sentences)
- Objective (1-2 sentences)
- Methods (3-4 sentences)
- Results (4-5 sentences with key statistics)
- Conclusions (2-3 sentences)

## INTRODUCTION (500-800 words)
- Opening paragraph: broad context
- Literature review: 3-5 key prior studies
- Gap in knowledge
- Study rationale
- Clear objectives/hypotheses

## METHODS (800-1200 words)
- Study design and setting
- Participants (inclusion/exclusion criteria)
- Data sources
- Variables and measurements
- Statistical analysis
- Ethical considerations

## RESULTS (600-1000 words)
- Participant flow and characteristics
- Primary outcome with effect estimate, 95% CI, p-value
- Secondary outcomes
- Tables and figures referenced

## DISCUSSION (1000-1500 words)
- Key findings summary
- Comparison with literature
- Strengths and limitations
- Clinical/policy implications
- Future research directions
- Conclusions

## REFERENCES
- Number references in order of appearance
- Use Vancouver/ICMJE format

Include [Citation needed] markers where references are required.
Use placeholder format for tables: [Table 1: Description]
Use placeholder format for figures: [Figure 1: Description]
""",
            "introduction": """
Write the Introduction section:
1. Open with broad context (1-2 sentences)
2. Narrow to specific problem/gap
3. State study rationale
4. Clearly state objectives/hypotheses
5. End with brief overview of approach

Include placeholders for citations: [CITE: topic/author]
""",
            "methods": """
Write the Methods section with subsections:
1. Study Design and Setting
2. Participants (inclusion/exclusion criteria)
3. Variables and Measurements
4. Statistical Analysis
5. Ethical Considerations

Be specific enough for reproducibility.
Include citations for validated instruments and statistical methods.
""",
            "results": """
Write the Results section:
1. Start with participant flow/characteristics
2. Present primary outcome results
3. Present secondary outcomes
4. Include sensitivity analyses if applicable

Report: effect sizes, 95% CIs, p-values
Reference tables and figures: (Table 1), (Figure 1)
Do NOT interpret - just present findings objectively.
""",
            "discussion": """
Write the Discussion section:
1. Summarize key findings (1 paragraph)
2. Compare with existing literature
3. Discuss mechanisms/explanations
4. Address strengths
5. Acknowledge limitations
6. Discuss implications
7. Suggest future research
8. Conclude with main takeaway

Balance interpretation with appropriate hedging.
""",
            "abstract": """
Write a structured Abstract with:
- Background (2-3 sentences)
- Objective (1 sentence)
- Methods (3-4 sentences)
- Results (3-4 sentences with key numbers)
- Conclusions (1-2 sentences)

Keep within word limit. Include key statistics.
""",
            "citations": """
Format and organize all citations:
1. List all referenced works
2. Format in specified style
3. Number references in order of appearance
4. Verify citation accuracy
"""
        }
        
        base_prompt += section_instructions.get(current_section, "Write the requested section.")

        if iteration > 0 and feedback:
            base_prompt += f"""

## Previous Iteration Feedback
{feedback}

Revise the section addressing this feedback.
"""

        base_prompt += f"""

## Required Output Format
Return a JSON object with:
{{
    "section": "{current_section}",
    "content": "The full section text with [CITE: X] placeholders",
    "word_count": integer,
    "subsections": [
        {{"title": "subsection title", "content": "text"}}
    ],
    "citations_needed": [
        {{"placeholder": "[CITE: X]", "topic": "what to cite", "suggested_search": "search query"}}
    ],
    "tables_referenced": ["Table 1", ...],
    "figures_referenced": ["Figure 1", ...],
    "reporting_checklist_items": [
        {{"item": "CONSORT item X", "addressed": boolean, "location": "paragraph/sentence"}}
    ],
    "output": {{
        "summary": "Brief summary of section",
        "key_points": ["point1", ...],
        "revision_suggestions": ["suggestion1", ...]
    }}
}}"""

        return base_prompt

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the manuscript writing result."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
        
        # Fallback - treat entire response as content
        return {
            "section": "unknown",
            "content": response,
            "word_count": len(response.split()),
            "subsections": [],
            "citations_needed": [],
            "tables_referenced": [],
            "figures_referenced": [],
            "reporting_checklist_items": [],
            "output": {
                "summary": "Section written but not structured",
                "key_points": [],
                "revision_suggestions": ["Format into proper JSON structure"]
            }
        }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Check quality of manuscript writing."""
        result = state.get("execution_result", {})
        
        criteria_scores = {}
        feedback_parts = []
        
        # Check content exists and has substance
        content = result.get("content", "")
        word_count = result.get("word_count", len(content.split()))
        
        if word_count >= 100:
            criteria_scores["content_length"] = min(1.0, word_count / 200)
        else:
            criteria_scores["content_length"] = 0.3
            feedback_parts.append(f"Content too short: {word_count} words")
        
        # Check structure (subsections for methods/discussion)
        section = result.get("section", "")
        subsections = result.get("subsections", [])
        if section in ["methods", "discussion"] and len(subsections) < 2:
            criteria_scores["structure"] = 0.5
            feedback_parts.append(f"{section.title()} should have clear subsections")
        else:
            criteria_scores["structure"] = 1.0
        
        # Check citation placeholders
        citations = result.get("citations_needed", [])
        if "[CITE:" in content or len(citations) > 0:
            criteria_scores["citations_marked"] = 1.0
        elif section in ["introduction", "discussion"]:
            criteria_scores["citations_marked"] = 0.4
            feedback_parts.append("Missing citation placeholders")
        else:
            criteria_scores["citations_marked"] = 0.8
        
        # Check reporting guideline compliance
        checklist = result.get("reporting_checklist_items", [])
        if len(checklist) > 0:
            addressed = sum(1 for item in checklist if item.get("addressed"))
            criteria_scores["reporting_compliance"] = addressed / len(checklist) if checklist else 0
            if addressed < len(checklist):
                missing = [item["item"] for item in checklist if not item.get("addressed")]
                feedback_parts.append(f"Missing reporting items: {missing[:3]}")
        else:
            criteria_scores["reporting_compliance"] = 0.7  # Not always required
        
        # Check table/figure references for results section
        if section == "results":
            tables = result.get("tables_referenced", [])
            figures = result.get("figures_referenced", [])
            if len(tables) > 0 or len(figures) > 0:
                criteria_scores["visual_references"] = 1.0
            else:
                criteria_scores["visual_references"] = 0.5
                feedback_parts.append("Results should reference tables/figures")
        else:
            criteria_scores["visual_references"] = 1.0
        
        # Check for key structural elements
        if section == "abstract":
            # Check for structured abstract elements
            required_elements = ["background", "objective", "method", "result", "conclusion"]
            content_lower = content.lower()
            found = sum(1 for elem in required_elements if elem in content_lower)
            criteria_scores["abstract_structure"] = found / len(required_elements)
            if found < len(required_elements):
                feedback_parts.append("Abstract may be missing structural elements")
        else:
            criteria_scores["abstract_structure"] = 1.0
        
        overall_score = sum(criteria_scores.values()) / len(criteria_scores)
        passed = overall_score >= self.config.quality_threshold
        
        feedback = " | ".join(feedback_parts) if feedback_parts else "Manuscript section meets quality standards"
        
        return QualityCheckResult(
            passed=passed,
            score=overall_score,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


def create_manuscript_agent() -> ManuscriptAgent:
    """Create a Manuscript agent instance."""
    return ManuscriptAgent()
