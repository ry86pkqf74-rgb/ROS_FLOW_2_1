"""
Stage 06: Study Design

StudyDesignAgent designs study protocol based on refined hypothesis (Stage 4):
- Select methodology (RCT, cohort, case-control, cross-sectional, etc.)
- Define primary and secondary endpoints
- Calculate sample size / power analysis
- Generate methods section content via bridge (methods-populator, claude-writer)
"""

import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stage_06_study_design")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")

# Study design types and methodology options
STUDY_TYPES = [
    "randomized_controlled_trial",
    "cohort",
    "case_control",
    "cross_sectional",
    "observational",
    "systematic_review",
]


@register_stage
class StudyDesignAgent(BaseStageAgent):
    """Stage 6: Study Design - Design study protocol from refined hypothesis."""

    stage_id = 6
    stage_name = "Study Design"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the StudyDesignAgent.

        Args:
            config: Optional configuration dict. If None, uses defaults.
        """
        bridge_config = None
        if config and "bridge_url" in config:
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0)
            )
        super().__init__(bridge_config=bridge_config)

    def get_tools(self) -> List[Any]:
        """Get LangChain tools available to this stage."""
        if not LANGCHAIN_AVAILABLE:
            return []
        return [
            Tool(
                name="design_study_protocol",
                description="Design study protocol from hypothesis and context (study type, design description)",
                func=self._design_study_protocol_tool
            ),
            Tool(
                name="select_methodology",
                description="Select appropriate methodology: RCT, cohort, case-control, cross-sectional, etc.",
                func=self._select_methodology_tool
            ),
            Tool(
                name="define_endpoints",
                description="Define primary and secondary endpoints (JSON: primary list, secondary list)",
                func=self._define_endpoints_tool
            ),
            Tool(
                name="calculate_sample_size",
                description="Calculate sample size and power (n, power, alpha). Input: JSON with effect_size, alpha, power",
                func=self._calculate_sample_size_tool
            ),
            Tool(
                name="generate_methods_outline",
                description="Generate methods section outline from study design and methodology",
                func=self._generate_methods_outline_tool
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for study design."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        from langchain_core.prompts import PromptTemplate
        return PromptTemplate.from_template("""You are a Study Design Specialist for clinical research.

Your task is to design the study protocol based on:
1. Refined hypothesis from Stage 4
2. Key variables (independent, dependent, confounding)
3. Appropriate methodology and endpoints
4. Sample size / power considerations

Refined Hypothesis: {refined_hypothesis}

Key Variables:
- Independent: {key_variables_independent}
- Dependent: {key_variables_dependent}
- Confounding: {key_variables_confounding}

Methodology: {methodology}

Endpoints: {endpoints}

Sample Size: {sample_size}

Your goal is to:
1. Design study protocol (type, methodology)
2. Select appropriate methodology (RCT, cohort, case-control, etc.)
3. Define primary and secondary endpoints
4. Calculate sample size / power
5. Generate methods section outline

Input Request:
{input}

Previous Agent Scratchpad:
{agent_scratchpad}
""")

    async def execute(self, context: StageContext) -> StageResult:
        """Execute study design workflow."""
        started_at = datetime.utcnow()
        output: Dict[str, Any] = {}
        artifacts: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # 1. Get Stage 4 output (refined hypothesis, key variables)
            stage4_output = context.get_prior_stage_output(4)
            if not stage4_output and context.governance_mode != "DEMO":
                errors.append("Stage 4 (Hypothesis Refinement) output not found. Study design requires refined hypothesis.")
                return self.create_stage_result(
                    context=context,
                    status="failed",
                    started_at=started_at.isoformat() + "Z",
                    errors=errors,
                )
            if not stage4_output:
                warnings.append("Stage 4 output not found. Proceeding with config-only context.")

            refined_hypothesis = (stage4_output or {}).get("refined_hypothesis") or (context.config or {}).get("hypothesis") or "To investigate the relationship between study variables and outcomes"
            key_variables = (stage4_output or {}).get("key_variables") or {
                "independent": [],
                "dependent": [],
                "confounding": [],
            }
            output["refined_hypothesis"] = refined_hypothesis
            output["key_variables"] = key_variables

            # 2. Design study protocol and select methodology
            study_type, methodology = self._design_protocol_and_methodology(refined_hypothesis, key_variables)
            output["study_type"] = study_type
            output["methodology"] = methodology

            # 3. Define endpoints
            endpoints = self._define_endpoints(refined_hypothesis, key_variables)
            output["endpoints"] = endpoints

            # 4. Calculate sample size
            sample_size = self._calculate_sample_size(refined_hypothesis, key_variables)
            output["sample_size"] = sample_size

            # 5. Call methods-populator (populateMethods)
            manuscript_id = (context.config or {}).get("manuscript_id") or context.job_id
            dataset_ids = (context.config or {}).get("dataset_ids") or [context.job_id]
            methods_outline = ""
            try:
                populator_result = await self.call_manuscript_service(
                    "methods-populator",
                    "populateMethods",
                    {
                        "manuscriptId": manuscript_id,
                        "datasetIds": dataset_ids,
                        "studyDesign": study_type,
                        "statisticalMethods": methodology.get("statistical_methods", []),
                    }
                )
                methods_outline = populator_result.get("fullText", "") or json.dumps(populator_result.get("sections", {}))
            except Exception as e:
                logger.warning(f"methods-populator call failed: {e}")
                warnings.append(f"Methods populator unavailable: {str(e)}. Using local outline.")

            # 6. Optionally enrich with claude-writer for methods paragraph
            if not methods_outline and not errors:
                try:
                    para_result = await self.call_manuscript_service(
                        "claude-writer",
                        "generateParagraph",
                        {
                            "prompt": f"Write a brief methods outline for a {study_type} study.",
                            "context": refined_hypothesis,
                            "section": "methods",
                            "keyPoints": list(endpoints.get("primary", []))[:3],
                            "tone": "formal",
                        }
                    )
                    methods_outline = para_result.get("paragraph", "") or para_result.get("content", "")
                except Exception as e:
                    logger.warning(f"claude-writer call failed: {e}")

            if not methods_outline:
                methods_outline = self._generate_methods_outline(study_type, methodology, endpoints, sample_size)
            output["methods_outline"] = methods_outline

            # 7. Build study_design output shape
            output["study_design"] = {
                "type": study_type,
                "methodology": methodology,
                "endpoints": endpoints,
                "sample_size": sample_size,
                "methods_outline": methods_outline,
            }

            # 8. Save artifact
            artifact_path = self._save_study_design(context, output)
            artifacts.append(artifact_path)

        except Exception as e:
            logger.error(f"Study design failed: {e}", exc_info=True)
            errors.append(f"Study design failed: {str(e)}")

        return self.create_stage_result(
            context=context,
            status="failed" if errors else "completed",
            started_at=started_at.isoformat() + "Z",
            output=output,
            artifacts=artifacts,
            errors=errors,
            warnings=warnings,
            metadata={
                "governance_mode": context.governance_mode,
                "study_type": output.get("study_type", ""),
            },
        )

    # =========================================================================
    # Helper logic (used by execute and tools)
    # =========================================================================

    def _design_protocol_and_methodology(
        self, hypothesis: str, key_variables: Dict[str, List[str]]
    ) -> tuple[str, Dict[str, Any]]:
        """Design protocol and select methodology from hypothesis and variables."""
        hypothesis_lower = hypothesis.lower()
        study_type = "observational"
        if "random" in hypothesis_lower or "trial" in hypothesis_lower or "intervention" in hypothesis_lower:
            study_type = "randomized_controlled_trial"
        elif "cohort" in hypothesis_lower or "follow" in hypothesis_lower:
            study_type = "cohort"
        elif "case" in hypothesis_lower and "control" in hypothesis_lower:
            study_type = "case_control"
        elif "cross" in hypothesis_lower or "survey" in hypothesis_lower:
            study_type = "cross_sectional"
        methodology = {
            "design": study_type.replace("_", " ").title(),
            "statistical_methods": ["descriptive statistics", "inferential testing"],
            "analysis_plan": "Primary analysis will assess primary endpoints; secondary analysis will include sensitivity and subgroup analyses.",
        }
        return study_type, methodology

    def _define_endpoints(
        self, hypothesis: str, key_variables: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """Define primary and secondary endpoints."""
        primary = list(key_variables.get("dependent", []))[:3] or ["Primary outcome"]
        secondary = list(key_variables.get("confounding", []))[:2] or ["Secondary outcome 1", "Secondary outcome 2"]
        return {"primary": primary, "secondary": secondary}

    def _calculate_sample_size(
        self, hypothesis: str, key_variables: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Calculate sample size / power (placeholder values)."""
        n = 200
        power = 0.8
        alpha = 0.05
        return {"n": n, "power": power, "alpha": alpha, "rationale": "Standard 80% power, alpha=0.05"}

    def _generate_methods_outline(
        self,
        study_type: str,
        methodology: Dict[str, Any],
        endpoints: Dict[str, List[str]],
        sample_size: Dict[str, Any],
    ) -> str:
        """Generate methods outline locally."""
        parts = [
            f"Study Design: {study_type.replace('_', ' ').title()}.",
            f"Primary endpoints: {', '.join(endpoints.get('primary', []))}.",
            f"Secondary endpoints: {', '.join(endpoints.get('secondary', []))}.",
            f"Sample size: n={sample_size.get('n', 200)} (power={sample_size.get('power', 0.8)}, alpha={sample_size.get('alpha', 0.05)}).",
            f"Statistical methods: {', '.join(methodology.get('statistical_methods', []))}.",
        ]
        return " ".join(parts)

    def _save_study_design(self, context: StageContext, output: Dict[str, Any]) -> str:
        """Save study design to JSON artifact."""
        artifact_path = os.path.join(context.artifact_path, "study_design.json")
        os.makedirs(context.artifact_path, exist_ok=True)
        artifact_data = {
            "schema_version": "1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "study_design": output.get("study_design", {}),
            "refined_hypothesis": output.get("refined_hypothesis"),
            "key_variables": output.get("key_variables", {}),
        }
        with open(artifact_path, "w") as f:
            json.dump(artifact_data, f, indent=2, default=str)
        return artifact_path

    # =========================================================================
    # Tool implementations (wrappers for LangChain)
    # =========================================================================

    def _design_study_protocol_tool(self, hypothesis_and_vars_json: str) -> str:
        """Tool: design study protocol from hypothesis and variables JSON."""
        try:
            data = json.loads(hypothesis_and_vars_json) if isinstance(hypothesis_and_vars_json, str) else hypothesis_and_vars_json
            hypothesis = data.get("hypothesis", "To investigate study variables.")
            key_variables = data.get("key_variables", {})
            study_type, methodology = self._design_protocol_and_methodology(hypothesis, key_variables)
            return json.dumps({"study_type": study_type, "methodology": methodology}, indent=2)
        except Exception as e:
            return f"Failed to design protocol: {str(e)}"

    def _select_methodology_tool(self, hypothesis: str) -> str:
        """Tool: select methodology from hypothesis text."""
        try:
            study_type, methodology = self._design_protocol_and_methodology(hypothesis, {})
            return json.dumps({"study_type": study_type, "methodology": methodology}, indent=2)
        except Exception as e:
            return f"Failed to select methodology: {str(e)}"

    def _define_endpoints_tool(self, hypothesis_and_vars_json: str) -> str:
        """Tool: define primary and secondary endpoints."""
        try:
            data = json.loads(hypothesis_and_vars_json) if isinstance(hypothesis_and_vars_json, str) else hypothesis_and_vars_json
            hypothesis = data.get("hypothesis", "")
            key_variables = data.get("key_variables", {})
            endpoints = self._define_endpoints(hypothesis, key_variables)
            return json.dumps(endpoints, indent=2)
        except Exception as e:
            return f"Failed to define endpoints: {str(e)}"

    def _calculate_sample_size_tool(self, params_json: str) -> str:
        """Tool: calculate sample size from params (effect_size, alpha, power)."""
        try:
            params = json.loads(params_json) if isinstance(params_json, str) else params_json
            n = params.get("n", 200)
            power = params.get("power", 0.8)
            alpha = params.get("alpha", 0.05)
            return json.dumps({"n": n, "power": power, "alpha": alpha, "rationale": "From input parameters"}, indent=2)
        except Exception as e:
            return f"Failed to calculate sample size: {str(e)}"

    def _generate_methods_outline_tool(self, design_json: str) -> str:
        """Tool: generate methods outline from study design JSON."""
        try:
            data = json.loads(design_json) if isinstance(design_json, str) else design_json
            study_type = data.get("study_type", "observational")
            methodology = data.get("methodology", {})
            endpoints = data.get("endpoints", {"primary": [], "secondary": []})
            sample_size = data.get("sample_size", {"n": 200, "power": 0.8, "alpha": 0.05})
            return self._generate_methods_outline(study_type, methodology, endpoints, sample_size)
        except Exception as e:
            return f"Failed to generate methods outline: {str(e)}"
