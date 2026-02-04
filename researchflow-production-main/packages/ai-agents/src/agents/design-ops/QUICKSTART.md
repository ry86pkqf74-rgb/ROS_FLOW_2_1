# DesignOps Agent - Quick Start Guide

## 5-Minute Setup

### 1. Installation

```bash
cd packages/ai-agents
pip install -r requirements.txt  # includes composio
```

### 2. Set Environment Variables

```bash
export FIGMA_API_TOKEN="your_figma_token"
export GITHUB_TOKEN="your_github_token"
export OPENAI_API_KEY="your_openai_key"
```

### 3. Basic Usage

```python
from packages.ai_agents.src.agents.design_ops import DesignOpsAgent

# Initialize
agent = DesignOpsAgent()

# Extract tokens
tokens = agent.extract_tokens(figma_file_id="ABC123XYZ")

# Validate
if not agent.validate_tokens(tokens):
    print("Validation failed!")
    exit(1)

# Transform
config_ts, tokens_json = agent.transform_to_tailwind(tokens)

# Create PR
pr_url = agent.create_pull_request(config_ts, tokens_json)
print(f"PR created: {pr_url}")
```

## Common Tasks

### Task 1: Extract Figma Tokens

```python
agent = DesignOpsAgent()
tokens = agent.extract_tokens("YOUR_FIGMA_FILE_ID")
print(f"Extracted {len(tokens)} tokens")
```

### Task 2: Validate Token Structure

```python
from packages.ai_agents.src.agents.design_ops import TokenValidator

validator = TokenValidator()
is_valid = validator.validate(parsed_tokens)

if not is_valid:
    errors = validator.get_errors()
    for error in errors:
        print(f"Error: {error}")
```

### Task 3: Generate Tailwind Config

```python
from packages.ai_agents.src.agents.design_ops import (
    FigmaTokenParser,
    TailwindConfigGenerator
)

parser = FigmaTokenParser()
parsed = parser.parse(figma_tokens)

generator = TailwindConfigGenerator()
config = generator.generate(parsed)

# Write to file
with open("tailwind.config.ts", "w") as f:
    f.write(config)
```

### Task 4: Generate PR Description

```python
from packages.ai_agents.src.agents.design_ops import DiffGenerator

diff_gen = DiffGenerator()
diffs = diff_gen.generate_diffs(old_tokens, new_tokens)

# Get markdown description
pr_description = diff_gen.generate_pr_description(diffs)
print(pr_description)
```

### Task 5: Setup Webhook

```python
webhook_id = agent.setup_webhook(
    figma_file_id="ABC123XYZ",
    webhook_url="https://your-domain.com/webhooks/figma"
)
print(f"Webhook ID: {webhook_id}")
```

## Workflow Examples

### Complete Design Token Sync

```python
import asyncio
from packages.ai_agents.src.agents.design_ops.workflows import (
    FigmaTokenExtractionWorkflow,
    TailwindConfigGenerationWorkflow,
    DesignSystemPRWorkflow,
    WorkflowStatus
)

async def main():
    # 1. Extract tokens
    extraction = FigmaTokenExtractionWorkflow()
    result1 = await extraction.execute("ABC123XYZ", figma_client)

    if result1.status != WorkflowStatus.SUCCESS:
        print(f"Extraction failed: {result1.error_message}")
        return

    # 2. Generate config
    generation = TailwindConfigGenerationWorkflow()
    result2 = await generation.execute(
        result1.context.figma_tokens,
        gpt4_client
    )

    if result2.status != WorkflowStatus.SUCCESS:
        print(f"Generation failed: {result2.error_message}")
        return

    # 3. Create PR
    pr_workflow = DesignSystemPRWorkflow()
    result3 = await pr_workflow.execute(
        result2.context,
        github_client,
        gpt4_client
    )

    print(f"PR created: {result3.context.pr_url}")

asyncio.run(main())
```

### Webhook Event Handler

```python
from fastapi import FastAPI, Request
from packages.ai_agents.src.agents.design_ops.workflows import WebhookHandlerWorkflow

app = FastAPI()

@app.post("/webhooks/figma")
async def handle_figma_webhook(request: Request):
    webhook_event = await request.json()

    workflow = WebhookHandlerWorkflow()
    result = await workflow.execute(
        webhook_event=webhook_event,
        figma_client=figma_client,
        github_client=github_client,
        gpt4_client=gpt4_client
    )

    return {"status": result.status.value, "pr_url": result.context.pr_url}
```

## Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Health Check

```python
status = agent.health_check()
print(status)
# Output:
# {
#   "agent": "healthy",
#   "timestamp": "2024-01-30T15:00:00",
#   "credentials": {
#     "figma": true,
#     "github": true,
#     "openai": true
#   },
#   "clients": {
#     "composio": true,
#     "figma_client": true,
#     "github_client": true
#   }
# }
```

### Simulate Mode (No Credentials)

When credentials are not available, agent runs in simulation mode:

```python
# Logs will show [SIM] prefix for simulated operations
# Example:
# [SIM] Simulating Figma extraction for file: ABC123XYZ
# [SIM] Creating branch: design-tokens/update-20240130-150000
# [SIM] Updating file: tailwind.config.ts
# [SIM] PR URL: https://github.com/researchflow/pull/12345
```

## File Locations

After implementation, you'll have:

```
packages/ai-agents/src/agents/design-ops/
├── __init__.py              # Main module exports
├── agent.py                 # DesignOpsAgent class (626 lines)
├── workflows.py             # Workflow definitions (581 lines)
├── token_transformer.py     # Token utilities (696 lines)
├── README.md                # Full documentation
├── IMPLEMENTATION.md        # Implementation details
└── QUICKSTART.md           # This file
```

## API Reference

### DesignOpsAgent

```python
# Initialization
agent = DesignOpsAgent(
    figma_token=None,           # FIGMA_API_TOKEN env var
    github_token=None,          # GITHUB_TOKEN env var
    openai_api_key=None,        # OPENAI_API_KEY env var
    repository="researchflow/researchflow-production",
    model="gpt-4o"
)

# Methods
agent.extract_tokens(figma_file_id: str) -> Dict[str, Any]
agent.transform_to_tailwind(figma_tokens: Dict) -> Tuple[str, Dict]
agent.validate_tokens(figma_tokens: Dict) -> bool
agent.create_pull_request(tokens_config, tokens_json, old_tokens=None) -> str
agent.setup_webhook(figma_file_id: str, webhook_url: str) -> str
agent.health_check() -> Dict[str, Any]
```

### FigmaTokenParser

```python
parser = FigmaTokenParser()
tokens = parser.parse(figma_data: Dict[str, Any]) -> Dict[str, TokenValue]

# Properties
parser.parsed_tokens: Dict[str, TokenValue]
parser.errors: List[str]
```

### TailwindConfigGenerator

```python
generator = TailwindConfigGenerator()
config = generator.generate(tokens: Dict[str, TokenValue]) -> str
```

### TokenValidator

```python
validator = TokenValidator()
is_valid = validator.validate(tokens: Dict[str, TokenValue]) -> bool
errors = validator.get_errors() -> List[str]
warnings = validator.get_warnings() -> List[str]
```

### DiffGenerator

```python
diff_gen = DiffGenerator()
diffs = diff_gen.generate_diffs(old_tokens, new_tokens) -> List[TokenDiff]
description = diff_gen.generate_pr_description(diffs) -> str
```

## Next Steps

1. **Read README.md** - Comprehensive documentation
2. **Review IMPLEMENTATION.md** - Technical details
3. **Check token_transformer.py** - Token handling utilities
4. **Review workflows.py** - Workflow orchestration
5. **Study agent.py** - Main agent implementation

## Support

### Common Errors

**ImportError: composio not found**
```bash
pip install composio
```

**Error: FIGMA_API_TOKEN not provided**
```bash
export FIGMA_API_TOKEN="your_token"
```

**Error: Token extraction failed**
- Check Figma file ID is correct
- Verify FIGMA_API_TOKEN is valid
- Check network connectivity

**Error: PR creation failed**
- Verify GITHUB_TOKEN has proper permissions
- Check repository name is correct
- Ensure base branch (main) exists

## Performance Tips

1. **Use token caching** - Avoid re-extracting unchanged tokens
2. **Batch operations** - Process multiple files in parallel
3. **Enable logging** - Helps identify bottlenecks
4. **Monitor rate limits** - Figma and GitHub have rate limits

## Security Tips

1. **Never commit credentials** - Use environment variables
2. **Rotate tokens regularly** - Change API tokens periodically
3. **Use minimal scopes** - Only grant necessary permissions
4. **Validate file paths** - Prevent path traversal attacks
5. **Sanitize PR descriptions** - Prevent injection attacks

## More Examples

### Example 1: Extract and Save Tokens

```python
agent = DesignOpsAgent()
tokens = agent.extract_tokens("ABC123")

with open("figma-tokens.json", "w") as f:
    json.dump(tokens, f, indent=2)
```

### Example 2: Validate Before Generating

```python
tokens = agent.extract_tokens("ABC123")

if not agent.validate_tokens(tokens):
    print("Validation failed, stopping")
    exit(1)

config, json_tokens = agent.transform_to_tailwind(tokens)
```

### Example 3: Compare Token Changes

```python
from packages.ai_agents.src.agents.design_ops import DiffGenerator

old = load_tokens("old-tokens.json")
new = agent.extract_tokens("ABC123")

diff_gen = DiffGenerator()
diffs = diff_gen.generate_diffs(old, new)

for diff in diffs:
    print(f"{diff.action}: {diff.token_name}")
    if diff.action == "modified":
        print(f"  {diff.old_value} → {diff.new_value}")
```

## Resources

- [Composio Docs](https://docs.composio.dev/)
- [Figma API](https://www.figma.com/developers/api)
- [GitHub API](https://docs.github.com/en/rest)
- [Tailwind CSS](https://tailwindcss.com/)
- [OpenAI API](https://platform.openai.com/docs/)

---

**Version:** 1.0.0
**Last Updated:** 2024-01-30
**Status:** Production Ready
