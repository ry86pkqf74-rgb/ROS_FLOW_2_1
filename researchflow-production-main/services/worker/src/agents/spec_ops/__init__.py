"""
SpecOps Agent - Notion PRD → GitHub Issues Automation (Phase 1.3)

This package provides the SpecOps Agent for bidirectional synchronization
of Notion PRD (Product Requirements Document) pages to GitHub issues.

Features:
- Parse PRD pages from Notion Problem Registry
- Extract structured requirements and acceptance criteria
- Generate GitHub issues with proper labels and milestones
- Update Notion with GitHub issue links
- Maintain version history and change tracking

Architecture:
- NotionPRDParser: Extract requirements from Notion pages
- IssueCreator: Generate GitHub issues
- LabelManager: Manage GitHub labels
- MilestoneMapper: Map PRD phases to milestones
- NotionLinkUpdater: Update Notion with links
- SpecOpsAgent: Main orchestration agent

Model: gpt-4o-mini (cost-efficient extraction/summarization)

Linear Issues: ROS-105, ROS-106

Example:
```python
from agents.spec_ops import create_spec_ops_agent

agent = create_spec_ops_agent(
    notion_token="ntn_...",
    github_token="ghp_...",
    github_repo="owner/repo"
)

result = await agent.execute(
    task_id="spec_ops_001",
    prd_page_id="notion_page_id"
)
```
"""

from .templates import (
    FEATURE_ISSUE_TEMPLATE,
    BUG_ISSUE_TEMPLATE,
    TASK_ISSUE_TEMPLATE,
    EPIC_ISSUE_TEMPLATE,
    get_template,
    format_template,
    validate_template_fields,
)

from .prd_parser import (
    Requirement,
    UserStory,
    AcceptanceCriteria,
    NotionPRDParser,
    RequirementExtractor,
    AcceptanceCriteriaParser,
    UserStoryGenerator,
)

from .github_sync import (
    GitHubIssue,
    Milestone,
    IssueCreator,
    LabelManager,
    MilestoneMapper,
    NotionLinkUpdater,
)

from .agent import (
    SpecOpsAgent,
    SpecOpsState,
    create_spec_ops_agent,
)

__all__ = [
    # Templates
    "FEATURE_ISSUE_TEMPLATE",
    "BUG_ISSUE_TEMPLATE",
    "TASK_ISSUE_TEMPLATE",
    "EPIC_ISSUE_TEMPLATE",
    "get_template",
    "format_template",
    "validate_template_fields",
    # PRD Parsing
    "Requirement",
    "UserStory",
    "AcceptanceCriteria",
    "NotionPRDParser",
    "RequirementExtractor",
    "AcceptanceCriteriaParser",
    "UserStoryGenerator",
    # GitHub Sync
    "GitHubIssue",
    "Milestone",
    "IssueCreator",
    "LabelManager",
    "MilestoneMapper",
    "NotionLinkUpdater",
    # Agent
    "SpecOpsAgent",
    "SpecOpsState",
    "create_spec_ops_agent",
]

__version__ = "1.0.0"
__author__ = "ResearchFlow Team"
