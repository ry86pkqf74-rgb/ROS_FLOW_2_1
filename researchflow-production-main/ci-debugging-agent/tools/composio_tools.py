#!/usr/bin/env python3
"""
Composio Tools Integration

GitHub, Linear, and other Composio-powered tools for CI debugging.
"""
import os
import sys
from typing import Optional
from dataclasses import dataclass

# Try to import Composio (requires Python 3.10+)
COMPOSIO_AVAILABLE = False
ComposioToolSet = None
Action = None
App = None

if sys.version_info >= (3, 10):
    try:
        from composio_langchain import ComposioToolSet, Action, App
        COMPOSIO_AVAILABLE = True
    except ImportError:
        pass

if not COMPOSIO_AVAILABLE:
    print("Note: Composio not available (requires Python 3.10+), using fallback tools")


@dataclass
class GitHubIssue:
    """GitHub issue representation."""
    title: str
    body: str
    labels: list[str]


@dataclass
class WorkflowRun:
    """GitHub Actions workflow run."""
    id: int
    name: str
    status: str
    conclusion: Optional[str]
    logs_url: str


def get_composio_toolset():
    """Get Composio toolset with API key."""
    if not COMPOSIO_AVAILABLE:
        return None
    
    api_key = os.environ.get('COMPOSIO_API_KEY', 'ak_YhbOJal4TkAsNUR0NX2j')
    return ComposioToolSet(api_key=api_key)


def get_github_tools():
    """Get GitHub tools from Composio."""
    toolset = get_composio_toolset()
    if not toolset:
        return []
    
    try:
        return toolset.get_tools(
            actions=[
                Action.GITHUB_GET_A_REPOSITORY,
                Action.GITHUB_LIST_REPOSITORY_ISSUES,
                Action.GITHUB_CREATE_AN_ISSUE,
                Action.GITHUB_GET_REPOSITORY_CONTENT,
                Action.GITHUB_LIST_REPOSITORY_WORKFLOWS,
            ]
        )
    except Exception as e:
        print(f"Error getting GitHub tools: {e}")
        return []


def get_linear_tools():
    """Get Linear tools from Composio."""
    toolset = get_composio_toolset()
    if not toolset:
        return []
    
    try:
        return toolset.get_tools(apps=[App.LINEAR])
    except Exception as e:
        print(f"Error getting Linear tools: {e}")
        return []


def create_github_issue(repo: str, issue: GitHubIssue) -> dict:
    """Create a GitHub issue for a bug found."""
    import subprocess
    
    # Use gh CLI as fallback
    try:
        result = subprocess.run(
            [
                "gh", "issue", "create",
                "--repo", repo,
                "--title", issue.title,
                "--body", issue.body,
                "--label", ",".join(issue.labels)
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_workflow_runs(repo: str, limit: int = 5) -> list[dict]:
    """Get recent workflow runs from GitHub."""
    import subprocess
    import json
    
    try:
        result = subprocess.run(
            [
                "gh", "run", "list",
                "--repo", repo,
                "--limit", str(limit),
                "--json", "databaseId,name,status,conclusion"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception as e:
        print(f"Error getting workflow runs: {e}")
        return []


def get_workflow_logs(repo: str, run_id: int) -> str:
    """Get logs from a workflow run."""
    import subprocess
    
    try:
        result = subprocess.run(
            ["gh", "run", "view", str(run_id), "--repo", repo, "--log"],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Error getting logs: {e}"
