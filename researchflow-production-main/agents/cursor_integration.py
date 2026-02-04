#!/usr/bin/env python3
"""
Cursor ↔ LangChain ↔ Composio Integration

This module provides the bridge for Cursor to call ResearchFlow services
via LangChain agents and Composio toolkits.

Usage:
1. Set environment variables:
   - RF_BASE_URL: ResearchFlow orchestrator URL (e.g., http://localhost:3001)
   - RF_ACCESS_TOKEN: Access token from Testros login
   - COMPOSIO_API_KEY: Your Composio API key
   - OPENAI_API_KEY: For LangChain agent LLM

2. Run this script or import as module:
   python cursor_integration.py

3. From Cursor, call exposed tools via HTTP or direct import.

@author Claude
@created 2026-01-30
"""

import os
import json
import asyncio
import logging
import time
import random
from typing import Dict, Any, List, Optional, Callable, TypeVar
from dataclasses import dataclass
from functools import wraps
import aiohttp
import requests

T = TypeVar('T')


# =============================================================================
# Retry Logic with Exponential Backoff
# =============================================================================

class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 30.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)
    retryable_exceptions: tuple = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.ChunkedEncodingError,
    )


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_status_codes: tuple = (429, 500, 502, 503, 504),
) -> Callable:
    """
    Decorator for retrying HTTP requests with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        retryable_status_codes: HTTP status codes that trigger retry

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # Check if result is a requests.Response with retryable status
                    if hasattr(result, 'status_code'):
                        if result.status_code in retryable_status_codes:
                            if attempt < max_retries:
                                delay = min(base_delay * (2 ** attempt), max_delay)
                                # Add jitter (±25%)
                                delay = delay * (0.75 + random.random() * 0.5)
                                logger.warning(
                                    f"[Retry] Attempt {attempt + 1}/{max_retries + 1} failed "
                                    f"with status {result.status_code}. Retrying in {delay:.2f}s..."
                                )
                                time.sleep(delay)
                                continue

                    return result

                except RetryConfig.retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        delay = delay * (0.75 + random.random() * 0.5)
                        logger.warning(
                            f"[Retry] Attempt {attempt + 1}/{max_retries + 1} failed "
                            f"with {type(e).__name__}: {e}. Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        raise

            if last_exception:
                raise last_exception
            return result

        return wrapper
    return decorator


def make_request_with_retry(
    method: str,
    url: str,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    timeout: int = 30,
    max_retries: int = 3,
) -> requests.Response:
    """
    Make an HTTP request with automatic retry and exponential backoff.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Request headers
        json_data: JSON body for POST/PUT requests
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Response object
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=json_data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check for retryable status codes
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < max_retries:
                    delay = min(1.0 * (2 ** attempt), 30.0)
                    delay = delay * (0.75 + random.random() * 0.5)
                    logger.warning(
                        f"[Retry] {method} {url} returned {response.status_code}. "
                        f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})..."
                    )
                    time.sleep(delay)
                    continue

            return response

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError) as e:
            last_exception = e
            if attempt < max_retries:
                delay = min(1.0 * (2 ** attempt), 30.0)
                delay = delay * (0.75 + random.random() * 0.5)
                logger.warning(
                    f"[Retry] {method} {url} failed with {type(e).__name__}. "
                    f"Retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries + 1})..."
                )
                time.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception
    return response

# LangChain imports (v1.2+ compatible)
from langchain_core.tools import tool, StructuredTool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# LangGraph imports for agent creation (LangChain v1.2+)
try:
    from langgraph.prebuilt import create_react_agent
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("[WARN] LangGraph not available. Agent creation will be limited.")

# Composio imports (optional - graceful fallback)
try:
    from composio_langchain import LangchainProvider
    from composio import Composio
    COMPOSIO_AVAILABLE = True
except ImportError:
    COMPOSIO_AVAILABLE = False
    LangchainProvider = None
    print("[WARN] Composio not installed. Install with: pip install composio-core composio-langchain")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ResearchFlowConfig:
    """Configuration for ResearchFlow API access"""
    base_url: str
    access_token: str

    @classmethod
    def from_env(cls) -> 'ResearchFlowConfig':
        return cls(
            base_url=os.getenv("RF_BASE_URL", "http://localhost:3001"),
            access_token=os.getenv("RF_ACCESS_TOKEN", "")
        )

    def auth_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }


# Global config
_config: Optional[ResearchFlowConfig] = None

def get_config() -> ResearchFlowConfig:
    global _config
    if _config is None:
        _config = ResearchFlowConfig.from_env()
    return _config


# =============================================================================
# ResearchFlow API Tools (LangChain)
# =============================================================================

@tool
def researchflow_chat(prompt: str, model: str = "auto") -> str:
    """
    Chat with ResearchFlow AI router.

    Args:
        prompt: The user prompt to send
        model: Model to use (auto, gpt-4o, claude-opus-4-20250805, etc.)

    Returns:
        AI response content
    """
    config = get_config()

    # Use retry logic for reliability
    response = make_request_with_retry(
        method='POST',
        url=f"{config.base_url}/api/ai/chat",
        headers=config.auth_headers(),
        json_data={
            "messages": [{"role": "user", "content": prompt}],
            "model": model
        },
        timeout=120,
        max_retries=3
    )

    if not response.ok:
        return f"Error: {response.status_code} - {response.text}"

    data = response.json()
    return data.get("content", data.get("message", str(data)))


@tool
def researchflow_invoke(task_type: str, input_data: str, research_id: str = "default") -> str:
    """
    Invoke a specific AI task on ResearchFlow.

    Args:
        task_type: Task type (protocol_reasoning, hypothesis_critique, etc.)
        input_data: JSON string of input data for the task
        research_id: Research project ID

    Returns:
        Task result
    """
    config = get_config()

    try:
        payload = json.loads(input_data) if isinstance(input_data, str) else input_data
    except json.JSONDecodeError:
        payload = {"content": input_data}

    # Use retry logic for reliability
    response = make_request_with_retry(
        method='POST',
        url=f"{config.base_url}/api/ai/invoke",
        headers=config.auth_headers(),
        json_data={
            "taskType": task_type,
            "input": payload,
            "researchId": research_id
        },
        timeout=180,
        max_retries=3
    )

    if not response.ok:
        return f"Error: {response.status_code} - {response.text}"

    return json.dumps(response.json(), indent=2)


@tool
def researchflow_create_workflow(name: str, description: str, template_key: str = "custom") -> str:
    """
    Create a new workflow in ResearchFlow.

    Args:
        name: Workflow name
        description: Workflow description
        template_key: Template key (custom, literature_review, clinical_trial, etc.)

    Returns:
        Created workflow details
    """
    config = get_config()

    response = requests.post(
        f"{config.base_url}/api/workflows",
        headers=config.auth_headers(),
        json={
            "name": name,
            "description": description,
            "templateKey": template_key,
            "definition": {"steps": []}
        },
        timeout=30
    )

    if not response.ok:
        return f"Error: {response.status_code} - {response.text}"

    return json.dumps(response.json(), indent=2)


@tool
def researchflow_list_workflows() -> str:
    """
    List all workflows in ResearchFlow.

    Returns:
        List of workflows
    """
    config = get_config()

    response = requests.get(
        f"{config.base_url}/api/workflows",
        headers=config.auth_headers(),
        timeout=30
    )

    if not response.ok:
        return f"Error: {response.status_code} - {response.text}"

    return json.dumps(response.json(), indent=2)


@tool
def researchflow_embeddings(text: str) -> str:
    """
    Generate embeddings for text using ResearchFlow.

    Args:
        text: Text to embed

    Returns:
        Embedding vector as JSON
    """
    config = get_config()

    response = requests.post(
        f"{config.base_url}/api/ai/embeddings",
        headers=config.auth_headers(),
        json={"input": text},
        timeout=60
    )

    if not response.ok:
        return f"Error: {response.status_code} - {response.text}"

    data = response.json()
    # Return summary since full embeddings are large
    if "embedding" in data:
        return f"Embedding generated: {len(data['embedding'])} dimensions"
    return json.dumps(data, indent=2)


@tool
def researchflow_health_check() -> str:
    """
    Check ResearchFlow service health.

    Returns:
        Health status of all services
    """
    config = get_config()

    try:
        response = requests.get(
            f"{config.base_url}/health",
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.ok:
            return f"✅ ResearchFlow is healthy: {response.json()}"
        else:
            return f"⚠️ Health check returned {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "❌ Cannot connect to ResearchFlow. Is the service running?"
    except Exception as e:
        return f"❌ Health check failed: {str(e)}"


# =============================================================================
# Composio Integration
# =============================================================================

def get_composio_tools(apps: List[str] = None) -> List:
    """
    Get Composio tools for specified apps.

    Args:
        apps: List of Composio app names (GITHUB, NOTION, SLACK, etc.)

    Returns:
        List of LangChain tools
    """
    if not COMPOSIO_AVAILABLE or LangchainProvider is None:
        logger.warning("Composio not available")
        return []

    apps = apps or ["GITHUB", "NOTION", "SLACK"]

    try:
        api_key = os.getenv("COMPOSIO_API_KEY")
        if not api_key:
            logger.warning("COMPOSIO_API_KEY not set")
            return []

        # Use new LangchainProvider API
        provider = LangchainProvider(api_key=api_key)
        return provider.get_tools(apps=apps)
    except Exception as e:
        logger.error(f"Failed to get Composio tools: {e}")
        return []


# =============================================================================
# Combined Agent Factory
# =============================================================================

class CursorAgentFactory:
    """Factory for creating agents that Cursor can use"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        composio_api_key: Optional[str] = None,
        rf_base_url: Optional[str] = None,
        rf_access_token: Optional[str] = None
    ):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.composio_api_key = composio_api_key or os.getenv("COMPOSIO_API_KEY")

        # Configure ResearchFlow
        global _config
        _config = ResearchFlowConfig(
            base_url=rf_base_url or os.getenv("RF_BASE_URL", "http://localhost:3001"),
            access_token=rf_access_token or os.getenv("RF_ACCESS_TOKEN", "")
        )

        # LLM initialized lazily (only when creating agents)
        self._llm = None

    @property
    def llm(self):
        """Lazily initialize LLM only when needed"""
        if self._llm is None:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY required for agent creation")
            self._llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                api_key=self.openai_api_key
            )
        return self._llm

    def get_researchflow_tools(self) -> List:
        """Get all ResearchFlow API tools"""
        return [
            researchflow_chat,
            researchflow_invoke,
            researchflow_create_workflow,
            researchflow_list_workflows,
            researchflow_embeddings,
            researchflow_health_check
        ]

    def create_agent(
        self,
        include_composio: bool = True,
        composio_apps: List[str] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Create a combined agent with ResearchFlow + Composio tools.

        Args:
            include_composio: Include Composio tools
            composio_apps: Specific Composio apps to include
            system_prompt: Custom system prompt

        Returns:
            Configured LangGraph agent (or dict with tools if LangGraph unavailable)
        """
        # Collect tools
        tools = self.get_researchflow_tools()

        if include_composio and COMPOSIO_AVAILABLE:
            composio_tools = get_composio_tools(composio_apps)
            tools.extend(composio_tools)

        # Create prompt
        default_prompt = """You are a research assistant with access to ResearchFlow services and external tools.

Available capabilities:
1. ResearchFlow AI: Chat, invoke tasks, manage workflows, generate embeddings
2. Composio: GitHub, Notion, Slack, and other integrations

When asked to perform tasks:
- Use researchflow_chat for general AI interactions
- Use researchflow_invoke for specific task types
- Use researchflow_create_workflow to set up new research workflows
- Use Composio tools for external service interactions

Always check service health before performing complex operations."""

        # Use LangGraph's create_react_agent (LangChain v1.2+)
        if LANGGRAPH_AVAILABLE:
            return create_react_agent(
                self.llm,
                tools,
                prompt=system_prompt or default_prompt
            )
        else:
            # Fallback: return tools and LLM for manual use
            logger.warning("LangGraph not available, returning tools dict for manual use")
            return {
                "llm": self.llm,
                "tools": tools,
                "system_prompt": system_prompt or default_prompt
            }


# =============================================================================
# Token Helper
# =============================================================================

def login_testros(base_url: str = None) -> Dict[str, Any]:
    """
    Login using Testros backdoor and get access token.

    Args:
        base_url: ResearchFlow base URL

    Returns:
        Login response with access token
    """
    url = base_url or os.getenv("RF_BASE_URL", "http://localhost:3001")

    response = requests.post(
        f"{url}/api/auth/login",
        headers={"Content-Type": "application/json"},
        json={"username": "Testros"},
        timeout=30
    )

    if not response.ok:
        raise Exception(f"Login failed: {response.status_code} - {response.text}")

    data = response.json()

    # Set in environment for subsequent calls
    if "accessToken" in data:
        os.environ["RF_ACCESS_TOKEN"] = data["accessToken"]
        global _config
        _config = None  # Reset to pick up new token

    return data


# =============================================================================
# CLI / Main
# =============================================================================

def main():
    """Demo the Cursor integration"""
    print("🔗 Cursor ↔ LangChain ↔ Composio Integration")
    print("=" * 60)

    # Check environment
    print("\n📋 Environment Check:")
    rf_url = os.getenv("RF_BASE_URL", "http://localhost:3001")
    print(f"  RF_BASE_URL: {rf_url}")
    print(f"  RF_ACCESS_TOKEN: {'✅ Set' if os.getenv('RF_ACCESS_TOKEN') else '❌ Not set'}")
    print(f"  OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"  COMPOSIO_API_KEY: {'✅ Set' if os.getenv('COMPOSIO_API_KEY') else '❌ Not set'}")
    print(f"  Composio Available: {'✅ Yes' if COMPOSIO_AVAILABLE else '❌ No'}")

    # Try to get token via Testros if not set
    if not os.getenv("RF_ACCESS_TOKEN"):
        print("\n🔑 Attempting Testros login...")
        try:
            result = login_testros(rf_url)
            print(f"  ✅ Logged in as: {result.get('user', {}).get('email', 'unknown')}")
            print(f"  Token: {result.get('accessToken', '')[:50]}...")
        except Exception as e:
            print(f"  ❌ Login failed: {e}")
            print("  Make sure ResearchFlow is running!")
            return

    # Check health
    print("\n🏥 Health Check:")
    health = researchflow_health_check.invoke({})
    print(f"  {health}")

    # List tools
    print("\n🔧 Available Tools:")
    factory = CursorAgentFactory()
    for tool in factory.get_researchflow_tools():
        print(f"  - {tool.name}: {tool.description[:60]}...")

    # Example usage
    print("\n📝 Example Usage:")
    print("""
    from cursor_integration import CursorAgentFactory, login_testros

    # Login (sets RF_ACCESS_TOKEN automatically)
    login_testros("http://localhost:3001")

    # Create agent
    factory = CursorAgentFactory()
    agent = factory.create_agent(include_composio=True)

    # Run task
    result = agent.invoke({"input": "List my ResearchFlow workflows"})
    print(result["output"])
    """)


if __name__ == "__main__":
    main()
