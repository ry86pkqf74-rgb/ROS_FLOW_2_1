#!/usr/bin/env python3
"""
Release Guardian Agent - Pre-Deploy Gate Enforcement and Rollback Readiness

This agent enforces deployment gates before any release:
1. Validates CI/CD pipeline status
2. Verifies evidence pack completeness
3. Enforces FAVES gates for LIVE deployments
4. Validates rollback plan and monitoring setup
5. Manages deployment approvals and notifications
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

# Composio imports - lazy loading with graceful fallback for LangGraph Cloud
try:
    from composio_langchain import ComposioToolSet, Action
    COMPOSIO_AVAILABLE = True
except ImportError as e:
    ComposioToolSet = None
    Action = None
    COMPOSIO_AVAILABLE = False
    import warnings
    warnings.warn(f"Composio not available: {e}. ReleaseGuardianAgent will have limited functionality.")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangChain Agent imports - lazy loading for compatibility
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    LANGCHAIN_AGENTS_AVAILABLE = True
except ImportError:
    try:
        from langchain_core.agents import AgentExecutor
        from langchain.agents import create_openai_functions_agent
        LANGCHAIN_AGENTS_AVAILABLE = True
    except ImportError:
        AgentExecutor = None
        create_openai_functions_agent = None
        LANGCHAIN_AGENTS_AVAILABLE = False
        import warnings
        warnings.warn("LangChain agent components not available.")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeploymentMode(Enum):
    """Deployment modes with different gate requirements"""
    DEMO = "DEMO"      # FAVES gates are advisory
    LIVE = "LIVE"      # All gates must pass
    STAGING = "STAGING"  # CI + Evidence required, FAVES optional


class GateStatus(Enum):
    """Status of deployment gates"""
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"
    WAIVED = "waived"  # Only for DEMO mode


@dataclass
class DeploymentGate:
    """Configuration for a deployment gate"""
    name: str
    description: str
    required_for: List[str]  # Deployment modes that require this gate
    checks: List[str]


# Deployment Gates Configuration
DEPLOYMENT_GATES = {
    "ci_checks": DeploymentGate(
        name="CI Checks",
        description="All GitHub Actions workflows must pass",
        required_for=["DEMO", "LIVE", "STAGING"],
        checks=[
            "Unit tests passing",
            "Integration tests passing",
            "Lint checks passing",
            "Security scan passing",
            "Build successful"
        ]
    ),
    "evidence_pack": DeploymentGate(
        name="Evidence Pack",
        description="Evidence pack hash must be computed and recorded",
        required_for=["DEMO", "LIVE", "STAGING"],
        checks=[
            "Model artifacts present",
            "Validation results present",
            "Hash computed and recorded",
            "Artifacts signed (if required)"
        ]
    ),
    "faves_gate": DeploymentGate(
        name="FAVES Gate",
        description="Fair, Appropriate, Valid, Effective, Safe criteria met",
        required_for=["LIVE"],  # Required only for LIVE
        checks=[
            "Fair - Subgroup audit exists",
            "Appropriate - Intended use documented",
            "Valid - Validation methodology documented",
            "Effective - Outcome metrics documented",
            "Safe - Monitoring/rollback plan exists"
        ]
    ),
    "rollback_plan": DeploymentGate(
        name="Rollback Plan",
        description="Documented and tested rollback procedure",
        required_for=["LIVE", "STAGING"],
        checks=[
            "Rollback procedure documented",
            "Rollback tested in staging",
            "Previous version tagged and available",
            "Database rollback plan (if applicable)"
        ]
    ),
    "monitoring": DeploymentGate(
        name="Monitoring Setup",
        description="Dashboard and alerting configured",
        required_for=["LIVE"],
        checks=[
            "Monitoring dashboard configured",
            "Alert thresholds set",
            "On-call rotation assigned",
            "Incident playbook linked"
        ]
    )
}


# Release Guardian Agent Configuration
# Actions are only available if Composio is installed
_RELEASE_GUARDIAN_ACTIONS = []
if COMPOSIO_AVAILABLE and Action is not None:
    _RELEASE_GUARDIAN_ACTIONS = [
        # GitHub Actions
        Action.GITHUB_GET_A_REPOSITORY,
        Action.GITHUB_LIST_REPOSITORY_WORKFLOWS,
        Action.GITHUB_LIST_WORKFLOW_RUNS,
        Action.GITHUB_GET_A_WORKFLOW_RUN,
        Action.GITHUB_GET_REPOSITORY_CONTENT,
        Action.GITHUB_CREATE_AN_ISSUE,
        Action.GITHUB_UPDATE_AN_ISSUE,
        Action.GITHUB_ADD_LABELS_TO_AN_ISSUE,
        Action.GITHUB_CREATE_A_RELEASE,
        Action.GITHUB_LIST_RELEASES,
        Action.GITHUB_GET_A_COMMIT,
        # Notion Actions
        Action.NOTION_GET_PAGE,
        Action.NOTION_UPDATE_A_PAGE,
        Action.NOTION_QUERY_A_DATABASE,
        Action.NOTION_CREATE_A_PAGE,
        # Slack Actions (for notifications)
        Action.SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL,
    ]

RELEASE_GUARDIAN_CONFIG = {
    "name": "Release Guardian Agent",
    "model": "gpt-4o",
    "temperature": 0,
    "toolkits": ["GITHUB", "NOTION", "SLACK", "DOCKER"] if COMPOSIO_AVAILABLE else [],
    "actions": _RELEASE_GUARDIAN_ACTIONS,
    "system_prompt": """You are the Release Guardian Agent for ResearchFlow.

Your responsibilities:
1. Enforce deployment gates before any release:
   - CI Checks: All GitHub Actions workflows must pass
   - Evidence Pack: Hash computed and recorded
   - FAVES Gate: Must pass for LIVE mode deployments
   - Rollback Plan: Must be documented and tested
   - Monitoring: Dashboard must be configured

2. Deployment Mode Rules:
   - DEMO mode: CI + Evidence required, FAVES advisory only
   - STAGING mode: CI + Evidence + Rollback required
   - LIVE mode: ALL gates must pass - no exceptions

3. Gate Validation Process:
   - Check GitHub Actions workflow status
   - Verify evidence pack in evidence/models/{version}/
   - Compute and verify evidence pack hash
   - Check Model Registry for FAVES status
   - Verify rollback procedure documentation
   - Confirm monitoring dashboard configuration

4. On Gate Failure:
   - Block the deployment
   - Create GitHub issue with specific failures
   - Send Slack notification to release channel
   - Request human signoff if override needed

5. Evidence Pack Hash:
   - Compute SHA256 hash of all artifacts
   - Record hash in deployment record
   - Verify hash matches Model Registry

CRITICAL RULES:
- NEVER approve LIVE deployments with failing FAVES gates
- ALWAYS require human signoff for gate overrides
- ALWAYS notify Slack on deployment decisions
- ALWAYS create deployment record in Notion

Deployment Record Format:
{
    "model_id": "string",
    "version": "string",
    "mode": "DEMO|STAGING|LIVE",
    "gates": {
        "ci_checks": "passed|failed",
        "evidence_pack": "passed|failed",
        "faves_gate": "passed|failed|waived",
        "rollback_plan": "passed|failed",
        "monitoring": "passed|failed"
    },
    "evidence_hash": "sha256:...",
    "approved_by": "string|null",
    "deployed_at": "timestamp|null",
    "notes": "string"
}
"""
}


class ReleaseGuardianAgent:
    """Release Guardian Agent for deployment gate enforcement"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        entity_id: str = "default",
        github_repo: str = "ry86pkqf74-rgb/researchflow-production",
        slack_channel: str = "#deployments",
        notion_databases: Optional[Dict[str, str]] = None
    ):
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.entity_id = entity_id
        self.github_repo = github_repo
        self.slack_channel = slack_channel
        self.notion_databases = notion_databases or {
            "deployments": os.getenv("NOTION_DEPLOYMENTS_DB", ""),
            "model_registry": os.getenv("NOTION_MODEL_REGISTRY_DB", ""),
            "incidents": os.getenv("NOTION_INCIDENTS_DB", ""),
        }

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

        # Initialize LLM
        self.llm = ChatOpenAI(
            model=RELEASE_GUARDIAN_CONFIG["model"],
            temperature=RELEASE_GUARDIAN_CONFIG["temperature"],
            api_key=self.openai_api_key
        )

        # Get tools
        self.tools = self.toolset.get_tools(actions=RELEASE_GUARDIAN_CONFIG["actions"])

        # Create agent
        self.agent = self._create_agent()

    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent with Composio tools"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", RELEASE_GUARDIAN_CONFIG["system_prompt"]),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(self.llm, self.tools, prompt)

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=20,
            return_intermediate_steps=True
        )

    def validate_deployment(
        self,
        model_id: str,
        model_version: str,
        deployment_mode: str = "DEMO",
        commit_sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate all deployment gates for a release"""
        logger.info(f"Validating deployment: {model_id} v{model_version} ({deployment_mode})")

        gates_info = {
            name: {
                "description": gate.description,
                "required_for": gate.required_for,
                "checks": gate.checks
            }
            for name, gate in DEPLOYMENT_GATES.items()
        }

        commit_clause = f"- Commit SHA: {commit_sha}" if commit_sha else ""

        result = self.agent.invoke({
            "input": f"""Validate deployment gates for release:

Model: {model_id}
Version: {model_version}
Mode: {deployment_mode}
{commit_clause}

Deployment Gates to Check:
{json.dumps(gates_info, indent=2)}

Steps:
1. CI Checks Gate:
   - List GitHub Actions workflows for {self.github_repo}
   - Check status of latest workflow runs
   - Verify all required checks pass

2. Evidence Pack Gate:
   - Check evidence/models/{model_version}/ exists
   - Verify required artifacts present
   - Compute SHA256 hash of evidence pack

3. FAVES Gate (for {deployment_mode}):
   - Query Model Registry for FAVES status
   - {"ALL criteria must PASS" if deployment_mode == "LIVE" else "Advisory only - document status"}

4. Rollback Plan Gate:
   - Verify rollback documentation exists
   - Check previous version is tagged

5. Monitoring Gate:
   - Verify monitoring dashboard is configured
   - Check alert thresholds are set

Gate Requirements for {deployment_mode} mode:
{self._get_required_gates(deployment_mode)}

After validation:
- If ALL required gates pass → Approve deployment
- If ANY required gate fails → Block deployment

Actions on Result:
- Create deployment record in Notion Deployments database
- Send Slack notification to {self.slack_channel}
- Create GitHub issue if blocked (with failure details)

Repository: {self.github_repo}"""
        })

        return result

    def _get_required_gates(self, mode: str) -> str:
        """Get list of required gates for a deployment mode"""
        required = []
        advisory = []
        for name, gate in DEPLOYMENT_GATES.items():
            if mode in gate.required_for:
                required.append(f"- {gate.name}: REQUIRED")
            else:
                advisory.append(f"- {gate.name}: ADVISORY")
        return "\n".join(required + advisory)

    def check_ci_status(self, commit_sha: Optional[str] = None) -> Dict[str, Any]:
        """Check CI/CD pipeline status"""
        logger.info(f"Checking CI status for {self.github_repo}")

        sha_clause = f"for commit {commit_sha}" if commit_sha else "for the latest commit"

        result = self.agent.invoke({
            "input": f"""Check CI/CD pipeline status {sha_clause}:

Repository: {self.github_repo}

Steps:
1. List all GitHub Actions workflows
2. Get the latest run for each workflow
3. Check status of each run:
   - success → ✅ PASSED
   - failure → ❌ FAILED
   - pending/in_progress → ⏳ PENDING
4. Report overall CI status
5. List any failed checks with details

Required workflow checks:
- test (unit tests)
- lint (code quality)
- build (compilation)
- security (vulnerability scan)"""
        })

        return result

    def compute_evidence_hash(
        self,
        model_version: str
    ) -> Dict[str, Any]:
        """Compute SHA256 hash of evidence pack"""
        logger.info(f"Computing evidence hash for version: {model_version}")

        result = self.agent.invoke({
            "input": f"""Compute evidence pack hash:

Version: {model_version}
Evidence Path: evidence/models/{model_version}/

Steps:
1. List all files in evidence/models/{model_version}/
2. Compute SHA256 hash of each file
3. Combine hashes into a manifest
4. Compute final SHA256 of manifest
5. Format as: sha256:<hash>
6. Record hash in deployment record

Evidence files to include:
- Model artifacts (*.pkl, *.h5, *.pt, etc.)
- Validation results (*.json)
- Compliance checklists (tripodai_checklist.json, etc.)
- Disclosures (hti1_disclosure.md)
- Configuration files

Repository: {self.github_repo}"""
        })

        return result

    def create_release(
        self,
        model_id: str,
        model_version: str,
        deployment_mode: str,
        release_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a GitHub release after gates pass"""
        logger.info(f"Creating release: {model_id} v{model_version}")

        notes = release_notes or f"Release {model_version} for {deployment_mode} deployment"

        result = self.agent.invoke({
            "input": f"""Create GitHub release after gates validation:

Model: {model_id}
Version: {model_version}
Mode: {deployment_mode}

Steps:
1. First, validate all deployment gates for {deployment_mode}
2. If gates pass, create GitHub release:
   - Tag: v{model_version}
   - Title: {model_id} v{model_version} ({deployment_mode})
   - Body: {notes}
   - Include evidence pack hash
3. Update Model Registry with release info
4. Create deployment record in Notion
5. Send Slack notification

If any required gate fails:
- DO NOT create release
- Create GitHub issue with failures
- Notify via Slack

Repository: {self.github_repo}"""
        })

        return result

    def request_override(
        self,
        model_id: str,
        model_version: str,
        failed_gates: List[str],
        justification: str,
        requested_by: str
    ) -> Dict[str, Any]:
        """Request human override for failed gates (DEMO mode only)"""
        logger.info(f"Override requested for: {model_id} v{model_version}")

        result = self.agent.invoke({
            "input": f"""Process deployment override request:

Model: {model_id}
Version: {model_version}
Failed Gates: {', '.join(failed_gates)}
Justification: {justification}
Requested By: {requested_by}

IMPORTANT: Override is only allowed for DEMO mode deployments.
For LIVE mode, ALL gates must pass - no overrides allowed.

Steps:
1. Create GitHub issue for override request:
   - Title: "[Override Request] {model_id} v{model_version}"
   - Body: Include failed gates and justification
   - Labels: "deployment", "override-request", "needs-review"
   - Assign to release managers

2. Send Slack notification to {self.slack_channel}:
   - Alert release managers
   - Include link to GitHub issue
   - Request review within 24 hours

3. Update deployment record with:
   - Status: "pending_override"
   - Override justification
   - Requested by

4. DO NOT proceed with deployment until human approval

Repository: {self.github_repo}"""
        })

        return result

    def trigger_rollback(
        self,
        model_id: str,
        current_version: str,
        target_version: str,
        reason: str
    ) -> Dict[str, Any]:
        """Trigger emergency rollback procedure"""
        logger.info(f"ROLLBACK triggered: {model_id} {current_version} → {target_version}")

        result = self.agent.invoke({
            "input": f"""EMERGENCY ROLLBACK TRIGGERED:

Model: {model_id}
Current Version: {current_version}
Target Version: {target_version}
Reason: {reason}

IMMEDIATE ACTIONS:
1. Send URGENT Slack notification to {self.slack_channel}
   - @channel mention for immediate attention
   - Include rollback reason

2. Create incident record in Notion Incidents database:
   - Type: Rollback
   - Severity: High
   - Affected: {model_id}
   - Timeline: Started now

3. Verify target version exists and is deployable:
   - Check release tag v{target_version} exists
   - Verify evidence pack available

4. Create GitHub issue for rollback tracking:
   - Title: "[ROLLBACK] {model_id}: {current_version} → {target_version}"
   - Labels: "incident", "rollback", "priority:critical"

5. Update deployment record:
   - Mark current deployment as "rolled_back"
   - Record rollback timestamp and reason

6. Document post-mortem requirement:
   - Create follow-up issue for root cause analysis
   - Due within 48 hours

Repository: {self.github_repo}

THIS IS AN EMERGENCY PROCEDURE - Execute immediately."""
        })

        return result

    def get_deployment_status(
        self,
        model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current deployment status for models"""
        logger.info(f"Getting deployment status for: {model_id or 'all models'}")

        filter_clause = f"for model {model_id}" if model_id else "for all models"

        result = self.agent.invoke({
            "input": f"""Get deployment status {filter_clause}:

Steps:
1. Query Notion Deployments database
2. For each deployment, show:
   - Model ID and version
   - Deployment mode (DEMO/STAGING/LIVE)
   - Gate status summary
   - Deployed timestamp
   - Current status

3. Highlight any:
   - Pending deployments
   - Failed gates requiring attention
   - Recent rollbacks

4. Check GitHub for:
   - Latest releases
   - Pending PRs for deployment

Format as a clear status report."""
        })

        return result

    def run(self, task: str) -> Dict[str, Any]:
        """Run the agent with a custom task"""
        return self.agent.invoke({"input": task})


def main():
    """Demo the Release Guardian agent"""
    print("🛡️ Release Guardian Agent - Deployment Gate Enforcement")
    print("=" * 60)

    # Check for required environment variables
    if not os.getenv("COMPOSIO_API_KEY"):
        print("⚠️  Set COMPOSIO_API_KEY environment variable")
        return
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Set OPENAI_API_KEY environment variable")
        return

    agent = ReleaseGuardianAgent()

    # List available tools
    print("\n📦 Available tools:")
    for tool in agent.tools:
        print(f"  - {tool.name}")

    # Show deployment gates
    print("\n🚦 Deployment Gates:")
    for name, gate in DEPLOYMENT_GATES.items():
        modes = ", ".join(gate.required_for)
        print(f"  - {gate.name}: Required for [{modes}]")

    # Example task
    print("\n🚀 Running example task...")
    result = agent.run(
        "Check the CI status for the latest commit on main branch"
    )
    print(f"\n📋 Result: {result['output']}")


if __name__ == "__main__":
    main()
