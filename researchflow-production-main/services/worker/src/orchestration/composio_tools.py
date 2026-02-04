"""
Composio Toolset Configuration for ResearchFlow
Provides unified tool integrations for GitHub, Linear, Slack, Notion, and Docker.
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)

try:
    from composio_langchain import ComposioToolSet
    COMPOSIO_AVAILABLE = True
except ImportError:
    ComposioToolSet = None
    COMPOSIO_AVAILABLE = False
    logger.warning("Composio not installed. Run: pip install composio-langchain")


class ResearchFlowToolset:
    """
    Manages Composio tool integrations for ResearchFlow orchestration.
    Provides access to GitHub, Linear, Slack, Notion, and custom tools.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("COMPOSIO_API_KEY")
        self._toolset = None
        self._initialized_apps: List[str] = []
        
    @property
    def toolset(self) -> Optional["ComposioToolSet"]:
        """Lazy initialization of Composio toolset."""
        if self._toolset is None and COMPOSIO_AVAILABLE:
            self._toolset = ComposioToolSet(api_key=self.api_key)
        return self._toolset
    
    def initialize_apps(self) -> None:
        """Initialize all configured app integrations."""
        if self.toolset is None:
            raise RuntimeError("Composio not installed")
        
        # GitHub integration
        if os.getenv("GITHUB_TOKEN"):
            try:
                self.toolset.add_app("github", auth_token=os.getenv("GITHUB_TOKEN"))
                self._initialized_apps.append("github")
                logger.info("GitHub integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize GitHub: {e}")
        
        # Linear integration  
        if os.getenv("LINEAR_API_KEY"):
            try:
                self.toolset.add_app("linear", api_key=os.getenv("LINEAR_API_KEY"))
                self._initialized_apps.append("linear")
                logger.info("Linear integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Linear: {e}")
        
        # Slack integration
        if os.getenv("SLACK_WEBHOOK"):
            try:
                self.toolset.add_app("slack", webhook_url=os.getenv("SLACK_WEBHOOK"))
                self._initialized_apps.append("slack")
                logger.info("Slack integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Slack: {e}")
        
        # Notion integration
        if os.getenv("NOTION_API_KEY"):
            try:
                self.toolset.add_app("notion", api_key=os.getenv("NOTION_API_KEY"))
                self._initialized_apps.append("notion")
                logger.info("Notion integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Notion: {e}")
    
    def get_tools(self, apps: Optional[List[str]] = None) -> List:
        """Get LangChain-compatible tools for specified apps."""
        if self.toolset is None:
            return []
        
        if apps is None:
            apps = self._initialized_apps
        
        return self.toolset.get_tools(apps=apps)
    
    def execute_action(self, action_name: str, params: Dict[str, Any]) -> Any:
        """Execute a Composio action directly."""
        if self.toolset is None:
            raise RuntimeError("Composio not initialized")
        
        return self.toolset.execute_action(action_name, params)


@lru_cache(maxsize=1)
def get_toolset() -> ResearchFlowToolset:
    """Get or create the singleton toolset instance."""
    toolset = ResearchFlowToolset()
    try:
        toolset.initialize_apps()
    except Exception as e:
        logger.error(f"Failed to initialize toolset: {e}")
    return toolset


# Convenience exports
def get_github_tools():
    return get_toolset().get_tools(apps=["github"])

def get_linear_tools():
    return get_toolset().get_tools(apps=["linear"])

def get_slack_tools():
    return get_toolset().get_tools(apps=["slack"])

def get_notion_tools():
    return get_toolset().get_tools(apps=["notion"])

def get_all_tools():
    return get_toolset().get_tools()
