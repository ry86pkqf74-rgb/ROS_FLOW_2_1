# SpecOps Agent - Quick Start Guide

## Installation

The SpecOps Agent is part of the ResearchFlow worker service. All dependencies are already installed in the project.

## Basic Usage

### 1. Import the Agent

```python
from agents.spec_ops import create_spec_ops_agent, NotionPRDParser, IssueCreator
```

### 2. Create an Instance

```python
agent = create_spec_ops_agent(
    notion_token="ntn_...",
    github_token="<your-github-token>",
    github_repo="owner/repo"
)
```

### 3. Execute Synchronization

```python
import asyncio

async def sync_prd():
    result = await agent.execute(
        task_id="spec_ops_001",
        prd_page_id="notion_page_id"
    )

    print(f"Created {result.result['created_issues']} issues")
    print(f"Updated {result.result['updated_pages']} Notion pages")
    if result.result['errors']:
        for error in result.result['errors']:
            print(f"Error: {error}")

    return result

result = asyncio.run(sync_prd())
```

## Component Usage Examples

### Parse a Notion PRD Page

```python
from agents.spec_ops import NotionPRDParser

parser = NotionPRDParser()

prd_content = {
    "id": "page_123",
    "title": "User Auth Feature",
    "content": """
    # Feature: User Authentication

    ## Priority: High

    Users need secure authentication.

    ## Acceptance Criteria
    - [ ] Users can sign up
    - [ ] Users can log in
    - [ ] MFA is supported
    """
}

parsed = parser.parse_prd_page(prd_content)
print(f"Parsed {len(parsed['requirements'])} requirements")
```

### Create GitHub Issues

```python
from agents.spec_ops import IssueCreator, Requirement

creator = IssueCreator()

requirement = Requirement(
    id="REQ-1",
    title="User Registration",
    description="Allow users to create accounts",
    requirement_type="feature",
    priority="high",
    acceptance_criteria=[
        "Users can sign up with email",
        "Validation on email format",
        "Password must be 8+ chars"
    ]
)

issue = creator.create_from_requirement(requirement)
print(f"Issue Title: {issue.title}")
print(f"Labels: {', '.join(issue.labels)}")
```

### Manage Labels

```python
from agents.spec_ops import LabelManager

mgr = LabelManager()

# Get all standard labels
labels = mgr.get_standard_labels()
for name, config in labels.items():
    print(f"{name}: {config['description']}")

# Validate labels
valid, warnings = mgr.validate_labels(["feature", "priority-high", "component/auth"])
print(f"Valid: {valid}")
print(f"Warnings: {warnings}")

# Create component label
label_name, config = mgr.create_component_label("authentication")
print(f"New label: {label_name}")
```

### Map Phases to Milestones

```python
from agents.spec_ops import MilestoneMapper, Requirement

mapper = MilestoneMapper()

requirement = Requirement(
    id="REQ-1",
    title="Auth System",
    description="User authentication",
    requirement_type="epic",
    priority="high",
    metadata={"phase": "phase_1"}
)

milestone = mapper.map_requirement_to_milestone(requirement)
print(f"Milestone: {milestone.title}")
print(f"Due: {milestone.due_date}")
```

### Parse Acceptance Criteria

```python
from agents.spec_ops import AcceptanceCriteriaParser

parser = AcceptanceCriteriaParser()

content = """
## Acceptance Criteria

Given the user is on the login page
When they enter valid credentials
Then they should be logged in successfully

- [ ] Email validation works
- [ ] Password is hashed
- [ ] Session token is created
"""

criteria = parser.parse(content)
print(f"Criteria: {criteria.criteria}")
print(f"Test scenarios: {criteria.test_scenarios}")
```

### Generate User Stories

```python
from agents.spec_ops import UserStoryGenerator

generator = UserStoryGenerator()

content = """
As a user, I want to log in with my email and password,
so that I can access my account securely.
"""

stories = generator.parse(content)
for story in stories:
    print(f"As {story.as_role}")
    print(f"I want to {story.i_want_to}")
    print(f"So that {story.so_that}")
```

## Configuration

### Environment Variables

```bash
# Notion API
export NOTION_API_TOKEN=ntn_...

# GitHub API
export GITHUB_TOKEN=<your-github-token>
export GITHUB_REPO=owner/repo

# OpenAI (for gpt-4o-mini)
export OPENAI_API_KEY=sk_...
```

### Agent Configuration

```python
from agents.spec_ops import SpecOpsAgent
from agents.base_agent import AgentConfig

config = AgentConfig(
    name="SpecOpsAgent",
    description="Notion PRD → GitHub Issues synchronization",
    stages=[],
    rag_collections=["prd_registry"],
    max_iterations=3,
    quality_threshold=0.8,
    timeout_seconds=180,
    phi_safe=True,
    model_provider="openai",
    model_name="gpt-4o-mini",
)

agent = SpecOpsAgent(config=config)
```

## Workflow

The SpecOps Agent follows a six-step workflow:

1. **Planner** - Analyzes the sync task and creates a plan
2. **PRD Fetcher** - Retrieves the Notion PRD page
3. **Parser** - Extracts requirements using NLP
4. **Issue Creator** - Generates GitHub issues
5. **Notion Updater** - Updates Notion with GitHub links
6. **Reflector** - Validates results and decides continuation

## Common Tasks

### Sync a Single PRD Page

```python
async def sync_single_prd():
    agent = create_spec_ops_agent()
    result = await agent.execute(
        task_id="sync_001",
        prd_page_id="your_notion_page_id"
    )
    return result
```

### Process Multiple PRD Pages

```python
async def sync_multiple_prds(page_ids):
    agent = create_spec_ops_agent()
    results = []

    for i, page_id in enumerate(page_ids):
        result = await agent.execute(
            task_id=f"sync_{i:03d}",
            prd_page_id=page_id
        )
        results.append(result)

    return results
```

### Extract Requirements Only

```python
from agents.spec_ops import NotionPRDParser

parser = NotionPRDParser()

prd = fetch_from_notion(page_id)
parsed = parser.parse_prd_page(prd)

for req in parsed['requirements']:
    print(f"{req.id}: {req.title} ({req.requirement_type})")
    print(f"  Priority: {req.priority}")
    print(f"  AC: {len(req.acceptance_criteria)} criteria")
```

### Create Issues Without Sync

```python
from agents.spec_ops import IssueCreator, Requirement

creator = IssueCreator()

requirements = [
    Requirement(id="R1", title="Feature 1", ...),
    Requirement(id="R2", title="Feature 2", ...),
]

for req in requirements:
    issue = creator.create_from_requirement(req)
    # Post to GitHub API
    post_to_github(issue)
```

## Error Handling

```python
result = await agent.execute(
    task_id="sync_001",
    prd_page_id="page_id"
)

if not result.success:
    print(f"Sync failed: {result.error}")
    for error in result.result['errors']:
        print(f"  - {error}")
else:
    print(f"Successfully created {result.result['created_issues']} issues")
```

## Performance Tips

- Use batch processing for multiple requirements
- Cache parsed requirements to avoid re-parsing
- Use appropriate timeout values for large PRDs
- Monitor quality scores and iterate if needed

## Debugging

### Enable Detailed Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("agents.spec_ops")
logger.setLevel(logging.DEBUG)
```

### Validate Requirements

```python
from agents.spec_ops import RequirementExtractor

extractor = RequirementExtractor()
requirements = extractor.parse(content)

for req in requirements:
    print(f"ID: {req.id}")
    print(f"Title: {req.title}")
    print(f"Type: {req.requirement_type}")
    print(f"Priority: {req.priority}")
    print(f"AC Count: {len(req.acceptance_criteria)}")
    print()
```

## Next Steps

1. **Composio Integration**: Implement actual Notion/GitHub API calls
2. **Webhook Support**: Enable real-time synchronization
3. **Status Tracking**: Sync issue status back to Notion
4. **Custom Mappings**: Configure field mappings for your workflow
5. **Testing**: Add comprehensive unit tests

## Resources

- [README.md](./README.md) - Full documentation
- [SPEC_OPS_IMPLEMENTATION.md](../../SPEC_OPS_IMPLEMENTATION.md) - Implementation details
- [BaseAgent](../base_agent.py) - Base agent implementation
- [Composio Docs](https://docs.composio.dev/) - Composio tooling documentation

## Support

For issues or questions:
1. Check the [README.md](./README.md) for detailed documentation
2. Review error messages in logs
3. Enable DEBUG logging for troubleshooting
4. Check Linear issue ROS-105 and ROS-106
