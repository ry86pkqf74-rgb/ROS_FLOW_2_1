"""
ResearchFlow AI Orchestration Router
=====================================
Unified coordination layer for routing requests to appropriate AI tools,
agents, and integrations based on task type and configuration.

Supports:
- LangSmith agents (transparency-monitor-agent)
- Composio multi-tool workflows (Linear, Slack, GitHub, Notion)
- Cloud providers (Anthropic, OpenAI, xAI)
- Local providers (LM Studio, Ollama)
"""

import json
import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Supported task types for routing."""
    TRANSPARENCY_MONITORING = "transparency-monitoring"
    COMPLIANCE_ALERT = "compliance-alert"
    FAVES_VALIDATION = "faves-validation"
    CODE_GENERATION = "code-generation"
    EMBEDDINGS = "embeddings"
    CODE_SEARCH = "code-search"
    AUTOCOMPLETE = "autocomplete"
    PHI_SAFE = "phi-safe"
    REASONING = "reasoning"
    CHAT = "chat"


class Provider(Enum):
    """Available AI providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    XAI = "xai"
    MERCURY = "mercury"
    SOURCEGRAPH = "sourcegraph"
    LM_STUDIO = "lm-studio"
    OLLAMA = "ollama"
    LANGSMITH = "langsmith"
    COMPOSIO = "composio"


@dataclass
class RoutingResult:
    """Result of routing decision."""
    provider: str
    model: Optional[str] = None
    agent: Optional[str] = None
    workflow: Optional[str] = None
    endpoint: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class OrchestrationRouter:
    """
    Main orchestration router for ResearchFlow AI integrations.

    Routes requests to the appropriate provider based on task type,
    PHI status, and configuration rules.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize router with configuration."""
        if config_path is None:
            # Default to config relative to this file
            config_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "ai-orchestration.json"

        self.config = self._load_config(config_path)
        self.default_provider = self.config.get("routing", {}).get("default", "anthropic")

        logger.info(f"OrchestrationRouter initialized with default provider: {self.default_provider}")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return self._default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "routing": {"default": "anthropic", "rules": []},
            "providers": {"cloud": {}, "local": {}},
            "agents": {}
        }

    def route(
        self,
        task_type: str,
        contains_phi: bool = False,
        complexity: str = "normal",
        requires_reasoning: bool = False
    ) -> RoutingResult:
        """
        Route a request to the appropriate provider.

        Args:
            task_type: Type of task to perform
            contains_phi: Whether the request contains PHI data
            complexity: Task complexity level (normal, high)
            requires_reasoning: Whether task requires advanced reasoning

        Returns:
            RoutingResult with provider and configuration details
        """
        rules = self.config.get("routing", {}).get("rules", [])

        # Check rules in order
        for rule in rules:
            condition = rule.get("condition", {})

            # PHI routing (highest priority)
            if condition.get("containsPHI") and contains_phi:
                return self._build_result(rule)

            # Task type routing
            if condition.get("taskType") == task_type:
                return self._build_result(rule)

            # Reasoning + complexity routing
            if (condition.get("requiresReasoning") == requires_reasoning and
                condition.get("complexity") == complexity):
                return self._build_result(rule)

        # Default routing
        return RoutingResult(
            provider=self.default_provider,
            config=self._get_provider_config(self.default_provider)
        )

    def _build_result(self, rule: Dict[str, Any]) -> RoutingResult:
        """Build routing result from rule."""
        provider = rule.get("provider", self.default_provider)
        return RoutingResult(
            provider=provider,
            model=rule.get("model"),
            agent=rule.get("agent"),
            workflow=rule.get("workflow"),
            config=self._get_provider_config(provider)
        )

    def _get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider."""
        # Check cloud providers
        cloud = self.config.get("providers", {}).get("cloud", {})
        if provider in cloud:
            return cloud[provider]

        # Check local providers
        local = self.config.get("providers", {}).get("local", {})
        if provider in local:
            return local[provider]

        # Check agents
        agents = self.config.get("agents", {})
        if provider in agents:
            return agents[provider]

        return None

    def get_langsmith_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get LangSmith agent configuration."""
        langsmith = self.config.get("agents", {}).get("langsmith", {})
        agents = langsmith.get("agents", {})
        return agents.get(agent_name)

    def get_composio_workflow(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Get Composio workflow configuration."""
        composio = self.config.get("agents", {}).get("composio", {})
        workflows = composio.get("workflows", {})
        return workflows.get(workflow_name)

    def get_composio_toolkit(self, toolkit_name: str) -> Optional[Dict[str, Any]]:
        """Get Composio toolkit configuration."""
        composio = self.config.get("agents", {}).get("composio", {})
        toolkits = composio.get("toolkits", {})
        return toolkits.get(toolkit_name)

    def get_faves_config(self) -> Dict[str, Any]:
        """Get FAVES compliance configuration."""
        return self.config.get("faves", {})

    def check_drift_threshold(self, psi_value: float) -> bool:
        """Check if PSI value exceeds drift threshold."""
        faves = self.get_faves_config()
        threshold = faves.get("thresholds", {}).get("psi", 0.2)
        return psi_value > threshold

    def get_drift_triggers(self) -> List[str]:
        """Get triggers for drift detection events."""
        faves = self.get_faves_config()
        return faves.get("triggers", {}).get("onDriftDetected", [])


class TransparencyMonitorClient:
    """
    Client for invoking the LangSmith transparency-monitor-agent.
    """

    def __init__(self, router: OrchestrationRouter):
        self.router = router
        self.agent_config = router.get_langsmith_agent("transparency-monitor-agent")

        if not self.agent_config:
            raise ValueError("transparency-monitor-agent not configured")

        logger.info(f"TransparencyMonitorClient initialized with model: {self.agent_config.get('model')}")

    def analyze_drift(
        self,
        model_id: str,
        psi_value: float,
        kl_divergence: float,
        feature_distributions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze model drift using the transparency monitor agent.

        Args:
            model_id: Identifier for the model being monitored
            psi_value: Population Stability Index value
            kl_divergence: KL divergence value
            feature_distributions: Current feature distributions

        Returns:
            Analysis result with recommendations
        """
        # Check thresholds
        exceeds_threshold = self.router.check_drift_threshold(psi_value)

        result = {
            "model_id": model_id,
            "metrics": {
                "psi": psi_value,
                "kl_divergence": kl_divergence
            },
            "exceeds_threshold": exceeds_threshold,
            "faves_dimensions": {
                "fair": self._assess_fairness(feature_distributions),
                "appropriate": True,  # Context-dependent
                "valid": psi_value < 0.25,  # Model still valid
                "effective": kl_divergence < 0.15,
                "safe": not exceeds_threshold
            }
        }

        if exceeds_threshold:
            result["action_required"] = "FAVES compliance review"
            result["triggers"] = self.router.get_drift_triggers()

        return result

    def _assess_fairness(self, distributions: Dict[str, Any]) -> bool:
        """Assess fairness based on feature distributions."""
        # Simplified fairness check - in production would be more sophisticated
        return True  # Placeholder


class ComposioWorkflowClient:
    """
    Client for invoking Composio multi-tool workflows.
    """

    def __init__(self, router: OrchestrationRouter):
        self.router = router
        self.composio_config = router.config.get("agents", {}).get("composio", {})

        logger.info(f"ComposioWorkflowClient initialized for workspace: {self.composio_config.get('workspace')}")

    def trigger_compliance_alert(
        self,
        issue_title: str,
        issue_description: str,
        labels: List[str] = None,
        slack_channel: str = "compliance-updates"
    ) -> Dict[str, Any]:
        """
        Trigger the FAVES compliance alert workflow.

        Creates a Linear issue, posts to Slack, and optionally creates a GitHub issue.

        Args:
            issue_title: Title for the compliance issue
            issue_description: Description of the compliance concern
            labels: Labels to apply to the issue
            slack_channel: Slack channel for notification

        Returns:
            Workflow execution result
        """
        workflow = self.router.get_composio_workflow("faves-compliance-alert")

        if not workflow:
            raise ValueError("faves-compliance-alert workflow not configured")

        # Build workflow payload
        payload = {
            "workflow": "faves-compliance-alert",
            "inputs": {
                "linear": {
                    "title": issue_title,
                    "description": issue_description,
                    "labels": labels or ["compliance"]
                },
                "slack": {
                    "channel": slack_channel,
                    "message": f"🚨 *Compliance Alert*: {issue_title}\n\n{issue_description}"
                },
                "github": {
                    "title": issue_title,
                    "body": issue_description,
                    "labels": ["compliance", "faves"]
                }
            }
        }

        logger.info(f"Triggering compliance alert workflow: {issue_title}")

        # In production, this would call the Composio API
        return {
            "status": "triggered",
            "workflow": "faves-compliance-alert",
            "payload": payload,
            "actions": workflow.get("actions", [])
        }

    def create_linear_issue(
        self,
        title: str,
        description: str,
        labels: List[str] = None
    ) -> Dict[str, Any]:
        """Create a Linear issue via Composio."""
        toolkit = self.router.get_composio_toolkit("linear")

        if not toolkit or not toolkit.get("enabled"):
            raise ValueError("Linear toolkit not enabled in Composio")

        return {
            "toolkit": "linear",
            "action": "create-issue",
            "inputs": {
                "title": title,
                "description": description,
                "labels": labels or []
            },
            "auth": toolkit.get("auth")
        }

    def send_slack_notification(
        self,
        channel: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a Slack notification via Composio."""
        toolkit = self.router.get_composio_toolkit("slack")

        if not toolkit or not toolkit.get("enabled"):
            raise ValueError("Slack toolkit not enabled in Composio")

        return {
            "toolkit": "slack",
            "action": "send-message",
            "inputs": {
                "channel": channel,
                "message": message
            }
        }


# Convenience functions for direct invocation
def get_router(config_path: Optional[str] = None) -> OrchestrationRouter:
    """Get a configured orchestration router instance."""
    return OrchestrationRouter(config_path)


def route_task(
    task_type: str,
    contains_phi: bool = False,
    config_path: Optional[str] = None
) -> RoutingResult:
    """Route a task to the appropriate provider."""
    router = get_router(config_path)
    return router.route(task_type, contains_phi=contains_phi)


def trigger_drift_alert(
    model_id: str,
    psi_value: float,
    issue_title: str,
    config_path: Optional[str] = None
) -> Dict[str, Any]:
    """Trigger a drift alert workflow if thresholds exceeded."""
    router = get_router(config_path)

    if router.check_drift_threshold(psi_value):
        workflow_client = ComposioWorkflowClient(router)
        return workflow_client.trigger_compliance_alert(
            issue_title=issue_title,
            issue_description=f"Model {model_id} PSI value ({psi_value}) exceeds threshold. Requires FAVES compliance review.",
            labels=["compliance", "drift-alert"]
        )

    return {"status": "no_action", "reason": "PSI within threshold"}


if __name__ == "__main__":
    # Example usage
    router = get_router()

    # Route a transparency monitoring task
    result = router.route(TaskType.TRANSPARENCY_MONITORING.value)
    print(f"Transparency monitoring routed to: {result.provider}")

    # Route a PHI-containing task
    phi_result = router.route("chat", contains_phi=True)
    print(f"PHI task routed to: {phi_result.provider}")

    # Check drift threshold
    exceeds = router.check_drift_threshold(0.25)
    print(f"PSI 0.25 exceeds threshold: {exceeds}")

    # Get FAVES config
    faves = router.get_faves_config()
    print(f"FAVES dimensions: {faves.get('dimensions')}")
