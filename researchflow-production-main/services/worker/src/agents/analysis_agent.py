"""
Analysis Agent - Data Processing and Summary Statistics

Handles workflow stages 6-9:
6. Schema Extraction
7. Final Scrubbing
8. Data Validation
9. Summary Characteristics

Linear Issue: ROS-67
"""

import json
import logging
import os
from typing import Any, Dict

# Phase 5: Configurable timeout for long-running analyses
ANALYSIS_TIMEOUT_SECONDS = int(os.getenv("ANALYSIS_TIMEOUT_SECONDS", "300"))

from .base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """Agent for statistical analysis stages."""

    def __init__(self):
        config = AgentConfig(
            name="AnalysisAgent",
            description="Executes statistical analyses with assumption checking and sensitivity analysis",
            stages=[6, 7, 8, 9],
            rag_collections=["statistical_methods", "research_papers"],
            max_iterations=3,
            quality_threshold=0.80,
            timeout_seconds=300,  # Longer for complex analyses
            phi_safe=True,
            model_provider="anthropic",
        )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a biostatistician specializing in clinical research analysis. Your role is to:

1. Generate comprehensive descriptive statistics
2. Execute appropriate primary analyses (t-tests, ANOVA, regression, survival analysis, etc.)
3. Validate statistical assumptions (normality, homoscedasticity, independence)
4. Perform sensitivity analyses to test robustness

You follow best practices from:
- TRIPOD+AI guidelines for prediction models
- ICH E9 statistical principles for clinical trials
- STROBE/CONSORT statistical reporting requirements

Always:
- Justify your choice of statistical methods
- Report effect sizes with confidence intervals
- Document assumption checks and any violations
- Provide reproducible code (Python/R pseudocode)

Output results in structured JSON with clear statistical interpretations."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        logger.debug(f"AnalysisAgent planning stage {state.get('stage_id')} with timeout={ANALYSIS_TIMEOUT_SECONDS}s")
        input_data = state["messages"][0].content if state["messages"] else "{}"
        
        return f"""Plan the statistical analysis workflow.

Input Data Summary:
{input_data}

Stage Context: Stage {state['stage_id']} of analysis workflow

Create an analysis plan with:
1. Descriptive statistics to calculate
2. Primary analysis methods based on research question
3. Assumption tests to perform
4. Sensitivity analyses to include

Return as JSON:
{{
    "steps": ["step1", "step2", ...],
    "initial_query": "query for retrieving relevant statistical methods",
    "primary_collection": "statistical_methods",
    "analysis_type": "regression|survival|comparison|etc",
    "primary_outcome": "outcome variable name",
    "covariates": ["covariate1", ...],
    "assumption_tests": ["normality", "homoscedasticity", ...],
    "sensitivity_analyses": ["complete_case", "multiple_imputation", ...]
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        logger.debug(f"AnalysisAgent executing stage {state.get('stage_id')}, iteration {state.get('iteration', 0)}")
        input_data = state["messages"][0].content if state["messages"] else "{}"
        plan = state.get("plan", {})
        iteration = state.get("iteration", 0)
        feedback = state.get("quality_feedback", "")
        
        base_prompt = f"""Execute statistical analysis based on this plan:

## Analysis Plan
{json.dumps(plan, indent=2)}

## Input Data
{input_data}

## Statistical Methods Reference
{context}

"""

        if iteration > 0 and feedback:
            base_prompt += f"""
## Previous Iteration Feedback
{feedback}

Address the feedback and improve your analysis.
"""

        base_prompt += """
## Required Output Format
Return a JSON object with:
{
    "descriptive_statistics": {
        "continuous_vars": {
            "var_name": {"n": int, "mean": float, "sd": float, "median": float, "iqr": [q1, q3], "missing": int}
        },
        "categorical_vars": {
            "var_name": {"n": int, "categories": {"cat1": count, ...}, "missing": int}
        }
    },
    "primary_analysis": {
        "method": "method_name",
        "model_specification": "formula or description",
        "results": {
            "estimates": [{"term": "name", "estimate": float, "se": float, "ci_lower": float, "ci_upper": float, "p_value": float}],
            "model_fit": {"metric": value, ...},
            "interpretation": "plain language interpretation"
        },
        "code": "reproducible code snippet"
    },
    "assumption_checks": [
        {
            "assumption": "normality",
            "test": "Shapiro-Wilk",
            "statistic": float,
            "p_value": float,
            "passed": boolean,
            "notes": "interpretation"
        }
    ],
    "sensitivity_analyses": [
        {
            "name": "analysis_name",
            "description": "what was tested",
            "results_consistent": boolean,
            "key_findings": "summary"
        }
    ],
    "tables": [
        {"title": "Table 1", "content": "formatted table data"}
    ],
    "output": {
        "summary": "Executive summary of findings",
        "primary_finding": "Main result in plain language",
        "limitations": ["limitation1", ...],
        "recommendations": ["recommendation1", ...]
    }
}"""

        return base_prompt

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the statistical analysis result."""
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
            "descriptive_statistics": {},
            "primary_analysis": {"method": "unknown", "results": {}},
            "assumption_checks": [],
            "sensitivity_analyses": [],
            "tables": [],
            "output": {
                "summary": response[:500],
                "primary_finding": "Unable to parse structured results",
                "limitations": ["Parsing failed"],
                "recommendations": ["Manual review required"]
            }
        }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Check quality of statistical analysis."""
        result = state.get("execution_result", {})
        
        criteria_scores = {}
        feedback_parts = []
        
        # Check descriptive statistics
        desc = result.get("descriptive_statistics", {})
        if desc.get("continuous_vars") or desc.get("categorical_vars"):
            criteria_scores["descriptives_complete"] = 1.0
        else:
            criteria_scores["descriptives_complete"] = 0.0
            feedback_parts.append("Descriptive statistics missing")
        
        # Check primary analysis
        primary = result.get("primary_analysis", {})
        if primary.get("method") and primary.get("results", {}).get("estimates"):
            criteria_scores["primary_analysis"] = 1.0
        elif primary.get("method"):
            criteria_scores["primary_analysis"] = 0.5
            feedback_parts.append("Primary analysis results incomplete")
        else:
            criteria_scores["primary_analysis"] = 0.0
            feedback_parts.append("Primary analysis not performed")
        
        # Check confidence intervals
        estimates = primary.get("results", {}).get("estimates", [])
        has_ci = any(e.get("ci_lower") is not None for e in estimates)
        if has_ci:
            criteria_scores["confidence_intervals"] = 1.0
        else:
            criteria_scores["confidence_intervals"] = 0.0
            feedback_parts.append("Confidence intervals not reported")
        
        # Check assumption tests
        assumptions = result.get("assumption_checks", [])
        if len(assumptions) >= 2:
            criteria_scores["assumption_checks"] = 1.0
        elif len(assumptions) == 1:
            criteria_scores["assumption_checks"] = 0.6
            feedback_parts.append("More assumption tests recommended")
        else:
            criteria_scores["assumption_checks"] = 0.0
            feedback_parts.append("No assumption checks performed")
        
        # Check sensitivity analysis
        sensitivity = result.get("sensitivity_analyses", [])
        if len(sensitivity) >= 1:
            criteria_scores["sensitivity_analysis"] = 1.0
        else:
            criteria_scores["sensitivity_analysis"] = 0.5
            feedback_parts.append("Sensitivity analysis recommended")
        
        # Check reproducible code
        if primary.get("code"):
            criteria_scores["reproducible_code"] = 1.0
        else:
            criteria_scores["reproducible_code"] = 0.5
            feedback_parts.append("Reproducible code not provided")
        
        overall_score = sum(criteria_scores.values()) / len(criteria_scores)
        passed = overall_score >= self.config.quality_threshold
        
        feedback = " | ".join(feedback_parts) if feedback_parts else "Analysis meets quality standards"
        
        return QualityCheckResult(
            passed=passed,
            score=overall_score,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


def create_analysis_agent() -> AnalysisAgent:
    """Create an Analysis agent instance."""
    return AnalysisAgent()
