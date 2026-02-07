import crypto from 'crypto';

import * as z from 'zod';

/**
 * Enhanced Slack Service Integration
 * Provides bidirectional communication, slash commands, interactive components,
 * and AI agent notifications
 */

// Configuration schema
export const SlackConfigSchema = z.object({
  botToken: z.string().min(1), // xoxb- token
  signingSecret: z.string().min(1),
  webhookUrl: z.string().url().optional(),
  appToken: z.string().optional(), // xapp- token for Socket Mode
});

export type SlackConfig = z.infer<typeof SlackConfigSchema>;

// Slack API endpoint
const SLACK_API_URL = 'https://slack.com/api';

/**
 * Verify Slack request signature
 * https://api.slack.com/authentication/verifying-requests-from-slack
 */
export function verifySlackSignature(
  signature: string,
  timestamp: string,
  body: string,
  signingSecret: string
): boolean {
  try {
    // Check timestamp to prevent replay attacks (5 minutes)
    const currentTime = Math.floor(Date.now() / 1000);
    if (Math.abs(currentTime - parseInt(timestamp)) > 60 * 5) {
      return false;
    }

    const sigBasestring = `v0:${timestamp}:${body}`;
    const hmac = crypto.createHmac('sha256', signingSecret);
    hmac.update(sigBasestring);
    const expectedSignature = `v0=${hmac.digest('hex')}`;

    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature)
    );
  } catch (error) {
    console.error('Failed to verify Slack signature:', error);
    return false;
  }
}

/**
 * Execute Slack API request
 */
async function slackApiRequest<T>(
  config: SlackConfig,
  method: string,
  data?: Record<string, unknown>
): Promise<{ ok: boolean; data?: T; error?: string }> {
  try {
    const response = await fetch(`${SLACK_API_URL}/${method}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${config.botToken}`,
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      return {
        ok: false,
        error: `Slack API error: ${response.status} ${response.statusText}`,
      };
    }

    const result = await response.json();

    if (!result.ok) {
      return {
        ok: false,
        error: result.error || 'Unknown Slack API error',
      };
    }

    return { ok: true, data: result };
  } catch (error) {
    console.error('Slack API request failed:', error);
    return {
      ok: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Post a message to a channel
 */
export async function postSlackMessage(
  config: SlackConfig,
  params: {
    channel: string;
    text?: string;
    blocks?: Array<Record<string, unknown>>;
    thread_ts?: string;
    attachments?: Array<Record<string, unknown>>;
  }
): Promise<{ success: boolean; ts?: string; error?: string }> {
  const result = await slackApiRequest<{ ts: string }>(
    config,
    'chat.postMessage',
    params
  );

  return {
    success: result.ok,
    ts: result.data?.ts,
    error: result.error,
  };
}

/**
 * Update an existing message
 */
export async function updateSlackMessage(
  config: SlackConfig,
  params: {
    channel: string;
    ts: string;
    text?: string;
    blocks?: Array<Record<string, unknown>>;
  }
): Promise<{ success: boolean; error?: string }> {
  const result = await slackApiRequest(config, 'chat.update', params);

  return {
    success: result.ok,
    error: result.error,
  };
}

/**
 * Add reaction to a message
 */
export async function addSlackReaction(
  config: SlackConfig,
  params: {
    channel: string;
    timestamp: string;
    name: string;
  }
): Promise<{ success: boolean; error?: string }> {
  const result = await slackApiRequest(config, 'reactions.add', params);

  return {
    success: result.ok,
    error: result.error,
  };
}

/**
 * Create a notification for AI agent tasks
 */
export async function notifyAIAgentTask(
  config: SlackConfig,
  params: {
    channel: string;
    agentName: string;
    taskName: string;
    status: 'started' | 'progress' | 'completed' | 'failed';
    details?: string;
    progress?: number;
    url?: string;
  }
): Promise<{ success: boolean; ts?: string; error?: string }> {
  const statusEmoji = {
    started: '🚀',
    progress: '⚙️',
    completed: '✅',
    failed: '❌',
  };

  const statusColor = {
    started: '#3B82F6',
    progress: '#F59E0B',
    completed: '#10B981',
    failed: '#EF4444',
  };

  const blocks: Array<Record<string, unknown>> = [
    {
      type: 'header',
      text: {
        type: 'plain_text',
        text: `${statusEmoji[params.status]} AI Agent: ${params.agentName}`,
      },
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Task:*\n${params.taskName}`,
        },
        {
          type: 'mrkdwn',
          text: `*Status:*\n${params.status.toUpperCase()}`,
        },
      ],
    },
  ];

  if (params.progress !== undefined) {
    const progressBar = createProgressBar(params.progress);
    blocks.push({
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Progress:* ${params.progress}%\n${progressBar}`,
      },
    });
  }

  if (params.details) {
    blocks.push({
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: params.details,
      },
    });
  }

  if (params.url) {
    blocks.push({
      type: 'actions',
      elements: [
        {
          type: 'button',
          text: {
            type: 'plain_text',
            text: 'View Details',
          },
          url: params.url,
          style: 'primary',
        },
      ],
    });
  }

  return await postSlackMessage(config, {
    channel: params.channel,
    blocks,
  });
}

/**
 * Create a progress bar for Slack messages
 */
function createProgressBar(percent: number): string {
  const total = 20;
  const filled = Math.round((percent / 100) * total);
  const empty = total - filled;
  return `${'█'.repeat(filled)}${'░'.repeat(empty)}`;
}

/**
 * Handle slash command
 */
export interface SlackSlashCommand {
  token: string;
  team_id: string;
  team_domain: string;
  channel_id: string;
  channel_name: string;
  user_id: string;
  user_name: string;
  command: string;
  text: string;
  api_app_id: string;
  response_url: string;
  trigger_id: string;
}

/**
 * Respond to a slash command (immediate response)
 */
export function createSlashCommandResponse(params: {
  text: string;
  response_type?: 'in_channel' | 'ephemeral';
  blocks?: Array<Record<string, unknown>>;
}): Record<string, unknown> {
  return {
    response_type: params.response_type || 'ephemeral',
    text: params.text,
    blocks: params.blocks,
  };
}

/**
 * Send delayed response to slash command via response_url
 */
export async function sendSlashCommandDelayedResponse(
  responseUrl: string,
  params: {
    text: string;
    response_type?: 'in_channel' | 'ephemeral';
    blocks?: Array<Record<string, unknown>>;
    replace_original?: boolean;
  }
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(responseUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        response_type: params.response_type || 'ephemeral',
        text: params.text,
        blocks: params.blocks,
        replace_original: params.replace_original || false,
      }),
    });

    return {
      success: response.ok,
      error: response.ok ? undefined : `HTTP ${response.status}`,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Handle interactive component (button clicks, select menus)
 */
export interface SlackInteractivePayload {
  type: 'block_actions' | 'view_submission' | 'view_closed';
  user: {
    id: string;
    username: string;
    name: string;
  };
  api_app_id: string;
  token: string;
  container?: {
    message_ts: string;
    channel_id: string;
  };
  trigger_id: string;
  team?: {
    id: string;
    domain: string;
  };
  channel?: {
    id: string;
    name: string;
  };
  message?: {
    ts: string;
    text: string;
  };
  actions?: Array<{
    action_id: string;
    block_id: string;
    type: string;
    value?: string;
    selected_option?: {
      value: string;
      text: {
        type: string;
        text: string;
      };
    };
    action_ts: string;
  }>;
  response_url?: string;
  view?: Record<string, unknown>;
}

/**
 * Open a modal dialog
 */
export async function openSlackModal(
  config: SlackConfig,
  params: {
    trigger_id: string;
    view: {
      type: 'modal';
      callback_id: string;
      title: {
        type: 'plain_text';
        text: string;
      };
      blocks: Array<Record<string, unknown>>;
      submit?: {
        type: 'plain_text';
        text: string;
      };
      close?: {
        type: 'plain_text';
        text: string;
      };
    };
  }
): Promise<{ success: boolean; error?: string }> {
  const result = await slackApiRequest(config, 'views.open', params);

  return {
    success: result.ok,
    error: result.error,
  };
}

/**
 * Get user info
 */
export async function getSlackUser(
  config: SlackConfig,
  userId: string
): Promise<{
  success: boolean;
  user?: {
    id: string;
    name: string;
    real_name: string;
    email?: string;
    is_bot: boolean;
  };
  error?: string;
}> {
  const result = await slackApiRequest<{
    user: {
      id: string;
      name: string;
      real_name: string;
      profile: {
        email?: string;
      };
      is_bot: boolean;
    };
  }>(config, 'users.info', { user: userId });

  return {
    success: result.ok,
    user: result.data
      ? {
          id: result.data.user.id,
          name: result.data.user.name,
          real_name: result.data.user.real_name,
          email: result.data.user.profile.email,
          is_bot: result.data.user.is_bot,
        }
      : undefined,
    error: result.error,
  };
}

/**
 * List channels
 */
export async function listSlackChannels(
  config: SlackConfig,
  params?: {
    exclude_archived?: boolean;
    types?: string; // e.g., 'public_channel,private_channel'
    limit?: number;
  }
): Promise<{
  success: boolean;
  channels?: Array<{
    id: string;
    name: string;
    is_channel: boolean;
    is_private: boolean;
    is_member: boolean;
  }>;
  error?: string;
}> {
  const result = await slackApiRequest<{
    channels: Array<{
      id: string;
      name: string;
      is_channel: boolean;
      is_private: boolean;
      is_member: boolean;
    }>;
  }>(config, 'conversations.list', {
    exclude_archived: params?.exclude_archived ?? true,
    types: params?.types ?? 'public_channel,private_channel',
    limit: params?.limit ?? 100,
  });

  return {
    success: result.ok,
    channels: result.data?.channels,
    error: result.error,
  };
}

/**
 * Create deployment notification with status and actions
 */
export async function notifyDeployment(
  config: SlackConfig,
  params: {
    channel: string;
    environment: string;
    version: string;
    status: 'started' | 'success' | 'failed';
    deployer?: string;
    commitHash?: string;
    commitMessage?: string;
    duration?: number;
    url?: string;
  }
): Promise<{ success: boolean; ts?: string; error?: string }> {
  const statusEmoji = {
    started: '🚀',
    success: '✅',
    failed: '❌',
  };

  const statusColor = {
    started: '#3B82F6',
    success: '#10B981',
    failed: '#EF4444',
  };

  const blocks: Array<Record<string, unknown>> = [
    {
      type: 'header',
      text: {
        type: 'plain_text',
        text: `${statusEmoji[params.status]} Deployment to ${params.environment}`,
      },
    },
    {
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*Version:*\n${params.version}`,
        },
        {
          type: 'mrkdwn',
          text: `*Status:*\n${params.status.toUpperCase()}`,
        },
      ],
    },
  ];

  if (params.deployer) {
    blocks.push({
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `Deployed by ${params.deployer}`,
        },
      ],
    });
  }

  if (params.commitHash && params.commitMessage) {
    blocks.push({
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Commit:* \`${params.commitHash.substring(0, 7)}\`\n${params.commitMessage}`,
      },
    });
  }

  if (params.duration) {
    blocks.push({
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `Duration: ${Math.round(params.duration / 1000)}s`,
        },
      ],
    });
  }

  if (params.url) {
    blocks.push({
      type: 'actions',
      elements: [
        {
          type: 'button',
          text: {
            type: 'plain_text',
            text: 'View Application',
          },
          url: params.url,
          style: params.status === 'success' ? 'primary' : undefined,
        },
      ],
    });
  }

  return await postSlackMessage(config, {
    channel: params.channel,
    blocks,
  });
}
