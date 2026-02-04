"""
Stage 14: Ethical Review

EthicalReviewAgent performs a rich, multi-criteria ethics assessment inspired by
Stage 13's internal review pattern. It:
- Aggregates prior stage outputs (IRB, PHI, study design, stats, validation)
- Evaluates ethics criteria (participant protection, consent, privacy, COI, risk/benefit)
- Simulates reviewer personas (IRB Chair, Bioethicist, Patient Advocate)
- Runs optional LangChain tools for guideline lookup and red-flag detection
- Emits structured reports, checklists, remediation recommendations, and red flags
"""

import json
import logging
import os
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from .base_stage_agent import BaseStageAgent, BaseTool, PromptTemplate, LANGCHAIN_AVAILABLE
from ..types import StageContext, StageResult
from ..registry import register_stage

logger = logging.getLogger("workflow_engine.stages.stage_14_ethicalreviewagent")

# LangChain tool import with graceful fallback
try:
    from langchain.tools import Tool
    LC_TOOL = Tool
except Exception:  # pragma: no cover - handled at runtime
    LC_TOOL = None

# ---------------------------------------------------------------------------
# Constants and defaults
# ---------------------------------------------------------------------------

ETHICS_CRITERIA = [
    "participant_protection",
    "informed_consent",
    "data_privacy",
    "conflict_of_interest",
    "risk_benefit",
]

CRITERIA_WEIGHTS = {
    "participant_protection": 0.25,
    "informed_consent": 0.2,
    "data_privacy": 0.2,
    "conflict_of_interest": 0.15,
    "risk_benefit": 0.2,
}

DEFAULT_PERSONAS = [
    {
        "id": "irb_chair",
        "name": "IRB Chair",
        "focus_areas": ["participant_protection", "informed_consent", "data_privacy"],
        "strictness": 0.85,
    },
    {
        "id": "bioethicist",
        "name": "Bioethicist",
        "focus_areas": ["risk_benefit", "conflict_of_interest", "participant_protection"],
        "strictness": 0.75,
    },
    {
        "id": "patient_advocate",
        "name": "Patient Advocate",
        "focus_areas": ["participant_protection", "informed_consent"],
        "strictness": 0.65,
    },
]

VULNERABLE_GROUPS = {
    "minors",
    "pregnant_people",
    "prisoners",
    "cognitively_impaired",
    "economically_disadvantaged",
    "critically_ill",
    "terminally_ill",
}

RED_FLAG_THRESHOLDS = {
    "missing_consent": True,
    "phi_high_risk": True,
    "vulnerable_group_without_safeguards": True,
    "no_irb_protocol": True,
}

GO_NO_GO_THRESHOLDS = {
    "min_overall_score": 7.5,
    "max_red_flags": 0,
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _safe_prior_output(context: StageContext, stage_id: int) -> Dict[str, Any]:
    """Return prior stage output or empty dict."""
    result = context.previous_results.get(stage_id)
    if result and result.output:
        return result.output
    return context.prior_stage_outputs.get(stage_id, {}).get("output_data", {}) or {}


def _detect_vulnerable_populations(population: Any) -> List[str]:
    """Detect vulnerable populations from free-text or structured input."""
    if not population:
        return []
    text = ""
    detected: List[str] = []
    if isinstance(population, str):
        text = population.lower()
    elif isinstance(population, dict):
        text = json.dumps(population).lower()
    elif isinstance(population, list):
        text = " ".join(str(item).lower() for item in population)
    for group in VULNERABLE_GROUPS:
        if group.replace("_", " ") in text:
            detected.append(group)
    return list(sorted(set(detected)))


def _evaluate_participant_protection(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate participant protection safeguards."""
    safeguards = ctx.get("safeguards", [])
    vulnerable = ctx.get("vulnerable_groups", [])
    phi_risk = ctx.get("phi_risk", "unknown")
    has_protocol = bool(ctx.get("irb_protocol"))

    score = 8.0
    rationale = []
    if vulnerable and not safeguards:
        score -= 2.5
        rationale.append("Vulnerable population identified without documented safeguards.")
    if phi_risk in ("high", "medium"):
        score -= 1.0
        rationale.append(f"PHI risk is {phi_risk}; requires stronger protection.")
    if not has_protocol:
        score -= 2.0
        rationale.append("No IRB protocol found; participant protections uncertain.")
    if not rationale:
        rationale.append("Adequate protections documented.")
    return {"criterion": "participant_protection", "score": max(score, 0.0), "rationale": rationale}


def _evaluate_informed_consent(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate informed consent presence and quality."""
    consent = ctx.get("consent", {})
    has_consent = consent.get("obtained", False)
    supports_languages = consent.get("languages", ["en"])
    waivers = consent.get("waivers", False)
    vulnerable = ctx.get("vulnerable_groups", [])

    score = 8.0 if has_consent else 4.0
    rationale = []
    if not has_consent:
        rationale.append("Consent not obtained or documentation missing.")
    if waivers:
        score -= 1.0
        rationale.append("Consent waiver requested; verify justification.")
    if vulnerable and "assent" not in consent.get("special_provisions", []):
        score -= 0.8
        rationale.append("Assent/guardian consent provisions missing for vulnerable groups.")
    if len(supports_languages) == 1 and supports_languages[0] == "en":
        score -= 0.5
        rationale.append("Consent only available in English; consider translation for inclusivity.")
    if not rationale:
        rationale.append("Informed consent properly documented with multilingual support.")
    return {"criterion": "informed_consent", "score": max(score, 0.0), "rationale": rationale}


def _evaluate_data_privacy(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate data privacy (HIPAA/GDPR) compliance."""
    privacy = ctx.get("privacy", {})
    hipaa = privacy.get("hipaa", {})
    gdpr = privacy.get("gdpr", {})
    retention = privacy.get("retention_days")
    phi_risk = ctx.get("phi_risk", "unknown")

    score = 8.0
    rationale = []
    if not hipaa.get("legal_basis"):
        score -= 1.0
        rationale.append("HIPAA legal basis not documented.")
    if not gdpr.get("legal_basis"):
        score -= 1.0
        rationale.append("GDPR legal basis not documented.")
    if not gdpr.get("data_minimization", True):
        score -= 0.7
        rationale.append("Data minimization not demonstrated.")
    if retention is None:
        score -= 0.5
        rationale.append("Retention period not specified.")
    if phi_risk == "high":
        score -= 1.0
        rationale.append("High PHI risk; ensure de-identification or limited data set.")
    if not rationale:
        rationale.append("Privacy controls aligned with HIPAA/GDPR and retention defined.")
    return {"criterion": "data_privacy", "score": max(score, 0.0), "rationale": rationale}


def _evaluate_conflict_of_interest(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Detect conflicts of interest."""
    disclosures = ctx.get("conflict_disclosures", [])
    flagged = [d for d in disclosures if d.get("has_conflict")]
    score = 9.0
    rationale = []
    if flagged:
        score -= 2.0
        rationale.append("Conflicts disclosed; management plan required.")
    if not disclosures:
        score -= 0.5
        rationale.append("No conflict disclosure provided.")
    if not rationale:
        rationale.append("No conflicts identified; disclosure completed.")
    return {"criterion": "conflict_of_interest", "score": max(score, 0.0), "rationale": rationale}


def _evaluate_risk_benefit(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Assess risk/benefit balance."""
    risks = ctx.get("risks", []) or []
    benefits = ctx.get("benefits", []) or []
    safeguards = ctx.get("safeguards", [])

    risk_level = len([r for r in risks if r])  # simple count
    benefit_level = len([b for b in benefits if b])

    score = 8.0
    rationale = []
    if risk_level > benefit_level:
        score -= 1.5
        rationale.append("Risks outweigh benefits; mitigation needed.")
    if risk_level and not safeguards:
        score -= 1.0
        rationale.append("Risks identified without safeguards.")
    if not risks:
        rationale.append("No material risks documented.")
    if not benefits:
        score -= 0.5
        rationale.append("Benefits not articulated; may impact justification.")
    if not rationale:
        rationale.append("Risk/benefit balance acceptable with safeguards.")
    return {
        "criterion": "risk_benefit",
        "score": max(score, 0.0),
        "rationale": rationale,
        "risk_count": risk_level,
        "benefit_count": benefit_level,
    }


def _compute_overall_score(criterion_results: List[Dict[str, Any]]) -> float:
    """Weighted average overall score."""
    total = 0.0
    weight_sum = 0.0
    for result in criterion_results:
        weight = CRITERIA_WEIGHTS.get(result["criterion"], 0.2)
        total += result["score"] * weight
        weight_sum += weight
    return round(total / weight_sum, 2) if weight_sum else 0.0


def _generate_recommendations(criterion_results: List[Dict[str, Any]], red_flags: List[str]) -> List[Dict[str, Any]]:
    """Create remediation recommendations based on low scores and red flags."""
    recs: List[Dict[str, Any]] = []
    for res in criterion_results:
        if res["score"] < 7.0:
            recs.append({
                "criterion": res["criterion"],
                "priority": "high" if res["score"] < 6 else "medium",
                "action": "; ".join(res["rationale"]),
                "owner": "ethics_officer",
                "due": "before_stage_15",
            })
    for flag in red_flags:
        recs.append({
            "criterion": "red_flag",
            "priority": "critical",
            "action": f"Resolve red flag: {flag}",
            "owner": "irb_team",
            "due": "immediate",
        })
    return recs


def _persona_review(persona: Dict[str, Any], criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Simulate persona scoring based on focus areas and strictness."""
    focus = persona.get("focus_areas", [])
    strictness = persona.get("strictness", 0.7)
    scores: Dict[str, float] = {}
    comments: List[str] = []

    for res in criteria:
        base = res["score"]
        adjusted = base - (1.0 * strictness if res["criterion"] in focus and base < 9 else 0.0)
        scores[res["criterion"]] = round(max(adjusted, 0.0), 2)
        if res["criterion"] in focus and base < 8:
            comments.append(f"{persona['name']} flagged {res['criterion']} ({res['score']})")

    overall = round(mean(scores.values()), 2) if scores else 0.0
    recommendation = "revise" if overall < 7.5 else "go"
    if overall < 6.0:
        recommendation = "no-go"

    return {
        "reviewer_id": persona["id"],
        "reviewer_name": persona["name"],
        "scores": scores,
        "overall_score": overall,
        "recommendation": recommendation,
        "comments": comments,
    }


def _detect_red_flags(ctx: Dict[str, Any]) -> List[str]:
    """Identify red flags from context and thresholds."""
    flags: List[str] = []
    if RED_FLAG_THRESHOLDS["missing_consent"] and not ctx.get("consent", {}).get("obtained", False):
        flags.append("missing_consent")
    if RED_FLAG_THRESHOLDS["phi_high_risk"] and ctx.get("phi_risk") == "high":
        flags.append("phi_high_risk")
    if RED_FLAG_THRESHOLDS["no_irb_protocol"] and not ctx.get("irb_protocol"):
        flags.append("no_irb_protocol")
    if ctx.get("vulnerable_groups") and not ctx.get("safeguards"):
        flags.append("vulnerable_group_without_safeguards")
    return flags


def _build_ethics_context(context: StageContext) -> Dict[str, Any]:
    """Aggregate inputs from config and prior stages into an ethics context."""
    config = context.config or {}
    irb_output = _safe_prior_output(context, 3)
    phi_output = _safe_prior_output(context, 5)
    design_output = _safe_prior_output(context, 6)
    stats_output = _safe_prior_output(context, 7)
    validation_output = _safe_prior_output(context, 10)
    bundling_output = _safe_prior_output(context, 15)

    population = (
        design_output.get("population") or
        config.get("population") or
        config.get("participants")
    )
    vulnerable_groups = _detect_vulnerable_populations(population)

    consent_info = config.get("consent", {})
    if irb_output.get("consent"):
        consent_info = {**consent_info, **irb_output["consent"]}

    privacy_info = config.get("privacy", {})
    if phi_output.get("privacy"):
        privacy_info = {**privacy_info, **phi_output["privacy"]}

    safeguards = config.get("safeguards", design_output.get("safeguards", []))

    return {
        "job_id": context.job_id,
        "population": population,
        "vulnerable_groups": vulnerable_groups,
        "consent": consent_info,
        "privacy": privacy_info,
        "phi_risk": phi_output.get("risk_level", "unknown"),
        "conflict_disclosures": config.get("conflict_disclosures", []),
        "risks": design_output.get("risks", config.get("risks", [])),
        "benefits": design_output.get("benefits", config.get("benefits", [])),
        "safeguards": safeguards,
        "irb_protocol": irb_output.get("protocol") or config.get("irb_protocol"),
        "statistics": stats_output,
        "validation": validation_output,
        "bundle": bundling_output,
    }


def _write_json_artifact(path: str, data: Any) -> None:
    """Write JSON artifact with UTF-8 encoding."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# LangChain tool factories (optional)
# ---------------------------------------------------------------------------

def _build_ethics_tools(ethics_context: Dict[str, Any]) -> List[BaseTool]:
    """Create LangChain tools if available."""
    if not LANGCHAIN_AVAILABLE or LC_TOOL is None:
        return []

    def guideline_lookup(query: str) -> str:
        guides = {
            "belmont": "Respect for Persons, Beneficence, Justice",
            "helsinki": "Participant safety, scientific validity, transparency",
            "gdpr": "Legal basis, minimization, purpose limitation, retention, rights",
            "hipaa": "Minimum necessary, safeguards, PHI identifiers, BAAs",
        }
        query_l = query.lower()
        matches = {k: v for k, v in guides.items() if k in query_l}
        if not matches:
            matches = guides
        return json.dumps({"query": query, "guidelines": matches}, indent=2)

    def irb_matcher(_: str) -> str:
        required = ["protocol_number", "risk_mitigation", "consent", "data_sharing"]
        present = {
            "protocol_number": bool(ethics_context.get("irb_protocol")),
            "risk_mitigation": bool(ethics_context.get("safeguards")),
            "consent": bool(ethics_context.get("consent", {}).get("obtained")),
            "data_sharing": bool(ethics_context.get("bundle")),
        }
        missing = [k for k, v in present.items() if not v]
        return json.dumps({"required": required, "present": present, "missing": missing}, indent=2)

    def red_flag_detector(_: str) -> str:
        return json.dumps({"red_flags": _detect_red_flags(ethics_context)}, indent=2)

    return [
        LC_TOOL(name="ethics_guideline_lookup", func=guideline_lookup, description="Lookup ethics guidelines"),
        LC_TOOL(name="irb_requirement_matcher", func=irb_matcher, description="Check IRB requirements"),
        LC_TOOL(name="red_flag_detector", func=red_flag_detector, description="Detect red flags"),
    ]


# ---------------------------------------------------------------------------
# Prompt template (LangChain optional)
# ---------------------------------------------------------------------------

def _build_prompt_template() -> PromptTemplate:
    if not LANGCHAIN_AVAILABLE:
        class _Stub:
            @classmethod
            def from_template(cls, _t):
                return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
        return _Stub.from_template("{input}")

    return PromptTemplate.from_template(
        "You are an ethical review agent for research workflows.\n"
        "Evaluate participant protection, informed consent, privacy, conflicts, and risk/benefit.\n"
        "Provide: checklist, scores, red flags, recommendations, and go/no-go.\n"
        "Context: {ethics_context}\n"
    )


# ---------------------------------------------------------------------------
# Stage implementation
# ---------------------------------------------------------------------------


@register_stage
class EthicalReviewAgent(BaseStageAgent):
    """Stage 14: Ethical Review with AI support and persona simulation."""

    stage_id = 14
    stage_name = "Ethical Review"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._prompt_template = _build_prompt_template()

    def get_tools(self) -> List[BaseTool]:
        return _build_ethics_tools({})

    def get_prompt_template(self) -> PromptTemplate:
        return self._prompt_template

    async def execute(self, context: StageContext) -> StageResult:
        started_at = datetime.utcnow().isoformat() + "Z"
        warnings: List[str] = []
        errors: List[str] = []
        artifacts: List[str] = []

        ethics_context = _build_ethics_context(context)
        tools = _build_ethics_tools(ethics_context)

        # Refresh prompt template with populated context
        if LANGCHAIN_AVAILABLE:
            self._prompt_template = _build_prompt_template()

        # Optional bridge enrichment
        bridge_output: Optional[Dict[str, Any]] = None
        try:
            bridge_output = await self.call_manuscript_service(
                "manuscript",
                "runStageEthicalReview",
                {
                    "job_id": context.job_id,
                    "config": context.config,
                    "stage_id": self.stage_id,
                    "stage_name": self.stage_name,
                    "ethics_context": ethics_context,
                },
            )
        except Exception as e:  # pragma: no cover - network/bridge fallback
            logger.warning("Bridge call failed: %s", e)
            warnings.append(f"Bridge enrichment failed: {e}")

        # Evaluate criteria
        criteria_results = [
            _evaluate_participant_protection(ethics_context),
            _evaluate_informed_consent(ethics_context),
            _evaluate_data_privacy(ethics_context),
            _evaluate_conflict_of_interest(ethics_context),
            _evaluate_risk_benefit(ethics_context),
        ]
        overall_score = _compute_overall_score(criteria_results)
        red_flags = _detect_red_flags(ethics_context)

        # Persona simulation
        personas = context.config.get("reviewer_personas", DEFAULT_PERSONAS) or DEFAULT_PERSONAS
        persona_reviews = [_persona_review(p, criteria_results) for p in personas]
        persona_avg = round(mean([p["overall_score"] for p in persona_reviews]), 2) if persona_reviews else 0.0

        # Recommendation logic
        decision = "go"
        if red_flags:
            decision = "revise"
        if len(red_flags) > GO_NO_GO_THRESHOLDS["max_red_flags"] or overall_score < GO_NO_GO_THRESHOLDS["min_overall_score"]:
            decision = "revise"
        if overall_score < 6.0:
            decision = "no-go"

        recommendations = _generate_recommendations(criteria_results, red_flags)
        checklist = [
            {
                "criterion": res["criterion"],
                "pass": res["score"] >= 7.5,
                "score": res["score"],
                "rationale": res["rationale"],
            }
            for res in criteria_results
        ]

        output = {
            "ethics_context": ethics_context,
            "criteria": criteria_results,
            "overall_score": overall_score,
            "persona_reviews": persona_reviews,
            "persona_average": persona_avg,
            "decision": decision,
            "red_flags": red_flags,
            "recommendations": recommendations,
            "checklist": checklist,
            "bridge_output": bridge_output,
            "tools_available": bool(tools),
        }

        # Persist artifacts
        report_path = os.path.join(context.artifact_path, f"ethics_report_{context.job_id}.json")
        checklist_path = os.path.join(context.artifact_path, f"ethics_checklist_{context.job_id}.json")
        summary_md_path = os.path.join(context.artifact_path, f"ethics_summary_{context.job_id}.md")

        try:
            _write_json_artifact(report_path, output)
            artifacts.append(report_path)
            _write_json_artifact(checklist_path, checklist)
            artifacts.append(checklist_path)
            md_content = [
                f"# Ethics Review Summary (Job {context.job_id})",
                f"- Overall score: {overall_score}",
                f"- Decision: {decision}",
                f"- Red flags: {', '.join(red_flags) if red_flags else 'None'}",
                f"- Personas: {', '.join([p['reviewer_name'] for p in persona_reviews])}",
            ]
            os.makedirs(os.path.dirname(summary_md_path), exist_ok=True)
            with open(summary_md_path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_content))
            artifacts.append(summary_md_path)
        except Exception as e:  # pragma: no cover - filesystem issues
            logger.error("Failed to write artifacts: %s", e)
            warnings.append(f"Failed to persist artifacts: {e}")

        # Governance-mode behavior
        if context.governance_mode == "DEMO":
            warnings.append("Running in DEMO mode; ethics evaluation may use defaults.")

        status = "failed" if errors else "completed"

        return self.create_stage_result(
            context=context,
            status=status,
            started_at=started_at,
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "overall_score": overall_score,
                "decision": decision,
                "red_flag_count": len(red_flags),
                "persona_count": len(persona_reviews),
            },
        )
