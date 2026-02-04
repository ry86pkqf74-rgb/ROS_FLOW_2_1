/**
 * AgentMonitor - Real-time agent status display for a workflow.
 * Uses TanStack Query with 2s refetch. Query key: ['agent-status', workflowId].
 */

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { fetchAgentStatus, type AgentStatusResponse, type AgentStatusOverall } from './types';
import { Bot, AlertCircle, Loader2, CheckCircle } from 'lucide-react';

const STATUS_CONFIG: Record<
  AgentStatusOverall,
  { label: string; variant: 'default' | 'secondary' | 'destructive'; icon: React.ReactNode }
> = {
  idle: { label: 'Idle', variant: 'secondary', icon: <Bot className="h-4 w-4" /> },
  running: {
    label: 'Running',
    variant: 'default',
    icon: <Loader2 className="h-4 w-4 animate-spin" />,
  },
  completed: {
    label: 'Completed',
    variant: 'default',
    icon: <CheckCircle className="h-4 w-4" />,
  },
  error: {
    label: 'Error',
    variant: 'destructive',
    icon: <AlertCircle className="h-4 w-4" />,
  },
};

export interface AgentMonitorProps {
  workflowId?: string;
  className?: string;
}

export function AgentMonitor({ workflowId, className = '' }: AgentMonitorProps) {
  const key = workflowId ?? 'current';
  const { data, isLoading, error } = useQuery<AgentStatusResponse>({
    queryKey: ['agent-status', key],
    queryFn: () => fetchAgentStatus(key),
    refetchInterval: 2000,
    enabled: true,
  });

  const payload = data ?? { status: 'idle' as const, agents: [] };
  const statusConfig = STATUS_CONFIG[payload.status];
  const hasAgentErrors = payload.agents.some((a) => a.error);
  const overallError = payload.status === 'error' || hasAgentErrors;

  if (isLoading && !data) {
    return (
      <Card className={className}>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent status
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="h-5 w-5" />
            Agent status
          </CardTitle>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            Live
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          {statusConfig?.icon}
          <Badge variant={statusConfig?.variant ?? 'secondary'}>
            {statusConfig?.label ?? payload.status}
          </Badge>
        </div>

        {payload.agents.length > 0 && (
          <ul className="space-y-2">
            {payload.agents.map((agent) => {
              const agentStatus = STATUS_CONFIG[agent.status];
              return (
                <li
                  key={agent.id}
                  className="flex flex-col gap-1 rounded-md border p-2 text-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{agent.name}</span>
                    <Badge variant={agentStatus?.variant ?? 'secondary'} className="text-xs">
                      {agentStatus?.label ?? agent.status}
                    </Badge>
                  </div>
                  {(agent.status === 'running' && agent.progress != null) && (
                    <Progress value={agent.progress} className="h-2" />
                  )}
                  {agent.error && (
                    <p className="text-destructive text-xs">{agent.error}</p>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error instanceof Error ? error.message : 'Failed to load agent status'}
            </AlertDescription>
          </Alert>
        )}

        {overallError && !error && payload.status === 'error' && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>Agent workflow reported an error.</AlertDescription>
          </Alert>
        )}

        {hasAgentErrors && !error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              One or more agents have errors. Check the list above.
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

export default AgentMonitor;
