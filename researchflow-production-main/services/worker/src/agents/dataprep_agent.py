"""
DataPrep Agent - Data Preparation and Validation

Handles workflow stages 1-2, 4-5:
1. Topic Declaration
2. Literature Search
4. Variable Definition
5. PHI Scanning

Note: Stage 3 (IRB Proposal) is handled by IRBAgent.

Linear Issue: ROS-67
"""

import json
import logging
from typing import Any, Dict, List

from .base_agent import (
    BaseAgent,
    AgentConfig,
    AgentState,
    QualityCheckResult,
)

logger = logging.getLogger(__name__)


class DataPrepAgent(BaseAgent):
    """Agent for data preparation and validation stages."""

    def __init__(self):
        config = AgentConfig(
            name="DataPrepAgent",
            description="Validates, cleans, and prepares research data for analysis",
            stages=[1, 2, 4, 5],  # Stage 3 (IRB) handled by IRBAgent
            rag_collections=["research_papers", "statistical_methods"],
            max_iterations=3,
            quality_threshold=0.85,
            timeout_seconds=180,
            phi_safe=True,  # Data may contain PHI
            model_provider="anthropic",
        )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are a research data preparation specialist. Your role is to:

1. Validate data formats and structures
2. Map variables to standardized codebooks
3. Identify and handle missing values appropriately
4. Detect and treat outliers based on statistical methods
5. Transform and normalize data for analysis

You follow best practices from:
- STROBE guidelines for observational studies
- CONSORT guidelines for clinical trials
- FDA data quality standards for clinical research

Always explain your reasoning and provide reproducible code/methods.
When handling sensitive data, assume PHI may be present and flag appropriately.

Output your results in structured JSON format with clear documentation."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        logger.debug(f"DataPrepAgent planning stage {state.get('stage_id')} with {len(state.get('messages', []))} messages")
        input_data = state["messages"][0].content if state["messages"] else "{}"
        
        return f"""Plan the data preparation workflow for this task.

Input Data Summary:
{input_data}

Stage Context: Stage {state['stage_id']} of data preparation workflow

Create a plan with:
1. Steps to validate and prepare the data
2. Key queries for retrieving relevant methodology
3. Quality criteria for success

Return as JSON:
{{
    "steps": ["step1", "step2", ...],
    "initial_query": "query for retrieving relevant data preparation methods",
    "primary_collection": "research_papers or statistical_methods",
    "quality_criteria": ["criterion1", "criterion2", ...],
    "expected_outputs": ["output1", "output2", ...]
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        logger.debug(f"DataPrepAgent executing stage {state.get('stage_id')}, iteration {state.get('iteration', 0)}")
        input_data = state["messages"][0].content if state["messages"] else "{}"
        plan = state.get("plan", {})
        iteration = state.get("iteration", 0)
        feedback = state.get("quality_feedback", "")
        
        base_prompt = f"""Execute data preparation based on this plan:

## Plan
{json.dumps(plan, indent=2)}

## Input Data
{input_data}

## Reference Context
{context}

## Current Step
Step {state.get('current_step', 1)} of {state.get('total_steps', 1)}
"""

        if iteration > 0 and feedback:
            base_prompt += f"""
## Previous Iteration Feedback
{feedback}

Please address the feedback and improve your output.
"""

        base_prompt += """
## Required Output Format
Return a JSON object with:
{
    "validation_results": {
        "format_valid": boolean,
        "issues_found": ["issue1", ...],
        "warnings": ["warning1", ...]
    },
    "variable_mapping": {
        "original_name": "standardized_name",
        ...
    },
    "cleaning_actions": [
        {"action": "description", "affected_rows": count, "method": "method_name"}
    ],
    "outlier_analysis": {
        "method": "IQR|Z-score|etc",
        "outliers_detected": count,
        "treatment": "description"
    },
    "transformations": [
        {"variable": "name", "transformation": "description", "reason": "why"}
    ],
    "output": {
        "summary": "Overall summary",
        "ready_for_analysis": boolean,
        "recommendations": ["rec1", ...]
    },
    "phi_flags": ["any PHI-related concerns"]
}"""

        return base_prompt

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the data preparation result."""
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif "{" in response:
                start = response.index("{")
                end = response.rindex("}") + 1
                return json.loads(response[start:end])
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse JSON response: {e}")
        
        # Fallback structure
        return {
            "validation_results": {"format_valid": True, "issues_found": [], "warnings": []},
            "variable_mapping": {},
            "cleaning_actions": [],
            "outlier_analysis": {"method": "unknown", "outliers_detected": 0},
            "transformations": [],
            "output": {
                "summary": response[:500],
                "ready_for_analysis": False,
                "recommendations": ["Manual review recommended"]
            },
            "phi_flags": []
        }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Check quality of data preparation results."""
        result = state.get("execution_result", {})
        
        criteria_scores = {}
        feedback_parts = []
        
        # Check validation completeness
        validation = result.get("validation_results", {})
        if validation.get("format_valid") is not None:
            criteria_scores["validation_complete"] = 1.0
        else:
            criteria_scores["validation_complete"] = 0.0
            feedback_parts.append("Data validation not completed")
        
        # Check variable mapping
        mapping = result.get("variable_mapping", {})
        if len(mapping) > 0:
            criteria_scores["variable_mapping"] = 1.0
        else:
            criteria_scores["variable_mapping"] = 0.5
            feedback_parts.append("Variable mapping may be incomplete")
        
        # Check cleaning documentation
        cleaning = result.get("cleaning_actions", [])
        if len(cleaning) > 0 or validation.get("issues_found", []) == []:
            criteria_scores["cleaning_documented"] = 1.0
        else:
            criteria_scores["cleaning_documented"] = 0.5
            feedback_parts.append("Cleaning actions not documented")
        
        # Check outlier analysis
        outliers = result.get("outlier_analysis", {})
        if outliers.get("method"):
            criteria_scores["outlier_analysis"] = 1.0
        else:
            criteria_scores["outlier_analysis"] = 0.3
            feedback_parts.append("Outlier analysis method not specified")
        
        # Check PHI handling
        phi_flags = result.get("phi_flags", [])
        output = result.get("output", {})
        if output.get("ready_for_analysis") and len(phi_flags) == 0:
            criteria_scores["phi_safe"] = 1.0
        elif len(phi_flags) > 0:
            criteria_scores["phi_safe"] = 0.7
            feedback_parts.append(f"PHI concerns flagged: {phi_flags}")
        else:
            criteria_scores["phi_safe"] = 0.8
        
        # Calculate overall score
        overall_score = sum(criteria_scores.values()) / len(criteria_scores)
        passed = overall_score >= self.config.quality_threshold
        
        feedback = " | ".join(feedback_parts) if feedback_parts else "Data preparation meets quality standards"
        
        return QualityCheckResult(
            passed=passed,
            score=overall_score,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


# Factory function
def create_dataprep_agent() -> DataPrepAgent:
    """Create a DataPrep agent instance."""
    return DataPrepAgent()
