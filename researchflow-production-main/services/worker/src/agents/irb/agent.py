"""
IRB Agent - Stages 13-14: Protocol review, compliance, consent forms.

This agent handles the IRB/ethics review phases of the research workflow:
- Stage 13: Protocol Review - Generate and review IRB protocol
- Stage 14: Consent & Compliance - Consent forms and regulatory compliance

All LLM calls route through the orchestrator's AI Router for PHI compliance.

IMPORTANT: This agent ALWAYS requires human review before submission.

See: Linear ROS-67 (Phase D: Remaining Agents)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging

from langgraph.graph import StateGraph, END

from ..base.langgraph_base import LangGraphBaseAgent
from ..base.state import AgentState, Message
from ...bridges.ai_router_bridge import AIRouterBridge, ModelOptions, ModelTier, GovernanceMode

logger = logging.getLogger(__name__)


class IRBAgent(LangGraphBaseAgent):
    """
    IRB Agent for Stages 13-14 of the research workflow.

    Handles:
    - IRB protocol generation and review
    - Risk assessment and mitigation
    - Informed consent form creation
    - PHI protection verification
    - Regulatory compliance checking

    CRITICAL: All IRB outputs require human review before submission.
    """

    def __init__(self, llm_bridge: Optional[AIRouterBridge] = None, checkpointer: Optional[Any] = None):
        """
        Initialize the IRB agent.

        Args:
            llm_bridge: AIRouterBridge instance for LLM calls (created if None)
            checkpointer: Optional LangGraph checkpointer
        """
        # Create bridge if not provided
        if llm_bridge is None:
            from ...bridges.ai_router_bridge import create_ai_router_bridge
            llm_bridge = create_ai_router_bridge()
            
        super().__init__(
            llm_bridge=llm_bridge,
            stages=[13, 14],
            agent_id='irb',
            checkpointer=checkpointer,
        )

    def get_quality_criteria(self) -> Dict[str, Any]:
        """
        Quality criteria for IRB agent.

        Returns:
            Dict of criterion name to threshold
        """
        return {
            'risk_assessed': True,  # Risk assessment completed
            'phi_addressed': True,  # PHI protection documented
            'consent_complete': True,  # All consent elements present
            'protocol_complete': True,  # Full protocol generated
            'vulnerable_pop_addressed': True,  # Vulnerable populations considered
            'human_reviewed': True,  # MANDATORY human review
        }

    def build_graph(self) -> StateGraph:
        """
        Build the IRB agent's LangGraph.

        Graph structure:
        start -> assess_risk -> check_phi -> generate_protocol ->
        create_consent -> review_compliance -> human_review (MANDATORY) ->
        quality_gate -> (improve or END)
        """
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("assess_risk", self.assess_risk_node)
        graph.add_node("check_phi", self.check_phi_node)
        graph.add_node("generate_protocol", self.generate_protocol_node)
        graph.add_node("create_consent", self.create_consent_node)
        graph.add_node("review_compliance", self.review_compliance_node)
        graph.add_node("human_review", self.human_review_node)
        graph.add_node("quality_gate", self.quality_gate_node)
        graph.add_node("save_version", self.save_version_node)
        graph.add_node("improve", self.improve_node)

        # Define edges
        graph.set_entry_point("assess_risk")

        graph.add_edge("assess_risk", "check_phi")
        graph.add_edge("check_phi", "generate_protocol")
        graph.add_edge("generate_protocol", "create_consent")
        graph.add_edge("create_consent", "review_compliance")
        # MANDATORY human review for IRB
        graph.add_edge("review_compliance", "human_review")
        graph.add_edge("human_review", "quality_gate")

        # Conditional routing after quality gate
        graph.add_conditional_edges(
            "quality_gate",
            self._route_after_quality_gate,
            {
                "save_version": "save_version",
                "end": END,
            }
        )

        # Conditional routing after save_version (improvement loop)
        graph.add_conditional_edges(
            "save_version",
            self.should_continue_improvement,
            {
                "continue": "improve",
                "complete": END,
            }
        )

        graph.add_edge("improve", "assess_risk")

        return graph.compile(checkpointer=self.checkpointer)

    def _route_after_quality_gate(self, state: AgentState) -> str:
        """Route after quality gate evaluation."""
        gate_status = state.get('gate_status', 'pending')

        if gate_status == 'passed':
            return "save_version"

        return "save_version"  # Always save for audit

    # =========================================================================
    # Node Implementations
    # =========================================================================

    async def assess_risk_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 13: Assess research risks.

        Evaluates potential risks to participants and research integrity.
        """
        logger.info(f"[IRB] Stage 13: Assessing risk", extra={'run_id': state.get('run_id')})

        messages = state.get('messages', [])
        previous_output = state.get('current_output', '')
        input_artifacts = state.get('input_artifact_ids', [])

        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Conduct a comprehensive risk assessment for this research study:

Previous Analysis:
{previous_output}

Research Context:
{user_context}

Assess the following risk categories:

1. PHYSICAL RISKS
   - Direct physical harm potential
   - Indirect physical consequences
   - Duration and reversibility

2. PSYCHOLOGICAL RISKS
   - Emotional distress
   - Psychological harm
   - Stigmatization potential

3. SOCIAL RISKS
   - Privacy breaches
   - Social harm from disclosure
   - Employment/insurance impacts

4. ECONOMIC RISKS
   - Financial harm
   - Time burden
   - Opportunity costs

5. LEGAL RISKS
   - Legal consequences of participation
   - Mandatory reporting requirements
   - Data disclosure requirements

6. RESEARCH-SPECIFIC RISKS
   - Genetic/biospecimen risks
   - Radiological exposure
   - Device/intervention risks

For each risk:
- Describe the risk
- Assess likelihood (rare/possible/likely)
- Assess severity (minimal/moderate/serious)
- Overall risk level (minimal/low/moderate/high)
- Proposed mitigation strategies

Determine overall risk category:
- Exempt
- Expedited review eligible
- Full board review required

Provide rationale for the determination.
"""

        risk_result = await self.call_llm(
            prompt=prompt,
            task_type='risk_assessment',
            state=state,
            model_tier='PREMIUM',  # Complex reasoning
        )

        message = self.add_assistant_message(
            state,
            f"I've completed the risk assessment for your study:\n\n{risk_result}"
        )

        return {
            'current_stage': 13,
            'risk_result': risk_result,
            'current_output': risk_result,
            'messages': [message],
        }

    async def check_phi_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Check PHI handling and protection.

        Critical for HIPAA compliance and participant privacy.
        """
        logger.info(f"[IRB] Checking PHI", extra={'run_id': state.get('run_id')})

        risk_result = state.get('risk_result', '')
        previous_output = state.get('current_output', '')

        prompt = f"""Assess Protected Health Information (PHI) handling in this study:

Risk Assessment:
{risk_result}

Previous Documentation:
{previous_output}

Evaluate PHI protection:

1. PHI CATEGORIES INVOLVED
   - Names
   - Dates (birth, admission, discharge, death)
   - Geographic data
   - Phone/fax numbers
   - Email addresses
   - SSN
   - Medical record numbers
   - Health plan numbers
   - Account numbers
   - License numbers
   - Vehicle/device identifiers
   - URLs
   - IP addresses
   - Biometric identifiers
   - Photos
   - Any other unique identifier

2. HIPAA COMPLIANCE
   - Is this a covered entity study?
   - Authorization requirements
   - De-identification method (Safe Harbor vs Expert Determination)
   - Limited data set considerations

3. DATA SECURITY MEASURES
   - Storage security (encryption at rest)
   - Transmission security (encryption in transit)
   - Access controls
   - Audit logging
   - Retention and destruction policies

4. BREACH RESPONSE
   - Incident response plan
   - Notification procedures
   - Documentation requirements

5. SPECIAL CONSIDERATIONS
   - Minor participant data
   - Sensitive health data (HIV, mental health, substance abuse)
   - Genetic information
   - Research vs. treatment records

Provide:
- PHI inventory
- Protection measures
- Gaps identified
- Recommendations

Flag any PHI compliance issues that MUST be addressed before submission.
"""

        phi_result = await self.call_llm(
            prompt=prompt,
            task_type='phi_detection',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'phi_result': phi_result,
            'current_output': phi_result,
        }

    async def generate_protocol_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate IRB protocol document.

        Creates a complete protocol following institutional template.
        """
        logger.info(f"[IRB] Generating protocol", extra={'run_id': state.get('run_id')})

        risk_result = state.get('risk_result', '')
        phi_result = state.get('phi_result', '')
        messages = state.get('messages', [])

        user_context = "\n".join([
            m['content'] if isinstance(m, dict) else str(m)
            for m in messages
            if (isinstance(m, dict) and m.get('role') == 'user')
        ])

        prompt = f"""Generate a complete IRB protocol document:

Risk Assessment:
{risk_result}

PHI Assessment:
{phi_result}

Research Context:
{user_context}

Create a protocol with these sections:

1. TITLE AND INVESTIGATORS
   - Protocol title
   - Principal investigator
   - Co-investigators
   - Study coordinator
   - Institution

2. STUDY OVERVIEW
   - Background and rationale
   - Research questions/hypotheses
   - Study design summary
   - Anticipated enrollment

3. OBJECTIVES AND ENDPOINTS
   - Primary objective
   - Secondary objectives
   - Primary endpoint
   - Secondary endpoints

4. STUDY POPULATION
   - Inclusion criteria
   - Exclusion criteria
   - Recruitment procedures
   - Retention strategies

5. STUDY PROCEDURES
   - Visit schedule
   - Procedures at each visit
   - Data collection methods
   - Intervention description (if applicable)

6. RISKS AND BENEFITS
   - Potential risks (from risk assessment)
   - Mitigation strategies
   - Potential benefits (direct and indirect)
   - Risk-benefit assessment

7. DATA MANAGEMENT
   - Data collection instruments
   - Data storage and security
   - Data quality assurance
   - Data sharing plans

8. PRIVACY AND CONFIDENTIALITY
   - PHI protection measures
   - De-identification procedures
   - Access controls
   - Breach procedures

9. INFORMED CONSENT
   - Consent process
   - Capacity assessment
   - Surrogate consent (if applicable)
   - Waiver requests (if applicable)

10. ADDITIONAL PROTECTIONS
    - Vulnerable populations
    - DSMB/DMC (if applicable)
    - Stopping rules
    - Protocol amendments

Provide a complete, submission-ready protocol draft.
"""

        protocol_result = await self.call_llm(
            prompt=prompt,
            task_type='irb_protocol',
            state=state,
            model_tier='PREMIUM',
        )

        return {
            'current_stage': 13,
            'protocol_result': protocol_result,
            'current_output': protocol_result,
        }

    async def create_consent_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Stage 14: Create informed consent form.

        Generates a complete informed consent document.
        """
        logger.info(f"[IRB] Stage 14: Creating consent", extra={'run_id': state.get('run_id')})

        protocol_result = state.get('protocol_result', '')
        risk_result = state.get('risk_result', '')

        prompt = f"""Create an informed consent form for this study:

Protocol Summary:
{protocol_result}

Risk Assessment:
{risk_result}

Generate a complete consent form with these elements:

1. STUDY TITLE AND CONTACT INFORMATION
   - Full study title
   - PI name and contact
   - 24-hour contact for emergencies
   - IRB contact for rights questions

2. INTRODUCTION
   - You are being asked to participate...
   - Purpose of the research
   - Why you were selected
   - Voluntary nature of participation

3. STUDY PROCEDURES
   - What participation involves
   - Time commitment
   - Number of visits
   - What will happen at each visit
   - Study duration

4. RISKS AND DISCOMFORTS
   - Physical risks
   - Psychological risks
   - Privacy risks
   - Unknown risks
   - Risks during pregnancy (if applicable)

5. BENEFITS
   - Potential direct benefits
   - Benefits to others/society
   - No guarantee of benefit

6. ALTERNATIVES
   - Alternative treatments/procedures
   - Option to not participate

7. CONFIDENTIALITY
   - How information is protected
   - Who has access
   - Limits to confidentiality
   - Data retention period

8. COSTS AND COMPENSATION
   - Costs to participant
   - Compensation offered
   - Payment schedule
   - Pro-rated compensation

9. VOLUNTARY PARTICIPATION
   - Right to refuse
   - Right to withdraw
   - No penalty for withdrawal
   - How to withdraw

10. INJURY CLAUSE (if applicable)
    - What happens if injured
    - Available treatments
    - Compensation for injury

11. NEW FINDINGS
    - How new information shared

12. SIGNATURE PAGE
    - Participant signature line
    - LAR signature (if applicable)
    - Witness signature (if required)
    - Researcher signature

Write at 8th grade reading level. Avoid jargon. Use "you" and "we".
"""

        consent_result = await self.call_llm(
            prompt=prompt,
            task_type='consent_form',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'current_stage': 14,
            'consent_result': consent_result,
            'current_output': consent_result,
        }

    async def review_compliance_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Review regulatory compliance.

        Ensures all regulatory requirements are addressed.
        """
        logger.info(f"[IRB] Reviewing compliance", extra={'run_id': state.get('run_id')})

        protocol_result = state.get('protocol_result', '')
        consent_result = state.get('consent_result', '')
        phi_result = state.get('phi_result', '')

        prompt = f"""Review regulatory compliance for this IRB submission:

Protocol:
{protocol_result}

Consent Form:
{consent_result}

PHI Assessment:
{phi_result}

Check compliance with:

1. COMMON RULE (45 CFR 46)
   - Informed consent requirements
   - IRB review requirements
   - Vulnerable populations protections
   - Expedited review eligibility

2. HIPAA (if applicable)
   - Authorization requirements
   - De-identification standards
   - Limited data set provisions
   - Waiver of authorization criteria

3. FDA REGULATIONS (if applicable)
   - IND/IDE requirements
   - Device regulations
   - Reporting requirements

4. INSTITUTIONAL REQUIREMENTS
   - Local IRB policies
   - Training requirements
   - Conflict of interest

5. SPECIAL POPULATIONS
   - Children (45 CFR 46 Subpart D)
   - Prisoners (45 CFR 46 Subpart C)
   - Pregnant women (45 CFR 46 Subpart B)
   - Cognitively impaired

6. DOCUMENTATION
   - Required forms
   - Approval letters needed
   - Training certifications

Provide:
- Compliance checklist (met/not met)
- Missing elements
- Required actions before submission
- Recommendations

⚠️ FLAG ANY CRITICAL COMPLIANCE GAPS
"""

        compliance_result = await self.call_llm(
            prompt=prompt,
            task_type='irb_protocol',
            state=state,
            model_tier='STANDARD',
        )

        return {
            'compliance_result': compliance_result,
            'current_output': compliance_result,
        }

    async def human_review_node(self, state: AgentState) -> Dict[str, Any]:
        """
        MANDATORY human review for IRB submissions.

        This node ALWAYS interrupts for human approval regardless of
        governance mode. IRB submissions cannot be automated.
        """
        logger.info(f"[IRB] MANDATORY human review", extra={'run_id': state.get('run_id')})

        protocol_result = state.get('protocol_result', '')
        consent_result = state.get('consent_result', '')
        compliance_result = state.get('compliance_result', '')
        risk_result = state.get('risk_result', '')

        # Create comprehensive summary for human reviewer
        summary = f"""
========================================
IRB SUBMISSION REVIEW REQUIRED
========================================

⚠️ HUMAN APPROVAL MANDATORY BEFORE SUBMISSION

RISK ASSESSMENT SUMMARY:
{risk_result[:500]}...

PROTOCOL SUMMARY:
{protocol_result[:500]}...

CONSENT FORM SUMMARY:
{consent_result[:500]}...

COMPLIANCE STATUS:
{compliance_result[:500]}...

========================================
ACTION REQUIRED:
1. Review all documents thoroughly
2. Verify all information is accurate
3. Confirm compliance requirements met
4. Approve or request revisions
========================================
"""

        message = self.add_assistant_message(
            state,
            f"""I've prepared the IRB submission materials.

⚠️ **IMPORTANT: Human review is REQUIRED before submission.**

Please review:
1. Protocol document
2. Informed consent form
3. Risk assessment
4. Compliance checklist

No IRB materials will be submitted without your explicit approval.

{summary}
"""
        )

        return {
            'human_review_required': True,
            'gate_status': 'needs_human',  # Force human review
            'review_summary': summary,
            'messages': [message],
        }

    async def improve_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Improvement node for iterating on feedback.
        """
        logger.info(f"[IRB] Improving based on feedback", extra={'run_id': state.get('run_id')})

        feedback = state.get('feedback', '')
        current_output = state.get('current_output', '')
        gate_result = state.get('gate_result', {})

        prompt = f"""Improve these IRB materials based on feedback:

Current Materials:
{current_output}

Feedback:
{feedback}

Quality Gate Results:
- Score: {gate_result.get('score', 'N/A')}
- Failed Criteria: {gate_result.get('criteria_failed', [])}
- Reason: {gate_result.get('reason', 'N/A')}

Address the specific issues. Focus on:
1. Regulatory compliance gaps
2. Risk assessment completeness
3. Consent clarity
4. PHI protection
5. Documentation requirements

Provide revised materials.
"""

        improved_result = await self.call_llm(
            prompt=prompt,
            task_type='irb_protocol',
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
        """Evaluate IRB-specific criteria."""
        output_lower = output.lower()

        if criterion == 'risk_assessed':
            risk_terms = ['risk', 'minimal', 'moderate', 'severe', 'likelihood', 'mitigation']
            has_risk = sum(1 for term in risk_terms if term in output_lower) >= 3
            return has_risk, 1.0 if has_risk else 0.3

        if criterion == 'phi_addressed':
            phi_terms = ['phi', 'hipaa', 'privacy', 'confidential', 'de-identified', 'protected']
            has_phi = sum(1 for term in phi_terms if term in output_lower) >= 2
            return has_phi, 1.0 if has_phi else 0.2

        if criterion == 'consent_complete':
            consent_elements = ['voluntary', 'risk', 'benefit', 'confidential', 'withdraw', 'signature']
            element_count = sum(1 for elem in consent_elements if elem in output_lower)
            score = element_count / len(consent_elements)
            return score >= 0.7, score

        if criterion == 'protocol_complete':
            protocol_sections = ['objective', 'population', 'procedure', 'risk', 'consent', 'data']
            section_count = sum(1 for sec in protocol_sections if sec in output_lower)
            score = section_count / len(protocol_sections)
            return score >= 0.8, score

        if criterion == 'vulnerable_pop_addressed':
            vuln_terms = ['children', 'prisoner', 'pregnant', 'cognitive', 'vulnerable', 'protect']
            has_vuln = any(term in output_lower for term in vuln_terms)
            return has_vuln, 1.0 if has_vuln else 0.5  # May not apply

        if criterion == 'human_reviewed':
            # Check state for human review completion
            return state.get('human_approved', False), 1.0 if state.get('human_approved') else 0.0

        return super()._evaluate_criterion(criterion, threshold, output, state)
