"""
DataPrep Agent - Stages 1-5: Data extraction, validation, cleaning, variable selection, cohort definition.

This agent handles the initial data preparation phases of the research workflow:
- Stage 1: Data Extraction - Extract structured data from clinical documents
- Stage 2: Data Validation - Run Pandera schemas, identify quality issues
- Stage 3: Data Cleaning - Apply fixes, handle missing values
- Stage 4: Variable Selection - Identify key variables for analysis
- Stage 5: Cohort Definition - Apply inclusion/exclusion criteria

All LLM calls route through the orchestrator's AI Router for PHI compliance.

See: Linear ROS-65 (Phase B: DataPrep Agent)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from langgraph.graph import StateGraph, END

from ..base.langgraph_base import LangGraphBaseAgent
from ..base.state import AgentState, AgentId, Message

logger = logging.getLogger(__name__)


class DataPrepAgent(LangGraphBaseAgent):
    """
    DataPrep Agent for Stages 1-5 of the research workflow.

    Handles:
    - Data extraction from clinical documents
    - Schema validation using Pandera
    - Data quality assessment and cleaning
    - Variable selection for analysis
    - Cohort definition with inclusion/exclusion criteria
    """

    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        """
        Initialize the DataPrep agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls
            checkpointer: Optional LangGraph checkpointer
        """
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[1, 2, 3, 4, 5],
            agent_id='dataprep',
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for DataPrep agent.

        Returns:
            Dict of criterion name to threshold
        """
        return {
            'min_rows': 30,  # Minimum rows for meaningful analysis
            'max_missing_percent': 20,  # Maximum 20% missing values
            'schema_valid': True,  # Pandera schema must pass
            'variables_selected': True,  # At least one variable selected
            'cohort_defined': True,  # Cohort criteria specified
        }

    def build_graph(self) -> StateGraph:
        """
        Build the DataPrep agent's LangGraph.

        Graph structure:
        start -> extract_data -> validate_schema -> identify_issues ->
        suggest_fixes -> apply_fixes -> select_variables ->
        define_cohort -> quality_gate -> (improve or END)
        """
        # Create the state graph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("extract_data", self.extract_data_node)
        graph.add_node("validate_schema", self.validate_schema_node)
        graph.add_node("identify_issues", self.identify_issues_node)
        graph.add_node("suggest_fixes", self.suggest_fixes_node)
        graph.add_node("apply_fixes", self.apply_fixes_node)
        graph.add_node("select_variables", self.select_variables_node)
        graph.add_node("define_cohort", self.define_cohort_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)

        # Define edges
        graph.set_entry_point("extract_data")

        graph.add_edge("extract_data", "validate_schema")
        graph.add_edge("validate_schema", "identify_issues")
        graph.add_edge("identify_issues", "suggest_fixes")
        graph.add_edge("suggest_fixes", "apply_fixes")
        graph.add_edge("apply_fixes", "select_variables")
        graph.add_edge("select_variables", "define_cohort")
        graph.add_edge("define_cohort", "quality_gate")

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

        graph.add_edge("improve", "validate_schema")

        # Compile with checkpointer
        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')
        governance_mode = state.get('governance_mode', 'DEMO')

        # In LIVE mode, always require human review for data prep
        if governance_mode == 'LIVE' and gate_status in ['passed', 'needs_human']:
            return "human_review"

        if gate_status == 'needs_human':
            return "human_review"

        if gate_status == 'passed':
            return "save_version"

        # Failed - still save version for improvement
        return "save_version"

    # =========================================================================
    # Node Implementations
    # =========================================================================

    async def extract_data_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 1: Extract structured data from clinical documents.

        Uses LLM to identify and extract key data fields from
        clinical documents, forms, and raw text.
        """
        logger.info(f"[DataPrep] Stage 1: Extracting data", extra={'run_id': state.get('run_id')})

        # Get input context
        input_artifacts = state.get('input_artifact_ids', [])
        messages = state.get('messages', [])

        # Build extraction prompt
        prompt = self._build_extraction_prompt(input_artifacts, messages)

        # Call LLM for extraction
        extraction_result = await self.call_llm(
            prompt=prompt,
            task_type='data_validation',
            state=state,
            model_tier='STANDARD',
        )

        # Create assistant message
        message = self.add_assistant_message(
            state,
            f"I've extracted the data from the provided documents. {extraction_result}"
        )

        return {
            'current_stage': 1,
            'current_output': extraction_result,
            'messages': [message],
            'extraction_result': extraction_result,
        }

    async def validate_schema_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 2: Validate data against Pandera schemas.

        Runs schema validation and identifies type mismatches,
        constraint violations, and missing required fields.
        """
        logger.info(f"[DataPrep] Stage 2: Validating schema", extra={'run_id': state.get('run_id')})

        # Get current data state
        extraction_result = state.get('extraction_result', '')

        # Build validation prompt
        prompt = f"""Analyze this extracted data for schema validation issues:

{extraction_result}

Check for:
1. Data type mismatches (strings where numbers expected, etc.)
2. Required field violations (missing mandatory fields)
3. Value range violations (negative ages, future dates, etc.)
4. Format issues (inconsistent date formats, invalid codes)

Return a structured assessment with:
- Schema: Identified schema pattern
- Valid: true/false
- Issues: List of validation issues found
- Severity: For each issue (error/warning)
"""

        validation_result = await self.call_llm(
            prompt=prompt,
            task_type='schema_validation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 2,
            'validation_result': validation_result,
            'current_output': validation_result,
        }

    async def identify_issues_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 3 prep: Identify data quality issues.

        Analyzes data for missing values, outliers, inconsistencies,
        and other quality concerns.
        """
        logger.info(f"[DataPrep] Stage 3: Identifying issues", extra={'run_id': state.get('run_id')})

        validation_result = state.get('validation_result', '')
        extraction_result = state.get('extraction_result', '')

        prompt = f"""Based on this data and validation results, identify data quality issues:

Data:
{extraction_result}

Validation Result:
{validation_result}

Analyze for:
1. Missing values - Which fields have missing data? What percentage?
2. Outliers - Any values that seem unusual for their context?
3. Inconsistencies - Conflicting values across related fields?
4. Duplicates - Potential duplicate records?
5. Temporal issues - Out-of-sequence dates or events?

For each issue:
- Describe the problem
- Specify affected records/fields
- Assess impact on analysis (high/medium/low)
- Note if this is likely data entry error vs. true data
"""

        issues_result = await self.call_llm(
            prompt=prompt,
            task_type='data_validation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 3,
            'issues_identified': issues_result,
            'current_output': issues_result,
        }

    async def suggest_fixes_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 3: Suggest fixes for identified issues.

        Proposes concrete solutions for data quality problems.
        """
        logger.info(f"[DataPrep] Suggesting fixes", extra={'run_id': state.get('run_id')})

        issues = state.get('issues_identified', '')

        prompt = f"""Given these data quality issues, suggest appropriate fixes:

Issues:
{issues}

For each issue, provide:
1. Recommended fix (imputation method, removal, correction, etc.)
2. Justification for the approach
3. Potential risks of the fix
4. Whether manual review is needed

Follow these principles:
- Prefer conservative fixes over aggressive changes
- Document all transformations for reproducibility
- Flag PHI-related issues for special handling
- Consider statistical implications of each fix
"""

        fixes_result = await self.call_llm(
            prompt=prompt,
            task_type='data_validation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'suggested_fixes': fixes_result,
            'current_output': fixes_result,
        }

    async def apply_fixes_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Apply suggested fixes (in DEMO mode, just describe).

        In LIVE mode, this would trigger actual data transformations
        with human approval.
        """
        logger.info(f"[DataPrep] Applying fixes", extra={'run_id': state.get('run_id')})

        suggested_fixes = state.get('suggested_fixes', '')
        governance_mode = state.get('governance_mode', 'DEMO')

        if governance_mode == 'DEMO':
            result = f"""[DEMO MODE] The following fixes would be applied in production:

{suggested_fixes}

No actual data modifications were made. In LIVE mode, these changes would be:
1. Applied to a working copy of the data
2. Logged for audit purposes
3. Reversible via version control
"""
        else:
            result = f"""Fixes to be applied (requires human approval):

{suggested_fixes}

Awaiting approval before modifying data."""

        return {
            'fixes_applied': result,
            'current_output': result,
        }

    async def select_variables_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 4: Select key variables for analysis.

        Identifies outcome variables, predictors, confounders,
        and potential effect modifiers.
        """
        logger.info(f"[DataPrep] Stage 4: Selecting variables", extra={'run_id': state.get('run_id')})

        extraction_result = state.get('extraction_result', '')
        messages = state.get('messages', [])

        # Get research context from messages
        user_context = "\n".join([m['content'] for m in messages if m['role'] == 'user'])

        prompt = f"""Based on this data and research context, select variables for analysis:

Data Available:
{extraction_result}

Research Context:
{user_context}

Identify and categorize:
1. Primary outcome variable(s) - Main endpoints of interest
2. Exposure/intervention variable(s) - Key independent variables
3. Potential confounders - Variables that may affect both exposure and outcome
4. Effect modifiers - Variables that may modify the exposure-outcome relationship
5. Covariates - Other variables to consider

For each variable:
- Provide the variable name and type
- Explain why it was selected
- Note any data quality concerns
- Suggest appropriate handling (continuous, categorical, transformation)
"""

        variables_result = await self.call_llm(
            prompt=prompt,
            task_type='variable_selection',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 4,
            'variables_selected': variables_result,
            'current_output': variables_result,
        }

    async def define_cohort_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 5: Define study cohort with inclusion/exclusion criteria.

        Specifies which subjects are included in the analysis
        and why others are excluded.
        """
        logger.info(f"[DataPrep] Stage 5: Defining cohort", extra={'run_id': state.get('run_id')})

        extraction_result = state.get('extraction_result', '')
        variables_result = state.get('variables_selected', '')
        messages = state.get('messages', [])

        user_context = "\n".join([m['content'] for m in messages if m['role'] == 'user'])

        prompt = f"""Define the study cohort for this analysis:

Data:
{extraction_result}

Selected Variables:
{variables_result}

Research Context:
{user_context}

Provide:
1. Inclusion criteria - Who is included and why
2. Exclusion criteria - Who is excluded and why
3. Time frame - Study period definition
4. Expected sample size after applying criteria
5. CONSORT-style flow diagram description

Consider:
- Missing data thresholds
- Follow-up requirements
- Population generalizability
- Potential selection bias
"""

        cohort_result = await self.call_llm(
            prompt=prompt,
            task_type='cohort_definition',
            state=state,
            model_tier='STANDARD',
        )

        # Create summary message
        message = self.add_assistant_message(
            state,
            f"Data preparation complete. Here's the cohort definition:\n\n{cohort_result}"
        )

        return {
            'current_stage': 5,
            'cohort_defined': cohort_result,
            'current_output': cohort_result,
            'messages': [message],
        }

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improvement node for iterating on feedback.

        Applies feedback from quality gate or human review
        to improve the data preparation.
        """
        logger.info(f"[DataPrep] Improving based on feedback", extra={'run_id': state.get('run_id')})

        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})

        # Build improvement prompt
        prompt = f"""Improve this data preparation based on feedback:

Current Output:
{current_output}

Feedback:
{feedback}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Address the specific issues raised and provide an improved version.
Focus on the failed criteria and incorporate the feedback directly.
"""

        improved_result = await self.call_llm(
            prompt=prompt,
            task_type='data_validation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_output': improved_result,
            'feedback': None,  # Clear feedback after applying
        }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_extraction_prompt(
        self,
        input_artifacts: List[str],
        messages: List[Message],
    ) -> str:
        """Build the data extraction prompt."""
        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else m.content
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user') or
               (hasattr(m, 'role') and m.role == 'user')
        ])

        return f"""Extract structured data from the provided clinical documents.

Input Artifacts: {', '.join(input_artifacts) if input_artifacts else 'None provided'}

User Context:
{user_context if user_context else 'No specific context provided'}

Instructions:
1. Identify all data fields present in the documents
2. Extract values with appropriate data types
3. Note any ambiguous or unclear values
4. Flag potential PHI for review
5. Organize data in a structured format

Output should include:
- Field names and their data types
- Sample values for each field
- Row count estimate
- Data quality observations
- PHI indicators (do not include actual PHI values)
"""

    def _evaluate_criterion(
        self,
        criterion: str,
        threshold: Any,
        output: str,
        state: AgentState,
    ) -> tuple[bool, float]:
        """Evaluate DataPrep-specific quality criteria."""
        # Override base implementation with DataPrep-specific logic

        if criterion == 'min_rows':
            # Check if we mention row count in output
            if 'row' in output.lower():
                # Simple heuristic - look for numbers near "row"
                import re
                matches = re.findall(r'(\d+)\s*(?:row|record|subject)', output.lower())
                if matches:
                    count = int(matches[0])
                    passed = count >= threshold
                    score = min(1.0, count / threshold) if threshold > 0 else 1.0
                    return passed, score
            # If can't determine, give partial score
            return True, 0.7

        if criterion == 'max_missing_percent':
            # Check for missing percentage mentions
            import re
            matches = re.findall(r'(\d+(?:\.\d+)?)\s*%?\s*missing', output.lower())
            if matches:
                percent = float(matches[0])
                passed = percent <= threshold
                score = 1.0 - (percent / 100) if percent <= 100 else 0.0
                return passed, score
            return True, 0.7

        if criterion == 'schema_valid':
            # Check for validation success indicators
            valid_indicators = ['valid', 'passed', 'no errors', 'schema matches']
            invalid_indicators = ['invalid', 'failed', 'error', 'violation']

            output_lower = output.lower()
            valid_count = sum(1 for i in valid_indicators if i in output_lower)
            invalid_count = sum(1 for i in invalid_indicators if i in output_lower)

            passed = valid_count > invalid_count
            score = 0.9 if passed else 0.3
            return passed, score

        if criterion == 'variables_selected':
            # Check if variables were selected
            var_indicators = ['outcome', 'predictor', 'covariate', 'variable', 'exposure']
            has_variables = any(i in output.lower() for i in var_indicators)
            return has_variables, 1.0 if has_variables else 0.0

        if criterion == 'cohort_defined':
            # Check if cohort criteria were defined
            cohort_indicators = ['inclusion', 'exclusion', 'cohort', 'criteria', 'sample size']
            has_cohort = any(i in output.lower() for i in cohort_indicators)
            return has_cohort, 1.0 if has_cohort else 0.0

        # Fallback to base implementation
        return super()._evaluate_criterion(criterion, threshold, output, state)
