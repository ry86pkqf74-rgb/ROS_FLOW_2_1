import * as z from 'zod';

/**
 * Cursor IDE Integration Package
 * Enables bidirectional communication between Cursor editor and ResearchFlow
 * AI agents for code generation, review, and task execution
 */

// Configuration schema
export const CursorConfigSchema = z.object({
  webhookUrl: z.string().url(),
  apiKey: z.string().min(1),
  workspaceId: z.string().optional(),
});

export type CursorConfig = z.infer<typeof CursorConfigSchema>;

/**
 * Agent command trigger types
 * Detected from special comments in code: @agent <command> <params>
 */
export type AgentCommand =
  | 'fix-this'
  | 'review'
  | 'optimize'
  | 'test'
  | 'document'
  | 'refactor'
  | 'explain';

/**
 * Code change event from Cursor
 */
export interface CursorCodeChangeEvent {
  type: 'code-change';
  workspaceId: string;
  filePath: string;
  language: string;
  changes: Array<{
    startLine: number;
    endLine: number;
    oldText: string;
    newText: string;
  }>;
  timestamp: string;
  userId?: string;
}

/**
 * Agent trigger event from code comments
 */
export interface CursorAgentTriggerEvent {
  type: 'agent-trigger';
  workspaceId: string;
  filePath: string;
  line: number;
  command: AgentCommand;
  params?: Record<string, unknown>;
  context: {
    startLine: number;
    endLine: number;
    code: string;
  };
  timestamp: string;
  userId?: string;
}

/**
 * Task completion notification to send back to Cursor
 */
export interface TaskProgressNotification {
  taskId: string;
  status: 'started' | 'in-progress' | 'completed' | 'failed';
  progress?: number;
  message?: string;
  result?: {
    type: 'code-suggestion' | 'review' | 'test-result' | 'documentation';
    content: string;
    filePath?: string;
    startLine?: number;
    endLine?: number;
  };
}

/**
 * Parse agent command from code comment
 * Example: // @agent fix-this {"priority": "high"}
 */
export function parseAgentCommand(
  comment: string
): { command: AgentCommand; params?: Record<string, unknown> } | null {
  const agentCommandRegex = /@agent\s+(\w+(?:-\w+)*)\s*({.*})?/;
  const match = comment.match(agentCommandRegex);

  if (!match) return null;

  const command = match[1] as AgentCommand;
  let params: Record<string, unknown> | undefined;

  if (match[2]) {
    try {
      params = JSON.parse(match[2]);
    } catch (error) {
      console.error('Failed to parse agent command params:', error);
    }
  }

  return { command, params };
}

/**
 * Send code change event to ResearchFlow orchestrator
 */
export async function sendCodeChangeEvent(
  config: CursorConfig,
  event: CursorCodeChangeEvent
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(`${config.webhookUrl}/cursor/code-change`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.apiKey,
      },
      body: JSON.stringify(event),
    });

    if (!response.ok) {
      return {
        success: false,
        error: `HTTP ${response.status}: ${await response.text()}`,
      };
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
 * Send agent trigger event to ResearchFlow orchestrator
 */
export async function sendAgentTriggerEvent(
  config: CursorConfig,
  event: CursorAgentTriggerEvent
): Promise<{
  success: boolean;
  taskId?: string;
  error?: string;
}> {
  try {
    const response = await fetch(`${config.webhookUrl}/cursor/agent-trigger`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.apiKey,
      },
      body: JSON.stringify(event),
    });

    if (!response.ok) {
      return {
        success: false,
        error: `HTTP ${response.status}: ${await response.text()}`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      taskId: data.taskId,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * Subscribe to task progress updates via SSE (Server-Sent Events)
 */
export function subscribeToTaskProgress(
  config: CursorConfig,
  taskId: string,
  onProgress: (notification: TaskProgressNotification) => void,
  onError?: (error: Error) => void
): () => void {
  const eventSource = new EventSource(
    `${config.webhookUrl}/cursor/task-progress/${taskId}?apiKey=${config.apiKey}`
  );

  eventSource.onmessage = (event) => {
    try {
      const notification: TaskProgressNotification = JSON.parse(event.data);
      onProgress(notification);
    } catch (error) {
      console.error('Failed to parse task progress notification:', error);
      if (onError) {
        onError(error instanceof Error ? error : new Error('Parse error'));
      }
    }
  };

  eventSource.onerror = (error) => {
    console.error('EventSource error:', error);
    if (onError) {
      onError(new Error('EventSource connection failed'));
    }
  };

  // Return cleanup function
  return () => {
    eventSource.close();
  };
}

/**
 * Extract code context around a line
 */
export function extractCodeContext(
  fullCode: string,
  targetLine: number,
  contextLines: number = 10
): { startLine: number; endLine: number; code: string } {
  const lines = fullCode.split('\n');
  const startLine = Math.max(0, targetLine - contextLines);
  const endLine = Math.min(lines.length - 1, targetLine + contextLines);

  const code = lines.slice(startLine, endLine + 1).join('\n');

  return {
    startLine,
    endLine,
    code,
  };
}

/**
 * Create code suggestion inline diff
 */
export function createInlineDiff(
  original: string,
  suggested: string
): Array<{
  type: 'unchanged' | 'added' | 'removed';
  line: string;
}> {
  const originalLines = original.split('\n');
  const suggestedLines = suggested.split('\n');
  const diff: Array<{ type: 'unchanged' | 'added' | 'removed'; line: string }> = [];

  // Simple line-by-line comparison (can be enhanced with proper diff algorithm)
  const maxLines = Math.max(originalLines.length, suggestedLines.length);

  for (let i = 0; i < maxLines; i++) {
    const origLine = originalLines[i];
    const suggLine = suggestedLines[i];

    if (origLine === suggLine) {
      diff.push({ type: 'unchanged', line: origLine });
    } else if (origLine !== undefined && suggLine === undefined) {
      diff.push({ type: 'removed', line: origLine });
    } else if (origLine === undefined && suggLine !== undefined) {
      diff.push({ type: 'added', line: suggLine });
    } else if (origLine !== suggLine) {
      diff.push({ type: 'removed', line: origLine });
      diff.push({ type: 'added', line: suggLine });
    }
  }

  return diff;
}

/**
 * Format agent commands available documentation
 */
export const AGENT_COMMANDS_HELP = `
# Available Agent Commands

Trigger AI agents directly from your code using special comments:

## Syntax
\`\`\`
// @agent <command> [optional-json-params]
\`\`\`

## Commands

### @agent fix-this
Automatically fix bugs or errors in the selected code
Example: \`// @agent fix-this {"priority": "high"}\`

### @agent review
Request code review with suggestions for improvements
Example: \`// @agent review\`

### @agent optimize
Optimize code for performance or efficiency
Example: \`// @agent optimize {"focus": "memory"}\`

### @agent test
Generate unit tests for the selected code
Example: \`// @agent test {"framework": "jest"}\`

### @agent document
Generate documentation for functions/classes
Example: \`// @agent document {"style": "jsdoc"}\`

### @agent refactor
Refactor code for better structure and maintainability
Example: \`// @agent refactor {"pattern": "functional"}\`

### @agent explain
Get detailed explanation of complex code
Example: \`// @agent explain\`

## Parameters
All commands accept optional JSON parameters for customization:
- \`priority\`: "low" | "medium" | "high" | "critical"
- \`context\`: Additional context string
- Command-specific params (see examples above)
`;

export { AgentCommand, CursorConfig };
