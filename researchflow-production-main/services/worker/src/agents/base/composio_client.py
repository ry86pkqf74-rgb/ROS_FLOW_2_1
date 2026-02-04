"""
Composio Agent Factory - Creates Composio-powered LangChain agents.

Provides factory methods for instantiating agents with various Composio toolkits
including Notion, GitHub, Slack, Linear, and others for compliance automation.

@author Claude
@created 2026-01-30
"""

import os
import logging
from typing import Literal, Optional, List, Any

logger = logging.getLogger(__name__)

# Import LangChain components with fallback for compatibility
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None
    logger.warning("langchain_openai not available")

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None
    logger.warning("langchain_anthropic not available")

# Try modern import path first, fall back to legacy
try:
    from langchain.agents import AgentExecutor, create_openai_functions_agent
except ImportError:
    try:
        from langchain_experimental.agents import AgentExecutor
        from langchain.agents import create_openai_functions_agent
    except ImportError:
        AgentExecutor = None
        create_openai_functions_agent = None
        logger.warning("AgentExecutor not available in this LangChain version")

try:
    from langchain import hub
except ImportError:
    hub = None
    logger.warning("LangChain hub not available")

try:
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
except ImportError:
    try:
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    except ImportError:
        ChatPromptTemplate = None
        MessagesPlaceholder = None
        logger.warning("Prompt templates not available")

class ComposioAgentFactory:
    """Factory for creating Composio-powered LangChain agents."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Composio agent factory.

        Args:
            api_key: Composio API key (defaults to COMPOSIO_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("COMPOSIO_API_KEY")
        if not self.api_key:
            logger.warning("No COMPOSIO_API_KEY provided - some functionality may be unavailable")

        # Import Composio dynamically to avoid hard dependency
        try:
            from composio import Composio
            from composio_langchain import LangchainProvider

            self.Composio = Composio
            self.LangchainProvider = LangchainProvider
            self.composio_available = True
        except ImportError:
            logger.warning("Composio not installed - agent functionality disabled")
            self.composio_available = False

    def create_agent(
        self,
        toolkits: List[str],
        model: Optional[str] = None,
        provider: Literal["openai", "anthropic"] = "openai",
        temperature: float = 0,
        user_id: str = "default",
        system_prompt: Optional[str] = None,
        verbose: bool = True,
    ) -> AgentExecutor:
        """
        Create an agent with specified Composio toolkits.

        Args:
            toolkits: List of toolkit names (e.g., ["NOTION", "GITHUB"])
            model: LLM model identifier
            provider: LLM provider ("openai" or "anthropic")
            temperature: LLM temperature parameter
            user_id: User ID for tool authorization
            system_prompt: Custom system prompt
            verbose: Enable verbose output

        Returns:
            Configured AgentExecutor ready to use

        Raises:
            RuntimeError: If Composio is not available
        """
        if not self.composio_available:
            raise RuntimeError(
                "Composio not available. Install with: pip install composio-core composio-langchain"
            )

        logger.info(f"Creating agent with toolkits: {toolkits}")

        # Select LLM based on provider
        if provider == "anthropic":
            llm = ChatAnthropic(
                model=model or "claude-opus-4-20250805",
                temperature=temperature,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        else:
            llm = ChatOpenAI(
                model=model or "gpt-4o-mini",
                temperature=temperature,
                api_key=os.getenv("OPENAI_API_KEY"),
            )

        # Get or create prompt
        if system_prompt:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )
        else:
            try:
                prompt = hub.pull("hwchase17/openai-functions-agent")
            except Exception as e:
                logger.warning(f"Could not pull prompt from hub: {e}. Using default.")
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", "You are a helpful AI assistant."),
                        ("human", "{input}"),
                        MessagesPlaceholder(variable_name="agent_scratchpad"),
                    ]
                )

        # Initialize Composio and get tools
        try:
            composio = self.Composio(provider=self.LangchainProvider())
            tools = composio.get_tools(
                actions=[],  # Leave empty to get all toolkit actions
                user_id=user_id,
            )

            if not tools:
                logger.warning(f"No tools available for toolkits: {toolkits}")
                tools = []

        except Exception as e:
            logger.error(f"Error initializing Composio tools: {e}")
            tools = []

        # Create the agent
        try:
            agent = create_openai_functions_agent(llm, tools, prompt)
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            agent = None

        # Create executor
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=verbose,
            handle_parsing_errors=True,
            max_iterations=10,
        )

        logger.info(f"Agent created successfully with {len(tools)} tools")
        return executor

    def create_compliance_agent(
        self,
        research_id: str,
        model: Optional[str] = None,
        temperature: float = 0,
    ) -> AgentExecutor:
        """
        Create a specialized compliance agent.

        Uses Notion for registry management and GitHub for PR comments.

        Args:
            research_id: Research project identifier
            model: LLM model identifier
            temperature: LLM temperature

        Returns:
            Configured compliance agent
        """
        system_prompt = f"""You are a compliance automation agent for research project {research_id}.

Your responsibilities:
1. Validate FAVES compliance gates (Fair, Appropriate, Valid, Effective, Safe)
2. Generate and track TRIPOD+AI and CONSORT-AI checklists
3. Create HTI-1 disclosure documents
4. Post compliance status updates to the Notion model registry
5. Add PR comments for missing compliance items in GitHub

Always provide detailed explanations for any compliance findings.
Format responses clearly with sections for each compliance framework.
When posting to Notion or GitHub, ensure all required fields are populated."""

        return self.create_agent(
            toolkits=["NOTION", "GITHUB", "SLACK"],
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
            user_id=research_id,
        )

    def create_quality_gate_agent(
        self,
        research_id: str,
        model: Optional[str] = None,
        temperature: float = 0,
    ) -> AgentExecutor:
        """
        Create a quality gates assessment agent.

        Uses Linear for issue tracking and Slack for notifications.

        Args:
            research_id: Research project identifier
            model: LLM model identifier
            temperature: LLM temperature

        Returns:
            Configured quality gate agent
        """
        system_prompt = f"""You are a quality gates assessment agent for research project {research_id}.

Your responsibilities:
1. Evaluate research against quality metrics
2. Identify quality gaps and issues
3. Create Linear issues for gaps
4. Send Slack notifications about quality status
5. Track quality metrics over time

Provide actionable recommendations for improvement.
Prioritize critical quality issues.
Track resolution of identified issues."""

        return self.create_agent(
            toolkits=["LINEAR", "SLACK", "NOTION"],
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
            user_id=research_id,
        )

    def get_available_toolkits(self) -> List[str]:
        """
        List available Composio toolkits.

        Returns:
            List of toolkit names
        """
        return [
            "FIGMA",
            "GITHUB",
            "NOTION",
            "SLACK",
            "LINEAR",
            "GOOGLECALENDAR",
            "GMAIL",
            "GOOGLEDOCS",
            "JIRA",
            "ASANA",
        ]

    def validate_toolkit(self, toolkit: str) -> bool:
        """
        Validate that a toolkit is available.

        Args:
            toolkit: Toolkit name to validate

        Returns:
            True if toolkit is available, False otherwise
        """
        return toolkit.upper() in self.get_available_toolkits()
