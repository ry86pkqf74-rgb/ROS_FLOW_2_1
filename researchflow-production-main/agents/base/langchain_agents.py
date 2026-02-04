"""
ResearchFlow LangChain Agent Factory with Composio Integration

This module provides ready-to-use LangChain agents configured with
Composio toolkits for the ResearchFlow platform.
"""

import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from composio import Composio, Action
from composio_langchain import ComposioToolSet
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain import hub


class AgentType(Enum):
    """Available agent types in ResearchFlow"""
    DESIGN_OPS = "design_ops"
    SPEC_OPS = "spec_ops"
    COMPLIANCE = "compliance"
    RELEASE_GUARDIAN = "release_guardian"
    WIRING_AUDIT = "wiring_audit"
    ORCHESTRATION_FIX = "orchestration_fix"
    DOCKER_STACK = "docker_stack"


class ModelProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class AgentConfig:
    """Configuration for a ResearchFlow agent"""
    name: str
    description: str
    toolkits: List[str]
    actions: List[str]
    model: str
    temperature: float = 0
    provider: ModelProvider = ModelProvider.OPENAI
    system_prompt: Optional[str] = None
    max_iterations: int = 10
    return_intermediate_steps: bool = False
    verbose: bool = True
    handle_parsing_errors: bool = True


# Agent configurations matching the spec
AGENT_CONFIGS: Dict[AgentType, AgentConfig] = {
    AgentType.DESIGN_OPS: AgentConfig(
        name="DesignOps Agent",
        description="Figma → design tokens → PR automation",
        toolkits=["figma", "github"],
        actions=[
            "FIGMA_EXTRACT_DESIGN_TOKENS",
            "FIGMA_DESIGN_TOKENS_TO_TAILWIND",
            "FIGMA_CREATE_DEV_RESOURCES",
            "FIGMA_CREATE_WEBHOOK",
            "GITHUB_CREATE_BRANCH",
            "GITHUB_COMMIT_FILES",
            "GITHUB_CREATE_PULL_REQUEST",
            "GITHUB_ADD_REVIEWERS",
        ],
        model="gpt-4o",
        temperature=0,
        system_prompt="""You are the DesignOps Agent for ResearchFlow.

Your responsibilities:
1. Monitor Figma for design changes via webhooks
2. Extract design tokens from Figma components
3. Transform tokens to Tailwind CSS configuration
4. Generate/update packages/design-tokens/tokens.json
5. Generate/update tailwind.config.ts
6. Run lint and Storybook build validation
7. Open PRs with comprehensive change summaries
8. Add appropriate reviewers from the design team

Always ensure design token changes maintain backward compatibility.
Document all breaking changes clearly in PR descriptions."""
    ),

    AgentType.SPEC_OPS: AgentConfig(
        name="SpecOps Agent",
        description="Notion PRD → GitHub issues synchronization",
        toolkits=["notion", "github"],
        actions=[
            "NOTION_FETCH_DATABASE",
            "NOTION_FETCH_DATABASE_ROW",
            "NOTION_INSERT_ROW_DATABASE",
            "NOTION_UPDATE_PAGE",
            "GITHUB_CREATE_ISSUE",
            "GITHUB_CREATE_MILESTONE",
            "GITHUB_ADD_LABELS",
        ],
        model="gpt-4o-mini",  # Cost-efficient for extraction
        temperature=0,
        system_prompt="""You are the SpecOps Agent for ResearchFlow.

Your responsibilities:
1. Fetch PRD pages from Notion Problem Registry
2. Extract requirements and acceptance criteria
3. Parse user stories and technical specifications
4. Create GitHub issues with proper structure:
   - Clear title following convention
   - Detailed description with acceptance criteria
   - Appropriate labels (feature, bug, task, epic)
   - Milestone assignment
5. Update Notion with GitHub issue links
6. Maintain bidirectional sync between Notion and GitHub

Always include:
- User story format: "As a [role], I want [feature] so that [benefit]"
- Clear acceptance criteria as checkboxes
- Technical notes for implementation guidance"""
    ),

    AgentType.COMPLIANCE: AgentConfig(
        name="Compliance Agent",
        description="Auto-generate TRIPOD+AI, CONSORT-AI, HTI-1 disclosures",
        toolkits=["notion", "github"],
        actions=[
            "NOTION_FETCH_DATABASE",
            "NOTION_UPDATE_PAGE",
            "NOTION_CREATE_PAGE",
            "GITHUB_CREATE_ISSUE",
            "GITHUB_ADD_LABELS",
        ],
        model="gpt-4o",
        temperature=0,
        system_prompt="""You are the Compliance Agent for ResearchFlow.

Your responsibilities:
1. Validate TRIPOD+AI checklist (27 items) for AI/ML model reporting
2. Validate CONSORT-AI checklist (12 items) for trial reporting
3. Enforce FAVES gates:
   - Fair: Subgroup performance audit exists
   - Appropriate: Intended use + contraindications documented
   - Valid: Calibration + validation methodology documented
   - Effective: Outcome metrics or "research-only" label present
   - Safe: Monitoring plan + rollback procedure + incident playbook exist
4. Generate HTI-1 source attribute disclosures
5. Update Model Registry in Notion with compliance status
6. Create GitHub issues for missing compliance items

Evidence pack artifacts location: evidence/models/{version}/
Output files:
- tripodai_checklist.json
- consortai_checklist.json
- hti1_disclosure.md

Never approve a LIVE deployment without all FAVES gates passing."""
    ),

    AgentType.RELEASE_GUARDIAN: AgentConfig(
        name="Release Guardian Agent",
        description="Pre-deploy gate enforcement + rollback readiness",
        toolkits=["github", "notion"],
        actions=[
            "GITHUB_GET_CI_STATUS",
            "GITHUB_CREATE_ISSUE",
            "NOTION_FETCH_DATABASE_ROW",
            "NOTION_UPDATE_PAGE",
        ],
        model="gpt-4o",
        temperature=0,
        system_prompt="""You are the Release Guardian Agent for ResearchFlow.

Your responsibilities:
1. Enforce deployment gates:
   - CI Checks: All GitHub Actions workflows must pass
   - Evidence Pack: Hash must be computed and recorded
   - FAVES Gate: Must pass for LIVE mode deployments
   - Rollback Plan: Must be documented and tested
   - Monitoring: Dashboard must be configured

2. Validation checklist before approving:
   [ ] All CI checks passed
   [ ] Evidence pack hash computed and recorded
   [ ] FAVES gate passed (LIVE mode only)
   [ ] Rollback plan documented
   [ ] Monitoring dashboard configured

3. For DEMO mode: FAVES gate is advisory only
4. For LIVE mode: ALL gates must pass

Actions on failure:
- Block deployment
- Create GitHub issue with specific failures
- Notify via Slack
- Request human signoff if override needed

Never approve LIVE deployments with failing FAVES gates."""
    ),

    AgentType.WIRING_AUDIT: AgentConfig(
        name="Wiring Audit Agent",
        description="Docs ↔ Code ↔ Runtime wiring audit",
        toolkits=["github"],
        actions=[
            "GITHUB_GET_A_REPOSITORY",
            "GITHUB_GET_REPOSITORY_CONTENT",
            "GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS",
            "GITHUB_CREATE_ISSUE",
        ],
        model=os.getenv("WIRING_AUDIT_MODEL", "gpt-4o-mini"),
        temperature=0,
        max_iterations=15,
        return_intermediate_steps=True,
        system_prompt="""You are the Wiring Audit Agent for ResearchFlow.

Your responsibilities:
1. Review docs for wiring claims (routes, services, env vars)
2. Cross-check code mounts and docker-compose wiring
3. Identify gaps and mismatches with evidence
4. Update wiring reports with clear remediation steps

Primary sources:
- docs/audit/WIRING_TRUTH_TABLE.md
- docs/audit/GAP_MATRIX.md
- docs/MANUSCRIPT_STUDIO_WIRING_AUDIT.md
- docs/UI_WIRING_GUIDE.md
- services/orchestrator/src/index.ts
- docker-compose.yml

Always cite file paths and endpoints for each finding."""
    ),

    AgentType.ORCHESTRATION_FIX: AgentConfig(
        name="Orchestration Fix Agent",
        description="Frontend ↔ backend wiring remediation",
        toolkits=["github"],
        actions=[
            "GITHUB_GET_REPOSITORY_CONTENT",
            "GITHUB_CREATE_BRANCH",
            "GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS",
            "GITHUB_CREATE_PULL_REQUEST",
            "GITHUB_CREATE_ISSUE",
            "GITHUB_ADD_LABELS",
        ],
        model=os.getenv("ORCHESTRATION_FIX_MODEL", "gpt-4o"),
        temperature=0,
        max_iterations=20,
        return_intermediate_steps=True,
        system_prompt="""You are the Orchestration Fix Agent for ResearchFlow.

Your responsibilities:
1. Fix wiring gaps between frontend and backend routes
2. Align API payloads and response shapes
3. Update docker-compose and env examples when needed
4. Keep docs in sync with code changes

Always prefer minimal, backward-compatible fixes."""
    ),

    AgentType.DOCKER_STACK: AgentConfig(
        name="Docker Stack Launch Agent",
        description="Docker stack wiring & web launch readiness",
        toolkits=["docker", "github"],
        actions=[
            "DOCKER_LIST_CONTAINERS",
            "DOCKER_INSPECT_CONTAINER",
            "DOCKER_GET_CONTAINER_LOGS",
            "GITHUB_GET_REPOSITORY_CONTENT",
            "GITHUB_CREATE_OR_UPDATE_FILE_CONTENTS",
            "GITHUB_CREATE_ISSUE",
        ],
        model=os.getenv("DOCKER_STACK_MODEL", "gpt-4o"),
        temperature=0,
        max_iterations=15,
        return_intermediate_steps=True,
        system_prompt="""You are the Docker Stack Launch Agent for ResearchFlow.

Your responsibilities:
1. Validate docker-compose wiring for web/orchestrator/worker/collab
2. Ensure Vite build args and Nginx proxy settings align
3. Provide a launch checklist and health verification steps
4. Update docs/scripts if the launch flow is incomplete."""
    ),
}


class ResearchFlowAgentFactory:
    """Factory for creating ResearchFlow LangChain agents with Composio tools"""

    def __init__(
        self,
        composio_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        entity_id: str = "researchflow"
    ):
        """
        Initialize the agent factory.

        Args:
            composio_api_key: Composio API key (or use COMPOSIO_API_KEY env var)
            openai_api_key: OpenAI API key (or use OPENAI_API_KEY env var)
            anthropic_api_key: Anthropic API key (or use ANTHROPIC_API_KEY env var)
            entity_id: Composio entity ID for tool connections
        """
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.entity_id = entity_id

        # Initialize Composio toolset
        self.toolset = ComposioToolSet(
            api_key=self.composio_api_key,
            entity_id=self.entity_id
        )

    def _get_llm(self, config: AgentConfig):
        """Get the appropriate LLM based on config"""
        if config.provider == ModelProvider.ANTHROPIC:
            return ChatAnthropic(
                model=config.model,
                temperature=config.temperature,
                api_key=self.anthropic_api_key
            )
        else:
            return ChatOpenAI(
                model=config.model,
                temperature=config.temperature,
                api_key=self.openai_api_key
            )

    def _get_prompt(self, config: AgentConfig) -> ChatPromptTemplate:
        """Create the prompt template for an agent"""
        system_message = config.system_prompt or f"You are the {config.name}. {config.description}"

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

    def create_agent(
        self,
        agent_type: AgentType,
        custom_config: Optional[AgentConfig] = None
    ) -> AgentExecutor:
        """
        Create a LangChain agent with Composio tools.

        Args:
            agent_type: Type of agent to create
            custom_config: Optional custom configuration override

        Returns:
            AgentExecutor ready to run
        """
        config = custom_config or AGENT_CONFIGS[agent_type]

        # Get LLM
        llm = self._get_llm(config)

        # Get Composio tools for this agent's actions
        tools = self.toolset.get_tools(
            actions=[Action[action] for action in config.actions]
        )

        # Create prompt
        prompt = self._get_prompt(config)

        # Create agent
        agent = create_openai_functions_agent(llm, tools, prompt)

        # Create executor
        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=config.verbose,
            handle_parsing_errors=config.handle_parsing_errors,
            max_iterations=config.max_iterations,
            return_intermediate_steps=config.return_intermediate_steps,
        )

    def create_design_ops_agent(self) -> AgentExecutor:
        """Create the DesignOps agent (Figma → PR)"""
        return self.create_agent(AgentType.DESIGN_OPS)

    def create_spec_ops_agent(self) -> AgentExecutor:
        """Create the SpecOps agent (Notion → GitHub)"""
        return self.create_agent(AgentType.SPEC_OPS)

    def create_compliance_agent(self) -> AgentExecutor:
        """Create the Compliance agent (TRIPOD+AI, FAVES)"""
        return self.create_agent(AgentType.COMPLIANCE)

    def create_release_guardian_agent(self) -> AgentExecutor:
        """Create the Release Guardian agent (deployment gates)"""
        return self.create_agent(AgentType.RELEASE_GUARDIAN)

    def create_wiring_audit_agent(self) -> AgentExecutor:
        """Create the Wiring Audit agent (docs ↔ code ↔ runtime)"""
        return self.create_agent(AgentType.WIRING_AUDIT)

    def create_orchestration_fix_agent(self) -> AgentExecutor:
        """Create the Orchestration Fix agent (frontend ↔ backend wiring)"""
        return self.create_agent(AgentType.ORCHESTRATION_FIX)

    def create_docker_stack_agent(self) -> AgentExecutor:
        """Create the Docker Stack Launch agent (web stack readiness)"""
        return self.create_agent(AgentType.DOCKER_STACK)

    def get_available_actions(self, toolkit: str) -> List[str]:
        """Get available Composio actions for a toolkit"""
        try:
            actions = self.toolset.get_actions(apps=[toolkit])
            return [str(action) for action in actions]
        except Exception as e:
            return [f"Error fetching actions: {e}"]


# Convenience function for quick agent creation
def create_agent(
    agent_type: AgentType,
    entity_id: str = "researchflow"
) -> AgentExecutor:
    """
    Quick helper to create a ResearchFlow agent.

    Usage:
        from agents.base.langchain_agents import create_agent, AgentType

        agent = create_agent(AgentType.DESIGN_OPS)
        result = agent.invoke({"input": "Extract design tokens from Figma"})
    """
    factory = ResearchFlowAgentFactory(entity_id=entity_id)
    return factory.create_agent(agent_type)


# Example usage
if __name__ == "__main__":
    import asyncio

    print("🤖 ResearchFlow Agent Factory Demo")
    print("=" * 50)

    # Create factory
    factory = ResearchFlowAgentFactory()

    # List available agent types
    print("\nAvailable agents:")
    for agent_type in AgentType:
        config = AGENT_CONFIGS[agent_type]
        print(f"  - {config.name}: {config.description}")
        print(f"    Toolkits: {', '.join(config.toolkits)}")
        print(f"    Model: {config.model}")

    # Create and test an agent (if keys are available)
    if os.getenv("COMPOSIO_API_KEY") and os.getenv("OPENAI_API_KEY"):
        print("\n🧪 Testing SpecOps Agent...")
        agent = factory.create_spec_ops_agent()

        result = agent.invoke({
            "input": "List all databases in my Notion workspace"
        })
        print(f"Result: {result['output']}")
    else:
        print("\n⚠️  Set COMPOSIO_API_KEY and OPENAI_API_KEY to test agents")
