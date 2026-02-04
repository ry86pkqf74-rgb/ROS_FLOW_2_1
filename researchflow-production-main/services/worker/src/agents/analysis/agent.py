"""
Analysis Agent - Stages 6-9: Statistical analysis, method selection, result interpretation.

This agent handles the analysis phases of the research workflow:
- Stage 6: Method Selection - Choose appropriate statistical methods
- Stage 7: Assumption Checking - Verify statistical assumptions
- Stage 8: Analysis Execution - Run statistical analysis
- Stage 9: Result Interpretation - Interpret and report findings

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


class AnalysisAgent(LangGraphBaseAgent):
    """
    Analysis Agent for Stages 6-9 of the research workflow.

    Handles:
    - Statistical method selection based on data characteristics
    - Assumption checking (normality, homoscedasticity, etc.)
    - Analysis execution and result computation
    - Statistical interpretation and reporting
    """

    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        """
        Initialize the Analysis agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls
            checkpointer: Optional LangGraph checkpointer
        """
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[6, 7, 8, 9],
            agent_id='analysis',
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for Analysis agent.

        Returns:
            Dict of criterion name to threshold
        """
        return {
            'method_justified': True,  # Statistical method must be justified
            'assumptions_checked': True,  # All relevant assumptions verified
            'p_value_threshold': 0.05,  # Significance level
            'effect_size_reported': True,  # Effect sizes must be included
            'confidence_intervals': True,  # CIs must be reported
            'sample_size_adequate': True,  # Power analysis considered
        }

    def build_graph(self) -> StateGraph:
        """
        Build the Analysis agent's LangGraph.

        Graph structure:
        start -> select_method -> check_assumptions -> decide_proceed ->
        execute_analysis -> interpret_results -> quality_gate -> (improve or END)
        """
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("select_method", self.select_method_node)
        graph.add_node("check_assumptions", self.check_assumptions_node)
        graph.add_node("decide_proceed", self.decide_proceed_node)
        graph.add_node("execute_analysis", self.execute_analysis_node)
        graph.add_node("interpret_results", self.interpret_results_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)
        graph.add_node("revise_method", self.revise_method_node)

        # Define edges
        graph.set_entry_point("select_method")

        graph.add_edge("select_method", "check_assumptions")

        # Conditional: proceed to analysis or revise method
        graph.add_conditional_edges(
            "check_assumptions",
            self._route_after_assumptions,
            {
                "proceed": "decide_proceed",
                "revise": "revise_method",
            }
        )

        graph.add_edge("revise_method", "check_assumptions")
        graph.add_edge("decide_proceed", "execute_analysis")
        graph.add_edge("execute_analysis", "interpret_results")
        graph.add_edge("interpret_results", "quality_gate")

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

        graph.add_edge("improve", "select_method")

        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_assumptions(self, state: AgentState) -> str:
        """Route based on assumption check results."""
        assumptions_result = state.get('assumptions_result', {})

        # Check if assumptions passed
        if isinstance(assumptions_result, dict):
            passed = assumptions_result.get('all_passed', True)
        else:
            # If string result, look for failure indicators
            passed = 'violated' not in str(assumptions_result).lower()

        return "proceed" if passed else "revise"

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')
        governance_mode = state.get('governance_mode', 'DEMO')

        # In LIVE mode, require human review for statistical analysis
        if governance_mode == 'LIVE' and gate_status in ['passed', 'needs_human']:
            return "human_review"

        if gate_status == 'needs_human':
            return "human_review"

        if gate_status == 'passed':
            return "save_version"

        return "save_version"

    # =========================================================================
    # Node Implementations
    # =========================================================================

    async def select_method_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 6: Select appropriate statistical methods.

        Analyzes data characteristics and research questions to
        recommend suitable statistical approaches.
        """
        logger.info(f"[Analysis] Stage 6: Selecting method", extra={'run_id': state.get('run_id')})

        # Get context from previous stages
        messages = state.get('messages', [])
        input_artifacts = state.get('input_artifact_ids', [])
        previous_output = state.get('current_output', '')

        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Select appropriate statistical methods for this analysis:

Previous Data Preparation Results:
{previous_output}

Research Context:
{user_context}

Based on the data characteristics and research question, recommend:

1. PRIMARY ANALYSIS METHOD
   - Specific test/model to use
   - Justification based on data type, distribution, sample size
   - Key assumptions to verify

2. ALTERNATIVE METHODS
   - Backup approaches if assumptions are violated
   - Non-parametric alternatives

3. SENSITIVITY ANALYSES
   - Robustness checks to perform
   - Subgroup analyses if appropriate

4. POWER CONSIDERATIONS
   - Expected effect size
   - Sample size adequacy
   - Type I/II error considerations

Provide clear rationale for each recommendation citing statistical methodology.
"""

        method_result = await self.call_llm(
            prompt=prompt,
            task_type='method_selection',
            state=state,
            model_tier='STANDARD',
        )

        message = self.add_assistant_message(
            state,
            f"I've analyzed the data and recommend the following statistical approach:\n\n{method_result}"
        )

        return {
            'current_stage': 6,
            'method_selected': method_result,
            'current_output': method_result,
            'messages': [message],
        }

    async def check_assumptions_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 7: Check statistical assumptions.

        Verifies that the selected method's assumptions are met
        by the data.
        """
        logger.info(f"[Analysis] Stage 7: Checking assumptions", extra={'run_id': state.get('run_id')})

        method_selected = state.get('method_selected', '')
        previous_output = state.get('current_output', '')

        prompt = f"""Check the statistical assumptions for this analysis:

Selected Method:
{method_selected}

Data Characteristics:
{previous_output}

Verify the following assumptions (as applicable):

1. NORMALITY
   - Distribution of dependent variable
   - Distribution of residuals
   - Use Shapiro-Wilk test for n < 50, visual inspection + KS test for larger samples

2. HOMOSCEDASTICITY
   - Equality of variances across groups
   - Levene's test or Breusch-Pagan test

3. INDEPENDENCE
   - Independence of observations
   - Check for clustering or repeated measures

4. LINEARITY
   - Linear relationship between predictors and outcome (for regression)
   - Residual plots inspection

5. MULTICOLLINEARITY
   - Correlation between predictors
   - VIF calculations

6. OUTLIERS AND INFLUENCE
   - Identification of influential observations
   - Cook's distance, leverage values

For each assumption:
- State whether it is met, violated, or borderline
- Provide the test statistic and p-value if applicable
- Recommend remedial action if violated
- Assess impact on results if assumption is borderline

Return a structured assessment with overall recommendation to proceed or revise method.
"""

        assumptions_result = await self.call_llm(
            prompt=prompt,
            task_type='assumption_checking',
            state=state,
            model_tier='STANDARD',
        )

        # Parse result to determine if we can proceed
        can_proceed = 'proceed' in assumptions_result.lower() or 'met' in assumptions_result.lower()

        return {
            'current_stage': 7,
            'assumptions_result': {
                'details': assumptions_result,
                'all_passed': can_proceed,
            },
            'current_output': assumptions_result,
        }

    async def decide_proceed_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Decision point: confirm we can proceed with analysis.
        """
        logger.info(f"[Analysis] Deciding to proceed", extra={'run_id': state.get('run_id')})

        assumptions_result = state.get('assumptions_result', {})
        method_selected = state.get('method_selected', '')

        return {
            'proceed_decision': 'proceed',
            'analysis_method_confirmed': method_selected,
        }

    async def revise_method_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Revise statistical method based on assumption violations.
        """
        logger.info(f"[Analysis] Revising method", extra={'run_id': state.get('run_id')})

        method_selected = state.get('method_selected', '')
        assumptions_result = state.get('assumptions_result', {})

        prompt = f"""The current statistical method's assumptions are violated. Revise the approach:

Original Method:
{method_selected}

Assumption Check Results:
{assumptions_result}

Please recommend:
1. An alternative method that is more robust to the violated assumptions
2. Data transformations that might help
3. Non-parametric alternatives if appropriate
4. Justification for the revised approach

The revised method should still address the original research question.
"""

        revised_result = await self.call_llm(
            prompt=prompt,
            task_type='method_selection',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'method_selected': revised_result,
            'current_output': revised_result,
            'revision_count': state.get('revision_count', 0) + 1,
        }

    async def execute_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 8: Execute the statistical analysis.

        In production, this would trigger actual statistical computation.
        For now, the LLM describes expected results format.
        """
        logger.info(f"[Analysis] Stage 8: Executing analysis", extra={'run_id': state.get('run_id')})

        method_selected = state.get('analysis_method_confirmed', state.get('method_selected', ''))
        governance_mode = state.get('governance_mode', 'DEMO')

        prompt = f"""Execute the statistical analysis using this method:

Method:
{method_selected}

Governance Mode: {governance_mode}

Provide a complete analysis report including:

1. DESCRIPTIVE STATISTICS
   - Sample characteristics (N, mean, SD, median, IQR)
   - Missing data summary
   - Comparison between groups if applicable

2. MAIN ANALYSIS RESULTS
   - Primary test statistic and p-value
   - Effect size (Cohen's d, OR, RR, regression coefficients)
   - 95% confidence intervals

3. SECONDARY ANALYSES
   - Subgroup analyses if planned
   - Sensitivity analyses

4. MODEL DIAGNOSTICS
   - Model fit statistics (R², AIC, BIC if applicable)
   - Residual analysis summary
   - Influential observations identified

5. RESULTS TABLES
   - Formatted tables ready for manuscript
   - Appropriate decimal places and notation

Format results according to statistical reporting guidelines (APA, STROBE, etc.)
"""

        analysis_result = await self.call_llm(
            prompt=prompt,
            task_type='statistical_analysis',
            state=state,
            model_tier='PREMIUM',  # Complex analysis needs frontier model
        )

        return {
            'current_stage': 8,
            'analysis_result': analysis_result,
            'current_output': analysis_result,
        }

    async def interpret_results_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 9: Interpret statistical results.

        Provides clinical/practical interpretation of findings.
        """
        logger.info(f"[Analysis] Stage 9: Interpreting results", extra={'run_id': state.get('run_id')})

        analysis_result = state.get('analysis_result', '')
        method_selected = state.get('method_selected', '')
        messages = state.get('messages', [])

        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Interpret these statistical results in clinical/practical context:

Analysis Results:
{analysis_result}

Statistical Method Used:
{method_selected}

Research Context:
{user_context}

Provide interpretation covering:

1. STATISTICAL SIGNIFICANCE
   - Which results are statistically significant?
   - Interpret p-values appropriately (avoid "highly significant" language)
   - Address multiple comparisons if applicable

2. CLINICAL/PRACTICAL SIGNIFICANCE
   - What do the effect sizes mean in practical terms?
   - Are the effects clinically meaningful?
   - Compare to established minimal clinically important differences

3. PRECISION OF ESTIMATES
   - Interpret confidence intervals
   - Discuss width of CIs and what it implies

4. GENERALIZABILITY
   - To what populations do results apply?
   - External validity considerations

5. LIMITATIONS
   - Statistical limitations
   - Potential biases
   - What the analysis cannot conclude

6. CONCLUSIONS
   - Main findings in plain language
   - Implications for practice/policy
   - Recommendations for future research

Avoid overstatement - be appropriately cautious in conclusions.
"""

        interpretation_result = await self.call_llm(
            prompt=prompt,
            task_type='result_interpretation',
            state=state,
            model_tier='STANDARD',
        )

        message = self.add_assistant_message(
            state,
            f"Analysis complete. Here's my interpretation:\n\n{interpretation_result}"
        )

        return {
            'current_stage': 9,
            'interpretation_result': interpretation_result,
            'current_output': interpretation_result,
            'messages': [message],
        }

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improvement node for iterating on feedback.
        """
        logger.info(f"[Analysis] Improving based on feedback", extra={'run_id': state.get('run_id')})

        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})

        prompt = f"""Improve this statistical analysis based on feedback:

Current Analysis:
{current_output}

Feedback:
{feedback}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Address the specific issues and provide improved analysis with:
1. Corrections to any statistical errors
2. Additional analyses if requested
3. Clearer interpretations
4. Better formatting/presentation
"""

        improved_result = await self.call_llm(
            prompt=prompt,
            task_type='statistical_analysis',
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
        """Evaluate Analysis-specific quality criteria."""
        output_lower = output.lower()

        if criterion == 'method_justified':
            justification_terms = ['because', 'since', 'appropriate', 'suitable', 'rationale', 'justified']
            has_justification = any(term in output_lower for term in justification_terms)
            return has_justification, 1.0 if has_justification else 0.3

        if criterion == 'assumptions_checked':
            assumption_terms = ['normality', 'homoscedasticity', 'independence', 'linearity', 'assumption']
            has_assumptions = any(term in output_lower for term in assumption_terms)
            return has_assumptions, 1.0 if has_assumptions else 0.3

        if criterion == 'p_value_threshold':
            import re
            # Look for p-values
            p_matches = re.findall(r'p\s*[=<>]\s*(\d+\.?\d*)', output_lower)
            if p_matches:
                min_p = min(float(p) for p in p_matches)
                passed = min_p <= threshold
                score = 1.0 - min_p if passed else 0.5
                return passed, score
            return True, 0.7  # Can't determine

        if criterion == 'effect_size_reported':
            effect_terms = ['effect size', "cohen's d", 'odds ratio', 'risk ratio', 'coefficient', 'r²', 'r-squared']
            has_effect = any(term in output_lower for term in effect_terms)
            return has_effect, 1.0 if has_effect else 0.2

        if criterion == 'confidence_intervals':
            ci_terms = ['confidence interval', '95% ci', '90% ci', 'ci:', '[', ']']
            has_ci = any(term in output_lower for term in ci_terms)
            return has_ci, 1.0 if has_ci else 0.2

        if criterion == 'sample_size_adequate':
            power_terms = ['power', 'sample size', 'n =', 'adequate', 'sufficient']
            has_power = any(term in output_lower for term in power_terms)
            return has_power, 1.0 if has_power else 0.5

        return super()._evaluate_criterion(criterion, threshold, output, state)
