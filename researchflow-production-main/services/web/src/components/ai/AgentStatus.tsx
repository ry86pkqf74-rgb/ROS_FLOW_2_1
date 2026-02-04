import React, { useMemo } from 'react';
import { useAgentStatus } from '../../hooks/useAgentStatus';

export type AgentPhase = 'DataPrep' | 'Analysis' | 'Quality' | 'IRB' | 'Manuscript';

interface AgentStatusProps {
  className?: string;
  showDetails?: boolean;
  compact?: boolean;
}

interface PhaseConfig {
  label: string;
  color: string;
  icon: string;
  description: string;
}

const PHASE_CONFIG: Record<AgentPhase, PhaseConfig> = {
  DataPrep: {
    label: 'Data Preparation',
    color: 'bg-blue-500',
    icon: '📊',
    description: 'Preparing and validating data for analysis',
  },
  Analysis: {
    label: 'Analysis',
    color: 'bg-purple-500',
    icon: '🔬',
    description: 'Running statistical and analytical workflows',
  },
  Quality: {
    label: 'Quality Assurance',
    color: 'bg-orange-500',
    icon: '✓',
    description: 'Validating results and checking quality metrics',
  },
  IRB: {
    label: 'IRB Review',
    color: 'bg-green-500',
    icon: '📋',
    description: 'Institutional Review Board compliance checks',
  },
  Manuscript: {
    label: 'Manuscript Generation',
    color: 'bg-indigo-500',
    icon: '📝',
    description: 'Generating and formatting manuscript output',
  },
};

const PHASE_ORDER: AgentPhase[] = [
  'DataPrep',
  'Analysis',
  'Quality',
  'IRB',
  'Manuscript',
];

export const AgentStatus: React.FC<AgentStatusProps> = ({
  className = '',
  showDetails = true,
  compact = false,
}) => {
  const { status, phase, progress, error, isConnected } = useAgentStatus();

  const currentPhaseIndex = useMemo(
    () => PHASE_ORDER.indexOf(phase),
    [phase]
  );

  const statusColor = useMemo(() => {
    if (error) return 'text-red-600';
    if (status === 'running') return 'text-green-600';
    if (status === 'paused') return 'text-yellow-600';
    return 'text-gray-600';
  }, [status, error]);

  const connectionStatus = useMemo(() => {
    return isConnected ? (
      <span className="flex items-center gap-2 text-green-600">
        <span className="inline-block w-2 h-2 bg-green-600 rounded-full animate-pulse" />
        Connected
      </span>
    ) : (
      <span className="flex items-center gap-2 text-gray-400">
        <span className="inline-block w-2 h-2 bg-gray-400 rounded-full" />
        Disconnected
      </span>
    );
  }, [isConnected]);

  if (compact) {
    return (
      <div
        className={`inline-flex items-center gap-2 px-3 py-1 bg-gray-100 rounded-full text-sm ${className}`}
      >
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
          }`}
        />
        <span className={statusColor}>
          {phase}
          {progress > 0 && progress < 100 ? ` (${progress}%)` : ''}
        </span>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Agent Status</h2>
          <p className="text-sm text-gray-600 mt-1">Real-time execution tracking</p>
        </div>
        <div className="text-right">{connectionStatus}</div>
      </div>

      {/* Current Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-600">Current Phase</p>
            <p className={`text-lg font-semibold mt-1 ${statusColor}`}>
              {PHASE_CONFIG[phase]?.label || phase}
            </p>
            {showDetails && (
              <p className="text-sm text-gray-500 mt-1">
                {PHASE_CONFIG[phase]?.description}
              </p>
            )}
          </div>
          <div className="text-4xl">
            {PHASE_CONFIG[phase]?.icon || '⚙️'}
          </div>
        </div>

        {/* Status Details */}
        <div className="mt-4 pt-4 border-t border-gray-200 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">Status</p>
            <p className={`text-sm font-semibold mt-1 ${statusColor}`}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase">
              Progress
            </p>
            <p className="text-sm font-semibold text-gray-900 mt-1">
              {progress}%
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Phase Timeline */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">
          Execution Timeline
        </h3>
        <div className="space-y-3">
          {PHASE_ORDER.map((phaseKey, index) => {
            const isCompleted = index < currentPhaseIndex;
            const isCurrent = index === currentPhaseIndex;
            const isUpcoming = index > currentPhaseIndex;
            const phaseConfig = PHASE_CONFIG[phaseKey];

            return (
              <div key={phaseKey} className="flex items-center gap-3">
                {/* Timeline Connector */}
                <div className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors ${
                      isCompleted
                        ? 'bg-green-500 text-white'
                        : isCurrent
                          ? `${phaseConfig.color} text-white animate-pulse`
                          : 'bg-gray-200 text-gray-400'
                    }`}
                  >
                    {isCompleted ? '✓' : phaseConfig.icon}
                  </div>
                  {index < PHASE_ORDER.length - 1 && (
                    <div
                      className={`w-0.5 h-6 mt-1 ${
                        isCompleted ? 'bg-green-500' : 'bg-gray-200'
                      }`}
                    />
                  )}
                </div>

                {/* Phase Info */}
                <div className="flex-1">
                  <p
                    className={`text-sm font-medium ${
                      isCompleted
                        ? 'text-green-700'
                        : isCurrent
                          ? 'text-gray-900'
                          : 'text-gray-400'
                    }`}
                  >
                    {phaseConfig.label}
                  </p>
                  {isCurrent && progress > 0 && (
                    <p className="text-xs text-gray-600 mt-1">
                      {progress}% complete
                    </p>
                  )}
                </div>

                {/* Phase Badge */}
                {isCompleted && (
                  <span className="text-xs font-semibold text-green-700 bg-green-50 px-2 py-1 rounded">
                    Done
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <h4 className="font-semibold text-red-900">Error</h4>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Connection Status Detail */}
      {!isConnected && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex gap-3">
            <span className="text-2xl">⚡</span>
            <div>
              <h4 className="font-semibold text-yellow-900">
                Connection Lost
              </h4>
              <p className="text-sm text-yellow-700 mt-1">
                Attempting to reconnect to the agent server...
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentStatus;
