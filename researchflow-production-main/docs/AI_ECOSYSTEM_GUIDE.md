# ResearchFlow: Complete AI Tool Ecosystem Guide v2.0
## All Tools Inventory & Integration Guide

**Last Updated**: 2026-01-28
**Repository**: https://github.com/ry86pkqf74-rgb/researchflow-production

---

# ============================================================================
# COMPLETE TOOL INVENTORY (From Your Notion)
# ============================================================================

## Your AI Tool Stack

| # | Tool | Category | Primary Use | Integration Type |
|---|------|----------|-------------|------------------|
| 1 | **n8n** | Automation | Workflow orchestration, webhooks | Self-hosted/Cloud |
| 2 | **Notion API** | Documentation | Knowledge base, databases | MCP + API |
| 3 | **Continue.dev** | IDE Extension | Inline completions, chat | VS Code/JetBrains |
| 4 | **Replit Agent** | Platform | Rapid prototyping, deployment | Web + Agent |
| 5 | **Context7** | Context Management | Documentation lookup, context | MCP Server |
| 6 | **Figma AI** | Design | UI specs, design tokens | MCP + Plugin |
| 7 | **Mercury Coder** | AI Assistant | Fast UI iteration | API/Chat |
| 8 | **Claude (Anthropic)** | AI Assistant | Complex reasoning, architecture | API/Chat/MCP |
| 9 | **Sourcegraph Cody** | Code Intelligence | Code search, AI assistance | IDE Extension |
| 10 | **GPT-4 / ChatGPT Pro** | AI Assistant | Code generation, structured output | API/Chat |
| 11 | **Grok (xAI)** | AI Assistant | Code review, debugging | API/Chat |
| 12 | **LM Studio** | Local LLM | Offline inference, privacy | Local Server |

---

# ============================================================================
# TOOL-BY-TOOL INTEGRATION GUIDE
# ============================================================================

## 1. n8n - Workflow Automation

### What It Does
- Visual workflow builder
- Connects services with webhooks
- Automates repetitive tasks
- Triggers on events (GitHub, Linear, etc.)

### ResearchFlow Integration
```yaml
# Example n8n Workflows for ResearchFlow:

1. GitHub → Linear Sync
   - Trigger: GitHub PR merged
   - Action: Update Linear issue to "Done"
   - Action: Post to Slack

2. New Run Notification
   - Trigger: Webhook from orchestrator
   - Action: Send email to stakeholders
   - Action: Create Notion log entry

3. Daily Status Report
   - Trigger: Cron (9am daily)
   - Action: Query Linear for open issues
   - Action: Generate summary
   - Action: Post to Slack/Email

4. PHI Alert Workflow
   - Trigger: Webhook on PHI detection
   - Action: Notify governance team
   - Action: Create audit log
   - Action: Block if no approval
```

### When to Use n8n
| Task | Use n8n? | Alternative |
|------|----------|-------------|
| Automate deployments | ✅ Yes | GitHub Actions |
| Connect Linear ↔ GitHub | ✅ Yes | Native integration |
| Custom notifications | ✅ Yes | Direct API calls |
| Complex multi-step workflows | ✅ Yes | Custom code |
| Simple one-off tasks | ❌ No | Direct tool use |

### Claude Coworker Prompt for n8n
```
When automating workflows:
1. Check if n8n workflow already exists
2. For new automations, describe the workflow to me
3. I'll create it in n8n Cloud or self-hosted instance
4. Provide webhook URLs back for integration

n8n Cloud URL: [Your n8n instance URL]
```

---

## 2. Notion API

### What It Does
- Create/update pages and databases
- Search across workspace
- Manage documentation
- Track project status

### MCP Commands Available
```
Notion:notion-search        # Search pages/databases
Notion:notion-fetch         # Get page content
Notion:notion-create-pages  # Create new pages
Notion:notion-update-page   # Update existing pages
Notion:notion-get-users     # List workspace users
Notion:notion-get-teams     # List teamspaces
```

### ResearchFlow Integration
```typescript
// Key Notion Databases
const NOTION_DATABASES = {
  missionControl: 'ResearchFlow Mission Control',
  taskTracker: 'Development Tasks',
  documentation: 'Technical Documentation',
  aiTools: 'AI Tool Inventory',  // Where your screenshot came from!
};

// Update task status
await Notion:notion-update-page({
  page_id: taskId,
  command: 'update_properties',
  properties: { Status: 'Complete' }
});
```

### When to Use Notion
| Task | Use Notion? | Alternative |
|------|-------------|-------------|
| Documentation | ✅ Yes | Markdown in repo |
| Project tracking | ⚠️ Maybe | Linear (better for dev) |
| Knowledge base | ✅ Yes | Confluence |
| Meeting notes | ✅ Yes | Google Docs |
| Code snippets | ❌ No | GitHub Gists |

---

## 3. Continue.dev

### What It Does
- Inline code completions
- Chat with codebase context
- Custom slash commands
- Multi-model support

### Configuration
```json
// ~/.continue/config.json
{
  "models": [
    {
      "title": "Claude 3.5 Sonnet",
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    },
    {
      "title": "GPT-4 Turbo",
      "provider": "openai", 
      "model": "gpt-4-turbo-preview"
    },
    {
      "title": "Local (LM Studio)",
      "provider": "lmstudio",
      "model": "codellama-13b"
    }
  ],
  "slashCommands": [
    {
      "name": "researchflow",
      "description": "Generate ResearchFlow component",
      "prompt": "Create a React component following ResearchFlow patterns..."
    }
  ],
  "contextProviders": [
    { "name": "codebase" },
    { "name": "docs", "params": { "sites": ["https://tanstack.com/query"] } },
    { "name": "terminal" }
  ]
}
```

### Key Commands
| Command | Use Case |
|---------|----------|
| Tab | Accept completion |
| Cmd+L | Open chat |
| Cmd+I | Inline edit |
| /edit | Edit selection |
| /comment | Add comments |
| @codebase | Search codebase |

### When to Use Continue.dev
| Task | Use Continue? | Alternative |
|------|---------------|-------------|
| Inline completions | ✅ Yes | Copilot |
| Quick edits | ✅ Yes | Cursor |
| Codebase questions | ✅ Yes | Cody |
| Multi-file refactor | ⚠️ Maybe | Cursor better |

---

## 4. Replit Agent

### What It Does
- Full-stack prototyping
- Instant deployment
- AI-assisted development
- Collaborative editing

### ResearchFlow Integration
```markdown
# Replit Agent Workflow

1. **Create Prototype**
   "Create a React component that displays a 20-stage workflow timeline
   with status indicators. Use Tailwind CSS."

2. **Iterate**
   "Add click handlers and a detail panel when a stage is selected"

3. **Export to Main Repo**
   - Copy validated code
   - Adjust imports for project structure
   - Commit to researchflow-production
```

### When to Use Replit Agent
| Task | Use Replit? | Alternative |
|------|-------------|-------------|
| Quick prototype | ✅ Yes | v0.dev |
| Full-stack demo | ✅ Yes | Local dev |
| Shareable preview | ✅ Yes | Vercel preview |
| Production code | ❌ No | Main repo |
| Complex integration | ❌ No | Local dev |

---

## 5. Context7 (MCP Server)

### What It Does
- Provides documentation context to AI
- Fetches library docs on demand
- Reduces hallucinations
- Up-to-date API references

### How to Use
```markdown
# Context7 provides real-time documentation lookup

When working with libraries, Context7 can fetch current docs:
- React Query documentation
- Prisma schema reference
- Tailwind CSS classes
- shadcn/ui component APIs

# Example Usage
"Using Context7, look up the TanStack Query useQuery options"
"Context7: What's the Prisma syntax for a many-to-many relation?"
```

### When to Use Context7
| Task | Use Context7? | Alternative |
|------|---------------|-------------|
| Library API lookup | ✅ Yes | Web search |
| Framework patterns | ✅ Yes | Documentation |
| Outdated knowledge | ✅ Yes | Web search |
| Project-specific code | ❌ No | Codebase search |

---

## 6. Figma AI / Figma MCP

### What It Does
- Extract design specs
- Get design tokens (colors, spacing)
- Generate screenshots
- Create Code Connect mappings

### MCP Commands Available
```
Figma:whoami                 # Check auth status
Figma:get_design_context     # Get component specs
Figma:get_screenshot         # Capture node image
Figma:get_variable_defs      # Get design tokens
Figma:get_code_connect_map   # Check code mappings
Figma:get_metadata           # Get node structure
Figma:generate_diagram       # Create FigJam diagrams
```

### ResearchFlow Integration
```typescript
// Before creating ANY UI component:

// 1. Get design context
const specs = await Figma:get_design_context({
  fileKey: "your-figma-file-key",
  nodeId: "component-node-id"
});

// 2. Get design tokens
const tokens = await Figma:get_variable_defs({
  fileKey: "your-figma-file-key",
  nodeId: "component-node-id"  
});

// 3. Create component matching specs
// 4. Add Code Connect mapping
await Figma:add_code_connect_map({
  fileKey: "...",
  nodeId: "...",
  componentName: "RunTimeline",
  source: "https://github.com/.../RunTimeline.tsx",
  label: "React"
});
```

### When to Use Figma
| Task | Use Figma? | Alternative |
|------|------------|-------------|
| Get exact specs | ✅ Yes | Screenshot + guess |
| Design tokens | ✅ Yes | Hardcode values |
| Component preview | ✅ Yes | Build and check |
| Architecture diagrams | ⚠️ Maybe | Mermaid in docs |

---

## 7. Mercury Coder

### What It Does
- Fast UI iteration
- Quick component generation
- Lightweight completions
- Speed over depth

### When to Use Mercury
| Task | Use Mercury? | Alternative |
|------|--------------|-------------|
| Quick UI draft | ✅ Yes | v0.dev |
| Simple components | ✅ Yes | Claude |
| Complex logic | ❌ No | Claude |
| Architecture | ❌ No | Claude |

### ResearchFlow Integration
```markdown
# Mercury is best for rapid UI iterations

Use Mercury when:
- You need a quick first draft
- Simple, self-contained components
- Speed matters more than perfection

Don't use Mercury when:
- Complex business logic
- Security-sensitive code
- Architectural decisions
```

---

## 8. Claude (Anthropic)

### What It Does
- Complex reasoning
- Architecture design
- Security review
- Multi-step planning
- Code explanation

### ResearchFlow Integration
This is your primary AI assistant for:
- System design and architecture
- Complex business logic
- Security-sensitive code
- Multi-file coordination
- Code review and debugging

### When to Use Claude
| Task | Use Claude? | Alternative |
|------|-------------|-------------|
| Architecture | ✅ Yes | - |
| Complex logic | ✅ Yes | GPT-4 |
| Security review | ✅ Yes | - |
| Simple completions | ❌ No | Continue.dev |
| UI generation | ⚠️ Maybe | v0.dev faster |

---

## 9. Sourcegraph Cody

### What It Does
- Code search across repos
- AI-assisted code understanding
- Find references and usages
- Explain complex code

### Configuration
```json
// Install Cody extension in VS Code
// Configure for your codebase:
{
  "cody.serverEndpoint": "https://sourcegraph.com",
  "cody.codebase": "github.com/ry86pkqf74-rgb/researchflow-production"
}
```

### Key Commands
| Command | Use Case |
|---------|----------|
| `Cody: Explain Code` | Understand complex functions |
| `Cody: Find References` | Find all usages |
| `Cody: Generate Tests` | Create test scaffolds |
| `Cody: Document Code` | Add JSDoc comments |

### When to Use Cody
| Task | Use Cody? | Alternative |
|------|-----------|-------------|
| Find code usages | ✅ Yes | grep/ripgrep |
| Understand legacy code | ✅ Yes | Claude |
| Cross-repo search | ✅ Yes | GitHub search |
| Generate new code | ⚠️ Maybe | Claude/Cursor |

---

## 10. GPT-4 / ChatGPT Pro

### What It Does
- Code generation
- Structured outputs (JSON mode)
- API integration
- Broad knowledge

### When to Use GPT-4
| Task | Use GPT-4? | Alternative |
|------|------------|-------------|
| OpenAPI generation | ✅ Yes | Claude |
| JSON schemas | ✅ Yes | Claude |
| Type definitions | ✅ Yes | Codex |
| Complex reasoning | ⚠️ Maybe | Claude better |

### ResearchFlow Integration
```typescript
// Use GPT-4 for structured outputs
const response = await openai.chat.completions.create({
  model: "gpt-4-turbo-preview",
  response_format: { type: "json_object" },
  messages: [
    { role: "system", content: "Generate TypeScript types..." },
    { role: "user", content: schemaDescription }
  ]
});
```

---

## 11. Grok (xAI)

### What It Does
- Code review
- Bug hunting
- Test generation
- Quick debugging

### When to Use Grok
| Task | Use Grok? | Alternative |
|------|-----------|-------------|
| Code review | ✅ Yes | Claude |
| Find bugs | ✅ Yes | Cody |
| Write tests | ✅ Yes | Codex |
| Architecture | ❌ No | Claude |

### ResearchFlow Integration
```markdown
# Grok is great for:
- Reviewing PRs
- Finding edge cases
- Generating test cases
- Quick debugging sessions

# Prompt pattern:
"Review this code for bugs, edge cases, and security issues:
[paste code]"
```

---

## 12. LM Studio (Local LLM)

### What It Does
- Run LLMs locally
- No API costs
- Privacy for sensitive data
- Offline capability

### Configuration
```bash
# Start LM Studio server
# Default: http://localhost:1234

# Configure Continue.dev to use it:
# Add to ~/.continue/config.json models array:
{
  "title": "Local CodeLlama",
  "provider": "lmstudio",
  "model": "codellama-13b-instruct"
}
```

### When to Use LM Studio
| Task | Use LM Studio? | Alternative |
|------|----------------|-------------|
| Sensitive/PHI code | ✅ Yes | Cloud APIs |
| Offline work | ✅ Yes | - |
| High volume tasks | ✅ Yes | Paid APIs |
| Best quality | ❌ No | Claude/GPT-4 |
| Complex reasoning | ❌ No | Claude |

### ResearchFlow Integration
```markdown
# LM Studio for ResearchFlow

Best uses:
- Processing PHI-adjacent code locally
- Bulk code generation (save API costs)
- Offline development
- Testing prompts before using paid APIs

Models to run:
- CodeLlama 13B/34B for code
- Mistral 7B for general tasks
- Deepseek Coder for completions
```

---

# ============================================================================
# TOOL SELECTION MATRIX
# ============================================================================

## Quick Reference: Which Tool for What?

| Task | 1st Choice | 2nd Choice | 3rd Choice |
|------|------------|------------|------------|
| **Architecture Design** | Claude | GPT-4 | - |
| **UI Component** | Figma → v0.dev → Cursor | Replit | Mercury |
| **Complex Logic** | Claude | GPT-4 | - |
| **Type Generation** | GPT-4 | Claude | Codex |
| **Inline Completion** | Continue.dev | Copilot | Cody |
| **Multi-file Edit** | Cursor | Continue.dev | Manual |
| **Code Search** | Cody | grep | GitHub |
| **Code Review** | Grok | Claude | Cody |
| **Test Generation** | Grok | Codex | Claude |
| **Quick Prototype** | Replit | v0.dev | CodeSandbox |
| **Documentation** | Notion | Claude | Markdown |
| **Workflow Automation** | n8n | GitHub Actions | Custom |
| **Library Docs** | Context7 | Web Search | Docs site |
| **Sensitive Code** | LM Studio | Claude (careful) | - |
| **Design Specs** | Figma MCP | Screenshot | - |
| **Issue Tracking** | Linear MCP | Notion | GitHub |

---

# ============================================================================
# MASTER DISCOVERY & VERIFICATION PROMPT
# ============================================================================

**Copy this entire block to Claude Coworker to verify all tools:**

```markdown
# 🔍 COMPLETE AI TOOL VERIFICATION

You have access to 12 AI tools. Verify EACH ONE before starting work.

## STEP 1: MCP INTEGRATIONS

### Figma MCP
Figma:whoami

### Linear MCP  
Linear:get_user query="me"

### Notion MCP
Notion:notion-get-users query="logan"

### Vercel MCP (if available)
List deployments

## STEP 2: IDE TOOLS STATUS

Report which of these you can access:
- [ ] Continue.dev - Inline completions?
- [ ] Cursor - Multi-file editing?
- [ ] Sourcegraph Cody - Code search?
- [ ] GitHub Copilot - Suggestions?

## STEP 3: AI ASSISTANTS

Confirm access to:
- [ ] Claude (that's you!)
- [ ] GPT-4 / ChatGPT Pro
- [ ] Mercury Coder
- [ ] Grok (xAI)
- [ ] LM Studio (local)

## STEP 4: PLATFORMS

Check availability:
- [ ] Replit Agent
- [ ] n8n Cloud
- [ ] Context7 MCP

## STEP 5: CREATE STATUS MATRIX

| Tool | Status | How to Access |
|------|--------|---------------|
| n8n | ✅/⚠️/❌ | |
| Notion API | ✅/⚠️/❌ | |
| Continue.dev | ✅/⚠️/❌ | |
| Replit Agent | ✅/⚠️/❌ | |
| Context7 | ✅/⚠️/❌ | |
| Figma AI | ✅/⚠️/❌ | |
| Mercury Coder | ✅/⚠️/❌ | |
| Claude | ✅/⚠️/❌ | |
| Sourcegraph Cody | ✅/⚠️/❌ | |
| GPT-4 | ✅/⚠️/❌ | |
| Grok | ✅/⚠️/❌ | |
| LM Studio | ✅/⚠️/❌ | |

## STEP 6: TOOL USAGE RULES

For EVERY task, follow this decision tree:

1. **UI Task?**
   → Figma:get_design_context FIRST
   → Then v0.dev or Replit for scaffold
   → Then Cursor for integration

2. **Logic Task?**
   → Claude for complex reasoning
   → GPT-4 for structured output
   → LM Studio if sensitive

3. **Code Search?**
   → Sourcegraph Cody
   → Context7 for library docs

4. **Automation?**
   → n8n for workflows
   → GitHub Actions for CI/CD

5. **Documentation?**
   → Notion for updates
   → Claude for writing

6. **Testing?**
   → Grok for test generation
   → Cody for finding edge cases

## STEP 7: PARALLEL EXECUTION

ALWAYS work on multiple streams:
- While Figma loads → Start Claude planning
- While generating types → Create Linear issues  
- While building → Write tests

## BEGIN VERIFICATION NOW

Report the complete status matrix before proceeding with any work.
```

---

# ============================================================================
# PHASE 4 TOOL ASSIGNMENTS (Updated)
# ============================================================================

| Stream | Primary Tools | Secondary Tools | Automation |
|--------|---------------|-----------------|------------|
| **4A: API** | GPT-4, Claude | Continue.dev, Cursor | n8n webhook on complete |
| **4B: WebSocket** | Claude | Continue.dev | n8n event routing |
| **4C: Live Run** | Figma → Replit → Cursor | Mercury, Continue | n8n status updates |
| **4D: Artifacts** | Figma → v0.dev → Cursor | Cody for search | - |
| **4E: Polish** | Cursor, Continue | Mercury | Notion doc updates |
| **4F: Testing** | Grok, Cody | Claude | n8n test reports |

---

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

## Tool Not Working?

| Tool | Common Issue | Fix |
|------|--------------|-----|
| Figma MCP | Auth expired | Reconnect in Claude settings |
| Linear MCP | Team not found | Run `Linear:list_teams` first |
| Notion MCP | Page not found | Check page ID format |
| Continue.dev | Not completing | Check config.json models |
| Cody | No results | Verify codebase indexed |
| LM Studio | Slow | Use smaller model |
| n8n | Webhook fails | Check URL and auth |
| Context7 | Outdated docs | Clear cache, refetch |
| Replit | Rate limited | Wait or use v0.dev |

## Fallback Chain

```
Primary fails? → Use secondary
Secondary fails? → Use tertiary
All fail? → Manual implementation + document issue
```

---

*Document Version: 2.0*
*Includes: All 12 tools from your Notion AI Tool Inventory*
*n8n, Notion API, Continue.dev, Replit Agent, Context7, Figma AI, Mercury Coder, Claude, Sourcegraph Cody, GPT-4, Grok, LM Studio*

---

# ============================================================================
# PHASE 10 ADDITIONS: CUSTOM TIER & FEATURE FLAGS
# ============================================================================

## CUSTOM Tier in Router

ResearchFlow's AI router now supports a CUSTOM tier for deploying self-managed models:

### Router Tiers

```typescript
export type ModelTier = 'free' | 'standard' | 'pro' | 'enterprise' | 'custom';

interface TierConfig {
  tier: ModelTier;
  costPerToken?: number;
  rateLimit?: number;           // requests per minute
  availability?: 'always' | 'business-hours' | 'limited';
  priority?: 'low' | 'normal' | 'high';
  features: {
    finetuning?: boolean;
    customization?: boolean;
    privateDeployment?: boolean;
  };
}

const customTierConfig: TierConfig = {
  tier: 'custom',
  costPerToken: 0,              // Self-hosted = no per-token cost
  rateLimit: 1000,              // Your own rate limits
  availability: 'always',
  priority: 'high',
  features: {
    finetuning: true,
    customization: true,
    privateDeployment: true
  }
};
```

### Using CUSTOM Tier

```typescript
// Route to custom-deployed model
const response = await aiRouter.dispatch({
  task: {
    type: 'text_generation',
    payload: { prompt: 'Extract methodology...' }
  },
  tier: 'custom',
  model: 'research-analyzer'  // Your Ollama model
});

// Or with fallback chain
const response = await aiRouter.dispatch({
  task: { type: 'text_generation', payload: {...} },
  preferredTier: 'custom',
  fallbackTiers: ['pro', 'enterprise']
};
```

### Cost Model for CUSTOM Tier

| Component | Cost |
|-----------|------|
| Ollama server hosting | Variable (your infrastructure) |
| GPU rental (optional) | $0.30-1.50/hour |
| Bandwidth | ~$0.01-0.10/GB |
| **Total typical** | **$0 (self-hosted) - $50+/month (cloud)** |

---

## Feature Flags Reference

### Phase 10 Feature Flags

All custom agent and CUSTOM tier features are controlled via feature flags for gradual rollout:

```typescript
export enum FeatureFlagKey {
  // Custom agents
  CUSTOM_AGENT_ENABLED = 'custom_agent_enabled',
  CUSTOM_AGENT_V2 = 'custom_agent_v2',
  CUSTOM_AGENT_ADVANCED_ROUTING = 'custom_agent_advanced_routing',
  
  // Custom tier in router
  CUSTOM_AGENT_MEMORY_MANAGEMENT = 'custom_agent_memory_management',
  CUSTOM_AGENT_PERFORMANCE_MONITORING = 'custom_agent_performance_monitoring',
  
  // A/B testing variants
  CUSTOM_AGENT_AB_TEST_VARIANT_A = 'custom_agent_ab_test_variant_a',
  CUSTOM_AGENT_AB_TEST_VARIANT_B = 'custom_agent_ab_test_variant_b',
  CUSTOM_AGENT_AB_TEST_CONTROL = 'custom_agent_ab_test_control',
  
  // Experimental features
  CUSTOM_AGENT_EXPERIMENTAL_INFERENCE = 'custom_agent_experimental_inference',
  CUSTOM_AGENT_EXPERIMENTAL_CACHING = 'custom_agent_experimental_caching',
  CUSTOM_AGENT_EXPERIMENTAL_BATCH_PROCESSING = 'custom_agent_experimental_batch_processing'
}

interface FeatureFlagConfig {
  key: FeatureFlagKey;
  enabled: boolean;
  rolloutPercentage: number;    // 0-100% of users
  variant?: 'a' | 'b' | 'control';
  metadata?: Record<string, unknown>;
}

const flagConfigs: Record<FeatureFlagKey, FeatureFlagConfig> = {
  [FeatureFlagKey.CUSTOM_AGENT_ENABLED]: {
    key: FeatureFlagKey.CUSTOM_AGENT_ENABLED,
    enabled: true,
    rolloutPercentage: 50,
    metadata: {
      description: 'Enable custom agent functionality for users',
      phase: 10,
      launchDate: '2026-Q1'
    }
  },
  
  [FeatureFlagKey.CUSTOM_AGENT_V2]: {
    key: FeatureFlagKey.CUSTOM_AGENT_V2,
    enabled: true,
    rolloutPercentage: 30,
    metadata: {
      description: 'Custom Agent V2 with improved routing',
      launchDate: '2026-Q1'
    }
  },
  
  [FeatureFlagKey.CUSTOM_AGENT_ADVANCED_ROUTING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_ADVANCED_ROUTING,
    enabled: true,
    rolloutPercentage: 25,
    metadata: {
      description: 'Advanced routing with semantic task matching',
      riskLevel: 'medium'
    }
  },
  
  [FeatureFlagKey.CUSTOM_AGENT_MEMORY_MANAGEMENT]: {
    key: FeatureFlagKey.CUSTOM_AGENT_MEMORY_MANAGEMENT,
    enabled: true,
    rolloutPercentage: 40,
    metadata: {
      description: 'Enhanced memory and token management',
      performanceImprovement: '35%'
    }
  },
  
  [FeatureFlagKey.CUSTOM_AGENT_PERFORMANCE_MONITORING]: {
    key: FeatureFlagKey.CUSTOM_AGENT_PERFORMANCE_MONITORING,
    enabled: true,
    rolloutPercentage: 60,
    metadata: {
      description: 'Real-time performance metrics and alerts',
      metricsTracked: ['latency', 'throughput', 'cost', 'error_rate']
    }
  },
  
  // A/B test variants for routing algorithm comparison
  [FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_A]: {
    key: FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_A,
    enabled: true,
    rolloutPercentage: 33,
    variant: 'a',
    metadata: {
      description: 'A/B Test Variant A: Original routing algorithm',
      testName: 'custom_agent_routing_ab_test',
      testStartDate: '2026-01-30'
    }
  },
  
  [FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_B]: {
    key: FeatureFlagKey.CUSTOM_AGENT_AB_TEST_VARIANT_B,
    enabled: true,
    rolloutPercentage: 33,
    variant: 'b',
    metadata: {
      description: 'A/B Test Variant B: Optimized routing algorithm',
      testName: 'custom_agent_routing_ab_test',
      expectedImprovement: '15-20%'
    }
  }
};
```

### Managing Feature Flags

```typescript
import { FeatureFlagManager, FeatureFlagKey } from '@researchflow/ai-router';

const flagManager = new FeatureFlagManager();

// Check if feature enabled for user
const context = {
  userId: 'user-123',
  organizationId: 'org-456',
  tier: 'pro',
  segment: 'early-adopter'
};

const isEnabled = flagManager.evaluateFlag(
  FeatureFlagKey.CUSTOM_AGENT_V2,
  context
).enabled;

if (isEnabled) {
  // Use v2 agent
  const agent = new CustomAgentV2();
} else {
  // Use v1 agent
  const agent = new CustomAgent();
}

// Get A/B test variant
const variant = flagManager.getABTestVariant(
  'custom_agent_routing_ab_test',
  context.userId
);

if (variant === 'a') {
  // Use algorithm A
} else if (variant === 'b') {
  // Use algorithm B
} else {
  // Control group - baseline
}

// Adjust rollout percentage
flagManager.setRolloutPercentage(
  FeatureFlagKey.CUSTOM_AGENT_V2,
  50  // Increase from 30% to 50%
);

// View statistics
const stats = flagManager.getFlagStatistics();
console.log(stats);
// Output:
// {
//   phase10: {
//     totalEnabled: 5,
//     totalDisabled: 0,
//     averageRolloutPercentage: 38,
//     flags: [...]
//   },
//   abTests: {
//     totalEnabled: 3,
//     totalDisabled: 0,
//     averageRolloutPercentage: 33,
//     flags: [...]
//   }
// }
```

---

## Monitoring Endpoints

### Health Check Endpoint

```
GET /api/monitoring/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-30T12:00:00Z",
  "components": {
    "database": { "status": "healthy", "latency": 5 },
    "redis": { "status": "healthy", "latency": 2 },
    "vectorStore": { "status": "healthy", "latency": 45 },
    "aiRouter": { "status": "healthy", "latency": 150 }
  }
}
```

### Metrics Endpoint

```
GET /api/monitoring/metrics
```

Response:
```json
{
  "timestamp": "2026-01-30T12:00:00Z",
  "agents": {
    "data-extraction": {
      "tasksProcessed": 1250,
      "successRate": 0.98,
      "avgLatency": 2314,
      "costPerTask": 0.15,
      "errorRate": 0.02
    },
    "statistical-analysis": {
      "tasksProcessed": 850,
      "successRate": 0.99,
      "avgLatency": 3500,
      "costPerTask": 0.22
    }
  },
  "featureFlags": {
    "totalFlags": 11,
    "enabledFlags": 11,
    "avgRolloutPercentage": 38.5
  }
}
```

### Feature Flag Status Endpoint

```
GET /api/monitoring/feature-flags?userId=user-123
```

Response:
```json
{
  "userId": "user-123",
  "evaluatedAt": "2026-01-30T12:00:00Z",
  "flags": {
    "custom_agent_enabled": {
      "enabled": true,
      "reason": "enabled",
      "rolloutPercentage": 50
    },
    "custom_agent_v2": {
      "enabled": true,
      "reason": "rollout_percentage",
      "rolloutPercentage": 30
    },
    "custom_agent_ab_test_variant_b": {
      "enabled": true,
      "variant": "b",
      "testName": "custom_agent_routing_ab_test"
    }
  }
}
```

### Router Metrics Endpoint

```
GET /api/monitoring/router/metrics
```

Response:
```json
{
  "timestamp": "2026-01-30T12:00:00Z",
  "tiers": {
    "free": {
      "requestsProcessed": 1500,
      "avgCost": 0.0,
      "avgLatency": 2500
    },
    "standard": {
      "requestsProcessed": 2300,
      "avgCost": 0.08,
      "avgLatency": 1200
    },
    "pro": {
      "requestsProcessed": 1200,
      "avgCost": 0.35,
      "avgLatency": 800
    },
    "custom": {
      "requestsProcessed": 450,
      "avgCost": 0.0,
      "avgLatency": 950
    }
  }
}
```

### Cost Tracking Endpoint

```
GET /api/monitoring/costs?period=month
```

Response:
```json
{
  "period": "2026-01",
  "totalCost": 1250.50,
  "byCost": {
    "gpt-4o": 850.25,
    "claude-opus": 300.15,
    "custom-models": 0,
    "ollama": 0,
    "local-models": 0
  },
  "byFeature": {
    "customAgents": 320.50,
    "ragPipeline": 450.25,
    "fineTuning": 200.00,
    "other": 280.75
  },
  "projectedMonthlySpend": 1250.50,
  "budgetAlert": false
}
```

---

## Integration with Monitoring Systems

### Prometheus Metrics

```typescript
// Export metrics for Prometheus scraping
app.get('/metrics', (req, res) => {
  const metrics = {
    custom_agents_total: counter.total,
    custom_agents_success_rate: gauge.successRate,
    custom_agents_latency_ms: histogram.latency,
    feature_flags_enabled: gauge.enabledCount
  };
  
  res.set('Content-Type', 'application/openmetrics-text');
  res.send(formatPrometheusMetrics(metrics));
});
```

### DataDog Integration

```typescript
const StatsD = require('node-dogstatsd').StatsD;

const dogstatsd = new StatsD({
  host: process.env.DATADOG_AGENT_HOST,
  port: process.env.DATADOG_AGENT_PORT
});

// Track custom agent performance
dogstatsd.gauge('custom_agent.latency', latencyMs, {
  tags: ['agent:data-extraction', 'phase:10']
});

dogstatsd.increment('custom_agent.requests', {
  tags: ['agent:manuscript-drafting', 'status:success']
});
```

---

*Phase 10 Addition | Updated 2026-01-30*
