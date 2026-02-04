# Multi-Application Integration Setup Guide

Complete integration of Notion, Figma, Linear, Slack, Docker, and Cursor for AI-driven parallel task execution in ResearchFlow (ROS).

## 🎯 Overview

This integration enables:
- **Project Planning**: Notion → Linear sync with AI agent assignment
- **Design to Code**: Figma → Cursor code generation
- **Automated Deployment**: Docker → Slack notifications
- **Parallel AI Execution**: Multi-agent orchestration across all tools
- **Real-time Updates**: Bidirectional sync and webhooks

## 📦 Components Installed

### Service Modules
- [services/orchestrator/src/services/linearService.ts](services/orchestrator/src/services/linearService.ts) - Linear GraphQL API integration
- [services/orchestrator/src/services/figmaService.ts](services/orchestrator/src/services/figmaService.ts) - Figma REST API integration
- [services/orchestrator/src/services/dockerRegistryService.ts](services/orchestrator/src/services/dockerRegistryService.ts) - Docker Hub + Engine API
- [services/orchestrator/src/services/slackService.ts](services/orchestrator/src/services/slackService.ts) - Enhanced Slack with slash commands
- [services/orchestrator/src/services/notionService.ts](services/orchestrator/src/services/notionService.ts) - AI agent task tracking
- [services/orchestrator/src/services/multiToolOrchestrator.ts](services/orchestrator/src/services/multiToolOrchestrator.ts) - Parallel execution dispatcher

### Integration Package
- [packages/cursor-integration/](packages/cursor-integration/) - Cursor IDE bidirectional communication

### Routes & Webhooks
- [services/orchestrator/src/routes/integrations.ts](services/orchestrator/src/routes/integrations.ts) - All webhook handlers

### N8N Workflows
- [infrastructure/n8n/workflows/figma-design-sync.json](infrastructure/n8n/workflows/figma-design-sync.json)
- [infrastructure/n8n/workflows/linear-task-automation.json](infrastructure/n8n/workflows/linear-task-automation.json)
- [infrastructure/n8n/workflows/docker-deployment-pipeline.json](infrastructure/n8n/workflows/docker-deployment-pipeline.json)
- [infrastructure/n8n/workflows/multi-agent-orchestrator.json](infrastructure/n8n/workflows/multi-agent-orchestrator.json)

## 🚀 Setup Instructions

### 1. Configure Environment Variables

```bash
# Copy integration environment template
cp .env.integrations.example .env.integrations

# Edit with your credentials
nano .env.integrations
```

**Required Credentials:**

#### Linear
1. Go to Linear Settings → API → Create Personal API Key
2. Copy key to `LINEAR_API_KEY`
3. Create webhook: Settings → Webhooks → New Webhook
4. Set URL: `https://your-domain.com/api/integrations/linear/webhook`
5. Copy secret to `LINEAR_WEBHOOK_SECRET`

#### Figma
1. Go to Figma Settings → Personal Access Tokens
2. Generate new token with File content permission
3. Copy to `FIGMA_ACCESS_TOKEN`
4. In your Figma file: Plugins → Webhooks → New Webhook
5. Set URL and passcode in `FIGMA_WEBHOOK_SECRET`

#### Slack
1. Go to https://api.slack.com/apps
2. Create New App → From scratch
3. Add Bot Token Scopes: `chat:write`, `commands`, `users:read`, `channels:read`
4. Install to Workspace
5. Copy Bot User OAuth Token to `SLACK_BOT_TOKEN`
6. Basic Information → Signing Secret to `SLACK_SIGNING_SECRET`
7. Create slash command `/ros` → Request URL: `https://your-domain.com/api/integrations/slack/commands`

#### Docker Hub
1. Docker Hub → Account Settings → Security → Access Tokens
2. Generate token with Read/Write permissions
3. Copy to `DOCKER_HUB_ACCESS_TOKEN`
4. Repository → Webhooks → Add Webhook
5. URL: `https://your-domain.com/api/integrations/docker/webhook`

#### Notion
1. Go to https://www.notion.so/my-integrations
2. Create New Integration
3. Copy Internal Integration Token to `NOTION_API_KEY`
4. Share your databases with the integration
5. Copy database IDs from URLs to environment variables

#### Cursor
1. Generate API key: `openssl rand -hex 32`
2. Set in `CURSOR_API_KEY`
3. Configure in Cursor settings (when extension is installed)

### 2. Install Dependencies

```bash
# Install Cursor integration package
cd packages/cursor-integration
npm install
npm run build
cd ../..

# Install Notion SDK (if not already installed)
npm install @notionhq/client
```

### 3. Configure Webhook Routes

Add integration routes to your Express app:

```typescript
// services/orchestrator/src/index.ts
import integrationRoutes from './routes/integrations';

app.use('/api/integrations', integrationRoutes);
```

### 4. Setup N8N Workflows

```bash
# Import workflows to n8n
# Option 1: Via n8n UI
1. Open n8n: http://localhost:5678
2. Click "Import from File"
3. Import each workflow JSON from infrastructure/n8n/workflows/

# Option 2: Via n8n CLI
n8n import:workflow --input=infrastructure/n8n/workflows/figma-design-sync.json
n8n import:workflow --input=infrastructure/n8n/workflows/linear-task-automation.json
n8n import:workflow --input=infrastructure/n8n/workflows/docker-deployment-pipeline.json
n8n import:workflow --input=infrastructure/n8n/workflows/multi-agent-orchestrator.json
```

### 5. Configure Notion Databases

Create the following databases in Notion and share with your integration:

**AI Agent Tasks Database:**
Properties:
- Name (Title)
- Agent (Select): data-extraction, code-implementation, etc.
- Status (Status): queued, in-progress, blocked, completed, failed
- Priority (Select): low, medium, high, critical
- Assigned To (Text)
- Estimated Duration (Number)
- Tags (Multi-select)
- Last Updated (Date)
- Linear URL (URL)

**Projects Database:**
Properties:
- Name (Title)
- Status (Status): planning, active, completed
- Start Date (Date)
- Target Date (Date)
- Owner (Text)

**Deployments Database:**
Properties:
- Name (Title)
- Environment (Select): development, staging, production
- Version (Text)
- Status (Status): success, failed, rollback
- Deployed By (Text)
- Deployment Date (Date)
- Duration (Number)
- Services (Multi-select)

### 6. Start Services

```bash
# Start all services with integrations
docker-compose up -d

# Or start orchestrator only
cd services/orchestrator
npm run dev
```

### 7. Test Integrations

```bash
# Test Linear webhook
curl -X POST http://localhost:3001/api/integrations/linear/webhook \
  -H "Content-Type: application/json" \
  -H "linear-signature: test" \
  -d '{"action":"create","type":"Issue","data":{"id":"test-1","title":"Test Issue"}}'

# Test Slack command
# In Slack: /ros agent code-review Test code review

# Test Cursor agent trigger
curl -X POST http://localhost:3001/api/integrations/cursor/agent-trigger \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-cursor-api-key" \
  -d '{"type":"agent-trigger","command":"fix-this","filePath":"src/test.ts","line":10}'
```

## 🎨 Usage Examples

### 1. Trigger AI Agent from Linear

Create a Linear issue with label `ai-agent:code-implementation`:
```
Title: Implement user authentication
Description: Add JWT-based authentication to the API
Labels: ai-agent:code-implementation, backend
```

**Result**: AI agent automatically triggered, task created in Notion, team notified in Slack

### 2. Design to Code Workflow

Update Figma file → Automatic flow:
1. Figma webhook triggers
2. Design tokens extracted
3. Cursor receives code generation task
4. Linear issue created for tracking
5. Notion project updated
6. Slack notification sent

### 3. Parallel AI Review

Use Slack command:
```
/ros agent parallel-review main.ts
```

**Result**: 4 AI agents run in parallel:
- Security scan
- Performance analysis
- Code quality check
- Accessibility review

Results aggregated in Notion with Slack summary.

### 4. Full Deployment Pipeline

Push Docker image:
```bash
docker push yournamespace/researchflow:v1.0.0
```

**Automatic flow**:
1. Docker Hub webhook triggers
2. Notion deployment log created
3. Linear issue updated
4. Slack notifications (start → progress → success)
5. Health checks executed

### 5. Cursor Agent Triggers

In your code editor:
```typescript
// @agent fix-this {"priority": "high"}
function buggyFunction() {
  // AI will analyze and fix this
}

// @agent test {"framework": "jest"}
export function calculateTotal(items: Item[]) {
  // AI will generate tests
}

// @agent review
class AuthService {
  // AI will review for security and best practices
}
```

## 📊 Multi-Tool Orchestration

### Pre-built Workflows

Use the orchestrator to run complex workflows:

```typescript
import { MultiToolOrchestrator } from './services/multiToolOrchestrator';

const orchestrator = new MultiToolOrchestrator(redisConnection);

// Full deployment workflow
const tasks = MultiToolOrchestrator.createWorkflowPlan('full-deployment', {
  deploymentName: 'v1.0.0 Release',
  environment: 'production',
  version: 'v1.0.0',
  linearTeamId: 'team-123',
  slackChannel: '#releases',
});

const plan = await orchestrator.createExecutionPlan('Release v1.0.0', tasks);
await orchestrator.executePlan(plan.id);

// Monitor progress
orchestrator.on('task:completed', ({ task, result }) => {
  console.log(`✅ Completed: ${task.id}`);
});

orchestrator.on('plan:completed', (plan) => {
  console.log(`🎉 Plan completed: ${plan.name}`);
});
```

Available workflows:
- `full-deployment`: Notion → Linear → Docker → Slack
- `design-to-code`: Figma → Cursor → Linear → Slack
- `issue-to-deployment`: Linear → AI Agent → Docker → Slack
- `parallel-ai-review`: 4 parallel AI reviews → Notion → Slack

## 🔧 Troubleshooting

### Webhooks Not Received

1. Check webhook URLs are publicly accessible
2. Verify signature/passcode configuration
3. Check logs: `docker-compose logs orchestrator`
4. Test with ngrok for local development:
   ```bash
   ngrok http 3001
   # Use ngrok URL in webhook configurations
   ```

### Linear Issues Not Creating Tasks

1. Verify `ai-agent:*` label format
2. Check Linear webhook is active
3. Verify `LINEAR_WEBHOOK_SECRET` matches
4. Check orchestrator logs for errors

### Slack Commands Not Working

1. Verify slash command URL configuration
2. Check `SLACK_SIGNING_SECRET` is correct
3. Ensure bot has required scopes
4. Test signature verification

### Docker Deployments Not Triggering

1. Verify Docker Hub webhook is active
2. Check repository name matches configuration
3. Verify callback URL verification
4. Check deployment environment logic

## 📚 API Reference

### Webhook Endpoints

- `POST /api/integrations/linear/webhook` - Linear events
- `POST /api/integrations/figma/webhook` - Figma events
- `POST /api/integrations/docker/webhook` - Docker Hub events
- `POST /api/integrations/slack/commands` - Slack slash commands
- `POST /api/integrations/slack/interactions` - Slack interactive components
- `POST /api/integrations/cursor/code-change` - Cursor code changes
- `POST /api/integrations/cursor/agent-trigger` - Cursor agent triggers
- `GET /api/integrations/cursor/task-progress/:taskId` - SSE progress stream

## 🔐 Security Considerations

1. **Webhook Verification**: All webhooks verify signatures/passcodes
2. **API Key Rotation**: Rotate keys every 90 days (configurable)
3. **Rate Limiting**: 100 requests/minute per integration (configurable)
4. **PHI Scanning**: Enabled for healthcare compliance
5. **Secret Management**: Use environment variables, never commit secrets

## 📈 Monitoring

View integration metrics in Grafana:
- Dashboard: "Integration Health"
- URL: http://localhost:3000/d/integrations

Metrics tracked:
- Webhook success/failure rates
- Agent execution times
- Task completion rates
- API call volumes
- Error rates by integration

## 🤝 Contributing

To add new integrations:

1. Create service module in `services/orchestrator/src/services/`
2. Add webhook handler in `routes/integrations.ts`
3. Create n8n workflow in `infrastructure/n8n/workflows/`
4. Add environment variables
5. Update this README
6. Add tests

## 📝 License

MIT - See LICENSE file for details

---

**Need Help?**
- Check existing issues: https://github.com/your-org/researchflow/issues
- Documentation: https://docs.researchflow.io
- Slack Community: #researchflow-support
