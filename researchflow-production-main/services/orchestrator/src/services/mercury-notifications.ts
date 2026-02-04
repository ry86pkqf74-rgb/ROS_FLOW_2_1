/**
 * Mercury Notifications & Logging Service
 * 
 * Integrates Mercury Coder with Notion, Linear, and Slack for:
 * - AI usage logging and cost tracking
 * - Task progress notifications
 * - Deployment status updates
 * - Agent performance metrics
 * 
 * @see https://docs.inceptionlabs.ai
 */

import { getMercuryCoderProvider, type MercuryResponse } from '@researchflow/ai-router';
import {
  NotionConfig,
  createAgentTask,
  updateAgentTaskStatus,
  logDeployment,
  type AgentTaskStatus,
} from './notionService';
import {
  LinearConfig,
  createLinearIssue,
  addLinearComment,
  assignAIAgentToIssue,
} from './linearService';
import {
  SlackConfig,
  notifyAIAgentTask,
  notifyDeployment as notifySlackDeployment,
  postSlackMessage,
} from './slackService';

// ============================================================================
// Types
// ============================================================================

export interface MercuryNotificationConfig {
  notion?: NotionConfig;
  linear?: LinearConfig;
  slack?: SlackConfig;
  /** Slack channel for Mercury notifications */
  slackChannel?: string;
  /** Enable automatic notifications */
  autoNotify?: boolean;
  /** Minimum latency (ms) to trigger performance alert */
  performanceAlertThresholdMs?: number;
  /** Cost threshold for alerts (USD) */
  costAlertThresholdUsd?: number;
}

export interface MercuryTaskNotification {
  taskId: string;
  taskName: string;
  agentId?: string;
  phaseId?: number;
  userId?: string;
  status: 'started' | 'progress' | 'completed' | 'failed';
  progress?: number;
  response?: MercuryResponse;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface MercuryUsageLog {
  timestamp: string;
  endpoint: 'chat' | 'fim' | 'apply' | 'edit';
  model: string;
  realtime: boolean;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  latencyMs: number;
  tokensPerSecond: number;
  estimatedCostUsd: number;
  taskId?: string;
  agentId?: string;
  phaseId?: number;
  userId?: string;
}

// ============================================================================
// Mercury Notification Service
// ============================================================================

export class MercuryNotificationService {
  private config: MercuryNotificationConfig;
  private usageLogs: MercuryUsageLog[] = [];
  private totalCost = 0;
  private totalTokens = 0;

  constructor(config: MercuryNotificationConfig) {
    this.config = {
      autoNotify: true,
      performanceAlertThresholdMs: 5000,
      costAlertThresholdUsd: 10,
      ...config,
    };
  }

  // ==========================================================================
  // Task Notifications
  // ==========================================================================

  /**
   * Notify about Mercury task status across all configured channels
   */
  async notifyTask(notification: MercuryTaskNotification): Promise<void> {
    const promises: Promise<unknown>[] = [];

    // Notion: Create or update task
    if (this.config.notion) {
      promises.push(this.notifyTaskToNotion(notification));
    }

    // Slack: Send notification
    if (this.config.slack && this.config.slackChannel) {
      promises.push(this.notifyTaskToSlack(notification));
    }

    // Linear: Add comment for significant events
    if (this.config.linear && notification.taskId) {
      if (notification.status === 'completed' || notification.status === 'failed') {
        promises.push(this.notifyTaskToLinear(notification));
      }
    }

    await Promise.allSettled(promises);
  }

  /**
   * Notify task status to Notion
   */
  private async notifyTaskToNotion(notification: MercuryTaskNotification): Promise<void> {
    if (!this.config.notion) return;

    try {
      if (notification.status === 'started') {
        await createAgentTask(this.config.notion, {
          taskName: notification.taskName,
          agentName: notification.agentId || 'mercury-coder',
          status: 'in-progress',
          priority: 'medium',
          description: this.buildTaskDescription(notification),
          tags: ['mercury', 'ai-agent', notification.response?.endpoint || 'chat'],
        });
      } else {
        // For updates, we'd need the Notion page ID
        // This would be tracked in a separate mapping
        const notionStatus = this.mapStatusToNotion(notification.status);
        const progressNote = this.buildProgressNote(notification);
        // Update would happen here if we had the page ID
        console.log(`[MercuryNotifications] Notion update: ${notionStatus} - ${progressNote}`);
      }
    } catch (error) {
      console.error('[MercuryNotifications] Failed to notify Notion:', error);
    }
  }

  /**
   * Notify task status to Slack
   */
  private async notifyTaskToSlack(notification: MercuryTaskNotification): Promise<void> {
    if (!this.config.slack || !this.config.slackChannel) return;

    try {
      // Build details with Mercury metrics
      let details = '';
      if (notification.response) {
        const { metrics, usage, endpoint, realtime } = notification.response;
        details = [
          `*Endpoint:* ${endpoint}${realtime ? ' (realtime)' : ''}`,
          `*Latency:* ${metrics.latencyMs}ms`,
          `*Speed:* ${metrics.tokensPerSecond} tokens/sec`,
          `*Tokens:* ${usage.totalTokens} (${usage.inputTokens}→${usage.outputTokens})`,
          `*Cost:* $${usage.estimatedCostUsd.toFixed(5)}`,
        ].join('\n');
      }

      if (notification.error) {
        details = `*Error:* ${notification.error}`;
      }

      await notifyAIAgentTask(this.config.slack, {
        channel: this.config.slackChannel,
        agentName: notification.agentId || 'Mercury Coder',
        taskName: notification.taskName,
        status: notification.status,
        progress: notification.progress,
        details: details || undefined,
      });
    } catch (error) {
      console.error('[MercuryNotifications] Failed to notify Slack:', error);
    }
  }

  /**
   * Notify task status to Linear
   */
  private async notifyTaskToLinear(notification: MercuryTaskNotification): Promise<void> {
    if (!this.config.linear || !notification.taskId) return;

    try {
      const comment = this.buildLinearComment(notification);
      await addLinearComment(this.config.linear, notification.taskId, comment);
    } catch (error) {
      console.error('[MercuryNotifications] Failed to notify Linear:', error);
    }
  }

  // ==========================================================================
  // Usage Logging
  // ==========================================================================

  /**
   * Log Mercury usage and check for alerts
   */
  async logUsage(response: MercuryResponse, context?: {
    taskId?: string;
    agentId?: string;
    phaseId?: number;
    userId?: string;
  }): Promise<void> {
    const log: MercuryUsageLog = {
      timestamp: new Date().toISOString(),
      endpoint: response.endpoint,
      model: response.model,
      realtime: response.realtime,
      inputTokens: response.usage.inputTokens,
      outputTokens: response.usage.outputTokens,
      totalTokens: response.usage.totalTokens,
      latencyMs: response.metrics.latencyMs,
      tokensPerSecond: response.metrics.tokensPerSecond,
      estimatedCostUsd: response.usage.estimatedCostUsd,
      ...context,
    };

    this.usageLogs.push(log);
    this.totalCost += response.usage.estimatedCostUsd;
    this.totalTokens += response.usage.totalTokens;

    // Check for performance alerts
    await this.checkAlerts(log);

    // Keep only last 1000 logs in memory
    if (this.usageLogs.length > 1000) {
      this.usageLogs = this.usageLogs.slice(-1000);
    }
  }

  /**
   * Check for performance/cost alerts
   */
  private async checkAlerts(log: MercuryUsageLog): Promise<void> {
    // Performance alert
    if (
      this.config.performanceAlertThresholdMs &&
      log.latencyMs > this.config.performanceAlertThresholdMs
    ) {
      await this.sendAlert(
        `⚠️ Mercury high latency: ${log.latencyMs}ms (threshold: ${this.config.performanceAlertThresholdMs}ms)`,
        { log }
      );
    }

    // Cost alert
    if (
      this.config.costAlertThresholdUsd &&
      this.totalCost > this.config.costAlertThresholdUsd
    ) {
      await this.sendAlert(
        `💰 Mercury cost threshold exceeded: $${this.totalCost.toFixed(4)} (threshold: $${this.config.costAlertThresholdUsd})`,
        { totalCost: this.totalCost, totalTokens: this.totalTokens }
      );
    }
  }

  /**
   * Send alert to Slack
   */
  private async sendAlert(message: string, data: Record<string, unknown>): Promise<void> {
    if (!this.config.slack || !this.config.slackChannel) return;

    try {
      await postSlackMessage(this.config.slack, {
        channel: this.config.slackChannel,
        text: message,
        blocks: [
          {
            type: 'section',
            text: { type: 'mrkdwn', text: message },
          },
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: '```' + JSON.stringify(data, null, 2) + '```',
            },
          },
        ],
      });
    } catch (error) {
      console.error('[MercuryNotifications] Failed to send alert:', error);
    }
  }

  // ==========================================================================
  // Deployment Notifications
  // ==========================================================================

  /**
   * Notify deployment status with Mercury metrics
   */
  async notifyDeployment(params: {
    environment: string;
    version: string;
    status: 'started' | 'success' | 'failed';
    deployer?: string;
    commitHash?: string;
    commitMessage?: string;
    duration?: number;
    mercuryStats?: {
      totalCalls: number;
      totalTokens: number;
      totalCostUsd: number;
      avgLatencyMs: number;
    };
  }): Promise<void> {
    const promises: Promise<unknown>[] = [];

    // Notion deployment log
    if (this.config.notion) {
      promises.push(
        logDeployment(this.config.notion, {
          environment: params.environment,
          version: params.version,
          status: params.status,
          deployedBy: params.deployer || 'system',
          commitHash: params.commitHash,
          commitMessage: params.commitMessage,
          duration: params.duration,
          services: ['mercury-coder', 'ai-router'],
          notes: params.mercuryStats
            ? `Mercury Stats: ${params.mercuryStats.totalCalls} calls, ${params.mercuryStats.totalTokens} tokens, $${params.mercuryStats.totalCostUsd.toFixed(4)}`
            : undefined,
        })
      );
    }

    // Slack notification
    if (this.config.slack && this.config.slackChannel) {
      promises.push(
        notifySlackDeployment(this.config.slack, {
          channel: this.config.slackChannel,
          environment: params.environment,
          version: params.version,
          status: params.status,
          deployer: params.deployer,
          commitHash: params.commitHash,
          commitMessage: params.commitMessage,
          duration: params.duration,
        })
      );
    }

    await Promise.allSettled(promises);
  }

  // ==========================================================================
  // Analytics
  // ==========================================================================

  /**
   * Get Mercury usage summary
   */
  getUsageSummary(): {
    totalCost: number;
    totalTokens: number;
    totalCalls: number;
    avgLatencyMs: number;
    avgTokensPerSecond: number;
    byEndpoint: Record<string, { calls: number; tokens: number; cost: number }>;
    realtimePercentage: number;
  } {
    const byEndpoint: Record<string, { calls: number; tokens: number; cost: number }> = {};
    let totalLatency = 0;
    let totalSpeed = 0;
    let realtimeCalls = 0;

    for (const log of this.usageLogs) {
      if (!byEndpoint[log.endpoint]) {
        byEndpoint[log.endpoint] = { calls: 0, tokens: 0, cost: 0 };
      }
      byEndpoint[log.endpoint].calls++;
      byEndpoint[log.endpoint].tokens += log.totalTokens;
      byEndpoint[log.endpoint].cost += log.estimatedCostUsd;
      totalLatency += log.latencyMs;
      totalSpeed += log.tokensPerSecond;
      if (log.realtime) realtimeCalls++;
    }

    const totalCalls = this.usageLogs.length;

    return {
      totalCost: this.totalCost,
      totalTokens: this.totalTokens,
      totalCalls,
      avgLatencyMs: totalCalls > 0 ? Math.round(totalLatency / totalCalls) : 0,
      avgTokensPerSecond: totalCalls > 0 ? Math.round(totalSpeed / totalCalls) : 0,
      byEndpoint,
      realtimePercentage: totalCalls > 0 ? Math.round((realtimeCalls / totalCalls) * 100) : 0,
    };
  }

  /**
   * Get recent logs
   */
  getRecentLogs(limit = 100): MercuryUsageLog[] {
    return this.usageLogs.slice(-limit);
  }

  // ==========================================================================
  // Helpers
  // ==========================================================================

  private mapStatusToNotion(status: MercuryTaskNotification['status']): AgentTaskStatus {
    const map: Record<MercuryTaskNotification['status'], AgentTaskStatus> = {
      started: 'in-progress',
      progress: 'in-progress',
      completed: 'completed',
      failed: 'failed',
    };
    return map[status];
  }

  private buildTaskDescription(notification: MercuryTaskNotification): string {
    const lines = [`Task: ${notification.taskName}`];
    if (notification.agentId) lines.push(`Agent: ${notification.agentId}`);
    if (notification.phaseId) lines.push(`Phase: ${notification.phaseId}`);
    if (notification.userId) lines.push(`User: ${notification.userId}`);
    return lines.join('\n');
  }

  private buildProgressNote(notification: MercuryTaskNotification): string {
    if (notification.response) {
      const { metrics, usage, endpoint } = notification.response;
      return `${endpoint}: ${metrics.latencyMs}ms, ${usage.totalTokens} tokens, $${usage.estimatedCostUsd.toFixed(5)}`;
    }
    if (notification.error) {
      return `Error: ${notification.error}`;
    }
    return `Status: ${notification.status}`;
  }

  private buildLinearComment(notification: MercuryTaskNotification): string {
    const lines = [`**Mercury Coder Task ${notification.status.toUpperCase()}**`];
    lines.push(`Task: ${notification.taskName}`);

    if (notification.response) {
      const { metrics, usage, endpoint, realtime } = notification.response;
      lines.push(`Endpoint: ${endpoint}${realtime ? ' (realtime)' : ''}`);
      lines.push(`Latency: ${metrics.latencyMs}ms`);
      lines.push(`Speed: ${metrics.tokensPerSecond} tokens/sec`);
      lines.push(`Tokens: ${usage.totalTokens}`);
      lines.push(`Cost: $${usage.estimatedCostUsd.toFixed(5)}`);
    }

    if (notification.error) {
      lines.push(`Error: ${notification.error}`);
    }

    return lines.join('\n');
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

let serviceInstance: MercuryNotificationService | null = null;

export function getMercuryNotificationService(
  config?: MercuryNotificationConfig
): MercuryNotificationService {
  if (!serviceInstance && config) {
    serviceInstance = new MercuryNotificationService(config);
  }
  if (!serviceInstance) {
    throw new Error('MercuryNotificationService not initialized. Provide config.');
  }
  return serviceInstance;
}

export function initMercuryNotifications(config: MercuryNotificationConfig): MercuryNotificationService {
  serviceInstance = new MercuryNotificationService(config);
  return serviceInstance;
}

export default MercuryNotificationService;
