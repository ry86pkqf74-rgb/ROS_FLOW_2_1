"""
Quality Agent - Stages 10-12: Sensitivity analysis, bias assessment, reproducibility.

This agent handles the quality assurance phases of the research workflow:
- Stage 10: Sensitivity Analysis - Robustness checks on results
- Stage 11: Bias Assessment - Identify and address potential biases
- Stage 12: Reproducibility Check - Ensure analysis is reproducible

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


class QualityAgent(LangGraphBaseAgent):
    """
    Quality Agent for Stages 10-12 of the research workflow.

    Handles:
    - Sensitivity analysis and robustness checks
    - Bias assessment (selection, information, confounding)
    - Reproducibility verification
    - STROBE/CONSORT compliance checking
    """

    def __init__(self, llm_bridge: Any, checkpointer: Optional[Any] = None):
        """
        Initialize the Quality agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls
            checkpointer: Optional LangGraph checkpointer
        """
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[10, 11, 12],
            agent_id='quality',
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for Quality agent.

        Returns:
            Dict of criterion name to threshold
        """
        return {
            'sensitivity_performed': True,  # At least one sensitivity analysis
            'bias_assessed': True,  # Bias assessment completed
            'reproducibility_score': 0.8,  # Minimum reproducibility score
            'strobe_compliance': 0.7,  # STROBE checklist compliance
            'documentation_complete': True,  # Methods fully documented
        }

    def build_graph(self) -> StateGraph:
        """
        Build the Quality agent's LangGraph.

        Graph structure:
        start -> sensitivity_analysis -> bias_assessment ->
        reproducibility_check -> compliance_check -> quality_gate -> (improve or END)
        """
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("sensitivity_analysis", self.sensitivity_analysis_node)
        graph.add_node("bias_assessment", self.bias_assessment_node)
        graph.add_node("reproducibility_check", self.reproducibility_check_node)
        graph.add_node("compliance_check", self.compliance_check_node)
        graph.add_node("generate_figures", self.generate_figures_node)
        graph.add_node("generate_tables", self.generate_tables_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)

        # Define edges
        graph.set_entry_point("sensitivity_analysis")

        graph.add_edge("sensitivity_analysis", "bias_assessment")
        graph.add_edge("bias_assessment", "reproducibility_check")
        graph.add_edge("reproducibility_check", "compliance_check")
        graph.add_edge("compliance_check", "generate_figures")
        graph.add_edge("generate_figures", "generate_tables")
        graph.add_edge("generate_tables", "quality_gate")

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

        graph.add_edge("improve", "sensitivity_analysis")

        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')
        governance_mode = state.get('governance_mode', 'DEMO')

        # Quality checks are critical - always review in LIVE mode
        if governance_mode == 'LIVE':
            return "human_review"

        if gate_status == 'needs_human':
            return "human_review"

        if gate_status == 'passed':
            return "save_version"

        return "save_version"

    # =========================================================================
    # Node Implementations
    # =========================================================================

    async def sensitivity_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 10: Perform sensitivity analyses.

        Conducts robustness checks to assess stability of results.
        """
        logger.info(f"[Quality] Stage 10: Sensitivity analysis", extra={'run_id': state.get('run_id')})

        previous_output = state.get('current_output', '')
        messages = state.get('messages', [])

        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Perform comprehensive sensitivity analyses on these results:

Previous Analysis Results:
{previous_output}

Research Context:
{user_context}

Conduct the following sensitivity analyses:

1. MISSING DATA SENSITIVITY
   - Complete case analysis
   - Multiple imputation comparison
   - Worst-case/best-case bounds

2. OUTLIER SENSITIVITY
   - Results with and without identified outliers
   - Robust regression alternatives
   - Winsorization effects

3. MODEL SPECIFICATION
   - Alternative model specifications
   - Different covariate sets
   - Interaction terms

4. SUBGROUP ANALYSES
   - Pre-specified subgroup analyses
   - Effect modification assessment
   - Stratified results

5. THRESHOLD SENSITIVITY
   - Different cutoff values
   - Continuous vs. categorical treatment
   - Dose-response if applicable

For each analysis:
- State the rationale
- Present the results
- Compare to main analysis
- Interpret implications for conclusions

Conclude with overall robustness assessment.
"""

        sensitivity_result = await self.call_llm(
            prompt=prompt,
            task_type='sensitivity_analysis',
            state=state,
            model_tier='PREMIUM',
        )

        message = self.add_assistant_message(
            state,
            f"I've completed the sensitivity analyses. Here are the robustness checks:\n\n{sensitivity_result}"
        )

        return {
            'current_stage': 10,
            'sensitivity_result': sensitivity_result,
            'current_output': sensitivity_result,
            'messages': [message],
        }

    async def bias_assessment_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 11: Assess potential biases.

        Evaluates selection bias, information bias, and confounding.
        """
        logger.info(f"[Quality] Stage 11: Bias assessment", extra={'run_id': state.get('run_id')})

        previous_output = state.get('current_output', '')
        sensitivity_result = state.get('sensitivity_result', '')

        prompt = f"""Assess potential biases in this study:

Analysis Results:
{previous_output}

Sensitivity Analysis:
{sensitivity_result}

Evaluate the following bias types:

1. SELECTION BIAS
   - How were participants selected?
   - Loss to follow-up patterns
   - Healthy worker effect
   - Volunteer bias
   - Direction and magnitude of potential bias

2. INFORMATION BIAS
   - Measurement error in exposures
   - Misclassification of outcomes
   - Recall bias
   - Observer/interviewer bias
   - Non-differential vs. differential misclassification

3. CONFOUNDING
   - Known confounders addressed?
   - Residual confounding
   - Unmeasured confounders
   - Direction of confounding

4. REVERSE CAUSATION
   - Temporality of exposure-outcome
   - Evidence for or against reverse causation

5. COLLIDER BIAS
   - Conditioning on colliders?
   - Selection based on outcome

6. GENERALIZABILITY
   - Internal validity assessment
   - External validity concerns
   - Transportability

For each bias:
- Rate severity (minimal, moderate, serious)
- Describe likely direction of effect
- Suggest mitigation strategies
- Impact on conclusions

Provide overall bias risk assessment using ROBINS-I or similar framework.
"""

        bias_result = await self.call_llm(
            prompt=prompt,
            task_type='bias_assessment',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 11,
            'bias_result': bias_result,
            'current_output': bias_result,
        }

    async def reproducibility_check_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 12: Check reproducibility.

        Ensures analysis is documented and reproducible.
        """
        logger.info(f"[Quality] Stage 12: Reproducibility check", extra={'run_id': state.get('run_id')})

        previous_output = state.get('current_output', '')

        prompt = f"""Assess the reproducibility of this analysis:

Current Analysis Documentation:
{previous_output}

Evaluate against these reproducibility criteria:

1. DATA AVAILABILITY
   - Is raw data accessible?
   - Are derived variables documented?
   - Is there a data dictionary?

2. CODE/ANALYSIS SCRIPTS
   - Are analysis scripts documented?
   - Can the analysis be re-run?
   - Software versions specified?

3. METHODOLOGY DOCUMENTATION
   - Are all methods clearly described?
   - Inclusion/exclusion criteria explicit?
   - Missing data handling documented?

4. STATISTICAL APPROACH
   - Model specifications complete?
   - Sensitivity analyses documented?
   - P-value calculations reproducible?

5. RESULT VERIFICATION
   - Tables internally consistent?
   - Figures match reported values?
   - No copy-paste errors?

6. PRE-REGISTRATION
   - Analysis plan pre-registered?
   - Deviations from plan documented?
   - Exploratory vs. confirmatory clear?

Provide:
- Reproducibility score (0-100)
- Specific gaps identified
- Recommendations for improvement
- Documentation needed

Rate overall reproducibility: Excellent/Good/Moderate/Poor
"""

        reproducibility_result = await self.call_llm(
            prompt=prompt,
            task_type='integrity_check',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 12,
            'reproducibility_result': reproducibility_result,
            'current_output': reproducibility_result,
        }

    async def compliance_check_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Check compliance with reporting guidelines (STROBE, CONSORT, etc.).
        """
        logger.info(f"[Quality] Checking compliance", extra={'run_id': state.get('run_id')})

        previous_output = state.get('current_output', '')
        bias_result = state.get('bias_result', '')

        prompt = f"""Check compliance with relevant reporting guidelines:

Analysis Summary:
{previous_output}

Bias Assessment:
{bias_result}

Evaluate against STROBE checklist (for observational studies):

TITLE AND ABSTRACT
□ 1a - Study design in title or abstract
□ 1b - Informative and balanced summary

INTRODUCTION
□ 2 - Scientific background and rationale
□ 3 - Specific objectives/hypotheses

METHODS
□ 4 - Study design key elements
□ 5 - Setting, locations, dates
□ 6 - Eligibility criteria
□ 7 - Define all outcomes, exposures, covariates
□ 8 - Data sources and measurement
□ 9 - Describe efforts to address bias
□ 10 - Study size explanation
□ 11 - Quantitative variables handling
□ 12 - Statistical methods

RESULTS
□ 13 - Participant numbers at each stage
□ 14 - Descriptive data
□ 15 - Outcome data
□ 16 - Main results with CIs and p-values
□ 17 - Other analyses

DISCUSSION
□ 18 - Key results summary
□ 19 - Limitations
□ 20 - Interpretation
□ 21 - Generalizability

OTHER
□ 22 - Funding disclosure

Score each item: Met / Partially Met / Not Met / N/A
Calculate overall compliance percentage.
"""

        compliance_result = await self.call_llm(
            prompt=prompt,
            task_type='integrity_check',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'compliance_result': compliance_result,
            'current_output': compliance_result,
        }

    async def generate_figures_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate figure specifications for results visualization.
        """
        logger.info(f"[Quality] Generating figures", extra={'run_id': state.get('run_id')})

        sensitivity_result = state.get('sensitivity_result', '')
        bias_result = state.get('bias_result', '')

        prompt = f"""Design figures to visualize these results:

Sensitivity Analysis:
{sensitivity_result}

Bias Assessment:
{bias_result}

Create specifications for:

1. FLOW DIAGRAM
   - CONSORT/STROBE style participant flow
   - Numbers at each stage
   - Reasons for exclusion

2. FOREST PLOT
   - Main results and sensitivity analyses
   - Subgroup results if applicable
   - Point estimates and confidence intervals

3. QUALITY ASSESSMENT FIGURE
   - Risk of bias visualization
   - Traffic light plot or similar

4. SENSITIVITY ANALYSIS VISUALIZATION
   - Tornado diagram for parameter sensitivity
   - Leave-one-out plots

For each figure:
- Describe layout and components
- Specify data to include
- Note axis labels and scales
- Suggest color scheme (colorblind-friendly)
- Provide figure caption

Figures should follow journal guidelines and be publication-ready.
"""

        figures_result = await self.call_llm(
            prompt=prompt,
            task_type='figure_generation',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'figures_result': figures_result,
            'current_output': figures_result,
        }

    async def generate_tables_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate table specifications for results presentation.
        """
        logger.info(f"[Quality] Generating tables", extra={'run_id': state.get('run_id')})

        sensitivity_result = state.get('sensitivity_result', '')
        compliance_result = state.get('compliance_result', '')

        prompt = f"""Design tables to present these results:

Sensitivity Analysis:
{sensitivity_result}

Compliance Check:
{compliance_result}

Create specifications for:

1. TABLE 1: BASELINE CHARACTERISTICS
   - Demographics
   - Clinical characteristics
   - By exposure group if applicable
   - Include N, %, mean (SD), median (IQR)

2. TABLE 2: MAIN RESULTS
   - Primary outcome
   - Effect estimates with 95% CI
   - P-values
   - Model adjusted/unadjusted

3. TABLE 3: SENSITIVITY ANALYSES
   - Results across different analytical approaches
   - Subgroup analyses
   - Alternative model specifications

4. SUPPLEMENTARY TABLES
   - Detailed model outputs
   - Additional sensitivity analyses
   - Missing data summaries

For each table:
- Column headers and row labels
- Data precision (decimal places)
- Footnote annotations
- Table caption

Tables should follow APA/journal formatting guidelines.
"""

        tables_result = await self.call_llm(
            prompt=prompt,
            task_type='table_generation',
            state=state,
            model_tier='STANDARD',
        )

        message = self.add_assistant_message(
            state,
            f"Quality assessment complete. Here are the figure and table specifications:\n\n{tables_result}"
        )

        return {
            'tables_result': tables_result,
            'current_output': tables_result,
            'messages': [message],
        }

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improvement node for iterating on feedback.
        """
        logger.info(f"[Quality] Improving based on feedback", extra={'run_id': state.get('run_id')})

        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})

        prompt = f"""Improve this quality assessment based on feedback:

Current Assessment:
{current_output}

Feedback:
{feedback}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Address the specific issues and provide improved assessment with:
1. Additional sensitivity analyses if needed
2. More thorough bias assessment
3. Better documentation
4. Improved figures/tables
"""

        improved_result = await self.call_llm(
            prompt=prompt,
            task_type='sensitivity_analysis',
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
        """Evaluate Quality-specific criteria."""
        output_lower = output.lower()

        if criterion == 'sensitivity_performed':
            sensitivity_terms = ['sensitivity', 'robustness', 'alternative', 'specification']
            has_sensitivity = any(term in output_lower for term in sensitivity_terms)
            return has_sensitivity, 1.0 if has_sensitivity else 0.2

        if criterion == 'bias_assessed':
            bias_terms = ['selection bias', 'information bias', 'confounding', 'bias assessment']
            has_bias = any(term in output_lower for term in bias_terms)
            return has_bias, 1.0 if has_bias else 0.2

        if criterion == 'reproducibility_score':
            import re
            # Look for reproducibility score
            matches = re.findall(r'reproducibility.*?(\d+)(?:\s*%|/100)?', output_lower)
            if matches:
                score = float(matches[-1]) / 100 if float(matches[-1]) > 1 else float(matches[-1])
                passed = score >= threshold
                return passed, score
            return True, 0.7

        if criterion == 'strobe_compliance':
            import re
            # Look for compliance percentage
            matches = re.findall(r'compliance.*?(\d+)(?:\s*%)?', output_lower)
            if matches:
                score = float(matches[-1]) / 100 if float(matches[-1]) > 1 else float(matches[-1])
                passed = score >= threshold
                return passed, score
            # Check for "met" items
            met_count = output_lower.count('met')
            total_items = 22  # STROBE items
            score = min(1.0, met_count / total_items)
            return score >= threshold, score

        if criterion == 'documentation_complete':
            doc_terms = ['documented', 'specified', 'described', 'available', 'complete']
            doc_score = sum(1 for term in doc_terms if term in output_lower) / len(doc_terms)
            return doc_score > 0.5, doc_score

        return super()._evaluate_criterion(criterion, threshold, output, state)
