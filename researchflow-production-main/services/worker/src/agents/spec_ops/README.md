# SpecOps Agent - Notion PRD → GitHub Issues (Phase 1.3)

## Overview

The SpecOps Agent is a cross-cutting LangGraph agent that synchronizes Notion PRD (Product Requirements Document) pages to GitHub issues. It automates the workflow of converting product requirements into actionable GitHub issues with proper labels, milestones, and acceptance criteria.

## Architecture

The SpecOps Agent follows the ResearchFlow agent pattern with a Planner → Parser → Creator → Updater → Reflector workflow:

```
PRD Page → Planner → PRD Fetcher → Parser → Issue Creator → Notion Updater → Reflector
                                                                                   ↓
                                                                              End/Continue
```

### Core Components

#### 1. **templates.py** - Issue Templates
- `FEATURE_ISSUE_TEMPLATE`: For new features and enhancements
- `BUG_ISSUE_TEMPLATE`: For bug reports and defects
- `TASK_ISSUE_TEMPLATE`: For technical tasks and refactoring
- `EPIC_ISSUE_TEMPLATE`: For large initiatives and epics
- Template formatting and validation utilities

#### 2. **prd_parser.py** - PRD Parsing Utilities
- `NotionPRDParser`: Main parser for complete PRD pages
- `RequirementExtractor`: Extract and normalize requirements
- `AcceptanceCriteriaParser`: Parse acceptance criteria in BDD/checklist format
- `UserStoryGenerator`: Generate user stories from requirements
- Data models: `Requirement`, `UserStory`, `AcceptanceCriteria`

#### 3. **github_sync.py** - GitHub Synchronization
- `IssueCreator`: Create GitHub issues from requirements
- `LabelManager`: Manage and apply labels
- `MilestoneMapper`: Map PRD phases to GitHub milestones
- `NotionLinkUpdater`: Update Notion with GitHub links
- Data models: `GitHubIssue`, `Milestone`

#### 4. **agent.py** - Main Agent
- `SpecOpsAgent`: LangGraph-based orchestration agent
- `SpecOpsState`: Agent state definition
- Workflow nodes: planner, prd_fetcher, parser, issue_creator, notion_updater, reflector
- Factory function: `create_spec_ops_agent()`

## Configuration

### Environment Variables
```bash
NOTION_API_TOKEN=ntn_...          # Notion API token
GITHUB_TOKEN=ghp_...              # GitHub personal access token
GITHUB_REPO=owner/repo            # GitHub repository
OPENAI_API_KEY=sk_...             # OpenAI API key (for gpt-4o-mini)
```

### Agent Configuration
```python
from agents.spec_ops import create_spec_ops_agent

agent = create_spec_ops_agent(
    notion_token="ntn_...",
    github_token="ghp_...",
    github_repo="owner/repo"
)
```

## Usage

### Basic Usage

```python
from agents.spec_ops import create_spec_ops_agent

# Create agent
agent = create_spec_ops_agent(
    notion_token="ntn_...",
    github_token="ghp_...",
    github_repo="owner/repo"
)

# Execute synchronization
result = await agent.execute(
    task_id="spec_ops_001",
    prd_page_id="notion_page_id"
)

# Check results
print(f"Created {result.result['created_issues']} issues")
print(f"Errors: {result.result['errors']}")
```

### Advanced: Component Usage

#### Parsing Requirements

```python
from agents.spec_ops import NotionPRDParser

parser = NotionPRDParser()

prd_content = {
    "id": "page_123",
    "title": "Feature PRD",
    "content": """
    # Feature: User Authentication
    ## Priority: High

    Users need secure authentication.

    ## Acceptance Criteria
    - [ ] Users can sign up
    - [ ] Users can log in
    """
}

parsed = parser.parse_prd_page(prd_content)
print(f"Parsed {len(parsed['requirements'])} requirements")
```

#### Creating Issues

```python
from agents.spec_ops import IssueCreator, Requirement

creator = IssueCreator()

requirement = Requirement(
    id="REQ-1",
    title="User Authentication",
    description="Implement OAuth2 authentication",
    requirement_type="feature",
    priority="high",
    acceptance_criteria=[
        "Users can sign up with email",
        "Users can log in with credentials"
    ]
)

issue = creator.create_from_requirement(requirement)
print(f"Issue: {issue.title}")
print(f"Labels: {issue.labels}")
```

#### Managing Labels

```python
from agents.spec_ops import LabelManager

label_mgr = LabelManager()

# Get standard labels
labels = label_mgr.get_standard_labels()

# Create component label
label_name, label_config = label_mgr.create_component_label("auth")

# Validate labels
valid, warnings = label_mgr.validate_labels(["feature", "priority-high", "unknown"])
```

#### Mapping Milestones

```python
from agents.spec_ops import MilestoneMapper, Requirement

mapper = MilestoneMapper()

requirement = Requirement(
    id="REQ-1",
    title="Feature",
    description="...",
    requirement_type="feature",
    priority="high",
    metadata={"phase": "phase_1"}
)

milestone = mapper.map_requirement_to_milestone(requirement)
print(f"Milestone: {milestone.title} due {milestone.due_date}")
```

## Workflow Steps

### 1. Planner
- Analyzes the sync task
- Determines PRD pages to process
- Establishes sync strategy

### 2. PRD Fetcher
- Retrieves PRD page from Notion via Composio
- Validates page content
- Handles retrieval errors

### 3. Parser
- Extracts requirements using NLP
- Parses acceptance criteria (BDD/checklist)
- Generates user stories
- Categorizes requirements (feature/bug/task/epic)

### 4. Issue Creator
- Creates GitHub issue templates
- Generates labels and milestones
- Validates issue structure
- Prepares for GitHub API

### 5. Notion Updater
- Prepares Notion page updates
- Adds GitHub issue links
- Updates sync metadata
- Batches updates

### 6. Reflector
- Validates results
- Generates quality metrics
- Determines next steps (continue/end)
- Handles errors and retries

## Data Models

### Requirement
```python
@dataclass
class Requirement:
    id: str                           # REQ-001
    title: str                        # Requirement title
    description: str                  # Full description
    requirement_type: str             # feature|bug|task|epic
    priority: str                     # high|medium|low
    tags: List[str]                   # Custom tags
    dependencies: List[str]           # Dependencies
    acceptance_criteria: List[str]    # AC list
    user_stories: List[UserStory]     # User stories
    estimated_effort: Optional[str]   # Story points
    related_components: List[str]     # Components
    metadata: Dict[str, Any]          # Custom metadata
```

### UserStory
```python
@dataclass
class UserStory:
    as_role: str          # "As a user"
    i_want_to: str        # "I want to..."
    so_that: str          # "So that..."
    acceptance_criteria: List[str]  # AC for story
```

### GitHubIssue
```python
@dataclass
class GitHubIssue:
    title: str
    body: str
    labels: List[str]
    assignees: List[str]
    milestone: Optional[str]
    prd_requirement_id: Optional[str]
    issue_type: str
```

## Quality Gates

- **Validation**: All required fields present
- **Completeness**: Acceptance criteria defined
- **Consistency**: Labels and milestones valid
- **Linkage**: PRD → GitHub mapping verified
- **Error Handling**: Graceful failure with logging

## Error Handling

The agent provides comprehensive error handling:

```python
result = await agent.execute(...)

if not result.success:
    for error in result.result['errors']:
        print(f"Error: {error}")
```

Common errors:
- Invalid PRD page ID
- Missing Notion token
- GitHub API rate limits
- Invalid requirement format
- Missing acceptance criteria

## Performance

- **Model**: gpt-4o-mini (cost-efficient)
- **Extraction Speed**: ~2-3 seconds per requirement
- **Issue Creation**: Batch processing supported
- **Timeout**: 180 seconds default

## Linear Issues

- ROS-105: Notion → GitHub synchronization foundation
- ROS-106: PRD parser implementation

## Future Enhancements

- [ ] Bidirectional sync (GitHub → Notion)
- [ ] Webhook support for real-time updates
- [ ] Custom field mappings
- [ ] Bulk import/export
- [ ] Approval workflow integration
- [ ] Change tracking and audit logs
- [ ] Status tracking synchronization

## Testing

```python
# Mock PRD content for testing
mock_prd = {
    "id": "test_page",
    "title": "Test PRD",
    "content": "# Feature: Test\nHigh priority test feature"
}

parser = NotionPRDParser()
result = parser.parse_prd_page(mock_prd)
assert len(result['requirements']) > 0
assert result['requirements'][0].requirement_type in ['feature', 'bug', 'task', 'epic']
```

## License

ResearchFlow Project - All Rights Reserved
