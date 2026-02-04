/**
 * AgentDebugger - Verbose debugging interface for agent workflow.
 * Trace visualization, timing breakdown, input/output inspection.
 * Accepts optional data prop so the same polled data can drive AgentMonitor and AgentDebugger.
 */

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { fetchAgentStatus, type AgentStatusResponse } from './types';
import { Bug, ListOrdered, Clock, ArrowRightLeft, ChevronDown } from 'lucide-react';

/** Sanitize for display: avoid leaking PHI; truncate large values */
function safeJson(value: unknown): string {
  if (value === undefined || value === null) return '—';
  try {
    const str = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    return str.length > 2000 ? str.slice(0, 2000) + '\n… (truncated)' : str;
  } catch {
    return String(value);
  }
}

export interface AgentDebuggerProps {
  workflowId?: string;
  /** When provided, use this instead of polling (e.g. from shared query with AgentMonitor) */
  data?: AgentStatusResponse | null;
  className?: string;
}

export function AgentDebugger({ workflowId, data: dataProp, className = '' }: AgentDebuggerProps) {
  const key = workflowId ?? 'current';
  const { data: queryData } = useQuery<AgentStatusResponse>({
    queryKey: ['agent-status', key],
    queryFn: () => fetchAgentStatus(key),
    refetchInterval: 2000,
    enabled: !dataProp,
  });

  const data = dataProp ?? queryData ?? { status: 'idle', agents: [] };
  const hasTrace = data.trace && data.trace.length > 0;
  const hasTiming = data.timing && data.timing.length > 0;
  const hasInputs = data.inputs && Object.keys(data.inputs).length > 0;
  const hasOutputs = data.outputs && Object.keys(data.outputs).length > 0;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Bug className="h-5 w-5" />
          Agent debug
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="trace" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="trace" className="flex items-center gap-1.5">
              <ListOrdered className="h-4 w-4" />
              Trace
              {hasTrace && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {data.trace!.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="timing" className="flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              Timing
              {hasTiming && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {data.timing!.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="io" className="flex items-center gap-1.5">
              <ArrowRightLeft className="h-4 w-4" />
              I/O
            </TabsTrigger>
          </TabsList>

          <TabsContent value="trace" className="mt-3">
            <ScrollArea className="h-[200px] rounded-md border p-3">
              {hasTrace ? (
                <ul className="space-y-2 text-sm">
                  {data.trace!.map((step, i) => (
                    <li key={i} className="flex flex-col gap-0.5 border-b pb-2 last:border-0">
                      <span className="font-medium">{step.step}</span>
                      {step.phase != null && (
                        <span className="text-muted-foreground text-xs">Phase: {step.phase}</span>
                      )}
                      {step.durationMs != null && (
                        <span className="text-muted-foreground text-xs">
                          {step.durationMs} ms
                        </span>
                      )}
                      {step.startedAt != null && (
                        <span className="text-muted-foreground text-xs">{step.startedAt}</span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground text-sm">No trace data</p>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="timing" className="mt-3">
            <ScrollArea className="h-[200px] rounded-md border p-3">
              {hasTiming ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="pb-2 pr-4 font-medium">Step</th>
                      <th className="pb-2 font-medium">Duration (ms)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.timing!.map((entry, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1.5 pr-4">{entry.name}</td>
                        <td className="py-1.5 font-mono text-muted-foreground">
                          {entry.durationMs}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-muted-foreground text-sm">No timing data</p>
              )}
            </ScrollArea>
          </TabsContent>

          <TabsContent value="io" className="mt-3">
            <div className="space-y-3">
              <Collapsible defaultOpen={hasInputs}>
                <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium">
                  <ChevronDown className="h-4 w-4" />
                  Input
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <ScrollArea className="h-[120px] rounded-md border p-3 mt-2">
                    <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                      {hasInputs ? safeJson(data.inputs) : '—'}
                    </pre>
                  </ScrollArea>
                </CollapsibleContent>
              </Collapsible>
              <Collapsible defaultOpen={hasOutputs && !hasInputs}>
                <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium">
                  <ChevronDown className="h-4 w-4" />
                  Output
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <ScrollArea className="h-[120px] rounded-md border p-3 mt-2">
                    <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                      {hasOutputs ? safeJson(data.outputs) : '—'}
                    </pre>
                  </ScrollArea>
                </CollapsibleContent>
              </Collapsible>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

export default AgentDebugger;
