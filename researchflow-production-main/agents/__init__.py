"""
ResearchFlow AI Agent Suite

This package provides specialized AI agents for the ResearchFlow platform:

- DesignOps Agent: Figma → Design Tokens → PR automation
- SpecOps Agent: Notion PRD → GitHub Issues synchronization
- Compliance Agent: TRIPOD+AI, CONSORT-AI, HTI-1, FAVES validation
- Release Guardian Agent: Deployment gate enforcement
- Docker Operations Agent: Container management for model deployment

All agents are built on LangChain with Composio toolkit integration.
"""

from agents.design_ops_agent import DesignOpsAgent
from agents.spec_ops_agent import SpecOpsAgent
from agents.compliance_agent import ComplianceAgent
from agents.release_guardian_agent import ReleaseGuardianAgent
from agents.docker_ops_agent import DockerOpsAgent
from agents.wiring_audit_agent import WiringAuditAgent
from agents.orchestration_fix_agent import OrchestrationFixAgent
from agents.docker_stack_agent import DockerStackAgent
from agents.orchestrator import ResearchFlowOrchestrator
from agents.base.langchain_agents import (
    ResearchFlowAgentFactory,
    AgentType,
    AgentConfig,
    ModelProvider,
    create_agent,
)

__all__ = [
    # Specialized Agents
    "DesignOpsAgent",
    "SpecOpsAgent",
    "ComplianceAgent",
    "ReleaseGuardianAgent",
    "DockerOpsAgent",
    "WiringAuditAgent",
    "OrchestrationFixAgent",
    "DockerStackAgent",
    # Orchestrator
    "ResearchFlowOrchestrator",
    # Factory and Helpers
    "ResearchFlowAgentFactory",
    "AgentType",
    "AgentConfig",
    "ModelProvider",
    "create_agent",
]

__version__ = "0.1.0"
