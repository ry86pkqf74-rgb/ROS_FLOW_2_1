"""
IRB Agent - IRB Proposal Generation

Handles workflow stage 3:
3. IRB Proposal - Auto-generate IRB application, risk assessment, consent forms

This agent generates IRB submission materials based on the research topic
and literature review from prior stages (Stages 1-2).

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


class IRBAgent(BaseAgent):
    """Agent for IRB protocol review and compliance stages."""

    def __init__(self):
        config = AgentConfig(
            name="IRBAgent",
            description="Generates IRB proposals, risk assessments, and consent form templates",
            stages=[3],  # Stage 3 = IRB Proposal generation
            rag_collections=["irb_protocols", "clinical_guidelines"],
            max_iterations=2,  # IRB review is more deterministic
            quality_threshold=0.90,  # Higher threshold for compliance
            timeout_seconds=180,
            phi_safe=True,  # Critical for IRB work
            model_provider="anthropic",
        )
        super().__init__(config)

    def _get_system_prompt(self) -> str:
        return """You are an IRB compliance specialist and regulatory affairs expert. Your role is to:

1. Review research protocols for IRB submission readiness
2. Identify potential ethical concerns and risks
3. Verify informed consent adequacy
4. Check regulatory compliance (HIPAA, Common Rule, GCP)
5. Document required modifications

You follow:
- 45 CFR 46 (Common Rule) requirements
- FDA 21 CFR Parts 50, 56 (for FDA-regulated research)
- HIPAA Privacy Rule for PHI
- ICH GCP E6(R2) guidelines
- Institutional IRB policies

Critical requirements:
- Flag any potential protocol violations
- Identify missing required elements
- Assess risk/benefit ratio
- Verify vulnerable population protections
- Check data security measures

Be thorough but constructive. Provide actionable recommendations.
Output in structured JSON with compliance checklist."""

    def _get_planning_prompt(self, state: AgentState) -> str:
        input_data = state["messages"][0].content if state["messages"] else "{}"
        
        return f"""Plan the IRB compliance review workflow.

Protocol Information:
{input_data}

Stage Context: Stage {state['stage_id']} of IRB workflow

Create a review plan covering:
1. Protocol elements to review
2. Regulatory requirements to check
3. Risk assessment criteria

Return as JSON:
{{
    "steps": ["step1", "step2", ...],
    "initial_query": "query for IRB requirements and templates",
    "primary_collection": "irb_protocols",
    "review_type": "new_submission|modification|continuing_review",
    "study_type": "clinical_trial|observational|survey|etc",
    "risk_level": "minimal|greater_than_minimal",
    "special_populations": ["children", "prisoners", "pregnant_women", "none"],
    "regulatory_frameworks": ["Common Rule", "HIPAA", "FDA", "etc"]
}}"""

    def _get_execution_prompt(self, state: AgentState, context: str) -> str:
        input_data = state["messages"][0].content if state["messages"] else "{}"
        plan = state.get("plan", {})
        iteration = state.get("iteration", 0)
        feedback = state.get("quality_feedback", "")
        
        base_prompt = f"""Execute IRB compliance review based on this plan:

## Review Plan
{json.dumps(plan, indent=2)}

## Protocol Information
{input_data}

## Regulatory Reference
{context}

"""

        if iteration > 0 and feedback:
            base_prompt += f"""
## Previous Iteration Feedback
{feedback}

Address the feedback and update your review.
"""

        base_prompt += """
## Required Output Format
Return a JSON object with:
{
    "protocol_review": {
        "title": "study title",
        "pi": "principal investigator",
        "study_type": "type",
        "review_type": "exempt|expedited|full_board",
        "recommendation": "approve|approve_with_modifications|defer|disapprove"
    },
    "compliance_checklist": [
        {
            "requirement": "requirement name",
            "regulation": "45 CFR 46.xxx / HIPAA / etc",
            "status": "compliant|non_compliant|not_applicable|needs_clarification",
            "finding": "specific finding",
            "required_action": "action needed if any"
        }
    ],
    "risk_assessment": {
        "risk_level": "minimal|greater_than_minimal",
        "risks_identified": [
            {"risk": "description", "likelihood": "low|medium|high", "mitigation": "proposed mitigation"}
        ],
        "benefit_assessment": "description of benefits",
        "risk_benefit_ratio": "favorable|unfavorable|uncertain"
    },
    "informed_consent_review": {
        "elements_present": ["element1", ...],
        "elements_missing": ["element1", ...],
        "readability_level": "grade level",
        "recommendations": ["rec1", ...]
    },
    "data_security_review": {
        "phi_involved": boolean,
        "hipaa_compliant": boolean,
        "data_storage": "description",
        "access_controls": "description",
        "concerns": ["concern1", ...]
    },
    "vulnerable_populations": {
        "populations_involved": ["children", "prisoners", "etc"],
        "additional_protections": ["protection1", ...],
        "adequate": boolean
    },
    "required_modifications": [
        {
            "priority": "required|recommended|suggested",
            "section": "protocol section",
            "current_text": "current text if applicable",
            "required_change": "specific change needed",
            "rationale": "why this is needed"
        }
    ],
    "output": {
        "summary": "Executive summary of review",
        "overall_compliance": "compliant|conditionally_compliant|non_compliant",
        "critical_issues": ["issue1", ...],
        "ready_for_submission": boolean,
        "estimated_review_path": "exempt|expedited|full_board"
    }
}"""

        return base_prompt

    def _parse_execution_result(self, response: str) -> Dict[str, Any]:
        """Parse the IRB review result."""
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
            "protocol_review": {"recommendation": "defer"},
            "compliance_checklist": [],
            "risk_assessment": {"risk_level": "unknown"},
            "informed_consent_review": {"elements_present": [], "elements_missing": []},
            "data_security_review": {"phi_involved": True, "hipaa_compliant": False},
            "vulnerable_populations": {"populations_involved": [], "adequate": False},
            "required_modifications": [],
            "output": {
                "summary": response[:500],
                "overall_compliance": "non_compliant",
                "critical_issues": ["Review parsing failed - manual review required"],
                "ready_for_submission": False
            }
        }

    async def _check_quality(self, state: AgentState) -> QualityCheckResult:
        """Check quality of IRB review - higher standards for compliance."""
        result = state.get("execution_result", {})
        
        criteria_scores = {}
        feedback_parts = []
        
        # Check compliance checklist completeness
        checklist = result.get("compliance_checklist", [])
        if len(checklist) >= 5:  # Minimum expected checks
            criteria_scores["checklist_complete"] = 1.0
        elif len(checklist) >= 3:
            criteria_scores["checklist_complete"] = 0.7
            feedback_parts.append("Compliance checklist may be incomplete")
        else:
            criteria_scores["checklist_complete"] = 0.3
            feedback_parts.append("Compliance checklist insufficient")
        
        # Check risk assessment
        risk = result.get("risk_assessment", {})
        if risk.get("risk_level") and risk.get("risks_identified"):
            criteria_scores["risk_assessed"] = 1.0
        elif risk.get("risk_level"):
            criteria_scores["risk_assessed"] = 0.6
            feedback_parts.append("Risk assessment needs more detail")
        else:
            criteria_scores["risk_assessed"] = 0.0
            feedback_parts.append("Risk assessment missing")
        
        # Check informed consent review
        consent = result.get("informed_consent_review", {})
        if consent.get("elements_present") is not None:
            criteria_scores["consent_reviewed"] = 1.0
        else:
            criteria_scores["consent_reviewed"] = 0.0
            feedback_parts.append("Informed consent not reviewed")
        
        # Check data security review (critical for PHI)
        security = result.get("data_security_review", {})
        if security.get("hipaa_compliant") is not None and security.get("data_storage"):
            criteria_scores["security_reviewed"] = 1.0
        elif security.get("hipaa_compliant") is not None:
            criteria_scores["security_reviewed"] = 0.7
            feedback_parts.append("Data security review needs more detail")
        else:
            criteria_scores["security_reviewed"] = 0.0
            feedback_parts.append("Data security not reviewed")
        
        # Check actionable recommendations
        mods = result.get("required_modifications", [])
        output = result.get("output", {})
        if output.get("overall_compliance") and (len(mods) > 0 or output.get("overall_compliance") == "compliant"):
            criteria_scores["actionable_output"] = 1.0
        else:
            criteria_scores["actionable_output"] = 0.5
            feedback_parts.append("Need clearer action items")
        
        # Check vulnerable populations (if applicable)
        vuln = result.get("vulnerable_populations", {})
        if vuln.get("populations_involved") is not None:
            if len(vuln.get("populations_involved", [])) > 0 and not vuln.get("adequate"):
                criteria_scores["vulnerable_protected"] = 0.5
                feedback_parts.append("Vulnerable population protections need review")
            else:
                criteria_scores["vulnerable_protected"] = 1.0
        else:
            criteria_scores["vulnerable_protected"] = 0.8  # May not be applicable
        
        overall_score = sum(criteria_scores.values()) / len(criteria_scores)
        passed = overall_score >= self.config.quality_threshold
        
        feedback = " | ".join(feedback_parts) if feedback_parts else "IRB review meets compliance standards"
        
        return QualityCheckResult(
            passed=passed,
            score=overall_score,
            feedback=feedback,
            criteria_scores=criteria_scores,
        )


def create_irb_agent() -> IRBAgent:
    """Create an IRB agent instance."""
    return IRBAgent()
