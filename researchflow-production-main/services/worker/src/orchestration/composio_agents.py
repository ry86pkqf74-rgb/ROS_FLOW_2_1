"""
Composio Agents for ResearchFlow 20-Stage Workflow

Implements 8 recommended agents from Grok analysis:
1. Literature Retrieval Agent
2. Data Analysis Agent
3. Manuscript Writer Agent
4. Conference Prep Task
5. Code Generation Agent
6. Collaboration Notifier Agent
7. Feedback Analyzer Task
8. Deep Research Sub-Agent
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from composio_langchain import ComposioToolSet, App, Action
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langgraph import Agent
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    logger.warning("Required dependencies not installed")


class WorkflowStage(Enum):
    """ResearchFlow 20-stage workflow mapping"""
    PROPOSAL = (1, 3)           # Stage 1-3
    REFINEMENT = (4, 8)         # Stage 4-8
    CODE_EXECUTION = (9, 11)    # Stage 9-11
    STATS_VIZ = (10, 12)        # Stage 10-12
    CONFERENCE = (20, 20)       # Stage 20


@dataclass
class AgentConfig:
    """Configuration for a Composio agent"""
    name: str
    description: str
    apps: List[str]
    stages: tuple
    llm_provider: str = "openai"  # openai, anthropic, local


class ResearchFlowAgents:
    """
    Factory for creating stage-specific Composio agents.
    
    Usage:
        agents = ResearchFlowAgents()
        lit_agent = agents.get_agent('literature_retrieval')
        result = lit_agent.run('Find papers on AI ethics')
    """
    
    AGENT_CONFIGS = {
        'literature_retrieval': AgentConfig(
            name='Literature Retrieval Agent',
            description='Searches/fetches papers from PubMed/Semantic Scholar',
            apps=['pubmed', 'semanticscholar', 'googledocs'],
            stages=(1, 3),
            llm_provider='openai'
        ),
        'data_analysis': AgentConfig(
            name='Data Analysis Agent',
            description='Analyzes datasets, generates plots in Sheets/Notion',
            apps=['googlesheets', 'notion'],
            stages=(10, 12),
            llm_provider='openai'
        ),
        'manuscript_writer': AgentConfig(
            name='Manuscript Writer Agent',
            description='Generates/refines proposals and manuscripts',
            apps=['googledocs'],
            stages=(4, 8),
            llm_provider='anthropic'
        ),
        'conference_prep': AgentConfig(
            name='Conference Prep Task',
            description='Discovers conferences, parses guidelines, generates abstracts',
            apps=['googlecalendar', 'slack', 'googledocs'],
            stages=(20, 20),
            llm_provider='openai'
        ),
        'code_generation': AgentConfig(
            name='Code Generation Agent',
            description='Generates/optimizes code for stats pipelines',
            apps=['github'],
            stages=(9, 11),
            llm_provider='local'
        ),
        'collaboration_notifier': AgentConfig(
            name='Collaboration Notifier Agent',
            description='Updates team via Slack/Notion on workflow progress',
            apps=['slack', 'notion'],
            stages=(1, 20),  # All stages
            llm_provider='openai'
        ),
        'feedback_analyzer': AgentConfig(
            name='Feedback Analyzer Task',
            description='Reads feedback from CSVs/Forms, summarizes for refinement',
            apps=['googleforms', 'googlesheets'],
            stages=(1, 20),  # Post-workflow
            llm_provider='openai'
        ),
        'deep_research': AgentConfig(
            name='Deep Research Sub-Agent',
            description='Multi-step research with web scraping and synthesis',
            apps=['exa', 'firecrawl', 'notion'],
            stages=(1, 3),
            llm_provider='anthropic'
        ),
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('COMPOSIO_API_KEY')
        self._toolset = None
        self._agents: Dict[str, Any] = {}
        
    @property
    def toolset(self) -> Optional['ComposioToolSet']:
        if self._toolset is None and DEPS_AVAILABLE:
            self._toolset = ComposioToolSet(api_key=self.api_key)
        return self._toolset
    
    def _get_llm(self, provider: str):
        """Get LLM based on provider preference"""
        if provider == 'anthropic':
            return ChatAnthropic(model='claude-3-5-sonnet-20241022', temperature=0)
        elif provider == 'local':
            # Use Ollama via OpenAI-compatible endpoint
            return ChatOpenAI(
                model='qwen2.5-coder:7b',
                base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434/v1'),
                api_key='ollama'
            )
        else:
            return ChatOpenAI(model='gpt-4o', temperature=0)
    
    def get_agent(self, agent_type: str) -> Optional['Agent']:
        """
        Get or create an agent by type.
        
        Args:
            agent_type: One of the AGENT_CONFIGS keys
            
        Returns:
            Configured LangGraph Agent with Composio tools
        """
        if not DEPS_AVAILABLE:
            logger.error("Dependencies not available")
            return None
            
        if agent_type not in self.AGENT_CONFIGS:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        if agent_type in self._agents:
            return self._agents[agent_type]
            
        config = self.AGENT_CONFIGS[agent_type]
        
        # Get tools for this agent's apps
        try:
            tools = self.toolset.get_tools(apps=config.apps)
        except Exception as e:
            logger.warning(f"Could not get tools for {config.apps}: {e}")
            tools = []
            
        # Create agent with appropriate LLM
        llm = self._get_llm(config.llm_provider)
        
        agent = Agent(
            tools=tools,
            llm=llm,
            planner='zero-shot-react'
        )
        
        self._agents[agent_type] = agent
        logger.info(f"Created agent: {config.name}")
        
        return agent
    
    def get_agents_for_stage(self, stage: int) -> List[str]:
        """Get agent types relevant for a workflow stage"""
        relevant = []
        for agent_type, config in self.AGENT_CONFIGS.items():
            start, end = config.stages
            if start <= stage <= end:
                relevant.append(agent_type)
        return relevant
    
    def run_agent(self, agent_type: str, task: str) -> Dict[str, Any]:
        """
        Run an agent with a task.
        
        Args:
            agent_type: Type of agent to use
            task: Task description
            
        Returns:
            Dict with result and metadata
        """
        agent = self.get_agent(agent_type)
        if agent is None:
            return {'error': 'Agent not available', 'result': None}
            
        config = self.AGENT_CONFIGS[agent_type]
        
        try:
            result = agent.run(task)
            return {
                'agent': config.name,
                'task': task,
                'result': result,
                'apps_used': config.apps,
                'error': None
            }
        except Exception as e:
            logger.error(f"Agent {agent_type} failed: {e}")
            return {
                'agent': config.name,
                'task': task,
                'result': None,
                'error': str(e)
            }


# Convenience functions
def get_lit_agent():
    return ResearchFlowAgents().get_agent('literature_retrieval')

def get_writer_agent():
    return ResearchFlowAgents().get_agent('manuscript_writer')

def get_code_agent():
    return ResearchFlowAgents().get_agent('code_generation')

def get_notifier_agent():
    return ResearchFlowAgents().get_agent('collaboration_notifier')


# Example usage
if __name__ == '__main__':
    agents = ResearchFlowAgents()
    
    # Get agents for Stage 3 (Lit Review)
    stage_3_agents = agents.get_agents_for_stage(3)
    print(f"Stage 3 agents: {stage_3_agents}")
    
    # Run literature retrieval
    result = agents.run_agent(
        'literature_retrieval',
        'Find recent papers on thyroid cancer AI diagnosis'
    )
    print(result)
