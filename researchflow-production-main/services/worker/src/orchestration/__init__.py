"""
ResearchFlow Orchestration Module

Provides LangChain, LangGraph, Composio, and LangSmith integrations
for AI-powered research workflow automation.

Components:
- composio_tools: Unified tool integrations (GitHub, Linear, Slack, Notion)
- composio_agents: 8 stage-specific agents for the 20-stage workflow
- llm_router: Multi-LLM routing with PHI detection
- langgraph_workflows: StateGraph workflows for research tasks
- langsmith_observability: Tracing, evaluation, and compliance monitoring
"""

# Composio Tools
from .composio_tools import (
    ResearchFlowToolset,
    get_toolset,
    get_github_tools,
    get_linear_tools,
    get_slack_tools,
    get_notion_tools,
    get_all_tools,
    COMPOSIO_AVAILABLE,
)

# Composio Agents (8 recommended agents)
from .composio_agents import (
    ResearchFlowAgents,
    AgentConfig,
    WorkflowStage,
    get_lit_agent,
    get_writer_agent,
    get_code_agent,
    get_notifier_agent,
)

# LLM Router
from .llm_router import (
    LLMRouter,
    PHIDetector,
    RoutingDecision,
    get_router,
    route_task,
)

# LangGraph Workflows
from .langgraph_workflows import (
    WorkflowState,
    ResearchWorkflow,
    create_research_workflow,
)

# LangSmith Observability (8 monitoring tasks)
from .langsmith_observability import (
    LangSmithObservability,
    TraceMetrics,
    get_observability,
    trace,
    configure_langsmith,
)

__all__ = [
    # Composio Tools
    'ResearchFlowToolset',
    'get_toolset',
    'get_github_tools',
    'get_linear_tools', 
    'get_slack_tools',
    'get_notion_tools',
    'get_all_tools',
    'COMPOSIO_AVAILABLE',
    
    # Composio Agents
    'ResearchFlowAgents',
    'AgentConfig',
    'WorkflowStage',
    'get_lit_agent',
    'get_writer_agent',
    'get_code_agent',
    'get_notifier_agent',
    
    # LLM Router
    'LLMRouter',
    'PHIDetector',
    'RoutingDecision',
    'get_router',
    'route_task',
    
    # LangGraph Workflows
    'WorkflowState',
    'ResearchWorkflow',
    'create_research_workflow',
    
    # LangSmith Observability
    'LangSmithObservability',
    'TraceMetrics',
    'get_observability',
    'trace',
    'configure_langsmith',
]

__version__ = '1.1.0'
