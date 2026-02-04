"""
CI Debugging Agent Configuration Settings
"""
import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GitHubConfig:
    """GitHub configuration settings."""
    owner: str = field(default_factory=lambda: os.getenv("GITHUB_OWNER", "ry86pkqf74-rgb"))
    repo: str = field(default_factory=lambda: os.getenv("GITHUB_REPO", "researchflow-production"))
    token: Optional[str] = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))
    default_branch: str = "main"


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class ComposioConfig:
    """Composio configuration settings."""
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("COMPOSIO_API_KEY"))
    user_id: str = field(default_factory=lambda: os.getenv("COMPOSIO_USER_ID", "ci-debugging-agent"))


@dataclass
class AgentConfig:
    """Agent behavior configuration."""
    max_iterations: int = 10
    max_retries: int = 3
    verbose: bool = True
    auto_fix: bool = False  # Whether to auto-apply fixes
    create_issues: bool = True  # Whether to create GitHub issues for found bugs
    create_prs: bool = False  # Whether to create PRs for fixes


@dataclass
class DebugTargets:
    """Debugging target configuration."""
    typescript_errors: bool = True
    docker_issues: bool = True
    frontend_issues: bool = True
    api_issues: bool = True
    security_issues: bool = True
    dependency_issues: bool = True


@dataclass
class Settings:
    """Main settings container."""
    github: GitHubConfig = field(default_factory=GitHubConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    composio: ComposioConfig = field(default_factory=ComposioConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    targets: DebugTargets = field(default_factory=DebugTargets)


# Global settings instance
settings = Settings()
