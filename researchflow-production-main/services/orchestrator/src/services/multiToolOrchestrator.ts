import { EventEmitter } from 'events';

import { Queue, Job, QueueEvents } from 'bullmq';
import * as z from 'zod';

/**
 * Multi-Tool Orchestration Dispatcher
 * Coordinates parallel task execution across Notion, Linear, Figma, Slack,
 * Docker, and Cursor integrations for AI-driven development workflows
 */

// Task types
export type TaskType =
  | 'notion-task-create'
  | 'linear-issue-create'
  | 'figma-design-review'
  | 'slack-notify'
  | 'docker-deploy'
  | 'cursor-code-gen'
  | 'ai-agent-execute';

// Task dependencies and execution order
export interface TaskDependency {
  taskId: string;
  requiredStatus: 'completed' | 'started';
}

// Orchestration task schema
export const OrchestrationTaskSchema = z.object({
  id: z.string(),
  type: z.enum([
    'notion-task-create',
    'linear-issue-create',
    'figma-design-review',
    'slack-notify',
    'docker-deploy',
    'cursor-code-gen',
    'ai-agent-execute',
  ]),
  priority: z.enum(['low', 'medium', 'high', 'critical']).default('medium'),
  params: z.record(z.unknown()),
  dependencies: z.array(z.string()).default([]),
  timeout: z.number().optional(),
  retryStrategy: z
    .object({
      maxRetries: z.number().default(3),
      backoffMs: z.number().default(5000),
    })
    .optional(),
});

export type OrchestrationTask = z.infer<typeof OrchestrationTaskSchema>;

// Execution plan
export interface ExecutionPlan {
  id: string;
  name: string;
  tasks: OrchestrationTask[];
  parallelGroups: string[][]; // Groups of tasks that can run in parallel
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
}

// Task execution result
export interface TaskResult {
  taskId: string;
  status: 'completed' | 'failed' | 'timeout';
  result?: unknown;
  error?: string;
  startTime: Date;
  endTime: Date;
  duration: number;
}

/**
 * Multi-Tool Orchestrator
 */
export class MultiToolOrchestrator extends EventEmitter {
  private queues: Map<TaskType, Queue>;
  private queueEventInstances: Map<TaskType, QueueEvents>;
  private executionPlans: Map<string, ExecutionPlan>;
  private taskResults: Map<string, TaskResult>;
  private redisConnection;

  constructor(redisConnection: any) {
    super();
    this.redisConnection = redisConnection;
    this.queues = new Map();
    this.queueEventInstances = new Map();
    this.executionPlans = new Map();
    this.taskResults = new Map();

    // Initialize queues for each task type
    this.initializeQueues();
  }

  /**
   * Initialize Bull queues for each integration
   */
  private initializeQueues(): void {
    const taskTypes: TaskType[] = [
      'notion-task-create',
      'linear-issue-create',
      'figma-design-review',
      'slack-notify',
      'docker-deploy',
      'cursor-code-gen',
      'ai-agent-execute',
    ];

    for (const taskType of taskTypes) {
      const queue = new Queue(`orchestrator:${taskType}`, {
        connection: this.redisConnection,
        defaultJobOptions: {
          attempts: 3,
          backoff: {
            type: 'exponential',
            delay: 5000,
          },
          removeOnComplete: {
            age: 3600, // Keep completed jobs for 1 hour
            count: 1000,
          },
          removeOnFail: {
            age: 86400, // Keep failed jobs for 24 hours
          },
        },
      });

      this.queues.set(taskType, queue);

      const queueEvents = new QueueEvents(`orchestrator:${taskType}`, {
        connection: this.redisConnection,
      });
      this.queueEventInstances.set(taskType, queueEvents);
    }
  }

  /**
   * Create execution plan with dependency analysis
   */
  async createExecutionPlan(
    name: string,
    tasks: OrchestrationTask[]
  ): Promise<ExecutionPlan> {
    const planId = `plan-${Date.now()}-${Math.random().toString(36).substring(7)}`;

    // Build dependency graph
    const dependencyGraph = this.buildDependencyGraph(tasks);

    // Calculate parallel execution groups
    const parallelGroups = this.calculateParallelGroups(tasks, dependencyGraph);

    const plan: ExecutionPlan = {
      id: planId,
      name,
      tasks,
      parallelGroups,
      createdAt: new Date(),
      status: 'pending',
    };

    this.executionPlans.set(planId, plan);
    this.emit('plan:created', plan);

    return plan;
  }

  /**
   * Build dependency graph for tasks
   */
  private buildDependencyGraph(
    tasks: OrchestrationTask[]
  ): Map<string, string[]> {
    const graph = new Map<string, string[]>();

    for (const task of tasks) {
      graph.set(task.id, task.dependencies);
    }

    return graph;
  }

  /**
   * Calculate which tasks can run in parallel
   * Returns groups of task IDs that have no dependencies on each other
   */
  private calculateParallelGroups(
    tasks: OrchestrationTask[],
    dependencyGraph: Map<string, string[]>
  ): string[][] {
    const groups: string[][] = [];
    const completed = new Set<string>();
    const taskMap = new Map(tasks.map((t) => [t.id, t]));

    while (completed.size < tasks.length) {
      const currentGroup: string[] = [];

      for (const task of tasks) {
        if (completed.has(task.id)) continue;

        // Check if all dependencies are completed
        const canExecute = task.dependencies.every((depId) =>
          completed.has(depId)
        );

        if (canExecute) {
          currentGroup.push(task.id);
        }
      }

      if (currentGroup.length === 0) {
        throw new Error('Circular dependency detected in task graph');
      }

      groups.push(currentGroup);
      currentGroup.forEach((taskId) => completed.add(taskId));
    }

    return groups;
  }

  /**
   * Execute a plan
   */
  async executePlan(planId: string): Promise<void> {
    const plan = this.executionPlans.get(planId);
    if (!plan) {
      throw new Error(`Execution plan not found: ${planId}`);
    }

    plan.status = 'running';
    plan.startedAt = new Date();
    this.emit('plan:started', plan);

    try {
      // Execute each parallel group sequentially
      for (const group of plan.parallelGroups) {
        await this.executeParallelGroup(plan, group);
      }

      plan.status = 'completed';
      plan.completedAt = new Date();
      this.emit('plan:completed', plan);
    } catch (error) {
      plan.status = 'failed';
      this.emit('plan:failed', { plan, error });
      throw error;
    }
  }

  /**
   * Execute a group of tasks in parallel
   */
  private async executeParallelGroup(
    plan: ExecutionPlan,
    taskIds: string[]
  ): Promise<void> {
    const tasks = taskIds
      .map((id) => plan.tasks.find((t) => t.id === id))
      .filter((t): t is OrchestrationTask => t !== undefined);

    this.emit('group:started', { planId: plan.id, taskIds });

    // Execute all tasks in parallel
    const taskPromises = tasks.map((task) => this.executeTask(plan.id, task));

    try {
      await Promise.all(taskPromises);
      this.emit('group:completed', { planId: plan.id, taskIds });
    } catch (error) {
      this.emit('group:failed', { planId: plan.id, taskIds, error });
      throw error;
    }
  }

  /**
   * Execute a single task
   */
  private async executeTask(
    planId: string,
    task: OrchestrationTask
  ): Promise<void> {
    const startTime = new Date();
    this.emit('task:started', { planId, task });

    try {
      const queue = this.queues.get(task.type);
      if (!queue) {
        throw new Error(`No queue found for task type: ${task.type}`);
      }

      // Add job to queue
      const job = await queue.add(
        task.id,
        {
          ...task.params,
          planId,
          taskId: task.id,
        },
        {
          priority: this.getPriorityValue(task.priority),
          attempts: task.retryStrategy?.maxRetries || 3,
          backoff: task.retryStrategy?.backoffMs || 5000,
          // TODO: BEHAVIOR CHANGE — per-job `timeout` removed (BullMQ v5 dropped
          // it from JobsOptions). If task.timeout was set to a meaningful value,
          // job execution is no longer time-bounded. lockDuration is NOT equivalent
          // (it controls lock renewal, not "kill after X ms"). To restore per-job
          // time limits, implement a worker-level cancellation or job watchdog.
          // See: https://docs.bullmq.io/patterns/cancellation
        }
      );

      // Wait for job completion
      const queueEvents = this.queueEventInstances.get(task.type)!;
      const result = await job.waitUntilFinished(queueEvents);

      const endTime = new Date();
      const taskResult: TaskResult = {
        taskId: task.id,
        status: 'completed',
        result,
        startTime,
        endTime,
        duration: endTime.getTime() - startTime.getTime(),
      };

      this.taskResults.set(task.id, taskResult);
      this.emit('task:completed', { planId, task, result: taskResult });
    } catch (error) {
      const endTime = new Date();
      const taskResult: TaskResult = {
        taskId: task.id,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        startTime,
        endTime,
        duration: endTime.getTime() - startTime.getTime(),
      };

      this.taskResults.set(task.id, taskResult);
      this.emit('task:failed', { planId, task, result: taskResult });
      throw error;
    }
  }

  /**
   * Get numeric priority value for BullMQ
   */
  private getPriorityValue(priority: string): number {
    const priorityMap: Record<string, number> = {
      critical: 1,
      high: 5,
      medium: 10,
      low: 15,
    };
    return priorityMap[priority] || 10;
  }

  /**
   * Pause execution plan
   */
  async pausePlan(planId: string): Promise<void> {
    const plan = this.executionPlans.get(planId);
    if (!plan) {
      throw new Error(`Execution plan not found: ${planId}`);
    }

    plan.status = 'paused';
    this.emit('plan:paused', plan);

    // Pause all queues
    for (const queue of this.queues.values()) {
      await queue.pause();
    }
  }

  /**
   * Resume execution plan
   */
  async resumePlan(planId: string): Promise<void> {
    const plan = this.executionPlans.get(planId);
    if (!plan) {
      throw new Error(`Execution plan not found: ${planId}`);
    }

    plan.status = 'running';
    this.emit('plan:resumed', plan);

    // Resume all queues
    for (const queue of this.queues.values()) {
      await queue.resume();
    }
  }

  /**
   * Get plan status with task results
   */
  getPlanStatus(planId: string): {
    plan: ExecutionPlan;
    taskResults: Map<string, TaskResult>;
    progress: {
      total: number;
      completed: number;
      failed: number;
      pending: number;
      percentage: number;
    };
  } {
    const plan = this.executionPlans.get(planId);
    if (!plan) {
      throw new Error(`Execution plan not found: ${planId}`);
    }

    const completed = Array.from(this.taskResults.values()).filter(
      (r) => r.status === 'completed'
    ).length;
    const failed = Array.from(this.taskResults.values()).filter(
      (r) => r.status === 'failed'
    ).length;
    const total = plan.tasks.length;
    const pending = total - completed - failed;

    return {
      plan,
      taskResults: this.taskResults,
      progress: {
        total,
        completed,
        failed,
        pending,
        percentage: Math.round((completed / total) * 100),
      },
    };
  }

  /**
   * Create a pre-built workflow plan
   */
  static createWorkflowPlan(
    workflow: 'full-deployment' | 'design-to-code' | 'issue-to-deployment' | 'parallel-ai-review',
    params: Record<string, unknown>
  ): OrchestrationTask[] {
    const workflows = {
      'full-deployment': this.fullDeploymentWorkflow(params),
      'design-to-code': this.designToCodeWorkflow(params),
      'issue-to-deployment': this.issueToDeploymentWorkflow(params),
      'parallel-ai-review': this.parallelAIReviewWorkflow(params),
    };

    return workflows[workflow];
  }

  /**
   * Full deployment workflow: Notion → Linear → Docker → Slack
   */
  private static fullDeploymentWorkflow(
    params: Record<string, unknown>
  ): OrchestrationTask[] {
    return [
      {
        id: 'task-1',
        type: 'notion-task-create',
        priority: 'high',
        params: {
          taskName: params.deploymentName || 'Deployment',
          agentName: 'deployment-agent',
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'task-2',
        type: 'linear-issue-create',
        priority: 'high',
        params: {
          title: `Deploy: ${params.deploymentName}`,
          teamId: params.linearTeamId,
          ...params,
        },
        dependencies: ['task-1'],
      },
      {
        id: 'task-3',
        type: 'docker-deploy',
        priority: 'critical',
        params: {
          environment: params.environment || 'production',
          version: params.version,
          ...params,
        },
        dependencies: ['task-2'],
      },
      {
        id: 'task-4',
        type: 'slack-notify',
        priority: 'medium',
        params: {
          channel: params.slackChannel || '#deployments',
          message: `Deployment completed: ${params.deploymentName}`,
          ...params,
        },
        dependencies: ['task-3'],
      },
    ];
  }

  /**
   * Design to code workflow: Figma → Cursor → Linear → Slack
   */
  private static designToCodeWorkflow(
    params: Record<string, unknown>
  ): OrchestrationTask[] {
    return [
      {
        id: 'design-review',
        type: 'figma-design-review',
        priority: 'high',
        params: {
          fileKey: params.figmaFileKey,
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'code-gen',
        type: 'cursor-code-gen',
        priority: 'high',
        params: {
          designTokens: '${design-review.result.tokens}',
          ...params,
        },
        dependencies: ['design-review'],
      },
      {
        id: 'create-issue',
        type: 'linear-issue-create',
        priority: 'medium',
        params: {
          title: `Implement design: ${params.designName}`,
          ...params,
        },
        dependencies: ['code-gen'],
      },
      {
        id: 'notify-team',
        type: 'slack-notify',
        priority: 'low',
        params: {
          channel: params.slackChannel || '#development',
          ...params,
        },
        dependencies: ['create-issue'],
      },
    ];
  }

  /**
   * Issue to deployment workflow
   */
  private static issueToDeploymentWorkflow(
    params: Record<string, unknown>
  ): OrchestrationTask[] {
    return [
      {
        id: 'ai-agent-1',
        type: 'ai-agent-execute',
        priority: 'high',
        params: {
          agentName: 'code-implementation',
          issueId: params.issueId,
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'ai-agent-2',
        type: 'ai-agent-execute',
        priority: 'high',
        params: {
          agentName: 'test-generation',
          issueId: params.issueId,
          ...params,
        },
        dependencies: ['ai-agent-1'],
      },
      {
        id: 'docker-build',
        type: 'docker-deploy',
        priority: 'critical',
        params: {
          environment: 'staging',
          ...params,
        },
        dependencies: ['ai-agent-2'],
      },
      {
        id: 'notify-success',
        type: 'slack-notify',
        priority: 'medium',
        params: {
          channel: params.slackChannel || '#deployments',
          ...params,
        },
        dependencies: ['docker-build'],
      },
    ];
  }

  /**
   * Parallel AI review workflow
   */
  private static parallelAIReviewWorkflow(
    params: Record<string, unknown>
  ): OrchestrationTask[] {
    return [
      {
        id: 'security-review',
        type: 'ai-agent-execute',
        priority: 'critical',
        params: {
          agentName: 'security-scan',
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'performance-review',
        type: 'ai-agent-execute',
        priority: 'high',
        params: {
          agentName: 'performance-analysis',
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'code-quality-review',
        type: 'ai-agent-execute',
        priority: 'high',
        params: {
          agentName: 'code-quality',
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'accessibility-review',
        type: 'ai-agent-execute',
        priority: 'medium',
        params: {
          agentName: 'accessibility-check',
          ...params,
        },
        dependencies: [],
      },
      {
        id: 'aggregate-results',
        type: 'notion-task-create',
        priority: 'medium',
        params: {
          taskName: 'AI Review Results',
          agentName: 'aggregator',
          ...params,
        },
        dependencies: [
          'security-review',
          'performance-review',
          'code-quality-review',
          'accessibility-review',
        ],
      },
      {
        id: 'notify-results',
        type: 'slack-notify',
        priority: 'low',
        params: {
          channel: params.slackChannel || '#code-reviews',
          ...params,
        },
        dependencies: ['aggregate-results'],
      },
    ];
  }

  /**
   * Cleanup
   */
  async close(): Promise<void> {
    for (const queue of this.queues.values()) {
      await queue.close();
    }
    this.removeAllListeners();
  }
}
