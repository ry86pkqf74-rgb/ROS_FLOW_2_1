"""
Statistical Rationale Generator

Features:
- Auto-generated methodology sections for manuscripts
- Decision tree documentation (Mermaid diagrams)
- Assumption test narratives
- Natural language summaries via LLM
- Audit trail export for compliance

This module is designed to be self-contained and flexible. It accepts loosely
structured model configuration and test results dictionaries, then produces
stable, compliance-friendly narratives that can be attached to analysis outputs.
The generator does not assume specific modeling libraries; it is intended to
work with a wide range of statistical workflows.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Iterable, Tuple
from datetime import datetime
import json
import logging
import csv
import io
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class StatisticalDecision:
    decision_type: str  # model_selection, variable_selection, test_choice
    chosen_option: str
    alternatives_considered: List[str]
    rationale: str
    evidence: Dict[str, Any]  # test statistics, p-values, AIC/BIC
    timestamp: str
    user_id: Optional[str] = None


@dataclass
class MethodologySection:
    title: str
    content: str
    citations: List[str]
    assumptions_stated: List[str]
    limitations_noted: List[str]


@dataclass
class AssumptionTestResult:
    name: str
    test: str
    statistic: Optional[float] = None
    p_value: Optional[float] = None
    passed: Optional[bool] = None
    context: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class AuditTrailExport:
    generated_at: str
    decision_count: int
    decisions: List[Dict[str, Any]]
    hash_chain: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)


DEFAULT_ASSUMPTION_LIBRARY: Dict[str, str] = {
    "normality": (
        "Residuals were assessed for approximate normality using formal tests "
        "and visual diagnostics to ensure model validity."
    ),
    "homoscedasticity": (
        "Homoscedasticity was evaluated by inspecting residual variance patterns "
        "and applying formal variance tests where appropriate."
    ),
    "independence": (
        "Independence of observations was assumed based on study design and "
        "confirmed through residual autocorrelation checks."
    ),
    "linearity": (
        "Linearity between predictors and outcome was evaluated using partial "
        "residual plots and model diagnostics."
    ),
    "proportional_hazards": (
        "The proportional hazards assumption was assessed using scaled residual "
        "diagnostics and time-varying checks."
    ),
    "multicollinearity": (
        "Multicollinearity was screened using variance inflation factors and "
        "pairwise correlation checks."
    ),
    "missing_at_random": (
        "Missingness was evaluated for patterns consistent with missing at random "
        "assumptions prior to imputation or exclusion."
    ),
    "model_convergence": (
        "Model convergence was verified through algorithm status indicators and "
        "stability across iterations."
    ),
    "outlier_influence": (
        "Influential observations were assessed with leverage and influence "
        "metrics to ensure robustness."
    ),
}

DEFAULT_LIMITATIONS_LIBRARY: Dict[str, str] = {
    "sample_size": (
        "Sample size may limit precision of estimates and power for detecting "
        "small effect sizes."
    ),
    "missing_data": (
        "Missing data could introduce bias if missingness mechanisms deviate "
        "from stated assumptions."
    ),
    "generalizability": (
        "Findings may not generalize beyond the study population and settings."
    ),
    "measurement_error": (
        "Measurement error in exposure or outcome variables could attenuate "
        "estimated associations."
    ),
    "unmeasured_confounding": (
        "Unmeasured confounding cannot be fully excluded despite adjustment."
    ),
    "model_specification": (
        "Model specification choices may affect results; alternative models may "
        "produce different estimates."
    ),
    "multiple_testing": (
        "Multiple testing may inflate type I error; interpret marginal findings "
        "with caution."
    ),
}


class StatisticalRationaleGenerator:
    """Generates human-readable statistical methodology documentation."""

    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.decisions: List[StatisticalDecision] = []

    def record_decision(self, decision: StatisticalDecision) -> None:
        """Record a statistical decision for audit trail."""
        normalized = self._normalize_decision(decision)
        self.decisions.append(normalized)
        logger.debug(
            "Recorded statistical decision", extra={"decision": asdict(normalized)}
        )

    def generate_methodology_section(
        self,
        analysis_type: str,
        model_config: Dict,
        test_results: Dict
    ) -> MethodologySection:
        """Generate manuscript-ready methodology section."""
        analysis_type = (analysis_type or "analysis").strip()
        model_config = model_config or {}
        test_results = test_results or {}

        overview_lines = self._render_analysis_overview(analysis_type, model_config)
        model_lines = self._render_model_specification(model_config)
        assumption_block, assumptions_list = self._render_assumption_tests(test_results)
        fit_lines = self._render_fit_diagnostics(test_results)
        sensitivity_lines = self._render_sensitivity_checks(model_config, test_results)
        decision_lines = self._render_decision_rationale()

        limitations_list = self._collect_limitations(model_config, test_results)
        limitations_lines = self._render_limitations(limitations_list)

        citations = self._collect_citations(model_config, test_results)

        content_parts: List[str] = []
        content_parts.extend(overview_lines)
        if model_lines:
            content_parts.append("Model specification:")
            content_parts.extend(self._indent_lines(model_lines))
        if assumption_block:
            content_parts.append("Assumption checks:")
            content_parts.extend(self._indent_lines(assumption_block))
        if fit_lines:
            content_parts.append("Model fit and diagnostics:")
            content_parts.extend(self._indent_lines(fit_lines))
        if sensitivity_lines:
            content_parts.append("Sensitivity and robustness:")
            content_parts.extend(self._indent_lines(sensitivity_lines))
        if decision_lines:
            content_parts.append("Decision rationale:")
            content_parts.extend(self._indent_lines(decision_lines))
        if limitations_lines:
            content_parts.append("Limitations:")
            content_parts.extend(self._indent_lines(limitations_lines))

        content = "\n".join([line for line in content_parts if line])

        title = f"Statistical Methods ({analysis_type.title()})"
        return MethodologySection(
            title=title,
            content=content,
            citations=citations,
            assumptions_stated=assumptions_list,
            limitations_noted=limitations_list,
        )

    def generate_decision_tree_diagram(self) -> str:
        """Generate Mermaid diagram of decision flow."""
        if not self.decisions:
            return "flowchart TD\n  Start([\"No decisions recorded\"])"

        ordered = self._sort_decisions(self.decisions)
        lines: List[str] = ["flowchart TD"]
        lines.append("  Start([\"Start\"])")

        prev_id = "Start"
        for idx, decision in enumerate(ordered, start=1):
            node_id = f"D{idx}"
            label = self._sanitize_mermaid_label(
                f"{decision.decision_type}: {decision.chosen_option}"
            )
            lines.append(f"  {node_id}[\"{label}\"]")
            lines.append(f"  {prev_id} --> {node_id}")

            if decision.alternatives_considered:
                for alt_idx, alt in enumerate(decision.alternatives_considered, start=1):
                    alt_id = f"{node_id}_A{alt_idx}"
                    alt_label = self._sanitize_mermaid_label(f"Alt: {alt}")
                    lines.append(f"  {alt_id}([\"{alt_label}\"]):::alt")
                    lines.append(f"  {node_id} -.-> {alt_id}")

            prev_id = node_id

        lines.append("  classDef alt fill:#f8f8f8,stroke:#999,stroke-dasharray: 3 3;")
        return "\n".join(lines)

    def generate_natural_language_summary(
        self,
        detail_level: str = "brief"  # brief, detailed, technical
    ) -> str:
        """Use LLM to generate readable summary."""
        detail_level = (detail_level or "brief").strip().lower()
        summary_context = self._build_summary_context(detail_level)

        if self.llm:
            llm_text = self._llm_generate_summary(summary_context, detail_level)
            if llm_text:
                return llm_text

        return self._build_summary_fallback(summary_context, detail_level)

    def export_audit_trail(self, format: str = "json") -> str:
        """Export decision log for IRB/compliance."""
        export_format = (format or "json").strip().lower()
        export_data = self._build_audit_export_payload()

        if export_format in {"json", "application/json"}:
            return self._export_json(export_data)
        if export_format in {"jsonl", "ndjson"}:
            return self._export_jsonl(export_data)
        if export_format == "csv":
            return self._export_csv(export_data)
        if export_format in {"md", "markdown"}:
            return self._export_markdown(export_data)
        if export_format in {"txt", "text"}:
            return self._export_text(export_data)

        raise ValueError(f"Unsupported export format: {format}")

    def _normalize_decision(self, decision: StatisticalDecision) -> StatisticalDecision:
        timestamp = decision.timestamp or self._now_iso()
        alternatives = decision.alternatives_considered or []
        evidence = decision.evidence or {}
        return StatisticalDecision(
            decision_type=(decision.decision_type or "unspecified").strip(),
            chosen_option=(decision.chosen_option or "unspecified").strip(),
            alternatives_considered=[str(x) for x in alternatives],
            rationale=(decision.rationale or "No rationale provided.").strip(),
            evidence=evidence,
            timestamp=timestamp,
            user_id=decision.user_id,
        )

    def _render_analysis_overview(self, analysis_type: str, model_config: Dict[str, Any]) -> List[str]:
        overview: List[str] = []
        dataset = model_config.get("dataset") or model_config.get("data") or {}
        sample_size = model_config.get("sample_size") or dataset.get("sample_size")
        outcome = model_config.get("outcome") or model_config.get("dependent_variable")
        exposure = model_config.get("exposure") or model_config.get("primary_exposure")

        overview.append(
            f"We conducted a {analysis_type} analysis to evaluate associations "
            "between specified predictors and outcomes."
        )

        if outcome:
            overview.append(f"Primary outcome: {outcome}.")
        if exposure:
            overview.append(f"Primary exposure: {exposure}.")
        if sample_size:
            overview.append(f"Sample size: {sample_size} observations.")

        study_design = model_config.get("study_design")
        if study_design:
            overview.append(f"Study design: {study_design}.")

        return overview

    def _render_model_specification(self, model_config: Dict[str, Any]) -> List[str]:
        lines: List[str] = []

        model_name = model_config.get("model") or model_config.get("model_name")
        if model_name:
            lines.append(f"Model: {model_name}.")

        formula = model_config.get("formula")
        if formula:
            lines.append(f"Formula: {formula}.")

        variables = self._ensure_list(model_config.get("variables"))
        covariates = self._ensure_list(model_config.get("covariates"))
        if variables:
            lines.append(f"Predictors: {', '.join(variables)}.")
        if covariates:
            lines.append(f"Covariates: {', '.join(covariates)}.")

        interaction_terms = self._ensure_list(model_config.get("interactions"))
        if interaction_terms:
            lines.append(f"Interactions modeled: {', '.join(interaction_terms)}.")

        random_effects = self._ensure_list(model_config.get("random_effects"))
        fixed_effects = self._ensure_list(model_config.get("fixed_effects"))
        if random_effects:
            lines.append(f"Random effects: {', '.join(random_effects)}.")
        if fixed_effects:
            lines.append(f"Fixed effects: {', '.join(fixed_effects)}.")

        link_function = model_config.get("link")
        family = model_config.get("family")
        if family:
            lines.append(f"Distribution family: {family}.")
        if link_function:
            lines.append(f"Link function: {link_function}.")

        estimation = model_config.get("estimation") or model_config.get("estimator")
        if estimation:
            lines.append(f"Estimation method: {estimation}.")

        weights = model_config.get("weights")
        if weights:
            lines.append("Weights were applied to account for sampling or imbalance.")

        transforms = self._ensure_list(model_config.get("transformations"))
        if transforms:
            lines.append(f"Transformations applied: {', '.join(transforms)}.")

        standardization = model_config.get("standardization")
        if standardization:
            lines.append(f"Standardization: {standardization}.")

        missing_data = model_config.get("missing_data")
        if missing_data:
            lines.append(f"Missing data handling: {missing_data}.")

        imputation = model_config.get("imputation")
        if imputation:
            lines.append(f"Imputation strategy: {imputation}.")

        software = model_config.get("software")
        if software:
            lines.append(f"Software: {software}.")

        return lines

    def _render_assumption_tests(self, test_results: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        assumptions: List[str] = []
        lines: List[str] = []

        raw_assumptions = test_results.get("assumptions")
        parsed_results: List[AssumptionTestResult] = []

        if isinstance(raw_assumptions, list):
            for item in raw_assumptions:
                parsed = self._parse_assumption_entry(item)
                if parsed:
                    parsed_results.append(parsed)
        elif isinstance(raw_assumptions, dict):
            for name, entry in raw_assumptions.items():
                parsed = self._parse_assumption_entry(entry, name_override=name)
                if parsed:
                    parsed_results.append(parsed)

        if parsed_results:
            for result in parsed_results:
                assumptions.append(result.name)
                narrative = self._format_assumption_narrative(result)
                if narrative:
                    lines.append(narrative)
        else:
            assumptions_from_config = self._ensure_list(test_results.get("assumptions_stated"))
            for name in assumptions_from_config:
                assumptions.append(name)
                default_text = DEFAULT_ASSUMPTION_LIBRARY.get(name.lower())
                if default_text:
                    lines.append(default_text)

        return lines, assumptions

    def _render_fit_diagnostics(self, test_results: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        fit = test_results.get("fit") or {}
        diagnostics = test_results.get("diagnostics") or {}

        metrics = []
        for key in ["r2", "adj_r2", "aic", "bic", "rmse", "mae", "log_likelihood"]:
            value = fit.get(key)
            if value is not None:
                metrics.append(f"{key.upper()}={self._format_value(value)}")

        if metrics:
            lines.append("Fit metrics: " + ", ".join(metrics) + ".")

        if diagnostics:
            for name, value in diagnostics.items():
                if isinstance(value, dict):
                    detail = ", ".join(
                        f"{k}={self._format_value(v)}" for k, v in value.items()
                    )
                    lines.append(f"{name}: {detail}.")
                else:
                    lines.append(f"{name}: {self._format_value(value)}.")

        return lines

    def _render_sensitivity_checks(self, model_config: Dict[str, Any], test_results: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        sensitivity = model_config.get("sensitivity") or test_results.get("sensitivity")
        if isinstance(sensitivity, list):
            lines.extend([str(item) for item in sensitivity])
        elif isinstance(sensitivity, dict):
            for key, value in sensitivity.items():
                if isinstance(value, dict):
                    detail = ", ".join(
                        f"{k}={self._format_value(v)}" for k, v in value.items()
                    )
                    lines.append(f"{key}: {detail}.")
                else:
                    lines.append(f"{key}: {self._format_value(value)}.")
        elif sensitivity:
            lines.append(str(sensitivity))

        robustness = model_config.get("robustness") or test_results.get("robustness")
        if isinstance(robustness, list):
            lines.extend([str(item) for item in robustness])
        elif isinstance(robustness, dict):
            for key, value in robustness.items():
                lines.append(f"{key}: {self._format_value(value)}.")
        elif robustness:
            lines.append(str(robustness))

        return lines

    def _render_decision_rationale(self) -> List[str]:
        lines: List[str] = []
        for decision in self._sort_decisions(self.decisions):
            evidence_summary = self._format_evidence(decision.evidence)
            line = (
                f"{decision.decision_type} - chose {decision.chosen_option}; "
                f"rationale: {decision.rationale}"
            )
            if evidence_summary:
                line += f" (evidence: {evidence_summary})"
            lines.append(line + ".")

        return lines

    def _render_limitations(self, limitations: List[str]) -> List[str]:
        lines: List[str] = []
        for item in limitations:
            default_text = DEFAULT_LIMITATIONS_LIBRARY.get(item.lower())
            lines.append(default_text or item)
        return lines

    def _collect_citations(self, model_config: Dict[str, Any], test_results: Dict[str, Any]) -> List[str]:
        citations: List[str] = []
        citations.extend(self._ensure_list(model_config.get("citations")))
        citations.extend(self._ensure_list(test_results.get("citations")))

        unique: List[str] = []
        for item in citations:
            if item and item not in unique:
                unique.append(item)
        return unique

    def _collect_limitations(self, model_config: Dict[str, Any], test_results: Dict[str, Any]) -> List[str]:
        limitations: List[str] = []
        limitations.extend(self._ensure_list(model_config.get("limitations")))
        limitations.extend(self._ensure_list(test_results.get("limitations")))

        if not limitations:
            return []

        unique: List[str] = []
        for item in limitations:
            if item and item not in unique:
                unique.append(item)
        return unique

    def _parse_assumption_entry(
        self, entry: Any, name_override: Optional[str] = None
    ) -> Optional[AssumptionTestResult]:
        if entry is None:
            return None

        if isinstance(entry, AssumptionTestResult):
            return entry

        if isinstance(entry, dict):
            name = name_override or entry.get("name") or "assumption"
            return AssumptionTestResult(
                name=str(name),
                test=str(entry.get("test", "")),
                statistic=self._coerce_float(entry.get("statistic")),
                p_value=self._coerce_float(entry.get("p_value")),
                passed=entry.get("passed"),
                context=entry.get("context"),
                notes=entry.get("notes"),
            )

        if isinstance(entry, str):
            return AssumptionTestResult(name=entry, test="")

        return None

    def _format_assumption_narrative(self, result: AssumptionTestResult) -> str:
        name = result.name
        test_name = result.test or "assumption test"
        statistic = self._format_value(result.statistic) if result.statistic is not None else None
        p_value = self._format_p_value(result.p_value)

        parts = [f"{name} assessed using {test_name}"]
        if statistic is not None:
            parts.append(f"statistic={statistic}")
        if p_value is not None:
            parts.append(f"p={p_value}")
        if result.passed is True:
            parts.append("passed")
        elif result.passed is False:
            parts.append("did not pass")

        narrative = ", ".join(parts)
        if result.context:
            narrative += f" ({result.context})"
        if result.notes:
            narrative += f". {result.notes}"
        return narrative + "."

    def _build_summary_context(self, detail_level: str) -> Dict[str, Any]:
        return {
            "detail_level": detail_level,
            "decision_count": len(self.decisions),
            "decisions": [self._decision_to_dict(d) for d in self._sort_decisions(self.decisions)],
        }

    def _llm_generate_summary(self, context: Dict[str, Any], detail_level: str) -> Optional[str]:
        prompt = self._build_llm_prompt(context, detail_level)
        if not prompt:
            return None

        for method_name in ["generate", "complete", "chat", "invoke"]:
            if hasattr(self.llm, method_name):
                try:
                    method = getattr(self.llm, method_name)
                    response = method(prompt)
                    return self._normalize_llm_response(response)
                except Exception as exc:
                    logger.warning("LLM generation failed", exc_info=exc)

        return None

    def _normalize_llm_response(self, response: Any) -> Optional[str]:
        if response is None:
            return None

        if isinstance(response, str):
            return response.strip()

        if isinstance(response, dict):
            for key in ["text", "content", "message", "output"]:
                value = response.get(key)
                if isinstance(value, str):
                    return value.strip()

        if hasattr(response, "text"):
            value = getattr(response, "text")
            if isinstance(value, str):
                return value.strip()

        if hasattr(response, "content"):
            value = getattr(response, "content")
            if isinstance(value, str):
                return value.strip()

        return None

    def _build_llm_prompt(self, context: Dict[str, Any], detail_level: str) -> str:
        decisions = context.get("decisions", [])
        if not decisions:
            return (
                "Provide a brief summary of the statistical workflow. "
                "Note that no decisions were recorded."
            )

        decision_text = "\n".join(
            f"- {d.get('decision_type')}: {d.get('chosen_option')} (rationale: {d.get('rationale')})"
            for d in decisions
        )

        return (
            "You are preparing a statistical rationale summary for a research audit.\n"
            f"Detail level: {detail_level}.\n"
            "Summarize the major decisions, their rationale, and any evidence provided.\n"
            "Use clear, professional language suitable for compliance documentation.\n"
            "Decisions:\n"
            f"{decision_text}\n"
        )

    def _build_summary_fallback(self, context: Dict[str, Any], detail_level: str) -> str:
        decisions = context.get("decisions", [])
        if not decisions:
            return "No statistical decisions have been recorded for this analysis."

        summary_lines: List[str] = []
        summary_lines.append(
            f"Recorded {len(decisions)} statistical decisions ({detail_level} summary)."
        )

        if detail_level == "brief":
            for decision in decisions[:3]:
                summary_lines.append(
                    f"{decision.get('decision_type')} -> {decision.get('chosen_option')}."
                )
            if len(decisions) > 3:
                summary_lines.append("Additional decisions documented in audit trail.")
        else:
            for decision in decisions:
                evidence = decision.get("evidence_summary")
                rationale = decision.get("rationale")
                line = f"{decision.get('decision_type')}: {decision.get('chosen_option')}."
                if rationale:
                    line += f" Rationale: {rationale}."
                if evidence:
                    line += f" Evidence: {evidence}."
                summary_lines.append(line)

        return " ".join(summary_lines)

    def _build_audit_export_payload(self) -> AuditTrailExport:
        decisions = [self._decision_to_dict(d) for d in self._sort_decisions(self.decisions)]
        hash_chain = self._build_hash_chain(decisions)

        return AuditTrailExport(
            generated_at=self._now_iso(),
            decision_count=len(decisions),
            decisions=decisions,
            hash_chain=hash_chain,
            metadata={
                "generator": "StatisticalRationaleGenerator",
                "version": "1.0",
            },
        )

    def _export_json(self, export_data: AuditTrailExport) -> str:
        payload = asdict(export_data)
        return json.dumps(payload, indent=2, default=str)

    def _export_jsonl(self, export_data: AuditTrailExport) -> str:
        output = io.StringIO()
        for decision in export_data.decisions:
            output.write(json.dumps(decision, default=str) + "\n")
        return output.getvalue()

    def _export_csv(self, export_data: AuditTrailExport) -> str:
        output = io.StringIO()
        fieldnames = [
            "decision_type",
            "chosen_option",
            "alternatives_considered",
            "rationale",
            "evidence",
            "timestamp",
            "user_id",
            "evidence_summary",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for decision in export_data.decisions:
            row = {key: decision.get(key) for key in fieldnames}
            writer.writerow(row)
        return output.getvalue()

    def _export_markdown(self, export_data: AuditTrailExport) -> str:
        lines: List[str] = []
        lines.append(f"# Statistical Audit Trail")
        lines.append("")
        lines.append(f"Generated at: {export_data.generated_at}")
        lines.append(f"Decision count: {export_data.decision_count}")
        lines.append("")
        lines.append("## Decisions")
        lines.append("")
        lines.append(
            "| Type | Chosen Option | Rationale | Evidence Summary | Timestamp |"
        )
        lines.append("| --- | --- | --- | --- | --- |")
        for decision in export_data.decisions:
            lines.append(
                "| {decision_type} | {chosen_option} | {rationale} | {evidence_summary} | {timestamp} |".format(
                    decision_type=self._escape_markdown(decision.get("decision_type", "")),
                    chosen_option=self._escape_markdown(decision.get("chosen_option", "")),
                    rationale=self._escape_markdown(decision.get("rationale", "")),
                    evidence_summary=self._escape_markdown(decision.get("evidence_summary", "")),
                    timestamp=self._escape_markdown(decision.get("timestamp", "")),
                )
            )

        lines.append("")
        lines.append("## Hash Chain")
        lines.append("")
        lines.append("| Index | Hash | Previous Hash |")
        lines.append("| --- | --- | --- |")
        for idx, entry in enumerate(export_data.hash_chain, start=1):
            lines.append(
                f"| {idx} | {entry.get('hash')} | {entry.get('prev_hash')} |"
            )

        return "\n".join(lines)

    def _export_text(self, export_data: AuditTrailExport) -> str:
        lines: List[str] = []
        lines.append("Statistical Audit Trail")
        lines.append(f"Generated at: {export_data.generated_at}")
        lines.append(f"Decision count: {export_data.decision_count}")
        lines.append("")
        for idx, decision in enumerate(export_data.decisions, start=1):
            lines.append(f"Decision {idx}")
            lines.append(f"  Type: {decision.get('decision_type')}")
            lines.append(f"  Chosen option: {decision.get('chosen_option')}")
            if decision.get("alternatives_considered"):
                lines.append(
                    f"  Alternatives: {', '.join(decision.get('alternatives_considered', []))}"
                )
            lines.append(f"  Rationale: {decision.get('rationale')}")
            if decision.get("evidence_summary"):
                lines.append(f"  Evidence: {decision.get('evidence_summary')}")
            lines.append(f"  Timestamp: {decision.get('timestamp')}")
            if decision.get("user_id"):
                lines.append(f"  User ID: {decision.get('user_id')}")
            lines.append("")

        return "\n".join(lines)

    def _build_hash_chain(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        chain: List[Dict[str, str]] = []
        previous_hash = self._hash_payload("GENESIS")

        for decision in decisions:
            payload = json.dumps(decision, sort_keys=True, default=str)
            current_hash = self._hash_payload(payload + previous_hash)
            chain.append({"hash": current_hash, "prev_hash": previous_hash})
            previous_hash = current_hash

        return chain

    def _decision_to_dict(self, decision: StatisticalDecision) -> Dict[str, Any]:
        data = asdict(decision)
        data["evidence_summary"] = self._format_evidence(decision.evidence)
        return data

    def _format_evidence(self, evidence: Dict[str, Any]) -> str:
        if not evidence:
            return ""

        parts: List[str] = []
        for key, value in evidence.items():
            if isinstance(value, dict):
                nested = ", ".join(
                    f"{k}={self._format_value(v)}" for k, v in value.items()
                )
                parts.append(f"{key}({nested})")
            else:
                parts.append(f"{key}={self._format_value(value)}")

        return "; ".join(parts)

    def _format_value(self, value: Any) -> str:
        if value is None:
            return "n/a"
        if isinstance(value, float):
            return f"{value:.4f}".rstrip("0").rstrip(".")
        return str(value)

    def _format_p_value(self, value: Optional[float]) -> Optional[str]:
        if value is None:
            return None
        try:
            if value < 0.001:
                return "<0.001"
            return f"{value:.3f}".rstrip("0").rstrip(".")
        except Exception:
            return None

    def _ensure_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        if isinstance(value, tuple):
            return [str(item) for item in value if item is not None]
        if isinstance(value, set):
            return [str(item) for item in value if item is not None]
        return [str(value)]

    def _indent_lines(self, lines: Iterable[str]) -> List[str]:
        return [f"  {line}" for line in lines if line]

    def _sort_decisions(self, decisions: List[StatisticalDecision]) -> List[StatisticalDecision]:
        def parse_ts(ts: str) -> Tuple[int, str]:
            try:
                return (int(datetime.fromisoformat(ts).timestamp()), ts)
            except Exception:
                return (0, ts)

        return sorted(decisions, key=lambda d: parse_ts(d.timestamp))

    def _sanitize_mermaid_label(self, label: str) -> str:
        cleaned = label.replace("\"", "'")
        cleaned = cleaned.replace("\n", " ")
        cleaned = cleaned.replace("\r", " ")
        return cleaned

    def _escape_markdown(self, text: str) -> str:
        return (
            text.replace("|", "\\|")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    def _hash_payload(self, payload: str) -> str:
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _coerce_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except Exception:
            return None
