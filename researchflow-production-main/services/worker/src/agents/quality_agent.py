"""
Quality Agent - Gap Analysis, Ideation, Selection, and Statistics

Handles workflow stages 10-13:
10. Literature Gap Analysis
11. Manuscript Ideation
12. Manuscript Selection
13. Statistical Analysis

Linear Issue: ROS-67
"""

import json
import logging
import os
from typing import Any, Dict

# Phase 5: Configurable QC sensitivity levels
QC_SENSITIVITY = os.getenv("QC_SENSITIVITY", "medium")
QC_THRESHOLDS = {
    "low": {"error_rate": 0.15, "confidence": 0.80},
    "medium": {"error_rate": 0.10, "confidence": 0.85},
    "high": {"error_rate": 0.05, "confidence": 0.90},
}

from .base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

logger = logging.getLogger(__name__)


class QualityAgent(BaseAgent):
    """Agent for quality output generation and verification."""

    def __init__(self):
        config = AgentConfig(
            name="QualityAgent",
            description="Generates publication-quality figures and tables with integrity verification",
            stages=[10, 11, 12, 13],  # Stage 13 = Results Interpretation
            rag_collections=["clinical_guidelines", "research_papers"],
            max_iterations=3,
            quality_threshold=0.85,
            timeout_seconds=180,
            phi_safe=True,
            model_provider="anthropic",
        )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a research visualization and quality specialist. Your role is to:

1. Generate publication-quality figures following journal guidelines
2. Create properly formatted tables (Table 1 demographics, results tables)
3. Verify data integrity and reproducibility
4. Ensure accessibility (colorblind-safe palettes, alt text)

You follow:
- ICMJE figure and table requirements
- APA/journal-specific formatting guidelines
- FAIR data principles
- Accessibility standards (WCAG for visualizations)

For figures:
- Use appropriate chart types for data
- Include proper axis labels, legends, and titles
- Specify colorblind-safe color palettes
- Provide matplotlib/seaborn/ggplot2 code

For tables:
- Follow Table 1 conventions for baseline characteristics
- Include appropriate statistics (n, %, mean±SD, median [IQR])
- Add footnotes for abbreviations and significance levels

Output in structured JSON with reproducible specifications."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        logger.debug(f"QualityAgent planning stage {state.get('stage_id')} with sensitivity={QC_SENSITIVITY}")
        input_data = state["messages"][0].content if state["messages"] else "{}"
        
        return f"""Plan the quality output generation workflow.

Input (Analysis Results):
{input_data}

Stage Context: Stage {state['stage_id']} of quality workflow

Create a plan for:
1. Figures to generate (types, data mappings)
2. Tables to create (structure, statistics)
3. Integrity checks to perform

Return as JSON:
{{
    "steps": ["step1", "step2", ...],
    "initial_query": "query for figure/table guidelines",
    "primary_collection": "clinical_guidelines",
    "figures_needed": [
        {{"type": "bar|line|scatter|forest|kaplan_meier", "purpose": "description"}}
    ],
    "tables_needed": [
        {{"type": "baseline|results|comparison", "title": "Table X"}}
    ],
    "integrity_checks": ["reproducibility", "value_ranges", "totals_match"]
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        thresholds = QC_THRESHOLDS.get(QC_SENSITIVITY, QC_THRESHOLDS["medium"])
        logger.debug(f"QualityAgent executing stage {state.get('stage_id')}, thresholds={thresholds}")
        input_data = state["messages"][0].content if state["messages"] else "{}"
        plan = state.get("plan", {})
        iteration = state.get("iteration", 0)
        feedback = state.get("quality_feedback", "")
        
        base_prompt = f"""Generate quality outputs based on this plan:

## Plan
{json.dumps(plan, indent=2)}

## Analysis Results
{input_data}

## Guidelines Reference
{context}

"""

        if iteration > 0 and feedback:
            base_prompt += f"""
## Previous Iteration Feedback
{feedback}

Address the feedback and improve outputs.
"""

        base_prompt += """
## Required Output Format
Return a JSON object with:
{
    "figures": [
        {
            "id": "fig1",
            "title": "Figure 1: Description",
            "type": "bar|line|scatter|forest|kaplan_meier|heatmap",
            "data_source": "description of data used",
            "specification": {
                "x_var": "variable_name",
                "y_var": "variable_name",
                "grouping": "optional grouping var",
                "error_bars": "95% CI|SE|SD",
                "color_palette": "colorblind_safe_name"
            },
            "code": "matplotlib/seaborn code to reproduce",
            "alt_text": "Accessibility description",
            "caption": "Full figure caption"
        }
    ],
    "tables": [
        {
            "id": "table1",
            "title": "Table 1: Baseline Characteristics",
            "type": "baseline|results|comparison",
            "columns": ["Characteristic", "Group A (n=X)", "Group B (n=Y)", "P-value"],
            "rows": [
                ["Age, mean (SD)", "45.2 (12.3)", "44.8 (11.9)", "0.82"],
                ...
            ],
            "footnotes": ["Abbreviations: ...", "* p < 0.05"],
            "format_spec": "APA|ICMJE|journal_specific"
        }
    ],
    "integrity_verification": {
        "checks_performed": [
            {
                "check": "check_name",
                "description": "what was verified",
                "status": "passed|warning|failed",
                "details": "specifics"
            }
        ],
        "data_provenance": {
            "source_files": ["file1", ...],
            "processing_steps": ["step1", ...],
            "hash": "data_hash_if_available"
        },
        "reproducibility_score": 0.0-1.0
    },
    "output": {
        "summary": "Summary of generated outputs",
        "publication_ready": boolean,
        "recommendations": ["rec1", ...]
    }
}"""

        return base_prompt

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the quality output result."""
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
        
        return {
            "figures": [],
            "tables": [],
            "integrity_verification": {"checks_performed": [], "reproducibility_score": 0.0},
            "output": {
                "summary": response[:500],
                "publication_ready": False,
                "recommendations": ["Manual formatting required"]
            }
        }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Check quality of generated outputs."""
        result = state.get("execution_result", {})
        
        criteria_scores = {}
        feedback_parts = []
        
        # Check figures
        figures = result.get("figures", [])
        if len(figures) > 0:
            # Check figure completeness
            complete_figs = sum(1 for f in figures if f.get("code") and f.get("alt_text"))
            criteria_scores["figures_complete"] = complete_figs / len(figures) if figures else 0
            if complete_figs < len(figures):
                feedback_parts.append("Some figures missing code or alt text")
        else:
            criteria_scores["figures_complete"] = 0.5  # May not need figures
        
        # Check tables
        tables = result.get("tables", [])
        if len(tables) > 0:
            complete_tables = sum(1 for t in tables if t.get("rows") and t.get("footnotes"))
            criteria_scores["tables_complete"] = complete_tables / len(tables) if tables else 0
            if complete_tables < len(tables):
                feedback_parts.append("Some tables missing rows or footnotes")
        else:
            criteria_scores["tables_complete"] = 0.5
        
        # Check integrity verification
        integrity = result.get("integrity_verification", {})
        checks = integrity.get("checks_performed", [])
        if len(checks) >= 2:
            passed_checks = sum(1 for c in checks if c.get("status") == "passed")
            criteria_scores["integrity_verified"] = passed_checks / len(checks) if checks else 0
        else:
            criteria_scores["integrity_verified"] = 0.3
            feedback_parts.append("Insufficient integrity checks")
        
        # Check reproducibility score
        repro_score = integrity.get("reproducibility_score", 0)
        criteria_scores["reproducibility"] = repro_score
        if repro_score < 0.8:
            feedback_parts.append(f"Reproducibility score low: {repro_score:.2f}")
        
        # Check accessibility
        has_alt_text = all(f.get("alt_text") for f in figures) if figures else True
        criteria_scores["accessibility"] = 1.0 if has_alt_text else 0.5
        if not has_alt_text:
            feedback_parts.append("Missing alt text for accessibility")
        
        overall_score = sum(criteria_scores.values()) / len(criteria_scores)
        passed = overall_score >= self.config.quality_threshold
        
        feedback = " | ".join(feedback_parts) if feedback_parts else "Quality outputs meet standards"
        
        return QualityCheckResult(
            passed=passed,
            score=overall_score,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


def create_quality_agent() -> QualityAgent:
    """Create a Quality agent instance."""
    return QualityAgent()
