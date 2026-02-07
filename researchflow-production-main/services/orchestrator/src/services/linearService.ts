import crypto from 'crypto';

import * as z from 'zod';

/**
 * Linear Service Integration
 * Provides issue tracking, project management, and AI agent task assignment
 * via Linear's GraphQL API
 */

// Configuration schema
export const LinearConfigSchema = z.object({
  apiKey: z.string().min(1),
  webhookSecret: z.string().optional(),
  teamId: z.string().optional(),
  workspaceId: z.string().optional(),
});

export type LinearConfig = z.infer<typeof LinearConfigSchema>;

// Linear GraphQL API endpoint
const LINEAR_API_URL = 'https://api.linear.app/graphql';

// Webhook event types
export type LinearWebhookEvent =
  | 'Issue'
  | 'Comment'
  | 'Project'
  | 'Cycle'
  | 'Label'
  | 'User';

export interface LinearWebhookPayload {
  action: 'create' | 'update' | 'remove';
  type: LinearWebhookEvent;
  data: {
    id: string;
    title?: string;
    description?: string;
    state?: {
      name: string;
      type: string;
    };
    assignee?: {
      id: string;
      name: string;
      email: string;
    };
    labels?: Array<{
      id: string;
      name: string;
      color: string;
    }>;
    priority?: number;
    estimate?: number;
    project?: {
      id: string;
      name: string;
    };
    team?: {
      id: string;
      name: string;
    };
  };
  createdAt: string;
  updatedAt?: string;
  url: string;
}

/**
 * Verify Linear webhook signature
 * Linear uses HMAC-SHA256 with webhook secret
 */
export function verifyLinearWebhookSignature(
  signature: string,
  body: string,
  secret: string
): boolean {
  try {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(body);
    const expectedSignature = hmac.digest('hex');
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature)
    );
  } catch (error) {
    console.error('Failed to verify Linear webhook signature:', error);
    return false;
  }
}

/**
 * Execute GraphQL query against Linear API
 */
async function linearGraphQLRequest<T>(
  config: LinearConfig,
  query: string,
  variables?: Record<string, unknown>
): Promise<{ data?: T; errors?: Array<{ message: string }> }> {
  try {
    const response = await fetch(LINEAR_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: config.apiKey,
      },
      body: JSON.stringify({ query, variables }),
    });

    if (!response.ok) {
      throw new Error(`Linear API error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Linear GraphQL request failed:', error);
    throw error;
  }
}

/**
 * Create an issue in Linear
 */
export async function createLinearIssue(
  config: LinearConfig,
  params: {
    title: string;
    description?: string;
    teamId: string;
    assigneeId?: string;
    priority?: number;
    estimate?: number;
    labelIds?: string[];
    projectId?: string;
    stateId?: string;
  }
): Promise<{ success: boolean; issueId?: string; error?: string }> {
  const mutation = `
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          identifier
          title
          url
        }
      }
    }
  `;

  try {
    const result = await linearGraphQLRequest<{
      issueCreate: {
        success: boolean;
        issue?: { id: string; identifier: string; title: string; url: string };
      };
    }>(config, mutation, {
      input: {
        title: params.title,
        description: params.description,
        teamId: params.teamId,
        assigneeId: params.assigneeId,
        priority: params.priority,
        estimate: params.estimate,
        labelIds: params.labelIds,
        projectId: params.projectId,
        stateId: params.stateId,
      },
    });

    if (result.errors) {
      return {
        success: false,
        error: result.errors.map((e) => e.message).join(', '),
      };
    }

    return {
      success: result.data?.issueCreate.success || false,
      issueId: result.data?.issueCreate.issue?.id,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Update an issue in Linear
 */
export async function updateLinearIssue(
  config: LinearConfig,
  issueId: string,
  updates: {
    title?: string;
    description?: string;
    stateId?: string;
    assigneeId?: string;
    priority?: number;
    estimate?: number;
    labelIds?: string[];
  }
): Promise<{ success: boolean; error?: string }> {
  const mutation = `
    mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
        issue {
          id
          title
        }
      }
    }
  `;

  try {
    const result = await linearGraphQLRequest<{
      issueUpdate: { success: boolean };
    }>(config, mutation, {
      id: issueId,
      input: updates,
    });

    if (result.errors) {
      return {
        success: false,
        error: result.errors.map((e) => e.message).join(', '),
      };
    }

    return { success: result.data?.issueUpdate.success || false };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get issue details from Linear
 */
export async function getLinearIssue(
  config: LinearConfig,
  issueIdOrIdentifier: string
): Promise<{
  success: boolean;
  issue?: {
    id: string;
    identifier: string;
    title: string;
    description?: string;
    state: { name: string; type: string };
    assignee?: { id: string; name: string; email: string };
    labels: Array<{ id: string; name: string; color: string }>;
    priority: number;
    estimate?: number;
    url: string;
  };
  error?: string;
}> {
  const query = `
    query Issue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        state {
          name
          type
        }
        assignee {
          id
          name
          email
        }
        labels {
          nodes {
            id
            name
            color
          }
        }
        priority
        estimate
        url
      }
    }
  `;

  try {
    const result = await linearGraphQLRequest<{
      issue: {
        id: string;
        identifier: string;
        title: string;
        description?: string;
        state: { name: string; type: string };
        assignee?: { id: string; name: string; email: string };
        labels: { nodes: Array<{ id: string; name: string; color: string }> };
        priority: number;
        estimate?: number;
        url: string;
      };
    }>(config, query, { id: issueIdOrIdentifier });

    if (result.errors) {
      return {
        success: false,
        error: result.errors.map((e) => e.message).join(', '),
      };
    }

    if (!result.data?.issue) {
      return { success: false, error: 'Issue not found' };
    }

    return {
      success: true,
      issue: {
        ...result.data.issue,
        labels: result.data.issue.labels.nodes,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Add comment to Linear issue
 */
export async function addLinearComment(
  config: LinearConfig,
  issueId: string,
  body: string
): Promise<{ success: boolean; commentId?: string; error?: string }> {
  const mutation = `
    mutation CommentCreate($input: CommentCreateInput!) {
      commentCreate(input: $input) {
        success
        comment {
          id
          body
        }
      }
    }
  `;

  try {
    const result = await linearGraphQLRequest<{
      commentCreate: { success: boolean; comment?: { id: string } };
    }>(config, mutation, {
      input: {
        issueId,
        body,
      },
    });

    if (result.errors) {
      return {
        success: false,
        error: result.errors.map((e) => e.message).join(', '),
      };
    }

    return {
      success: result.data?.commentCreate.success || false,
      commentId: result.data?.commentCreate.comment?.id,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Get team workflows (states) for issue management
 */
export async function getLinearTeamWorkflows(
  config: LinearConfig,
  teamId: string
): Promise<{
  success: boolean;
  workflows?: Array<{
    id: string;
    name: string;
    type: string;
    position: number;
  }>;
  error?: string;
}> {
  const query = `
    query Team($id: String!) {
      team(id: $id) {
        states {
          nodes {
            id
            name
            type
            position
          }
        }
      }
    }
  `;

  try {
    const result = await linearGraphQLRequest<{
      team: {
        states: {
          nodes: Array<{
            id: string;
            name: string;
            type: string;
            position: number;
          }>;
        };
      };
    }>(config, query, { id: teamId });

    if (result.errors) {
      return {
        success: false,
        error: result.errors.map((e) => e.message).join(', '),
      };
    }

    return {
      success: true,
      workflows: result.data?.team.states.nodes,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * List projects in a team
 */
export async function listLinearProjects(
  config: LinearConfig,
  teamId?: string
): Promise<{
  success: boolean;
  projects?: Array<{
    id: string;
    name: string;
    description?: string;
    state: string;
    progress: number;
    targetDate?: string;
  }>;
  error?: string;
}> {
  const query = teamId
    ? `
    query Team($id: String!) {
      team(id: $id) {
        projects {
          nodes {
            id
            name
            description
            state
            progress
            targetDate
          }
        }
      }
    }
  `
    : `
    query Projects {
      projects {
        nodes {
          id
          name
          description
          state
          progress
          targetDate
        }
      }
    }
  `;

  try {
    const result = await linearGraphQLRequest<{
      team?: {
        projects: {
          nodes: Array<{
            id: string;
            name: string;
            description?: string;
            state: string;
            progress: number;
            targetDate?: string;
          }>;
        };
      };
      projects?: {
        nodes: Array<{
          id: string;
          name: string;
          description?: string;
          state: string;
          progress: number;
          targetDate?: string;
        }>;
      };
    }>(config, query, teamId ? { id: teamId } : undefined);

    if (result.errors) {
      return {
        success: false,
        error: result.errors.map((e) => e.message).join(', '),
      };
    }

    const projects = teamId
      ? result.data?.team?.projects.nodes
      : result.data?.projects?.nodes;

    return {
      success: true,
      projects,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Assign AI agent to Linear issue via custom label
 */
export async function assignAIAgentToIssue(
  config: LinearConfig,
  issueId: string,
  agentName: string
): Promise<{ success: boolean; error?: string }> {
  // First, find or create the AI agent label
  const labelQuery = `
    query Labels($filter: IssueLabelFilter) {
      issueLabels(filter: $filter) {
        nodes {
          id
          name
        }
      }
    }
  `;

  try {
    const labelResult = await linearGraphQLRequest<{
      issueLabels: { nodes: Array<{ id: string; name: string }> };
    }>(config, labelQuery, {
      filter: { name: { eq: `ai-agent:${agentName}` } },
    });

    let labelId: string | undefined;

    if (labelResult.data?.issueLabels.nodes.length) {
      labelId = labelResult.data.issueLabels.nodes[0].id;
    } else {
      // Create the label if it doesn't exist
      const createLabelMutation = `
        mutation IssueLabelCreate($input: IssueLabelCreateInput!) {
          issueLabelCreate(input: $input) {
            success
            issueLabel {
              id
            }
          }
        }
      `;

      const createResult = await linearGraphQLRequest<{
        issueLabelCreate: { success: boolean; issueLabel?: { id: string } };
      }>(config, createLabelMutation, {
        input: {
          name: `ai-agent:${agentName}`,
          color: '#6B46C1', // Purple for AI agents
          teamId: config.teamId,
        },
      });

      labelId = createResult.data?.issueLabelCreate.issueLabel?.id;
    }

    if (!labelId) {
      return { success: false, error: 'Failed to create or find AI agent label' };
    }

    // Get current labels
    const issueResult = await getLinearIssue(config, issueId);
    if (!issueResult.success || !issueResult.issue) {
      return { success: false, error: 'Failed to fetch issue' };
    }

    const currentLabelIds = issueResult.issue.labels.map((l) => l.id);
    const updatedLabelIds = [...currentLabelIds, labelId];

    // Update issue with the new label
    return await updateLinearIssue(config, issueId, {
      labelIds: updatedLabelIds,
    });
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
