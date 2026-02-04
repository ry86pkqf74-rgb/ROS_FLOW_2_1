/**
 * AgentProgress Component
 * 
 * Visualizes LangGraph agent execution progress with:
 * - Real-time status updates
 * - Iteration/quality tracking
 * - Artifact previews
 * - Error handling
 * 
 * Linear Issue: ROS-85
 */

import React, { useMemo } from 'react';
import { 
  useAgentProgress, 
  AgentStatus, 
  AgentProgress as AgentProgressData,
  AgentResult,
  UseAgentProgressOptions,
} from '../hooks/useAgentProgress';

// Icons (inline SVG for simplicity)
const Icons = {
  check: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  ),
  error: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  ),
  spinner: (
    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  ),
  robot: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  ),
  document: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
};

// Status colors and labels
const STATUS_CONFIG: Record<AgentStatus, { color: string; bgColor: string; label: string }> = {
  idle: { color: 'text-gray-500', bgColor: 'bg-gray-100', label: 'Ready' },
  queued: { color: 'text-yellow-600', bgColor: 'bg-yellow-50', label: 'Queued' },
  connecting: { color: 'text-blue-500', bgColor: 'bg-blue-50', label: 'Connecting...' },
  running: { color: 'text-blue-600', bgColor: 'bg-blue-50', label: 'Running' },
  completed: { color: 'text-green-600', bgColor: 'bg-green-50', label: 'Completed' },
  failed: { color: 'text-red-600', bgColor: 'bg-red-50', label: 'Failed' },
  disconnected: { color: 'text-gray-500', bgColor: 'bg-gray-100', label: 'Disconnected' },
};

// Stage names for display
const STAGE_NAMES: Record<string, string> = {
  initializing: 'Initializing',
  plan: 'Planning',
  retrieve: 'Retrieving Context',
  execute: 'Executing',
  reflect: 'Quality Check',
  starting: 'Starting',
  processing: 'Processing',
};

export interface AgentProgressProps {
  /** Task ID to track (auto-connects when provided) */
  taskId?: string;
  /** WebSocket options */
  wsOptions?: UseAgentProgressOptions;
  /** Show detailed view */
  detailed?: boolean;
  /** Custom className */
  className?: string;
  /** Callback when result is available */
  onResult?: (result: AgentResult) => void;
  /** Show artifacts inline */
  showArtifacts?: boolean;
}

export function AgentProgressComponent({
  taskId,
  wsOptions,
  detailed = false,
  className = '',
  onResult,
  showArtifacts = true,
}: AgentProgressProps) {
  const {
    status,
    progress,
    result,
    error,
    agentName,
    connect,
    disconnect,
    isConnected,
  } = useAgentProgress({
    ...wsOptions,
    onComplete: (result) => {
      wsOptions?.onComplete?.(result);
      onResult?.(result);
    },
  });

  // Auto-connect when taskId changes
  React.useEffect(() => {
    if (taskId && taskId !== '') {
      connect(taskId);
    }
    return () => {
      disconnect();
    };
  }, [taskId, connect, disconnect]);

  const statusConfig = STATUS_CONFIG[status];
  const stageName = progress?.stage ? (STAGE_NAMES[progress.stage] || progress.stage) : null;

  // Quality score color
  const qualityColor = useMemo(() => {
    const score = progress?.qualityScore ?? result?.qualityScore ?? 0;
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  }, [progress?.qualityScore, result?.qualityScore]);

  // Progress percentage for bar
  const progressPercent = useMemo(() => {
    if (status === 'completed') return 100;
    if (status === 'failed') return 100;
    if (!progress) return 0;
    
    const iteration = progress.iteration || 0;
    const total = progress.totalIterations || 3;
    const stageWeight: Record<string, number> = {
      plan: 0.1,
      retrieve: 0.3,
      execute: 0.6,
      reflect: 0.9,
    };
    
    const baseProgress = (iteration / total) * 100;
    const stageBonus = (stageWeight[progress.stage] || 0.5) * (100 / total);
    return Math.min(95, baseProgress + stageBonus);
  }, [status, progress]);

  if (status === 'idle' && !taskId) {
    return null;
  }

  return (
    <div className={`rounded-lg border ${statusConfig.bgColor} p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={statusConfig.color}>
            {status === 'running' || status === 'connecting' ? Icons.spinner : Icons.robot}
          </span>
          <span className="font-medium">
            {agentName || 'Agent'}
          </span>
          <span className={`text-sm px-2 py-0.5 rounded-full ${statusConfig.bgColor} ${statusConfig.color}`}>
            {statusConfig.label}
          </span>
        </div>
        
        {isConnected && (
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Progress Bar */}
      {(status === 'running' || status === 'queued') && (
        <div className="mb-3">
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {progress && (
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>{stageName}</span>
              <span>Iteration {progress.iteration}/{progress.totalIterations || '?'}</span>
            </div>
          )}
        </div>
      )}

      {/* Quality Score */}
      {(progress?.qualityScore !== undefined || result?.qualityScore !== undefined) && (
        <div className="flex items-center gap-2 text-sm mb-2">
          <span className="text-gray-600">Quality:</span>
          <span className={`font-medium ${qualityColor}`}>
            {((progress?.qualityScore ?? result?.qualityScore ?? 0) * 100).toFixed(0)}%
          </span>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-2 rounded mt-2">
          {Icons.error}
          <span>{error}</span>
        </div>
      )}

      {/* Success Message */}
      {status === 'completed' && result && (
        <div className="flex items-center gap-2 text-green-600 text-sm mt-2">
          {Icons.check}
          <span>Completed in {(result.durationMs / 1000).toFixed(1)}s</span>
        </div>
      )}

      {/* Detailed View */}
      {detailed && result && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 text-sm mb-4">
            <div>
              <div className="text-gray-500">Iterations</div>
              <div className="font-medium">{result.iterations}</div>
            </div>
            <div>
              <div className="text-gray-500">Duration</div>
              <div className="font-medium">{(result.durationMs / 1000).toFixed(1)}s</div>
            </div>
            <div>
              <div className="text-gray-500">RAG Sources</div>
              <div className="font-medium">{result.ragSources.length}</div>
            </div>
          </div>

          {/* Artifacts */}
          {showArtifacts && result.artifacts && result.artifacts.length > 0 && (
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2">Artifacts</div>
              <div className="space-y-2">
                {result.artifacts.map((artifact, i) => (
                  <div 
                    key={i}
                    className="flex items-center gap-2 text-sm bg-white p-2 rounded border"
                  >
                    {Icons.document}
                    <span className="text-gray-600">{artifact.type}</span>
                    <span className="text-xs text-gray-400">
                      {new Date(artifact.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Result Preview */}
          {result.result && (
            <div className="mt-4">
              <div className="text-sm font-medium text-gray-700 mb-2">Result Preview</div>
              <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto max-h-40">
                {JSON.stringify(result.result, null, 2).slice(0, 500)}
                {JSON.stringify(result.result).length > 500 && '...'}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Compact inline version
export function AgentProgressInline({ 
  taskId, 
  className = '' 
}: { 
  taskId?: string; 
  className?: string;
}) {
  const { status, progress, agentName } = useAgentProgress();

  React.useEffect(() => {
    if (taskId) {
      // Would need access to connect, simplified for inline
    }
  }, [taskId]);

  const statusConfig = STATUS_CONFIG[status];

  if (status === 'idle') return null;

  return (
    <span className={`inline-flex items-center gap-1.5 text-sm ${className}`}>
      <span className={statusConfig.color}>
        {status === 'running' ? Icons.spinner : 
         status === 'completed' ? Icons.check :
         status === 'failed' ? Icons.error : Icons.robot}
      </span>
      <span className="text-gray-600">
        {agentName || 'Agent'}: {progress?.stage || statusConfig.label}
      </span>
    </span>
  );
}

export default AgentProgressComponent;
