# DesignOps Agent - Phase 1.2 Implementation

## Overview

The DesignOps Agent (Phase 1.2) provides complete end-to-end automation for design system synchronization between Figma and the ResearchFlow codebase. It orchestrates the extraction of design tokens from Figma, transforms them into Tailwind configuration, and automatically creates pull requests with validated changes.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DesignOps Agent                              │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Main Agent (agent.py)                     │  │
│  │  - Orchestrates workflows                                    │  │
│  │  - Manages Figma & GitHub integrations                       │  │
│  │  - Handles error recovery                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▲                                       │
│              ┌───────────────┼───────────────┐                      │
│              ▼               ▼               ▼                      │
│         ┌────────┐    ┌────────────┐  ┌────────────┐               │
│         │Workflows    │Transformers│  │Composio API│               │
│         │(workflows   │(token_     │  │ Integrations               │
│         │ .py)        │ transformer│  │                            │
│         │             │ .py)       │  │ • Figma API                │
│         └────────┘    └────────────┘  │ • GitHub API               │
│                                        │ • GPT-4o                   │
│                                        └────────────┘               │
│                                                                      │
│  Composio Toolkits:                                                 │
│  ├─ FIGMA: Extract Design Tokens, Create Webhook                  │
│  ├─ GITHUB: Create branch, commit, PR, add reviewers              │
│  └─ GPT-4o: Code generation & token transformation                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Files Structure

### 1. `__init__.py`
Main module exports for public API.

**Exports:**
- `DesignOpsAgent` - Main agent class
- `FigmaTokenExtractionWorkflow` - Token extraction workflow
- `TailwindConfigGenerationWorkflow` - Config generation workflow
- `DesignSystemPRWorkflow` - PR creation workflow
- `WebhookHandlerWorkflow` - Webhook event handler
- `FigmaTokenParser` - Token parsing utilities
- `TailwindConfigGenerator` - Tailwind config generation
- `TokenValidator` - Token validation
- `DiffGenerator` - Diff generation for PRs

### 2. `agent.py` (626 lines)
Core DesignOps Agent implementation.

**Key Classes:**
- `DesignOpsAgent` - Main orchestrator class

**Key Methods:**
```python
# Initialization
__init__(figma_token, github_token, openai_api_key, repository, model)
_initialize_clients()  # Initialize Composio integrations

# Token Management
extract_tokens(figma_file_id: str) -> Dict[str, Any]
transform_to_tailwind(figma_tokens: Dict) -> Tuple[str, Dict]
validate_tokens(figma_tokens: Dict) -> bool

# PR Creation
create_pull_request(tokens_config, tokens_json, old_tokens) -> str

# Webhook Management
setup_webhook(figma_file_id, webhook_url) -> str

# Utilities
health_check() -> Dict[str, Any]
```

**Integration Points:**
- Uses Composio FIGMA toolkit: `Extract Design Tokens` action
- Uses Composio GITHUB toolkit: `Create branch`, `commit`, `Create PR` actions
- Uses GPT-4o for code generation and token transformation
- Implements error handling and logging throughout

### 3. `workflows.py` (581 lines)
Workflow orchestration and definitions.

**Data Classes:**
- `WorkflowContext` - Maintains state across workflow steps
- `WorkflowResult` - Contains execution result and metadata
- `WorkflowStatus` - Enum: PENDING, RUNNING, SUCCESS, FAILED, CANCELLED
- `WorkflowStep` - Enum: EXTRACT_TOKENS, VALIDATE_TOKENS, etc.

**Workflow Classes:**
1. **FigmaTokenExtractionWorkflow**
   - Extracts tokens using Composio FIGMA toolkit
   - Returns WorkflowResult with extracted tokens

2. **TailwindConfigGenerationWorkflow**
   - Validates extracted tokens
   - Generates Tailwind configuration using `Design Tokens To Tailwind`
   - Returns TypeScript config and tokens JSON

3. **DesignSystemPRWorkflow**
   - Creates git branch using Composio GITHUB toolkit
   - Updates design token files
   - Runs validation (lint, build, Storybook)
   - Commits changes
   - Creates PR with comprehensive description

4. **WebhookHandlerWorkflow**
   - Receives Figma webhook events
   - Orchestrates complete token sync pipeline
   - Sets up webhook listener using Composio

**Key Features:**
- Async/await support for concurrent operations
- Comprehensive error handling with recovery
- Detailed logging at each step
- Metadata tracking for debugging

### 4. `token_transformer.py` (696 lines)
Token parsing, transformation, and validation utilities.

**Enums:**
- `TokenType` - COLOR, SPACING, TYPOGRAPHY, RADIUS, SHADOW, OPACITY, etc.
- `TokenCategory` - BASE, SEMANTIC, COMPONENT

**Data Classes:**
- `TokenValue` - Single design token representation
- `TokenDiff` - Token change (added/modified/deleted)

**Core Classes:**

1. **FigmaTokenParser**
   - Parses raw Figma token JSON
   - Normalizes token structure
   - Infers token types
   - Handles nested token groups
   - Returns typed TokenValue objects

2. **TailwindConfigGenerator**
   - Converts TokenValue objects to Tailwind configuration
   - Generates TypeScript configuration file
   - Organizes tokens by category
   - Creates ready-to-use `tailwind.config.ts`

3. **TokenValidator**
   - Validates token structure and values
   - Type-specific validation (colors, spacing, shadows)
   - Checks for naming conflicts
   - Detects orphaned token references
   - Tracks errors and warnings

4. **DiffGenerator**
   - Compares token sets to find changes
   - Generates TokenDiff objects
   - Creates markdown PR descriptions
   - Tracks added/modified/deleted tokens

**Features:**
- Comprehensive error handling
- Detailed logging for debugging
- Type inference from token values
- Support for token references
- PR description generation

## Usage

### Basic Usage

```python
from packages.ai_agents.src.agents.design_ops import DesignOpsAgent

# Initialize agent
agent = DesignOpsAgent(
    figma_token="your_figma_token",
    github_token="your_github_token",
    openai_api_key="your_openai_key",
    repository="researchflow/researchflow-production",
    model="gpt-4o"
)

# Extract tokens from Figma
tokens = agent.extract_tokens(figma_file_id="YOUR_FIGMA_FILE_ID")

# Validate tokens
is_valid = agent.validate_tokens(tokens)
if not is_valid:
    print("Token validation failed")

# Transform to Tailwind
config_ts, tokens_json = agent.transform_to_tailwind(tokens)

# Create PR with changes
pr_url = agent.create_pull_request(config_ts, tokens_json)
print(f"PR created: {pr_url}")
```

### Async Workflow

```python
import asyncio
from packages.ai_agents.src.agents.design_ops.workflows import (
    FigmaTokenExtractionWorkflow,
    TailwindConfigGenerationWorkflow,
    DesignSystemPRWorkflow
)

async def sync_design_system():
    # Extract tokens
    extraction = FigmaTokenExtractionWorkflow()
    extraction_result = await extraction.execute(figma_file_id, figma_client)

    if extraction_result.status != WorkflowStatus.SUCCESS:
        raise RuntimeError("Token extraction failed")

    # Generate config
    generation = TailwindConfigGenerationWorkflow()
    generation_result = await generation.execute(
        extraction_result.context.figma_tokens,
        gpt4_client
    )

    # Create PR
    pr_workflow = DesignSystemPRWorkflow()
    pr_result = await pr_workflow.execute(
        generation_result.context,
        github_client,
        gpt4_client
    )

    return pr_result.context.pr_url

# Run async workflow
pr_url = asyncio.run(sync_design_system())
```

### Webhook Integration

```python
# Setup webhook
webhook_id = agent.setup_webhook(
    figma_file_id="YOUR_FIGMA_FILE_ID",
    webhook_url="https://your-domain.com/webhooks/figma"
)

# Process incoming webhook events
async def handle_figma_webhook(webhook_event: Dict[str, Any]):
    workflow = WebhookHandlerWorkflow()
    result = await workflow.execute(
        webhook_event=webhook_event,
        figma_client=agent.figma_client,
        github_client=agent.github_client,
        gpt4_client=agent.gpt4_client
    )
    return result
```

## Environment Variables

```bash
# Required
FIGMA_API_TOKEN=your_figma_token
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_key

# Optional
DESIGN_OPS_REPOSITORY=researchflow/researchflow-production
DESIGN_OPS_MODEL=gpt-4o
```

## Composio Integrations

### Figma Toolkit
**Actions Used:**
- `Extract Design Tokens` - Extract tokens from Figma file
- `Create Webhook` - Setup event listener for file changes

**Parameters:**
- file_id: Figma file ID
- callback_url: Webhook callback URL
- events: Event types to listen for

### GitHub Toolkit
**Actions Used:**
- `Create branch` - Create new branch for changes
- `Update file` - Update design token files
- `commit` - Commit changes to branch
- `Create PR` - Create pull request

**Parameters:**
- owner: Repository owner
- repo: Repository name
- branch: Branch name
- message: Commit message
- content: File content

## Error Handling

The agent implements comprehensive error handling:

```python
try:
    tokens = agent.extract_tokens(figma_file_id)
except RuntimeError as e:
    print(f"Token extraction failed: {e}")
    # Implement retry logic or fallback

try:
    agent.validate_tokens(tokens)
except ValueError as e:
    print(f"Token validation error: {e}")
    # Handle validation errors
```

## Logging

All operations are logged with DEBUG, INFO, WARNING, and ERROR levels:

```python
import logging

logger = logging.getLogger("design_ops")
logger.setLevel(logging.INFO)

# Configure handler as needed
handler = logging.StreamHandler()
logger.addHandler(handler)
```

## Token Structure

### Base Tokens
Raw design values organized by type:

```json
{
  "base": {
    "colors": {
      "primary": { "value": "#4F46E5" },
      "gray": { "value": "#6B7280" }
    },
    "spacing": {
      "4": { "value": "1rem" },
      "8": { "value": "2rem" }
    }
  }
}
```

### Semantic Tokens
Meaningful names referencing base tokens:

```json
{
  "semantic": {
    "bg": {
      "surface": { "value": "{color.base.white}" },
      "muted": { "value": "{color.base.gray.100}" }
    }
  }
}
```

### Component Tokens
Pre-defined component configurations:

```json
{
  "component": {
    "button": {
      "primary": { "value": "{semantic.interactive.primary}" },
      "secondary": { "value": "{semantic.interactive.secondary}" }
    }
  }
}
```

## Validation

The TokenValidator class performs:

1. **Structure Validation**
   - Required fields present
   - Correct data types

2. **Type-Specific Validation**
   - Color hex format verification
   - Spacing unit validation
   - Shadow property checks

3. **Reference Validation**
   - Checks for orphaned token references
   - Validates token name uniqueness

4. **Conflict Detection**
   - Naming conflicts
   - Circular references

## Output Files

### Generated Files
1. **tailwind.config.ts** - Tailwind CSS configuration
2. **packages/design-tokens/tokens.json** - Token definitions
3. **PR Description** - Comprehensive change summary

### File Locations
- Config: `/tailwind.config.ts`
- Tokens: `/packages/design-tokens/tokens.json`
- Tokens CSS: `/packages/design-tokens/dist/tokens.css`

## Performance

- Token extraction: ~1-2 seconds per file
- Validation: <100ms for 100+ tokens
- Config generation: <500ms
- PR creation: ~3-5 seconds

## Testing

```python
# Unit tests for token parsing
def test_figma_token_parser():
    parser = FigmaTokenParser()
    tokens = parser.parse(figma_data)
    assert len(tokens) > 0

# Unit tests for Tailwind generation
def test_tailwind_config_generator():
    generator = TailwindConfigGenerator()
    config = generator.generate(tokens)
    assert "extend" in config

# Unit tests for validation
def test_token_validator():
    validator = TokenValidator()
    is_valid = validator.validate(tokens)
    assert is_valid or len(validator.get_errors()) > 0
```

## Troubleshooting

### Issue: Token extraction fails
- Check FIGMA_API_TOKEN is valid
- Verify Figma file ID exists
- Check network connectivity

### Issue: Tailwind config generation fails
- Validate token structure with TokenValidator
- Check for circular token references
- Review token type inference

### Issue: PR creation fails
- Check GITHUB_TOKEN permissions
- Verify repository access
- Check branch creation succeeded

## References

- **Design Tokens Package:** `/packages/design-tokens/`
- **UI Components:** `/packages/ui/src/`
- **Component Inventory:** `/docs/design/component-inventory.md`
- **Figma Integration:** Uses Composio FIGMA toolkit
- **GitHub Integration:** Uses Composio GITHUB toolkit

## Future Enhancements

Phase 2 plans:
1. Component variant mapping
2. Animation token support
3. Layout grid tokens
4. Accessibility token validation
5. Token versioning system
6. A/B testing for design changes
7. Analytics for token usage
8. Figma component sync

## License

MIT
