/**
 * Agent monitoring types and API contract.
 * Used by AgentMonitor and AgentDebugger. Query key: ['agent-status', workflowId].
 */

export type AgentStatusOverall = 'idle' | 'running' | 'completed' | 'error';

export interface AgentStatusItem {
  id: string;
  name: string;
  status: AgentStatusOverall;
  progress?: number;
  error?: string;
}

export interface AgentTraceStep {
  step: string;
  phase?: string;
  startedAt?: string;
  durationMs?: number;
}

export interface AgentTimingEntry {
  name: string;
  durationMs: number;
}

export interface AgentStatusResponse {
  status: AgentStatusOverall;
  agents: AgentStatusItem[];
  trace?: AgentTraceStep[];
  timing?: AgentTimingEntry[];
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
}

const DEFAULT_AGENT_STATUS: AgentStatusResponse = {
  status: 'idle',
  agents: [],
};

/**
 * Fetch agent status for a workflow. Returns default payload on 404 or network error
 * so the UI never breaks before the backend exposes the endpoint.
 */
export async function fetchAgentStatus(
  workflowIdKey: string
): Promise<AgentStatusResponse> {
  if (typeof window === 'undefined') return DEFAULT_AGENT_STATUS;
  const workflowId = workflowIdKey === 'current' ? '' : workflowIdKey;
  const path = workflowId
    ? `/api/workflows/${workflowId}/agent-status`
    : '/api/agent-status';
  try {
    const res = await fetch(path, { credentials: 'include' });
    if (!res.ok) return DEFAULT_AGENT_STATUS;
    const data = await res.json();
    return {
      status: data.status ?? 'idle',
      agents: Array.isArray(data.agents) ? data.agents : [],
      trace: data.trace,
      timing: data.timing,
      inputs: data.inputs,
      outputs: data.outputs,
    };
  } catch {
    return DEFAULT_AGENT_STATUS;
  }
}
