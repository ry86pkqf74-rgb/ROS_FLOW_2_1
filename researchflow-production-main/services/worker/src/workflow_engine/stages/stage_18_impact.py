"""
Stage 18: Impact Assessment

Handles research impact assessment including:
- Citation potential analysis and Altmetric score prediction
- Field advancement and policy relevance scoring
- Academic audience mapping and industry application potential
- Public health implications and policy maker relevance
- Impact radar chart data, stakeholder matrix, timeline projections
- Executive summary, detailed impact report, presentation slides data

This stage produces impact metrics and reporting for dissemination.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stage_18_impact")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")

# Default metric weights for impact scoring
DEFAULT_METRIC_WEIGHTS = {
    "citation_potential": 0.3,
    "altmetric": 0.25,
    "field_advancement": 0.25,
    "policy_relevance": 0.2,
}


# ---------------------------------------------------------------------------
# Impact metrics
# ---------------------------------------------------------------------------

def compute_citation_potential(
    previous_results: Dict[int, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute citation potential score and factors (journal tier, novelty, methods).

    Args:
        previous_results: Results from previous stages
        config: Job config with optional journal_tier, novelty_hint

    Returns:
        Dict with score, factors, confidence
    """
    base_score = 6.0
    factors: Dict[str, Any] = {"journal_tier": "unknown", "novelty": "medium", "methods_strength": "medium"}
    if config:
        factors["journal_tier"] = config.get("journal_tier", "unknown")
        factors["novelty"] = config.get("novelty_hint", "medium")
    for stage_id, result in previous_results.items():
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if isinstance(output, dict):
            if output.get("methodology") or output.get("methods"):
                factors["methods_strength"] = "strong"
                base_score += 0.5
            if output.get("novelty") or output.get("innovation"):
                factors["novelty"] = "high"
                base_score += 0.5
    score = min(10.0, max(0.0, base_score))
    return {
        "score": round(score, 2),
        "factors": factors,
        "confidence": "medium" if len(previous_results) > 3 else "low",
    }


def predict_altmetric_score(
    previous_results: Dict[int, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Predict Altmetric score range and drivers (social, media, policy).

    Args:
        previous_results: Results from previous stages
        config: Job config

    Returns:
        Dict with score_range, drivers
    """
    low, high = 5, 25
    if previous_results:
        n = len(previous_results)
        low = max(0, 5 + n)
        high = min(100, 15 + n * 3)
    drivers = {
        "social": "medium",
        "media": "low",
        "policy": config.get("policy_relevance", "low") if config else "low",
    }
    return {
        "score_range": {"min": low, "max": high},
        "drivers": drivers,
        "note": "Predicted range based on pipeline stage count and config.",
    }


def assess_field_advancement(previous_results: Dict[int, Any]) -> Dict[str, Any]:
    """Assess field advancement score and contributing factors.

    Args:
        previous_results: Results from previous stages

    Returns:
        Dict with advancement_score, contributing_factors, comparison_note
    """
    score = 5.0
    factors: List[str] = []
    for stage_id, result in previous_results.items():
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if isinstance(output, dict):
            if output.get("novelty") or output.get("innovation"):
                factors.append("Novelty/innovation")
                score += 1.0
            if output.get("methodology") or output.get("reproducibility"):
                factors.append("Methodological rigor")
                score += 0.5
    score = min(10.0, max(0.0, score))
    return {
        "advancement_score": round(score, 2),
        "contributing_factors": factors or ["Pipeline completeness"],
        "comparison_note": "Relative to typical pipeline output; compare to field benchmarks.",
    }


def compute_policy_relevance_score(
    previous_results: Dict[int, Any],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute policy relevance score, policy domains, evidence strength.

    Args:
        previous_results: Results from previous stages
        config: Job config with optional policy_domains

    Returns:
        Dict with score, policy_domains, evidence_strength
    """
    domains = config.get("policy_domains", ["health", "research"]) if config else ["health", "research"]
    score = 5.0
    for stage_id, result in previous_results.items():
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if isinstance(output, dict) and (output.get("policy") or output.get("recommendations")):
            score += 1.0
            break
    score = min(10.0, max(0.0, score))
    return {
        "score": round(score, 2),
        "policy_domains": domains if isinstance(domains, list) else [domains],
        "evidence_strength": "medium" if len(previous_results) > 5 else "preliminary",
    }


# ---------------------------------------------------------------------------
# Stakeholder analysis
# ---------------------------------------------------------------------------

def map_academic_audience(previous_results: Dict[int, Any]) -> List[Dict[str, Any]]:
    """Map academic audience: disciplines, journals, conferences, seniority.

    Args:
        previous_results: Results from previous stages

    Returns:
        List of audience segment dicts
    """
    segments = [
        {"discipline": "Clinical research", "journals": ["General medical"], "conferences": [], "seniority": "mixed"},
        {"discipline": "Methodology", "journals": ["Methods-focused"], "conferences": [], "seniority": "mixed"},
    ]
    for stage_id, result in previous_results.items():
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if isinstance(output, dict) and output.get("study_design"):
            segments[0]["journals"] = ["Domain-specific journals"]
            break
    return segments


def assess_industry_application_potential(previous_results: Dict[int, Any]) -> Dict[str, Any]:
    """Assess industry application potential: sectors, use cases, readiness.

    Args:
        previous_results: Results from previous stages

    Returns:
        Dict with sectors, use_cases, readiness
    """
    sectors = ["Healthcare", "Pharma", "Health tech"]
    use_cases = ["Evidence synthesis", "Decision support", "Quality improvement"]
    readiness = "prototype" if len(previous_results) > 10 else "early"
    return {
        "sectors": sectors,
        "use_cases": use_cases,
        "readiness": readiness,
    }


def assess_public_health_implications(previous_results: Dict[int, Any]) -> Dict[str, Any]:
    """Assess public health implications: implications, reach, equity notes.

    Args:
        previous_results: Results from previous stages

    Returns:
        Dict with implications, reach, equity_notes
    """
    implications: List[str] = []
    for stage_id, result in previous_results.items():
        output = getattr(result, "output", None) or (result.get("output", {}) if isinstance(result, dict) else {})
        if isinstance(output, dict) and output.get("discussion"):
            implications.append("Discussion section suggests public health relevance.")
            break
    if not implications:
        implications.append("Pipeline output may inform practice and policy.")
    return {
        "implications": implications,
        "reach": "regional" if previous_results else "unknown",
        "equity_notes": "Consider equity in interpretation and dissemination.",
    }


def assess_policy_maker_relevance(previous_results: Dict[int, Any]) -> Dict[str, Any]:
    """Assess policy maker relevance: policy levels, agencies, relevance score.

    Args:
        previous_results: Results from previous stages

    Returns:
        Dict with policy_levels, agencies, relevance_score
    """
    score = 5.0
    if previous_results:
        score = min(10.0, 5.0 + len(previous_results) * 0.3)
    return {
        "policy_levels": ["Local", "National", "International"],
        "agencies": ["Health departments", "Research funders", "Guideline bodies"],
        "relevance_score": round(score, 2),
    }


# ---------------------------------------------------------------------------
# Visualization (data only)
# ---------------------------------------------------------------------------

def build_impact_radar_data(metrics_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Build impact radar chart data: axes (citation, altmetric, field, policy), values, labels.

    Args:
        metrics_dict: Dict with citation_potential, altmetric, field_advancement, policy_relevance

    Returns:
        Dict with axes, values, labels for radar chart
    """
    axes = ["citation_potential", "altmetric", "field_advancement", "policy_relevance"]
    values: List[float] = []
    labels: List[str] = []
    for ax in axes:
        m = metrics_dict.get(ax) or {}
        if isinstance(m, dict):
            val = m.get("score") or m.get("advancement_score") or m.get("relevance_score")
            if val is None and "score_range" in m:
                r = m["score_range"]
                val = (r.get("min", 0) + r.get("max", 0)) / 2.0 if isinstance(r, dict) else 5.0
        else:
            val = float(m) if m is not None else 5.0
        values.append(round(float(val) if val is not None else 5.0, 2))
        labels.append(ax.replace("_", " ").title())
    return {"axes": axes, "values": values, "labels": labels}


def build_stakeholder_matrix_data(stakeholder_results: Dict[str, Any]) -> Dict[str, Any]:
    """Build stakeholder matrix (e.g. interest vs influence) for frontend.

    Args:
        stakeholder_results: Output from stakeholder analysis helpers

    Returns:
        Dict with quadrants or matrix data
    """
    quadrants = [
        {"name": "High interest, high influence", "stakeholders": ["PIs", "Funders"], "x": 1, "y": 1},
        {"name": "High interest, low influence", "stakeholders": ["Patients", "Public"], "x": 0, "y": 1},
        {"name": "Low interest, high influence", "stakeholders": ["Policymakers", "Regulators"], "x": 1, "y": 0},
        {"name": "Low interest, low influence", "stakeholders": ["General audience"], "x": 0, "y": 0},
    ]
    return {"quadrants": quadrants, "axes": ["influence", "interest"]}


def build_timeline_projections(
    metrics: Dict[str, Any],
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build timeline projections: time points (e.g. 6m, 12m, 24m) with projected metric values.

    Args:
        metrics: Impact metrics dict
        config: Config with optional projection_months

    Returns:
        List of projection dicts with period, projected values
    """
    months = config.get("projection_months", [6, 12, 24]) if config else [6, 12, 24]
    if not isinstance(months, list):
        months = [6, 12, 24]
    base_citation = 0.0
    base_altmetric = 10.0
    cp = metrics.get("citation_potential") or {}
    alt = metrics.get("altmetric") or {}
    if isinstance(cp, dict) and cp.get("score") is not None:
        base_citation = float(cp["score"]) * 0.5
    if isinstance(alt, dict) and isinstance(alt.get("score_range"), dict):
        r = alt["score_range"]
        base_altmetric = (r.get("min", 0) + r.get("max", 0)) / 2.0
    projections: List[Dict[str, Any]] = []
    for m in months:
        projections.append({
            "period_months": m,
            "citation_projection": round(base_citation + m * 0.2, 2),
            "altmetric_projection": round(base_altmetric + m * 0.5, 2),
        })
    return projections


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def generate_executive_summary(
    metrics: Dict[str, Any],
    stakeholder_analysis: Dict[str, Any],
) -> str:
    """Generate short narrative executive summary.

    Args:
        metrics: Impact metrics dict
        stakeholder_analysis: Stakeholder analysis dict

    Returns:
        Summary string
    """
    parts = ["Impact assessment summary."]
    if metrics:
        cp = metrics.get("citation_potential") or {}
        if isinstance(cp, dict) and cp.get("score") is not None:
            parts.append(f"Citation potential score: {cp['score']}.")
        adv = metrics.get("field_advancement") or {}
        if isinstance(adv, dict) and adv.get("advancement_score") is not None:
            parts.append(f"Field advancement score: {adv['advancement_score']}.")
    if stakeholder_analysis:
        industry = stakeholder_analysis.get("industry_application") or {}
        if isinstance(industry, dict) and industry.get("readiness"):
            parts.append(f"Industry readiness: {industry['readiness']}.")
    return " ".join(parts)


def generate_detailed_impact_report(
    metrics: Dict[str, Any],
    stakeholder: Dict[str, Any],
    visualizations: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate detailed impact report: sections (summary, metrics, stakeholders, visuals, recommendations).

    Args:
        metrics: Impact metrics
        stakeholder: Stakeholder analysis
        visualizations: Visualization data

    Returns:
        Dict with sections
    """
    summary = generate_executive_summary(metrics, stakeholder)
    return {
        "summary": summary,
        "metrics": metrics,
        "stakeholders": stakeholder,
        "visualizations": visualizations,
        "recommendations": [
            "Disseminate to academic and policy audiences.",
            "Track citations and Altmetric after publication.",
            "Update impact assessment with real-world data.",
        ],
    }


def build_presentation_slides_data(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build presentation slides data: slide titles and bullet/content for decks.

    Args:
        report: Output from generate_detailed_impact_report

    Returns:
        List of slide dicts with title, bullets
    """
    slides: List[Dict[str, Any]] = [
        {"title": "Impact Assessment Overview", "bullets": [report.get("summary", "Impact assessment complete.")]},
        {"title": "Key Metrics", "bullets": ["Citation potential", "Altmetric projection", "Field advancement", "Policy relevance"]},
        {"title": "Stakeholder Analysis", "bullets": ["Academic audience", "Industry application", "Public health", "Policy makers"]},
        {"title": "Recommendations", "bullets": report.get("recommendations", [])},
    ]
    return slides


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

@register_stage
class ImpactAssessmentAgent(BaseStageAgent):
    """Stage 18: Impact Assessment.

    Computes impact metrics, stakeholder analysis, visualization data,
    and reporting. Optionally calls TypeScript manuscript service.
    """

    stage_id = 18
    stage_name = "Impact Assessment"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ImpactAssessmentAgent."""
        bridge_config = None
        if config and config.get("bridge_url"):
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0),
            )
        super().__init__(bridge_config=bridge_config)

    def get_tools(self) -> List[Any]:
        """Get LangChain tools for this stage."""
        if not LANGCHAIN_AVAILABLE or Tool is None:
            return []
        return [
            Tool(
                name="analyze_citation_potential",
                description="Analyze citation potential. Input: JSON with previous_results and config.",
                func=self._analyze_citation_potential_tool,
            ),
            Tool(
                name="predict_altmetric",
                description="Predict Altmetric score. Input: JSON with previous_results and config.",
                func=self._predict_altmetric_tool,
            ),
            Tool(
                name="assess_field_advancement",
                description="Assess field advancement. Input: JSON with previous_results.",
                func=self._assess_field_advancement_tool,
            ),
            Tool(
                name="score_policy_relevance",
                description="Score policy relevance. Input: JSON with previous_results and config.",
                func=self._score_policy_relevance_tool,
            ),
            Tool(
                name="map_academic_audience",
                description="Map academic audience. Input: JSON with previous_results.",
                func=self._map_academic_audience_tool,
            ),
            Tool(
                name="assess_industry_potential",
                description="Assess industry application potential. Input: JSON with previous_results.",
                func=self._assess_industry_potential_tool,
            ),
            Tool(
                name="assess_public_health",
                description="Assess public health implications. Input: JSON with previous_results.",
                func=self._assess_public_health_tool,
            ),
            Tool(
                name="assess_policy_relevance",
                description="Assess policy maker relevance. Input: JSON with previous_results.",
                func=self._assess_policy_relevance_tool,
            ),
            Tool(
                name="radar_chart_data",
                description="Build impact radar chart data. Input: JSON with metrics_dict.",
                func=self._radar_chart_data_tool,
            ),
            Tool(
                name="stakeholder_matrix_data",
                description="Build stakeholder matrix data. Input: JSON with stakeholder_results.",
                func=self._stakeholder_matrix_data_tool,
            ),
            Tool(
                name="timeline_projections",
                description="Build timeline projections. Input: JSON with metrics and config.",
                func=self._timeline_projections_tool,
            ),
            Tool(
                name="generate_executive_summary",
                description="Generate executive summary. Input: JSON with metrics and stakeholder_analysis.",
                func=self._generate_executive_summary_tool,
            ),
            Tool(
                name="generate_impact_report",
                description="Generate detailed impact report. Input: JSON with metrics, stakeholder, visualizations.",
                func=self._generate_impact_report_tool,
            ),
            Tool(
                name="build_slides_data",
                description="Build presentation slides data. Input: JSON with report.",
                func=self._build_slides_data_tool,
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for impact assessment."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t):
                    return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        try:
            from langchain_core.prompts import PromptTemplate
        except ImportError:
            from langchain.prompts import PromptTemplate  # type: ignore
        return PromptTemplate.from_template("""You are an Impact Assessment Specialist for research projects.

Your task is to:
1. Analyze citation potential, predict Altmetric score, assess field advancement, score policy relevance
2. Map academic audience, assess industry and public health potential, assess policy maker relevance
3. Build radar chart data, stakeholder matrix, timeline projections
4. Generate executive summary, detailed impact report, and presentation slides data

Metric weights: {metric_weights}

Input: {input}

Previous Agent Scratchpad: {agent_scratchpad}
""")

    def _parse_input(self, input_json: str) -> Dict[str, Any]:
        try:
            return json.loads(input_json) if isinstance(input_json, str) else input_json
        except Exception:
            return {}

    # Tool implementations
    def _analyze_citation_potential_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = compute_citation_potential(data.get("previous_results", {}), data.get("config", {}))
        return json.dumps({"status": "ok", "citation_potential": out}, indent=2)

    def _predict_altmetric_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = predict_altmetric_score(data.get("previous_results", {}), data.get("config", {}))
        return json.dumps({"status": "ok", "altmetric": out}, indent=2)

    def _assess_field_advancement_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = assess_field_advancement(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "field_advancement": out}, indent=2)

    def _score_policy_relevance_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = compute_policy_relevance_score(data.get("previous_results", {}), data.get("config", {}))
        return json.dumps({"status": "ok", "policy_relevance": out}, indent=2)

    def _map_academic_audience_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = map_academic_audience(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "academic_audience": out}, indent=2)

    def _assess_industry_potential_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = assess_industry_application_potential(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "industry_application": out}, indent=2)

    def _assess_public_health_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = assess_public_health_implications(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "public_health": out}, indent=2)

    def _assess_policy_relevance_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = assess_policy_maker_relevance(data.get("previous_results", {}))
        return json.dumps({"status": "ok", "policy_maker_relevance": out}, indent=2)

    def _radar_chart_data_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_impact_radar_data(data.get("metrics_dict", {}))
        return json.dumps({"status": "ok", "radar_data": out}, indent=2)

    def _stakeholder_matrix_data_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_stakeholder_matrix_data(data.get("stakeholder_results", {}))
        return json.dumps({"status": "ok", "matrix_data": out}, indent=2)

    def _timeline_projections_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_timeline_projections(data.get("metrics", {}), data.get("config", {}))
        return json.dumps({"status": "ok", "projections": out}, indent=2)

    def _generate_executive_summary_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = generate_executive_summary(data.get("metrics", {}), data.get("stakeholder_analysis", {}))
        return json.dumps({"status": "ok", "summary": out}, indent=2)

    def _generate_impact_report_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = generate_detailed_impact_report(
            data.get("metrics", {}),
            data.get("stakeholder", {}),
            data.get("visualizations", {}),
        )
        return json.dumps({"status": "ok", "report": out}, indent=2)

    def _build_slides_data_tool(self, input_json: str) -> str:
        data = self._parse_input(input_json)
        out = build_presentation_slides_data(data.get("report", {}))
        return json.dumps({"status": "ok", "slides": out}, indent=2)

    async def execute(self, context: StageContext) -> StageResult:
        """Execute impact assessment: metrics, stakeholder analysis, visualization, reporting."""
        started_at = datetime.utcnow().isoformat() + "Z"
        errors: List[str] = []
        warnings: List[str] = []
        output: Dict[str, Any] = {}

        logger.info(f"Starting Impact Assessment for job {context.job_id}")

        config = context.config or {}
        inputs = getattr(context, "inputs", config.get("inputs", {}))

        prev: Dict[int, Any] = {}
        if context.previous_results:
            for k, v in context.previous_results.items():
                prev[k] = asdict(v) if hasattr(v, "__dataclass_fields__") else v

        # Impact metrics
        citation = compute_citation_potential(prev, config)
        altmetric = predict_altmetric_score(prev, config)
        field_adv = assess_field_advancement(prev)
        policy_rel = compute_policy_relevance_score(prev, config)
        output["impact_metrics"] = {
            "citation_potential": citation,
            "altmetric": altmetric,
            "field_advancement": field_adv,
            "policy_relevance": policy_rel,
        }

        # Stakeholder analysis
        academic = map_academic_audience(prev)
        industry = assess_industry_application_potential(prev)
        public_health = assess_public_health_implications(prev)
        policy_maker = assess_policy_maker_relevance(prev)
        output["stakeholder_analysis"] = {
            "academic_audience": academic,
            "industry_application": industry,
            "public_health": public_health,
            "policy_maker_relevance": policy_maker,
        }

        # Visualization
        radar = build_impact_radar_data(output["impact_metrics"])
        matrix = build_stakeholder_matrix_data(output["stakeholder_analysis"])
        timeline = build_timeline_projections(output["impact_metrics"], config)
        output["visualization"] = {
            "radar_chart": radar,
            "stakeholder_matrix": matrix,
            "timeline_projections": timeline,
        }

        # Reporting
        summary = generate_executive_summary(output["impact_metrics"], output["stakeholder_analysis"])
        report = generate_detailed_impact_report(
            output["impact_metrics"],
            output["stakeholder_analysis"],
            output["visualization"],
        )
        slides = build_presentation_slides_data(report)
        output["reporting"] = {
            "executive_summary": summary,
            "detailed_report": report,
            "presentation_slides": slides,
        }

        # Optional bridge call
        try:
            response = await self.call_manuscript_service(
                service_name="manuscript",
                method_name="runStageImpactAssessment",
                params={
                    "job_id": context.job_id,
                    "governance_mode": context.governance_mode,
                    "config": config,
                    "inputs": inputs,
                    "stage_id": self.stage_id,
                    "stage_name": self.stage_name,
                    "impact_output": output,
                },
            )
            if response:
                output["bridge_response"] = response
        except Exception as e:
            logger.warning(f"Bridge runStageImpactAssessment failed: {type(e).__name__}: {e}")
            warnings.append(f"Bridge call failed: {str(e)}. Proceeding with in-memory output.")

        status = "failed" if errors else "completed"
        if context.governance_mode == "DEMO":
            output["demo_mode"] = True
            warnings.append("Running in DEMO mode - impact assessment is simulated")

        return self.create_stage_result(
            context=context,
            status=status,
            started_at=started_at,
            output=output,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "metric_categories": list(DEFAULT_METRIC_WEIGHTS.keys()),
            },
        )
