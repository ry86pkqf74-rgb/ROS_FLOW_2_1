"""
Stage 11: Iteration

Handles analysis iteration with AI routing including:
- Processing iteration requests with changes to apply
- Tracking version history and diffs
- Generating AI-powered suggestions for improvements
- Managing the iterative refinement workflow
"""

import hashlib
import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import StageContext, StageResult
from ..registry import register_stage
from .base_stage_agent import BaseStageAgent

logger = logging.getLogger("workflow_engine.stages.stage_11_iteration")

# LangChain imports with graceful fallback
try:
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    Tool = None  # type: ignore
    logger.warning("LangChain not available. Tools will not be available.")


def compute_content_hash(content: Any) -> str:
    """Compute a hash for content to track changes.

    Args:
        content: Content to hash (will be serialized to string)

    Returns:
        SHA256 hash of the content
    """
    content_str = str(content)
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]


def generate_diff(
    previous_version: Dict[str, Any],
    current_version: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate a diff between two versions.

    Args:
        previous_version: The previous version data
        current_version: The current version data

    Returns:
        Diff summary showing changes
    """
    diff = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": [],
    }

    prev_keys = set(previous_version.keys()) if previous_version else set()
    curr_keys = set(current_version.keys()) if current_version else set()

    # Find added keys
    for key in curr_keys - prev_keys:
        diff["added"].append({
            "key": key,
            "value": current_version[key],
        })

    # Find removed keys
    for key in prev_keys - curr_keys:
        diff["removed"].append({
            "key": key,
            "value": previous_version[key],
        })

    # Find modified and unchanged
    for key in prev_keys & curr_keys:
        if previous_version[key] != current_version[key]:
            diff["modified"].append({
                "key": key,
                "old_value": previous_version[key],
                "new_value": current_version[key],
            })
        else:
            diff["unchanged"].append(key)

    return diff


def create_version_entry(
    version_number: int,
    changes: Dict[str, Any],
    author: str = "system"
) -> Dict[str, Any]:
    """Create a version history entry.

    Args:
        version_number: The version number
        changes: Changes applied in this version
        author: Author of the changes

    Returns:
        Version entry dictionary
    """
    return {
        "version_id": str(uuid.uuid4()),
        "version_number": version_number,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "author": author,
        "changes_summary": changes.get("summary", ""),
        "changes_applied": changes.get("changes", []),
        "content_hash": compute_content_hash(changes),
        "rollback_available": version_number > 1,
    }


def generate_ai_suggestions(
    iteration_request: Dict[str, Any],
    previous_results: Dict[int, Any]
) -> List[Dict[str, Any]]:
    """Generate AI-powered suggestions for iteration improvements.

    Args:
        iteration_request: The current iteration request
        previous_results: Results from previous stages

    Returns:
        List of AI suggestions
    """
    suggestions = []

    # Analyze the iteration request and generate suggestions
    changes = iteration_request.get("changes", [])
    focus_areas = iteration_request.get("focus_areas", [])

    # Generate suggestions based on focus areas
    if "statistical_analysis" in focus_areas:
        suggestions.append({
            "suggestion_id": str(uuid.uuid4()),
            "type": "methodology",
            "priority": "high",
            "title": "Consider Additional Statistical Tests",
            "description": "Based on the data distribution, consider applying non-parametric tests for robustness.",
            "confidence": 0.85,
            "auto_applicable": False,
        })

    if "data_quality" in focus_areas:
        suggestions.append({
            "suggestion_id": str(uuid.uuid4()),
            "type": "data_quality",
            "priority": "medium",
            "title": "Outlier Detection Refinement",
            "description": "Apply IQR-based outlier detection to improve data quality.",
            "confidence": 0.78,
            "auto_applicable": True,
        })

    # Default suggestions if no focus areas specified
    if not suggestions:
        suggestions.append({
            "suggestion_id": str(uuid.uuid4()),
            "type": "general",
            "priority": "low",
            "title": "Review Parameter Settings",
            "description": "Consider reviewing analysis parameters based on current results.",
            "confidence": 0.65,
            "auto_applicable": False,
        })

    return suggestions


def route_iteration(
    iteration_request: Dict[str, Any]
) -> Dict[str, Any]:
    """Route the iteration to appropriate processing pipeline.

    Args:
        iteration_request: The iteration request with changes

    Returns:
        Routing decision with pipeline and parameters
    """
    iteration_type = iteration_request.get("type", "general")
    changes = iteration_request.get("changes", [])

    # Determine routing based on iteration type
    routing = {
        "pipeline": "default",
        "priority": "normal",
        "requires_reanalysis": False,
        "affected_stages": [],
        "estimated_duration_ms": 1000,
    }

    if iteration_type == "parameter_change":
        routing["pipeline"] = "parameter_update"
        routing["requires_reanalysis"] = True
        routing["affected_stages"] = [6, 7, 8]  # Analysis stages
        routing["estimated_duration_ms"] = 5000

    elif iteration_type == "data_subset":
        routing["pipeline"] = "data_subset"
        routing["requires_reanalysis"] = True
        routing["affected_stages"] = [4, 5, 6, 7, 8]  # From validation onwards
        routing["estimated_duration_ms"] = 10000

    elif iteration_type == "methodology_change":
        routing["pipeline"] = "full_reanalysis"
        routing["requires_reanalysis"] = True
        routing["affected_stages"] = [6, 7, 8, 9, 10]  # All analysis and interpretation
        routing["priority"] = "high"
        routing["estimated_duration_ms"] = 15000

    return routing


@register_stage
class IterationAgent(BaseStageAgent):
    """Stage 11: Iteration

    Handles analysis iteration with AI routing by processing
    iteration requests, tracking version history, and generating
    AI-powered suggestions for improvements.
    """

    stage_id = 11
    stage_name = "Iteration"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the IterationAgent.

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
                name="analyze_feedback",
                description="Analyze reviewer/validation feedback. Input: JSON with feedback, comments, or focus_areas.",
                func=self._analyze_feedback_tool,
            ),
            Tool(
                name="prioritize_revisions",
                description="Prioritize needed revisions. Input: JSON with revisions list or feedback.",
                func=self._prioritize_revisions_tool,
            ),
            Tool(
                name="route_to_stage",
                description="Determine which stage needs re-execution. Input: JSON with iteration type or iteration_request.",
                func=self._route_to_stage_tool,
            ),
            Tool(
                name="track_iteration",
                description="Track iteration history and changes. Input: JSON with version_number, changes, previous_data, current_data.",
                func=self._track_iteration_tool,
            ),
            Tool(
                name="assess_convergence",
                description="Assess if iterations are converging. Input: JSON with version_history or iteration_log.",
                func=self._assess_convergence_tool,
            ),
        ]

    def get_prompt_template(self):
        """Get prompt template for analysis iteration with AI routing."""
        if not LANGCHAIN_AVAILABLE:
            class _StubTemplate:
                @classmethod
                def from_template(cls, _t): return type("_T", (), {"template": _t, "format": lambda s, **kw: s.template})()
            return _StubTemplate.from_template("{input}")
        try:
            from langchain_core.prompts import PromptTemplate
        except ImportError:
            from langchain.prompts import PromptTemplate  # type: ignore
        return PromptTemplate.from_template("""You are an Iteration Specialist for clinical research analysis.

Your task is to manage analysis iteration:
1. Analyze reviewer/validation feedback
2. Prioritize needed revisions
3. Route to the appropriate stage for re-execution
4. Track iteration history and changes
5. Assess if iterations are converging

Iteration Summary: {iteration_summary}

Input Request:
{input}

Previous Agent Scratchpad:
{agent_scratchpad}
""")

    # =========================================================================
    # Tool implementations (wrappers for LangChain)
    # =========================================================================

    def _analyze_feedback_tool(self, input_json: str) -> str:
        """Tool: analyze reviewer/validation feedback."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            feedback = data.get("feedback", data.get("comments", []))
            focus_areas = data.get("focus_areas", [])
            if isinstance(feedback, dict):
                feedback = [feedback]
            themes = list(set(focus_areas)) if focus_areas else ["general"]
            severity = "medium"
            if any("methodology" in str(t).lower() for t in themes):
                severity = "high"
            suggested_actions = []
            if "statistical_analysis" in focus_areas:
                suggested_actions.append("Consider additional statistical tests")
            if "data_quality" in focus_areas:
                suggested_actions.append("Refine outlier detection")
            if not suggested_actions:
                suggested_actions.append("Review parameters and re-run analysis")
            return json.dumps({
                "themes": themes,
                "severity": severity,
                "suggested_actions": suggested_actions,
                "feedback_count": len(feedback) if isinstance(feedback, list) else 1,
                "summary": f"Feedback analyzed: {len(themes)} theme(s), severity {severity}.",
            }, indent=2)
        except Exception as e:
            return f"Failed to analyze feedback: {str(e)}"

    def _prioritize_revisions_tool(self, input_json: str) -> str:
        """Tool: prioritize needed revisions."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            revisions = data.get("revisions", data.get("feedback", []))
            if isinstance(revisions, dict):
                revisions = [revisions]
            if not revisions:
                return json.dumps({
                    "prioritized": [],
                    "rationale": "No revisions provided.",
                }, indent=2)
            prioritized = []
            for i, rev in enumerate(revisions):
                priority = rev.get("priority", "medium")
                if isinstance(rev, str):
                    prioritized.append({"order": i + 1, "item": rev, "priority": "medium", "rationale": "Unspecified"})
                else:
                    prioritized.append({
                        "order": i + 1,
                        "item": rev.get("title", rev.get("description", str(rev))),
                        "priority": priority,
                        "rationale": rev.get("rationale", f"Priority {priority}"),
                    })
            return json.dumps({
                "prioritized": prioritized,
                "rationale": f"Ordered {len(prioritized)} revision(s) by priority.",
            }, indent=2)
        except Exception as e:
            return f"Failed to prioritize revisions: {str(e)}"

    def _route_to_stage_tool(self, input_json: str) -> str:
        """Tool: determine which stage needs re-execution."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            iteration_request = data.get("iteration_request", data)
            if not isinstance(iteration_request, dict):
                iteration_request = {"type": "general", "changes": []}
            routing = route_iteration(iteration_request)
            return json.dumps(routing, indent=2)
        except Exception as e:
            return f"Failed to route to stage: {str(e)}"

    def _track_iteration_tool(self, input_json: str) -> str:
        """Tool: track iteration history and changes."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            version_number = data.get("version_number", 1)
            changes = data.get("changes", {})
            previous_data = data.get("previous_data", {})
            current_data = data.get("current_data", {})
            version_entry = create_version_entry(
                version_number=version_number,
                changes=changes if isinstance(changes, dict) else {"summary": "", "changes": changes},
                author=data.get("author", "system"),
            )
            diff = generate_diff(previous_data, current_data)
            return json.dumps({
                "version_entry": version_entry,
                "diff_summary": {
                    "added": len(diff.get("added", [])),
                    "removed": len(diff.get("removed", [])),
                    "modified": len(diff.get("modified", [])),
                },
            }, indent=2)
        except Exception as e:
            return f"Failed to track iteration: {str(e)}"

    def _assess_convergence_tool(self, input_json: str) -> str:
        """Tool: assess if iterations are converging."""
        try:
            data = json.loads(input_json) if isinstance(input_json, str) else input_json
            history = data.get("version_history", data.get("iteration_log", []))
            if not isinstance(history, list):
                history = []
            n = len(history)
            if n < 2:
                status = "insufficient_data"
                recommendation = "Continue iterations to assess convergence."
            elif n >= 5:
                status = "stable"
                recommendation = "Consider finalizing; sufficient iterations."
            else:
                status = "converging"
                recommendation = "Continue 1–2 more iterations to confirm."
            return json.dumps({
                "status": status,
                "iterations_count": n,
                "metric_summary": {"iterations": n, "status": status},
                "recommendation": recommendation,
            }, indent=2)
        except Exception as e:
            return f"Failed to assess convergence: {str(e)}"

    async def execute(self, context: StageContext) -> StageResult:
        """Execute analysis iteration with AI routing.

        Args:
            context: StageContext with job configuration

        Returns:
            StageResult with iteration_log, version_info, and ai_suggestions
        """
        started_at = datetime.utcnow().isoformat() + "Z"
        warnings: List[str] = []
        errors: List[str] = []
        artifacts: List[str] = []

        logger.info(f"Starting iteration stage for job {context.job_id}")

        # Get iteration configuration
        iteration_config = context.config.get("iteration", {})
        iteration_request = iteration_config.get("iteration_request", {})
        enable_ai_suggestions = iteration_config.get("enable_ai_suggestions", True)
        max_versions = iteration_config.get("max_versions", 100)

        # Get version history from metadata or initialize
        version_history = context.metadata.get("version_history", [])
        current_version = len(version_history) + 1

        # Initialize output structure
        output: Dict[str, Any] = {
            "iteration_log": [],
            "version_info": {},
            "ai_suggestions": [],
            "routing": {},
            "diff": {},
            "summary": {},
        }

        try:
            # Validate iteration request
            if not iteration_request:
                warnings.append("No iteration_request provided in configuration")
                iteration_request = {"type": "general", "changes": []}

            logger.info(f"Processing iteration request type: {iteration_request.get('type', 'unknown')}")

            # Create iteration log entry
            iteration_entry = {
                "iteration_id": str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_type": iteration_request.get("type", "general"),
                "changes_requested": iteration_request.get("changes", []),
                "focus_areas": iteration_request.get("focus_areas", []),
                "requester": iteration_request.get("requester", "system"),
                "status": "processing",
            }
            output["iteration_log"].append(iteration_entry)

            # Route the iteration to appropriate pipeline
            output["routing"] = route_iteration(iteration_request)
            logger.info(f"Routing to pipeline: {output['routing']['pipeline']}")

            # Generate diff if we have previous version data
            previous_data = iteration_request.get("previous_data", {})
            current_data = iteration_request.get("current_data", {})
            if previous_data or current_data:
                output["diff"] = generate_diff(previous_data, current_data)

            # Create version entry
            version_entry = create_version_entry(
                version_number=current_version,
                changes=iteration_request,
                author=iteration_request.get("requester", "system")
            )

            # Check version limit
            if current_version > max_versions:
                warnings.append(f"Version limit ({max_versions}) reached - consider archiving old versions")

            output["version_info"] = {
                "current_version": version_entry,
                "version_number": current_version,
                "total_versions": current_version,
                "previous_versions_count": len(version_history),
                "version_history_summary": [
                    {"version": v.get("version_number"), "created_at": v.get("created_at")}
                    for v in version_history[-5:]  # Last 5 versions
                ],
            }

            # Optional: call peer-review bridge
            # Serialize previous_results to JSON-serializable dict (StageResult dataclass is not)
            manuscript_payload: Dict[str, Any] = {}
            if context.previous_results:
                manuscript_payload = {
                    str(stage_id): asdict(result)
                    for stage_id, result in context.previous_results.items()
                }

            peer_review_result: Optional[Dict[str, Any]] = None
            try:
                peer_review_result = await self.call_manuscript_service(
                    "peer-review",
                    "simulateReview",
                    {
                        "manuscriptId": context.job_id,
                        "manuscript": manuscript_payload,
                    },
                )
            except Exception as e:
                logger.warning(f"peer-review failed: {type(e).__name__}: {e}")
                warnings.append(f"Peer review failed: {str(e)}. Proceeding without.")

            if peer_review_result:
                output["peer_review"] = peer_review_result

            # Generate AI suggestions if enabled
            if enable_ai_suggestions:
                output["ai_suggestions"] = generate_ai_suggestions(
                    iteration_request,
                    context.previous_results
                )
                # Optional: call claude-writer for revision/section content
                try:
                    claude_result = await self.call_manuscript_service(
                        "claude-writer",
                        "generateSection",
                        {
                            "section": "revisions",
                            "context": json.dumps({
                                "iteration_request": iteration_request,
                                "suggestions_count": len(output["ai_suggestions"]),
                                "previous_results_summary": str(context.previous_results)[:500] if context.previous_results else "",
                            }),
                        },
                    )
                    if claude_result:
                        output["claude_revision_suggestion"] = claude_result
                except Exception as e:
                    logger.warning(f"claude-writer generateSection unavailable: {e}")
                    warnings.append(f"Claude writer unavailable: {str(e)}. Using in-process suggestions only.")
                logger.info(f"Generated {len(output['ai_suggestions'])} AI suggestions")
            else:
                warnings.append("AI suggestions are disabled")

            # Update iteration log entry status
            iteration_entry["status"] = "completed"
            iteration_entry["routing_pipeline"] = output["routing"]["pipeline"]
            iteration_entry["version_created"] = current_version

            # Generate summary
            output["summary"] = {
                "iteration_type": iteration_request.get("type", "general"),
                "changes_count": len(iteration_request.get("changes", [])),
                "version_created": current_version,
                "requires_reanalysis": output["routing"]["requires_reanalysis"],
                "affected_stages": output["routing"]["affected_stages"],
                "ai_suggestions_count": len(output["ai_suggestions"]),
                "diff_summary": {
                    "added": len(output["diff"].get("added", [])),
                    "removed": len(output["diff"].get("removed", [])),
                    "modified": len(output["diff"].get("modified", [])),
                },
            }

            # Add demo mode indicator
            if context.governance_mode == "DEMO":
                output["demo_mode"] = True
                warnings.append("Running in DEMO mode - iteration processing is simulated")

            # Write artifact
            try:
                os.makedirs(context.artifact_path, exist_ok=True)
                artifact_path = os.path.join(context.artifact_path, "iteration_report.json")
                artifact_data = {
                    "schema_version": "1.0",
                    "generated_at": datetime.utcnow().isoformat() + "Z",
                    "job_id": context.job_id,
                    "iteration_log": output["iteration_log"],
                    "version_info": output["version_info"],
                    "routing": output["routing"],
                    "summary": output["summary"],
                }
                with open(artifact_path, "w") as f:
                    json.dump(artifact_data, f, indent=2, default=str)
                artifacts.append(artifact_path)
            except Exception as e:
                logger.warning(f"Could not write iteration artifact: {e}")
                warnings.append(f"Could not write iteration artifact: {str(e)}")

        except Exception as e:
            logger.error(f"Error during iteration: {str(e)}")
            errors.append(f"Iteration stage failed: {str(e)}")

        status = "failed" if errors else "completed"

        return self.create_stage_result(
            context=context,
            status=status,
            started_at=started_at,
            output=output,
            artifacts=artifacts,
            warnings=warnings,
            errors=errors,
            metadata={
                "governance_mode": context.governance_mode,
                "version_number": current_version,
                "routing_pipeline": output.get("routing", {}).get("pipeline", "unknown"),
            },
        )
