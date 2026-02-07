import { Client } from '@notionhq/client';
import { z } from 'zod';

/**
 * Enhanced Notion Service Integration
 * Extends basic Notion integration with AI agent task tracking, workflow management,
 * and automated project planning capabilities
 */

// Configuration schema
export const NotionConfigSchema = z.object({
  apiKey: z.string().min(1),
  databaseIds: z.object({
    tasks: z.string().optional(),
    agents: z.string().optional(),
    projects: z.string().optional(),
    deployments: z.string().optional(),
  }),
});

export type NotionConfig = z.infer<typeof NotionConfigSchema>;

/**
 * Initialize Notion client
 */
export function createNotionClient(config: NotionConfig): Client {
  return new Client({ auth: config.apiKey });
}

/**
 * AI Agent Task Status
 */
export type AgentTaskStatus =
  | 'queued'
  | 'in-progress'
  | 'blocked'
  | 'completed'
  | 'failed';

/**
 * Create AI agent task in Notion
 */
export async function createAgentTask(
  config: NotionConfig,
  params: {
    taskName: string;
    agentName: string;
    description?: string;
    status?: AgentTaskStatus;
    priority?: 'low' | 'medium' | 'high' | 'critical';
    assignedTo?: string;
    projectId?: string;
    estimatedDuration?: number;
    dependencies?: string[];
    tags?: string[];
  }
): Promise<{ success: boolean; pageId?: string; error?: string }> {
  const client = createNotionClient(config);
  const databaseId = config.databaseIds.tasks;

  if (!databaseId) {
    return {
      success: false,
      error: 'Tasks database ID not configured',
    };
  }

  try {
    const properties: any = {
      Name: {
        title: [
          {
            text: {
              content: params.taskName,
            },
          },
        ],
      },
      'Agent': {
        select: {
          name: params.agentName,
        },
      },
      'Status': {
        status: {
          name: params.status || 'queued',
        },
      },
    };

    if (params.priority) {
      properties['Priority'] = {
        select: {
          name: params.priority,
        },
      };
    }

    if (params.assignedTo) {
      properties['Assigned To'] = {
        rich_text: [
          {
            text: {
              content: params.assignedTo,
            },
          },
        ],
      };
    }

    if (params.estimatedDuration) {
      properties['Estimated Duration (min)'] = {
        number: params.estimatedDuration,
      };
    }

    if (params.tags && params.tags.length > 0) {
      properties['Tags'] = {
        multi_select: params.tags.map((tag) => ({ name: tag })),
      };
    }

    const children: any[] = [];

    if (params.description) {
      children.push({
        object: 'block',
        type: 'paragraph',
        paragraph: {
          rich_text: [
            {
              text: {
                content: params.description,
              },
            },
          ],
        },
      });
    }

    if (params.dependencies && params.dependencies.length > 0) {
      children.push({
        object: 'block',
        type: 'heading_3',
        heading_3: {
          rich_text: [
            {
              text: {
                content: 'Dependencies',
              },
            },
          ],
        },
      });

      params.dependencies.forEach((dep) => {
        children.push({
          object: 'block',
          type: 'bulleted_list_item',
          bulleted_list_item: {
            rich_text: [
              {
                text: {
                  content: dep,
                },
              },
            ],
          },
        });
      });
    }

    const response = await client.pages.create({
      parent: {
        database_id: databaseId,
      },
      properties,
      children: children.length > 0 ? children : undefined,
    });

    return {
      success: true,
      pageId: response.id,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Update AI agent task status
 */
export async function updateAgentTaskStatus(
  config: NotionConfig,
  pageId: string,
  status: AgentTaskStatus,
  progressNote?: string
): Promise<{ success: boolean; error?: string }> {
  const client = createNotionClient(config);

  try {
    const properties: any = {
      Status: {
        status: {
          name: status,
        },
      },
      'Last Updated': {
        date: {
          start: new Date().toISOString(),
        },
      },
    };

    await client.pages.update({
      page_id: pageId,
      properties,
    });

    // Add progress note as a comment
    if (progressNote) {
      await client.comments.create({
        parent: {
          page_id: pageId,
        },
        rich_text: [
          {
            text: {
              content: `[${new Date().toISOString()}] ${progressNote}`,
            },
          },
        ],
      });
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Query agent tasks by status or agent name
 */
export async function queryAgentTasks(
  config: NotionConfig,
  filters?: {
    agentName?: string;
    status?: AgentTaskStatus;
    priority?: string;
  }
): Promise<{
  success: boolean;
  tasks?: Array<{
    id: string;
    name: string;
    agent: string;
    status: string;
    priority?: string;
    createdTime: string;
    lastEditedTime: string;
  }>;
  error?: string;
}> {
  const client = createNotionClient(config);
  const databaseId = config.databaseIds.tasks;

  if (!databaseId) {
    return {
      success: false,
      error: 'Tasks database ID not configured',
    };
  }

  try {
    const filter: any = {
      and: [],
    };

    if (filters?.agentName) {
      filter.and.push({
        property: 'Agent',
        select: {
          equals: filters.agentName,
        },
      });
    }

    if (filters?.status) {
      filter.and.push({
        property: 'Status',
        status: {
          equals: filters.status,
        },
      });
    }

    if (filters?.priority) {
      filter.and.push({
        property: 'Priority',
        select: {
          equals: filters.priority,
        },
      });
    }

    const response = await client.databases.query({
      database_id: databaseId,
      filter: filter.and.length > 0 ? filter : undefined,
      sorts: [
        {
          property: 'Last Updated',
          direction: 'descending',
        },
      ],
    });

    const tasks = response.results.map((page: any) => ({
      id: page.id,
      name: page.properties.Name?.title?.[0]?.text?.content || 'Untitled',
      agent: page.properties.Agent?.select?.name || 'Unknown',
      status: page.properties.Status?.status?.name || 'unknown',
      priority: page.properties.Priority?.select?.name,
      createdTime: page.created_time,
      lastEditedTime: page.last_edited_time,
    }));

    return {
      success: true,
      tasks,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Create project planning board
 */
export async function createProjectPlan(
  config: NotionConfig,
  params: {
    projectName: string;
    description?: string;
    phases: Array<{
      name: string;
      tasks: Array<{
        name: string;
        agent?: string;
        priority?: string;
        estimatedDuration?: number;
      }>;
    }>;
    startDate?: string;
    targetDate?: string;
    owner?: string;
  }
): Promise<{ success: boolean; projectId?: string; taskIds?: string[]; error?: string }> {
  const client = createNotionClient(config);
  const projectDbId = config.databaseIds.projects;

  if (!projectDbId) {
    return {
      success: false,
      error: 'Projects database ID not configured',
    };
  }

  try {
    // Create project page
    const projectResponse = await client.pages.create({
      parent: {
        database_id: projectDbId,
      },
      properties: {
        Name: {
          title: [
            {
              text: {
                content: params.projectName,
              },
            },
          ],
        },
        Status: {
          status: {
            name: 'planning',
          },
        },
        'Start Date': params.startDate
          ? {
              date: {
                start: params.startDate,
              },
            }
          : undefined,
        'Target Date': params.targetDate
          ? {
              date: {
                start: params.targetDate,
              },
            }
          : undefined,
        Owner: params.owner
          ? {
              rich_text: [
                {
                  text: {
                    content: params.owner,
                  },
                },
              ],
            }
          : undefined,
      },
    });

    // Create tasks for each phase
    const taskIds: string[] = [];

    for (const phase of params.phases) {
      // Add phase heading
      await client.blocks.children.append({
        block_id: projectResponse.id,
        children: [
          {
            object: 'block',
            type: 'heading_2',
            heading_2: {
              rich_text: [
                {
                  text: {
                    content: phase.name,
                  },
                },
              ],
            },
          },
        ],
      });

      // Create tasks
      for (const task of phase.tasks) {
        const taskResult = await createAgentTask(config, {
          taskName: task.name,
          agentName: task.agent || 'unassigned',
          priority: task.priority as any,
          estimatedDuration: task.estimatedDuration,
          projectId: projectResponse.id,
        });

        if (taskResult.success && taskResult.pageId) {
          taskIds.push(taskResult.pageId);
        }
      }
    }

    return {
      success: true,
      projectId: projectResponse.id,
      taskIds,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Log deployment to Notion
 */
export async function logDeployment(
  config: NotionConfig,
  params: {
    environment: string;
    version: string;
    status: 'success' | 'failed' | 'rollback';
    deployedBy: string;
    commitHash?: string;
    commitMessage?: string;
    duration?: number;
    services?: string[];
    notes?: string;
  }
): Promise<{ success: boolean; pageId?: string; error?: string }> {
  const client = createNotionClient(config);
  const databaseId = config.databaseIds.deployments;

  if (!databaseId) {
    return {
      success: false,
      error: 'Deployments database ID not configured',
    };
  }

  try {
    const response = await client.pages.create({
      parent: {
        database_id: databaseId,
      },
      properties: {
        Name: {
          title: [
            {
              text: {
                content: `${params.environment} - ${params.version}`,
              },
            },
          ],
        },
        Environment: {
          select: {
            name: params.environment,
          },
        },
        Version: {
          rich_text: [
            {
              text: {
                content: params.version,
              },
            },
          ],
        },
        Status: {
          status: {
            name: params.status,
          },
        },
        'Deployed By': {
          rich_text: [
            {
              text: {
                content: params.deployedBy,
              },
            },
          ],
        },
        'Deployment Date': {
          date: {
            start: new Date().toISOString(),
          },
        },
        'Duration (s)': params.duration
          ? {
              number: Math.round(params.duration / 1000),
            }
          : undefined,
        Services: params.services
          ? {
              multi_select: params.services.map((s) => ({ name: s })),
            }
          : undefined,
      },
      children: [
        ...(params.commitHash && params.commitMessage
          ? [
              {
                object: 'block' as const,
                type: 'paragraph' as const,
                paragraph: {
                  rich_text: [
                    {
                      text: {
                        content: `Commit: ${params.commitHash}\n${params.commitMessage}`,
                      },
                    },
                  ],
                },
              },
            ]
          : []),
        ...(params.notes
          ? [
              {
                object: 'block' as const,
                type: 'paragraph' as const,
                paragraph: {
                  rich_text: [
                    {
                      text: {
                        content: params.notes,
                      },
                    },
                  ],
                },
              },
            ]
          : []),
      ],
    });

    return {
      success: true,
      pageId: response.id,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Sync Linear issue to Notion task
 */
export async function syncLinearToNotion(
  config: NotionConfig,
  linearIssue: {
    id: string;
    identifier: string;
    title: string;
    description?: string;
    status: string;
    priority: number;
    assignee?: string;
    labels?: string[];
  }
): Promise<{ success: boolean; pageId?: string; error?: string }> {
  return await createAgentTask(config, {
    taskName: `[${linearIssue.identifier}] ${linearIssue.title}`,
    agentName: linearIssue.labels?.find((l) => l.startsWith('ai-agent:'))?.split(':')[1] || 'manual',
    description: linearIssue.description,
    status: mapLinearStatusToNotion(linearIssue.status),
    priority: mapLinearPriorityToNotion(linearIssue.priority),
    assignedTo: linearIssue.assignee,
    tags: linearIssue.labels,
  });
}

/**
 * Map Linear status to Notion status
 */
function mapLinearStatusToNotion(linearStatus: string): AgentTaskStatus {
  const statusMap: Record<string, AgentTaskStatus> = {
    backlog: 'queued',
    todo: 'queued',
    'in progress': 'in-progress',
    done: 'completed',
    canceled: 'failed',
  };

  return statusMap[linearStatus.toLowerCase()] || 'queued';
}

/**
 * Map Linear priority (0-4) to Notion priority
 */
function mapLinearPriorityToNotion(
  priority: number
): 'low' | 'medium' | 'high' | 'critical' {
  if (priority === 0) return 'low';
  if (priority === 1) return 'low';
  if (priority === 2) return 'medium';
  if (priority === 3) return 'high';
  return 'critical';
}
