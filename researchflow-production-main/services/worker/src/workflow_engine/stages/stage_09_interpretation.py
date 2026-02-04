"""
Stage 09: Result Interpretation

Handles collaborative result interpretation including:
- Processing analysis findings
- Generating discussion threads
- Creating annotations for key findings
- Facilitating collaborative interpretation workflows
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stages.stage_09_interpretation")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")


def generate_discussion_thread(
    finding_id: str,
    finding_text: str,
    author: str = "system"
) -> Dict[str, Any]:
    """Generate a discussion thread for a finding.

    Args:
        finding_id: Unique identifier for the finding
        finding_text: Text description of the finding
        author: Author of the initial thread

    Returns:
        Dictionary representing a discussion thread
    """
    return {
        "thread_id": str(uuid.uuid4()),
        "finding_id": finding_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "author": author,
        "initial_comment": f"Discussion initiated for finding: {finding_text[:100]}...",
        "replies": [],
        "status": "open",
        "tags": [],
    }


def create_annotation(
    finding_id: str,
    annotation_type: str,
    content: str,
    author: str = "system"
) -> Dict[str, Any]:
    """Create an annotation for a finding.

    Args:
        finding_id: The finding this annotation relates to
        annotation_type: Type of annotation (highlight, note, question, etc.)
        content: Annotation content
        author: Author of the annotation

    Returns:
        Dictionary representing an annotation
    """
    return {
        "annotation_id": str(uuid.uuid4()),
        "finding_id": finding_id,
        "type": annotation_type,
        "content": content,
        "author": author,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "resolved": False,
    }


def extract_key_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract and prioritize key findings from analysis results.

    Args:
        findings: List of findings from analysis

    Returns:
        List of key findings with priority scores
    """
    key_findings = []
    for idx, finding in enumerate(findings):
        priority = finding.get("priority", "medium")
        priority_score = {"high": 3, "medium": 2, "low": 1}.get(priority, 2)

        key_findings.append({
            "finding_id": finding.get("id", f"finding_{idx}"),
            "summary": finding.get("summary", finding.get("text", "")),
            "priority": priority,
            "priority_score": priority_score,
            "category": finding.get("category", "general"),
            "confidence": finding.get("confidence", 0.8),
            "supporting_data": finding.get("supporting_data", []),
        })

    # Sort by priority score descending
    key_findings.sort(key=lambda x: x["priority_score"], reverse=True)
    return key_findings


@register_stage
class InterpretationAgent(BaseStageAgent):
    """Stage 09: Result Interpretation.

    Handles collaborative result interpretation by processing
    analysis findings, generating discussion threads, and
    creating annotations for team collaboration.
    """

    stage_id = 9
    stage_name = "Result Interpretation"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the InterpretationAgent.

        Args:
            config: Optional configuration dict. If None, uses defaults.
        """
        bridge_config = None
        if config and "bridge_url" in config:
            from ..bridge import BridgeConfig
            bridge_config = BridgeConfig(
                base_url=config["bridge_url"],
                timeout=config.get("bridge_timeout", 30.0),
            )
        super().__init__(bridge_config=bridge_config)

    def get_tools(self) -> List[Any]:
        """Get LangChain tools available to this stage."""
        if not LANGCHAIN_AVAILABLE:
            return []
        return [
            Tool(
                name="interpret_statistics",
                description="Interpret statistical findings in clinical context. Input: JSON with findings or summary.",
                func=self._interpret_statistics_tool,
            ),
            Tool(
                name="compare_to_literature",
                description="Compare findings with published literature. Input: JSON with findings or key_points.",
                func=self._compare_to_literature_tool,
            ),
            Tool(
                name="identify_clinical_significance",
                description="Assess clinical vs statistical significance. Input: JSON with findings or effect_sizes.",
                func=self._identify_clinical_significance_tool,
            ),
            Tool(
                name="generate_implications",
                description="Generate clinical/research implications. Input: JSON with findings or summary.",
                func=self._generate_implications_tool,
            ),
            Tool(
                name="identify_limitations",
                description="Identify study limitations. Input: JSON with study_design or findings.",
                func=self._identify_limitations_tool,
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for result interpretation."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        try:
            from langchain_core.prompts import PromptTemplate
        except ImportError:
            from langchain.prompts import PromptTemplate  # type: ignore
        return PromptTemplate.from_template("""You are a Result Interpretation Specialist for clinical research.

Your task is to interpret analysis findings in context:
1. Interpret statistical findings in clinical context
2. Compare findings with published literature
3. Assess clinical vs statistical significance
4. Generate clinical and research implications
5. Identify study limitations and future directions

Key Findings: {key_findings}

Input Request:
{input}

Previous Agent Scratchpad:
{agent_scratchpad}
""")

    # =========================================================================
    # Tool implementations (wrappers for LangChain)
    # =========================================================================

    def _interpret_statistics_tool(self, input_json: str) -> str:
        """Tool: interpret statistical findings in clinical context."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            findings = data.get("findings", data.get("summary", ""))
            if not findings:
                return json.dumps({
                    "interpretation": "",
                    "clinical_context": "",
                    "message": "No findings or summary provided",
                }, indent=2)
            summary = findings[0].get("summary", str(findings)) if isinstance(findings, list) and findings else str(findings)
            return json.dumps({
                "interpretation": f"Analysis indicates: {summary[:200]}",
                "clinical_context": "Interpretation in clinical context requires domain review.",
                "findings_count": len(findings) if isinstance(findings, list) else 0,
            }, indent=2)
        except Exception as e:
            return f"Failed to interpret statistics: {str(e)}"

    def _compare_to_literature_tool(self, input_json: str) -> str:
        """Tool: compare findings with published literature."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            findings = data.get("findings", data.get("key_points", []))
            if not findings:
                return json.dumps({
                    "comparisons": [],
                    "message": "No findings or key_points provided",
                }, indent=2)
            n = len(findings) if isinstance(findings, list) else 0
            return json.dumps({
                "comparisons": [{"finding": str(f)[:100], "literature_note": "Compare with published evidence."} for f in (findings[:5] if isinstance(findings, list) else [findings])],
                "findings_count": n,
            }, indent=2)
        except Exception as e:
            return f"Failed to compare to literature: {str(e)}"

    def _identify_clinical_significance_tool(self, input_json: str) -> str:
        """Tool: assess clinical vs statistical significance."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            findings = data.get("findings", data.get("effect_sizes", {}))
            if not findings:
                return json.dumps({
                    "clinical_significance": "",
                    "statistical_significance": "",
                    "message": "No findings or effect_sizes provided",
                }, indent=2)
            return json.dumps({
                "clinical_significance": "Clinical significance should be assessed by domain experts.",
                "statistical_significance": "Statistical significance from analysis should be reviewed.",
                "findings_reviewed": len(findings) if isinstance(findings, (list, dict)) else 0,
            }, indent=2)
        except Exception as e:
            return f"Failed to identify clinical significance: {str(e)}"

    def _generate_implications_tool(self, input_json: str) -> str:
        """Tool: generate clinical/research implications."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            findings = data.get("findings", data.get("summary", ""))
            if not findings:
                return json.dumps({
                    "clinical": [],
                    "research": [],
                    "message": "No findings or summary provided",
                }, indent=2)
            return json.dumps({
                "clinical": ["Implications for practice should be derived from key findings."],
                "research": ["Future research directions should build on these results."],
                "findings_count": len(findings) if isinstance(findings, list) else 0,
            }, indent=2)
        except Exception as e:
            return f"Failed to generate implications: {str(e)}"

    def _identify_limitations_tool(self, input_json: str) -> str:
        """Tool: identify study limitations."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            study_design = data.get("study_design", data.get("findings", []))
            if not study_design:
                return json.dumps({
                    "limitations": [],
                    "future_directions": [],
                    "message": "No study_design or findings provided",
                }, indent=2)
            return json.dumps({
                "limitations": ["Study design and sample limitations should be documented."],
                "future_directions": ["Larger cohorts and replication studies recommended."],
                "reviewed": True,
            }, indent=2)
        except Exception as e:
            return f"Failed to identify limitations: {str(e)}"

    async def execute(self, context: StageContext) -> StageResult:
        """Execute collaborative result interpretation.

        Args:
            context: StageContext with job configuration

        Returns:
            StageResult with interpretations, key_findings, discussion_threads, and interpretation block
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        warnings: List[str] = []
        errors: List[str] = []
        artifacts: List[str] = []

        logger.info(f"Starting interpretation stage for job {context.job_id}")

        interpretation_config = context.config.get("interpretation", {})
        findings = interpretation_config.get("findings", [])
        auto_generate_threads = interpretation_config.get("auto_generate_threads", True)
        annotation_types = interpretation_config.get("annotation_types", ["highlight", "note", "question"])

        output: Dict[str, Any] = {
            "interpretations": [],
            "key_findings": [],
            "discussion_threads": [],
            "annotations": [],
            "summary": {},
            "interpretation": {
                "key_findings": [],
                "clinical_significance": "",
                "comparison_to_literature": [],
                "implications": {"clinical": [], "research": []},
                "limitations": [],
                "future_directions": [],
            },
        }

        try:
            if findings:
                output["key_findings"] = extract_key_findings(findings)
                output["interpretation"]["key_findings"] = list(output["key_findings"])
                logger.info(f"Extracted {len(output['key_findings'])} key findings")
            else:
                warnings.append("No findings provided in configuration - using empty findings list")

            # Optional: call discussion-builder bridge
            discussion_builder_result: Optional[Dict[str, Any]] = None
            statistical_results = [{"id": f.get("finding_id"), "summary": f.get("summary", "")} for f in output["key_findings"]]
            try:
                discussion_builder_result = await self.call_manuscript_service(
                    "discussion-builder",
                    "build",
                    {"manuscriptId": context.job_id, "findings": statistical_results},
                )
            except Exception as e:
                logger.warning(f"discussion-builder unavailable: {e}")
                warnings.append(f"Discussion builder unavailable: {str(e)}. Proceeding without.")

            if discussion_builder_result:
                output["interpretation"]["clinical_significance"] = discussion_builder_result.get("clinical_significance", "") or ""
                output["interpretation"]["comparison_to_literature"] = discussion_builder_result.get("comparison_to_literature", [])
                output["interpretation"]["implications"] = discussion_builder_result.get("implications", {"clinical": [], "research": []})
                output["interpretation"]["limitations"] = discussion_builder_result.get("limitations", [])
                output["interpretation"]["future_directions"] = discussion_builder_result.get("future_directions", [])

            # Synthesize interpretation block from findings if bridge did not fill it
            if not output["interpretation"]["clinical_significance"] and output["key_findings"]:
                summaries = [f.get("summary", "") for f in output["key_findings"][:3]]
                output["interpretation"]["clinical_significance"] = " ".join(summaries)[:500] or "Key findings require clinical review."
            if not output["interpretation"]["implications"]["clinical"]:
                output["interpretation"]["implications"]["clinical"] = ["Interpret findings in light of local practice and guidelines."]
            if not output["interpretation"]["implications"]["research"]:
                output["interpretation"]["implications"]["research"] = ["Replication and larger studies recommended."]
            if not output["interpretation"]["limitations"]:
                output["interpretation"]["limitations"] = ["Study design and sample size limitations should be documented."]
            if not output["interpretation"]["future_directions"]:
                output["interpretation"]["future_directions"] = ["Prospective validation and subgroup analyses."]

            for finding in output["key_findings"]:
                interpretation = {
                    "finding_id": finding["finding_id"],
                    "interpretation_id": str(uuid.uuid4()),
                    "original_summary": finding["summary"],
                    "interpreted_meaning": f"Analysis indicates: {finding['summary']}",
                    "clinical_relevance": finding.get("category", "general"),
                    "confidence_level": finding.get("confidence", 0.8),
                    "recommended_actions": [],
                    "created_at": datetime.utcnow().isoformat() + "Z",
                }
                output["interpretations"].append(interpretation)

            if auto_generate_threads and output["key_findings"]:
                for finding in output["key_findings"]:
                    if finding["priority_score"] >= 2:
                        thread = generate_discussion_thread(
                            finding_id=finding["finding_id"],
                            finding_text=finding["summary"],
                            author="interpretation_engine"
                        )
                        output["discussion_threads"].append(thread)
                logger.info(f"Generated {len(output['discussion_threads'])} discussion threads")

            for finding in output["key_findings"]:
                if finding["priority_score"] >= 3:
                    annotation = create_annotation(
                        finding_id=finding["finding_id"],
                        annotation_type="highlight",
                        content=f"High-priority finding requiring review: {finding['summary'][:50]}",
                        author="interpretation_engine"
                    )
                    output["annotations"].append(annotation)

            output["summary"] = {
                "total_findings": len(findings),
                "key_findings_count": len(output["key_findings"]),
                "high_priority_count": sum(1 for f in output["key_findings"] if f["priority_score"] >= 3),
                "medium_priority_count": sum(1 for f in output["key_findings"] if f["priority_score"] == 2),
                "low_priority_count": sum(1 for f in output["key_findings"] if f["priority_score"] == 1),
                "discussion_threads_created": len(output["discussion_threads"]),
                "annotations_created": len(output["annotations"]),
            }

            if context.governance_mode == "DEMO":
                output["demo_mode"] = True
                warnings.append("Running in DEMO mode - interpretation is simulated")

            # Write artifact
            try:
                os.makedirs(context.artifact_path, exist_ok=True)
                artifact_path = os.path.join(context.artifact_path, "interpretation_results.json")
                artifact_data = {
                    "schema_version": "1.0",
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "job_id": context.job_id,
                    "interpretation": output["interpretation"],
                    "key_findings_count": len(output["key_findings"]),
                    "summary": output["summary"],
                }
                with open(artifact_path, "w") as f:
                    json.dump(artifact_data, f, indent=2, default=str)
                artifacts.append(artifact_path)
            except Exception as e:
                logger.warning(f"Could not write interpretation artifact: {e}")
                warnings.append(f"Could not write interpretation artifact: {str(e)}")

        except Exception as e:
            logger.error(f"Error during interpretation: {str(e)}")
            errors.append(f"Interpretation failed: {str(e)}")

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
                "governance_mode": context.governance_mode,
                "findings_processed": len(findings),
            },
        )
