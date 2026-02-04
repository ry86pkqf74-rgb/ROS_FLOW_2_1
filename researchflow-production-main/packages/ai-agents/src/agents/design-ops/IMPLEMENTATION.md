# DesignOps Agent - Implementation Guide

## Phase 1.2: Figma → Tokens → Tailwind → PR Automation

### Project Overview

The DesignOps Agent automates the complete design system synchronization workflow:

```
Figma Design File
      │
      ├─► Extract Design Tokens (Composio FIGMA)
      │
      ├─► Parse & Validate Tokens (FigmaTokenParser)
      │
      ├─► Transform to Tailwind (TailwindConfigGenerator)
      │
      ├─► Generate files:
      │   ├─ tailwind.config.ts
      │   └─ packages/design-tokens/tokens.json
      │
      ├─► Create Branch (Composio GITHUB)
      │
      ├─► Update Files (Composio GITHUB)
      │
      ├─► Validate (lint + build + Storybook)
      │
      ├─► Commit Changes (Composio GITHUB)
      │
      └─► Create PR (Composio GITHUB)
            │
            └─► Webhook Setup (Composio FIGMA)
```

## Implementation Details

### 1. Token Extraction Flow

**File:** `token_transformer.py` - `FigmaTokenParser`

```python
# Input: Raw Figma token JSON
figma_data = {
    "color": {
        "primary": {
            "value": "#4F46E5",
            "type": "color"
        }
    }
}

# Process:
parser = FigmaTokenParser()
tokens = parser.parse(figma_data)

# Output: Normalized TokenValue objects
# tokens["color.primary"] = TokenValue(
#     name="color.primary",
#     type=TokenType.COLOR,
#     value="#4F46E5",
#     category=TokenCategory.BASE
# )
```

**Key Features:**
- Recursive parsing of nested token groups
- Type inference from token values
- Category detection (base, semantic, component)
- Error collection and reporting
- Metadata extraction

### 2. Token Validation Flow

**File:** `token_transformer.py` - `TokenValidator`

```python
validator = TokenValidator()
is_valid = validator.validate(tokens)

# Validates:
# 1. Structure: Required fields, correct types
# 2. Values: Type-specific validation
# 3. References: Token reference validity
# 4. Conflicts: Naming conflicts
```

**Validation Types:**
- **Color Tokens:** Hex format, RGB/RGBA format
- **Spacing Tokens:** Valid units (px, rem, em, %)
- **Shadow Tokens:** Required shadow properties (x, y, blur)
- **References:** All referenced tokens exist
- **Naming:** No duplicate names (case-insensitive)

### 3. Tailwind Config Generation

**File:** `token_transformer.py` - `TailwindConfigGenerator`

```python
generator = TailwindConfigGenerator()
config_ts = generator.generate(parsed_tokens)

# Output TypeScript file:
# import type { Config } from "tailwindcss";
#
# const config: Config = {
#   content: [...],
#   theme: {
#     extend: {
#       colors: { ... },
#       spacing: { ... },
#       fontSize: { ... },
#       ...
#     }
#   }
# };
#
# export default config;
```

**Token Type Mapping:**
- `TokenType.COLOR` → `theme.extend.colors`
- `TokenType.SPACING` → `theme.extend.spacing`
- `TokenType.TYPOGRAPHY` → `theme.extend.fontSize`, `fontFamily`, `fontWeight`
- `TokenType.RADIUS` → `theme.extend.borderRadius`
- `TokenType.SHADOW` → `theme.extend.boxShadow`
- `TokenType.OPACITY` → `theme.extend.opacity`
- `TokenType.ZINDEX` → `theme.extend.zIndex`

### 4. PR Workflow

**File:** `workflows.py` - `DesignSystemPRWorkflow`

**Step 1: Create Branch**
```
Composio GITHUB: Create branch
Branch Name: design-tokens/update-YYYYMMDD-HHMMSS
Base: main
```

**Step 2: Update Files**
```
Files Updated:
├─ tailwind.config.ts
└─ packages/design-tokens/tokens.json
```

**Step 3: Validation**
```
Runs:
├─ npm run lint
├─ npm run build
└─ npm run storybook:build
```

**Step 4: Commit**
```
Composio GITHUB: commit
Message: "Update design tokens from Figma
- Extract latest tokens
- Regenerate Tailwind config
- Update token definitions"

Co-authored: DesignOps Agent
```

**Step 5: Create PR**
```
Composio GITHUB: Create PR
Title: "Update design tokens from Figma"
Body: Auto-generated with:
  - Change summary
  - Added/modified/deleted tokens
  - Validation results
  - Testing checklist
```

### 5. Webhook Integration

**File:** `workflows.py` - `WebhookHandlerWorkflow`

```python
# Setup webhook
webhook_id = agent.setup_webhook(
    figma_file_id="...",
    webhook_url="https://researchflow.dev/webhooks/figma"
)

# On webhook event:
# {
#   "type": "file_update",
#   "file_id": "...",
#   "timestamp": "...",
#   "triggering_user_id": "..."
# }

# Triggers complete sync workflow
workflow = WebhookHandlerWorkflow()
result = await workflow.execute(
    webhook_event=event,
    figma_client=figma_client,
    github_client=github_client,
    gpt4_client=gpt4_client
)
```

## Composio Integration Points

### FIGMA Toolkit

**Action: Extract Design Tokens**
```python
# Extracting tokens from Figma
response = figma_client.execute_action(
    action_name="Extract Design Tokens",
    parameters={"file_id": "abc123"}
)
tokens = response.get("data", {})
```

**Action: Create Webhook**
```python
# Setting up webhook listener
response = figma_client.execute_action(
    action_name="Create Webhook",
    parameters={
        "file_id": "abc123",
        "callback_url": "https://...",
        "events": ["file_update", "file_export"]
    }
)
webhook_id = response.get("webhook_id")
```

### GITHUB Toolkit

**Action: Create branch**
```python
response = github_client.execute_action(
    action_name="Create branch",
    parameters={
        "owner": "researchflow",
        "repo": "researchflow-production",
        "branch_name": "design-tokens/update-20240130-150000",
        "base_branch": "main"
    }
)
```

**Action: Update file**
```python
response = github_client.execute_action(
    action_name="Update file",
    parameters={
        "owner": "researchflow",
        "repo": "researchflow-production",
        "branch": "design-tokens/update-...",
        "path": "tailwind.config.ts",
        "content": "...",
        "message": "Update Tailwind config"
    }
)
```

**Action: commit**
```python
response = github_client.execute_action(
    action_name="commit",
    parameters={
        "owner": "researchflow",
        "repo": "researchflow-production",
        "branch": "design-tokens/update-...",
        "message": "Update design tokens from Figma\n\nCo-authored-by: ..."
    }
)
```

**Action: Create PR**
```python
response = github_client.execute_action(
    action_name="Create PR",
    parameters={
        "owner": "researchflow",
        "repo": "researchflow-production",
        "title": "Update design tokens from Figma",
        "body": "# Design System Token Updates\n\n...",
        "head": "design-tokens/update-...",
        "base": "main"
    }
)
pr_url = response.get("html_url")
```

## Error Handling Strategy

### Extraction Errors
```
Token Extraction Failed
├─ Invalid Figma credentials → Check FIGMA_API_TOKEN
├─ File not found → Verify Figma file ID
├─ API rate limit → Implement retry with backoff
└─ Network error → Implement connection retry
```

### Validation Errors
```
Token Validation Failed
├─ Invalid structure → Report specific validation errors
├─ Naming conflicts → Suggest token name corrections
├─ Orphaned references → List undefined tokens
└─ Type mismatch → Show expected vs actual type
```

### Generation Errors
```
Config Generation Failed
├─ Unsupported token type → Fall back to generic value
├─ Invalid CSS value → Validate and sanitize
└─ Type conversion error → Use safe defaults
```

### PR Errors
```
PR Creation Failed
├─ Branch creation failed → Check GitHub credentials/permissions
├─ File update failed → Verify file paths and permissions
├─ Commit failed → Check commit message format
└─ PR creation failed → Check base branch exists
```

## Testing Strategy

### Unit Tests

**Token Parser Tests:**
```python
def test_parse_flat_tokens():
    # Test simple flat token structure

def test_parse_nested_tokens():
    # Test nested token groups

def test_infer_token_type():
    # Test type inference from values

def test_handle_parse_errors():
    # Test error handling in parsing
```

**Validator Tests:**
```python
def test_validate_color_tokens():
    # Test color validation (hex, rgb)

def test_validate_spacing_tokens():
    # Test spacing validation (units)

def test_detect_naming_conflicts():
    # Test conflict detection

def test_check_orphaned_references():
    # Test reference validation
```

**Generator Tests:**
```python
def test_generate_colors():
    # Test color extraction

def test_generate_spacing():
    # Test spacing extraction

def test_build_config_file():
    # Test complete config file generation
```

**Workflow Tests:**
```python
def test_extraction_workflow():
    # Test token extraction workflow

def test_generation_workflow():
    # Test config generation workflow

def test_pr_workflow():
    # Test PR creation workflow

def test_webhook_workflow():
    # Test webhook handling workflow
```

### Integration Tests
```python
def test_full_sync_workflow():
    # Extract → Validate → Generate → PR

def test_webhook_trigger():
    # Webhook event → Complete sync

def test_error_recovery():
    # Handle errors and recover
```

## Configuration

### Environment Setup
```bash
# .env
FIGMA_API_TOKEN=fgk_your_token
GITHUB_TOKEN=ghp_your_token
OPENAI_API_KEY=sk-your_key

# Optional
DESIGN_OPS_REPOSITORY=researchflow/researchflow-production
DESIGN_OPS_MODEL=gpt-4o
LOG_LEVEL=INFO
```

### Agent Configuration
```python
agent = DesignOpsAgent(
    figma_token=os.getenv("FIGMA_API_TOKEN"),
    github_token=os.getenv("GITHUB_TOKEN"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    repository="researchflow/researchflow-production",
    model="gpt-4o"
)
```

## Monitoring & Logging

### Log Levels
- **DEBUG:** Detailed token parsing steps
- **INFO:** Major workflow steps, token counts
- **WARNING:** Validation warnings, retries
- **ERROR:** Failures, exceptions

### Key Log Points
```
1. Agent initialization → INFO
2. Token extraction start → INFO
3. Token extraction complete → INFO (token count)
4. Validation start → DEBUG
5. Validation warnings → WARNING
6. Config generation → INFO
7. Branch creation → INFO
8. File updates → DEBUG
9. Commit → INFO
10. PR creation → INFO (PR URL)
```

## Performance Optimization

### Caching
```python
# Cache extracted tokens to avoid re-extraction
token_cache: Dict[str, Dict[str, Any]] = {}

def extract_tokens_cached(file_id: str, ttl: int = 3600):
    if file_id in token_cache:
        return token_cache[file_id]

    tokens = agent.extract_tokens(file_id)
    token_cache[file_id] = tokens
    return tokens
```

### Batch Operations
```python
# Process multiple files in parallel
async def extract_multiple_tokens(file_ids: List[str]):
    tasks = [
        extract_tokens(file_id)
        for file_id in file_ids
    ]
    return await asyncio.gather(*tasks)
```

### Lazy Validation
```python
# Skip expensive validation checks if not needed
validator = TokenValidator(skip_reference_check=False)
```

## Security Considerations

### Token Security
```python
# Store credentials securely
- Use environment variables
- Never commit credentials
- Rotate tokens regularly
- Use minimal required scopes
```

### File Operations
```python
# Validate file paths
def safe_file_update(path: str, content: str):
    # Ensure path is within allowed directories
    if not is_safe_path(path):
        raise SecurityError("Path not allowed")
```

### PR Validation
```python
# Validate PR content before creation
def validate_pr_description(description: str):
    # Check for malicious content
    # Sanitize user input
    # Verify git safety
```

## Deployment

### Development
```bash
# Install dependencies
pip install composio

# Set environment variables
export FIGMA_API_TOKEN=...
export GITHUB_TOKEN=...
export OPENAI_API_KEY=...

# Run agent
python -m packages.ai_agents.src.agents.design_ops
```

### Production
```bash
# Docker deployment
docker build -t design-ops-agent .
docker run -e FIGMA_API_TOKEN=... -e GITHUB_TOKEN=... design-ops-agent

# Kubernetes
kubectl apply -f design-ops-deployment.yaml
```

## Troubleshooting Guide

### Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Check
```python
status = agent.health_check()
print(status)
# {
#   "agent": "healthy",
#   "credentials": {...},
#   "clients": {...}
# }
```

### Common Issues

**Issue: Token extraction timeout**
Solution: Increase timeout, check Figma file size

**Issue: Invalid Tailwind config**
Solution: Validate tokens with TokenValidator

**Issue: PR creation fails**
Solution: Check GitHub permissions, verify branch

## References

- **Composio Documentation:** https://docs.composio.dev/
- **Figma API:** https://www.figma.com/developers/api
- **GitHub API:** https://docs.github.com/en/rest
- **Tailwind CSS:** https://tailwindcss.com/docs
- **OpenAI API:** https://platform.openai.com/docs/api-reference
- **ResearchFlow Design System:** `/packages/design-tokens/`
