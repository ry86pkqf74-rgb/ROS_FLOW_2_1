import { raw } from 'body-parser';
import { Router, Request, Response } from 'express';
import * as z from 'zod';

// Import service modules
import {
  CursorCodeChangeEvent,
  CursorAgentTriggerEvent,
} from '../../packages/cursor-integration/src';
import {
  DockerWebhookPayload,
  verifyDockerWebhook,
} from '../services/dockerRegistryService';
import {
  FigmaWebhookPayload,
  verifyFigmaWebhookPasscode,
  getFigmaFile,
  postFigmaComment,
  postAIDesignReview,
} from '../services/figmaService';
import {
  LinearWebhookPayload,
  verifyLinearWebhookSignature,
  createLinearIssue,
  updateLinearIssue,
  addLinearComment,
} from '../services/linearService';
import {
  SlackSlashCommand,
  SlackInteractivePayload,
  verifySlackSignature,
  createSlashCommandResponse,
  postSlackMessage,
  notifyAIAgentTask,
} from '../services/slackService';
import { asString } from '../utils/asString';

const router = Router();

/**
 * Linear Webhook Handler
 * Receives issue updates, comments, and triggers AI agents
 */
router.post('/linear/webhook', async (req: Request, res: Response) => {
  try {
    const signature = req.headers['linear-signature'] as string;
    const secret = process.env.LINEAR_WEBHOOK_SECRET;

    if (!secret || !verifyLinearWebhookSignature(signature, JSON.stringify(req.body), secret)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }

    const payload: LinearWebhookPayload = req.body;

    // Handle different Linear events
    switch (payload.action) {
      case 'create':
        if (payload.type === 'Issue') {
          // Check for AI agent labels
          const aiAgentLabel = payload.data.labels?.find((l) =>
            l.name.startsWith('ai-agent:')
          );

          if (aiAgentLabel) {
            const agentName = aiAgentLabel.name.split(':')[1];
            // Trigger AI agent execution
            await triggerAIAgent({
              agentName,
              taskId: payload.data.id,
              taskTitle: payload.data.title || '',
              taskDescription: payload.data.description,
              priority: payload.data.priority,
            });
          }
        }
        break;

      case 'update':
        // Handle issue updates
        break;
    }

    res.json({ received: true });
  } catch (error) {
    console.error('Linear webhook error:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

/**
 * Figma Webhook Handler
 * Receives design updates and triggers design review
 */
router.post('/figma/webhook', async (req: Request, res: Response) => {
  try {
    const payload: FigmaWebhookPayload = req.body;
    const passcode = process.env.FIGMA_WEBHOOK_PASSCODE;

    if (!passcode || !verifyFigmaWebhookPasscode(payload, passcode)) {
      return res.status(401).json({ error: 'Invalid passcode' });
    }

    // Handle different Figma events
    switch (payload.event_type) {
      case 'FILE_UPDATE':
        // Trigger design review agent
        await triggerDesignReview({
          fileKey: payload.file_key,
          fileName: payload.file_name,
          triggeredBy: payload.triggered_by?.handle,
        });
        break;

      case 'FILE_COMMENT':
        // Handle design comments
        break;
    }

    res.json({ received: true });
  } catch (error) {
    console.error('Figma webhook error:', error);
    res.status(500).json({ error: 'Webhook processing failed' });
  }
});

/**
 * Docker Hub Webhook Handler
 * Receives image push events and triggers deployments
 */
router.post('/docker/webhook', async (req: Request, res: Response) => {
  try {
    const payload: DockerWebhookPayload = req.body;

    // Verify callback URL
    if (payload.callback_url) {
      await verifyDockerWebhook(payload.callback_url);
    }

    // Trigger deployment based on tag
    const tag = payload.push_data.tag;
    const repository = payload.repository.repo_name;

    // Determine environment from tag
    let environment = 'development';
    if (tag === 'latest' || tag.startsWith('v')) {
      environment = 'production';
    } else if (tag === 'staging') {
      environment = 'staging';
    }

    await triggerDeployment({
      repository,
      tag,
      environment,
      pusher: payload.push_data.pusher,
    });

    res.json({ state: 'success', description: 'Deployment triggered' });
  } catch (error) {
    console.error('Docker webhook error:', error);
    res.json({ state: 'failure', description: 'Deployment failed' });
  }
});

/**
 * Slack Slash Command Handler
 * Handles /ros commands for AI agent interaction
 */
router.post('/slack/commands', async (req: Request, res: Response) => {
  try {
    const timestamp = req.headers['x-slack-request-timestamp'] as string;
    const signature = req.headers['x-slack-signature'] as string;
    const secret = process.env.SLACK_SIGNING_SECRET;

    if (!secret || !verifySlackSignature(signature, timestamp, req.rawBody, secret)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }

    const command: SlackSlashCommand = req.body;

    // Parse command
    const [action, ...args] = command.text.split(' ');

    switch (action) {
      case 'agent':
        // /ros agent <agent-name> [task-description]
        const agentName = args[0];
        const taskDescription = args.slice(1).join(' ');

        if (!agentName) {
          return res.json(
            createSlashCommandResponse({
              text: 'Usage: /ros agent <agent-name> [task-description]',
              response_type: 'ephemeral',
            })
          );
        }

        // Trigger agent asynchronously
        triggerAIAgentFromSlack(agentName, taskDescription, command.response_url);

        return res.json(
          createSlashCommandResponse({
            text: `🤖 Triggering agent: ${agentName}...`,
            response_type: 'ephemeral',
          })
        );

      case 'status':
        // /ros status [task-id]
        const taskId = args[0];
        const status = await getTaskStatus(taskId);

        return res.json(
          createSlashCommandResponse({
            text: status ? `Status: ${status}` : 'Task not found',
            response_type: 'ephemeral',
          })
        );

      case 'list':
        // /ros list [filter]
        const filter = args[0];
        const tasks = await listTasks(filter);

        return res.json(
          createSlashCommandResponse({
            text: `Active tasks:\n${tasks.map((t) => `• ${t.name}`).join('\n')}`,
            response_type: 'ephemeral',
          })
        );

      case 'help':
        return res.json(
          createSlashCommandResponse({
            text: `Available commands:
• /ros agent <name> [description] - Trigger AI agent
• /ros status [task-id] - Check task status
• /ros list [filter] - List active tasks
• /ros help - Show this help`,
            response_type: 'ephemeral',
          })
        );

      default:
        return res.json(
          createSlashCommandResponse({
            text: `Unknown command: ${action}. Type /ros help for usage.`,
            response_type: 'ephemeral',
          })
        );
    }
  } catch (error) {
    console.error('Slack command error:', error);
    res.json(
      createSlashCommandResponse({
        text: '❌ Command failed. Please try again.',
        response_type: 'ephemeral',
      })
    );
  }
});

/**
 * Slack Interactive Component Handler
 * Handles button clicks and menu selections
 */
router.post('/slack/interactions', async (req: Request, res: Response) => {
  try {
    const timestamp = req.headers['x-slack-request-timestamp'] as string;
    const signature = req.headers['x-slack-signature'] as string;
    const secret = process.env.SLACK_SIGNING_SECRET;

    if (!secret || !verifySlackSignature(signature, timestamp, req.rawBody, secret)) {
      return res.status(401).json({ error: 'Invalid signature' });
    }

    const payload: SlackInteractivePayload = JSON.parse(req.body.payload);

    // Handle different interaction types
    if (payload.type === 'block_actions' && payload.actions) {
      for (const action of payload.actions) {
        if (action.action_id.startsWith('approve_')) {
          // Handle approval actions
          const taskId = action.value;
          await approveTask(taskId);
        } else if (action.action_id.startsWith('reject_')) {
          // Handle rejection actions
          const taskId = action.value;
          await rejectTask(taskId);
        }
      }
    }

    res.json({ response_type: 'ephemeral', text: 'Action processed' });
  } catch (error) {
    console.error('Slack interaction error:', error);
    res.status(500).json({ error: 'Interaction failed' });
  }
});

/**
 * Cursor Code Change Handler
 * Receives code changes from Cursor IDE
 */
router.post('/cursor/code-change', async (req: Request, res: Response) => {
  try {
    const apiKey = req.headers['x-api-key'] as string;
    if (apiKey !== process.env.CURSOR_API_KEY) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    const event: CursorCodeChangeEvent = req.body;

    // Process code changes (e.g., trigger code analysis)
    await processCodeChange(event);

    res.json({ success: true });
  } catch (error) {
    console.error('Cursor code change error:', error);
    res.status(500).json({ error: 'Failed to process code change' });
  }
});

/**
 * Cursor Agent Trigger Handler
 * Receives agent trigger requests from Cursor IDE
 */
router.post('/cursor/agent-trigger', async (req: Request, res: Response) => {
  try {
    const apiKey = req.headers['x-api-key'] as string;
    if (apiKey !== process.env.CURSOR_API_KEY) {
      return res.status(401).json({ error: 'Invalid API key' });
    }

    const event: CursorAgentTriggerEvent = req.body;

    // Trigger AI agent with code context
    const taskId = await triggerAIAgent({
      agentName: event.command,
      taskTitle: `${event.command} on ${event.filePath}:${event.line}`,
      taskDescription: event.context.code,
      priority: (event.params?.priority as number) || 2,
      metadata: {
        filePath: event.filePath,
        line: event.line,
        command: event.command,
        userId: event.userId,
      },
    });

    res.json({ success: true, taskId });
  } catch (error) {
    console.error('Cursor agent trigger error:', error);
    res.status(500).json({ error: 'Failed to trigger agent' });
  }
});

/**
 * Cursor Task Progress SSE Endpoint
 * Streams task progress updates to Cursor IDE
 */
router.get('/cursor/task-progress/:taskId', (req: Request, res: Response) => {
  const apiKey = req.query.apiKey as string;
  if (apiKey !== process.env.CURSOR_API_KEY) {
    return res.status(401).json({ error: 'Invalid API key' });
  }

  const taskId = asString(req.params.taskId);

  // Set headers for SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  // Subscribe to task updates
  const unsubscribe = subscribeToTaskUpdates(taskId, (update) => {
    res.write(`data: ${JSON.stringify(update)}\n\n`);

    if (update.status === 'completed' || update.status === 'failed') {
      res.end();
    }
  });

  // Cleanup on connection close
  req.on('close', () => {
    unsubscribe();
    res.end();
  });
});

// Helper functions (to be implemented)
async function triggerAIAgent(params: any): Promise<string> {
  // Implementation: Queue agent execution job
  return `task-${Date.now()}`;
}

async function triggerDesignReview(params: any): Promise<void> {
  // Implementation: Queue design review job
}

async function triggerDeployment(params: any): Promise<void> {
  // Implementation: Queue deployment job
}

async function triggerAIAgentFromSlack(
  agentName: string,
  description: string,
  responseUrl: string
): Promise<void> {
  // Implementation: Trigger agent and send updates to response_url
}

async function getTaskStatus(taskId: string): Promise<string | null> {
  // Implementation: Query task status from database
  return null;
}

async function listTasks(filter?: string): Promise<Array<{ name: string }>> {
  // Implementation: Query tasks from database
  return [];
}

async function approveTask(taskId: string): Promise<void> {
  // Implementation: Approve and execute task
}

async function rejectTask(taskId: string): Promise<void> {
  // Implementation: Reject and cancel task
}

async function processCodeChange(event: CursorCodeChangeEvent): Promise<void> {
  // Implementation: Process code changes
}

function subscribeToTaskUpdates(
  taskId: string,
  callback: (update: any) => void
): () => void {
  // Implementation: Subscribe to Redis/EventEmitter for task updates
  return () => {};
}

export default router;
