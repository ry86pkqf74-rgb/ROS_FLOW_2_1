/**
 * Example Usage of Phase 7 Frontend Integration Components
 *
 * This file demonstrates various ways to use AgentStatus, CopilotResponse,
 * and the useAgentStatus hook in real-world scenarios.
 */

import React, { useState } from 'react';
import { AgentStatus } from './AgentStatus';
import { CopilotResponse, type SourceCitation } from './CopilotResponse';
import { useAgentStatus } from '../../hooks/useAgentStatus';

/**
 * Example 1: Basic Agent Status Display
 *
 * Simple display of agent execution status with default configuration.
 */
export const BasicAgentStatusExample: React.FC = () => {
  return (
    <div className="p-8 bg-gray-50 rounded-lg">
      <h2 className="text-2xl font-bold mb-6">Basic Agent Status</h2>
      <AgentStatus />
    </div>
  );
};

/**
 * Example 2: Compact Agent Status for Header
 *
 * Space-efficient version suitable for page headers or sidebars.
 */
export const CompactAgentStatusExample: React.FC = () => {
  return (
    <div className="flex items-center justify-between bg-white p-4 border-b border-gray-200">
      <h1 className="text-xl font-bold">Research Dashboard</h1>
      <AgentStatus compact={true} />
    </div>
  );
};

/**
 * Example 3: Basic Copilot Response
 *
 * Display a simple copilot response with source citations.
 */
export const BasicCopilotResponseExample: React.FC = () => {
  const sources: SourceCitation[] = [
    {
      id: 'doc-001',
      title: 'Patient Demographics Study (2024)',
      type: 'document',
      relevanceScore: 0.95,
    },
    {
      id: 'ds-001',
      title: 'Clinical Outcomes Database',
      type: 'dataset',
      relevanceScore: 0.87,
    },
    {
      id: 'analysis-001',
      title: 'Statistical Analysis Results',
      type: 'analysis',
      relevanceScore: 0.92,
    },
  ];

  const response = `Based on [ref:doc-001], the patient cohort consisted of 500 subjects
with an average age of 45 years. The statistical analysis using data from
[ref:ds-001] revealed significant differences between treatment groups
(p < 0.05). These findings are consistent with [ref:analysis-001],
which employed multivariate regression techniques.`;

  return (
    <div className="p-8 bg-gray-50 rounded-lg">
      <h2 className="text-2xl font-bold mb-6">Analysis Results</h2>
      <CopilotResponse
        content={response}
        sources={sources}
        confidenceScore={0.92}
        showConfidenceMetrics={true}
      />
    </div>
  );
};

/**
 * Example 4: Streaming Copilot Response
 *
 * Demonstrates real-time streaming response with auto-scroll.
 */
export const StreamingCopilotResponseExample: React.FC = () => {
  const [content, setContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(true);

  React.useEffect(() => {
    // Simulate streaming response
    const fullContent = `The analysis of [ref:dataset-1] demonstrates a strong correlation
between variables X and Y. Our preliminary findings suggest that [ref:study-1]
may need to be revisited with updated methodology. Furthermore, [ref:analysis-1]
supports our hypothesis that demographic factors play a significant role.`;

    let index = 0;
    const timer = setInterval(() => {
      if (index < fullContent.length) {
        setContent(fullContent.substring(0, index + 1));
        index++;
      } else {
        setIsStreaming(false);
        clearInterval(timer);
      }
    }, 30);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="p-8 bg-gray-50 rounded-lg">
      <h2 className="text-2xl font-bold mb-6">Real-time Analysis</h2>
      <CopilotResponse
        content={content}
        sources={[
          {
            id: 'dataset-1',
            title: 'Primary Dataset',
            type: 'dataset',
            relevanceScore: 0.88,
          },
          {
            id: 'study-1',
            title: 'Related Study',
            type: 'document',
            relevanceScore: 0.75,
          },
          {
            id: 'analysis-1',
            title: 'Preliminary Analysis',
            type: 'analysis',
            relevanceScore: 0.91,
          },
        ]}
        confidenceScore={0.85}
        isStreaming={isStreaming}
      />
    </div>
  );
};

/**
 * Example 5: Full Dashboard with Agent Status and Response
 *
 * Comprehensive example showing agent status alongside copilot response.
 */
export const FullDashboardExample: React.FC = () => {
  const { status, phase, progress } = useAgentStatus({
    wsUrl: process.env.REACT_APP_AGENT_WS_URL,
  });

  const isExecuting = status === 'running';

  const sources: SourceCitation[] = [
    {
      id: 'protocol-001',
      title: 'Study Protocol v2.1',
      type: 'document',
      relevanceScore: 0.98,
    },
    {
      id: 'cohort-data',
      title: 'Patient Cohort Demographics',
      type: 'dataset',
      relevanceScore: 0.91,
    },
    {
      id: 'prior-analysis',
      title: 'Pilot Study Results',
      type: 'analysis',
      relevanceScore: 0.84,
    },
    {
      id: 'external-reference',
      title: 'FDA Guidance Document',
      url: 'https://fda.gov/...',
      type: 'external',
      relevanceScore: 0.76,
    },
  ];

  const analysisText = `According to [ref:protocol-001], the study was designed as a randomized controlled trial
with stratification by [ref:cohort-data]. The primary outcome showed a treatment effect of 23%
(95% CI: 15%-31%, p=0.003). These results are consistent with findings from [ref:prior-analysis]
but demonstrate greater efficacy. In alignment with [ref:external-reference], all safety
monitoring protocols were followed throughout the study duration.`;

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            ResearchFlow Analysis Dashboard
          </h1>
          <p className="text-gray-600 mt-2">
            Real-time agent execution and AI-powered analysis results
          </p>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Agent Status */}
          <div className="lg:col-span-1">
            <AgentStatus
              showDetails={true}
              compact={false}
              className="h-full"
            />
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-2 space-y-6">
            {/* Results Card */}
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-2xl font-bold text-gray-900">
                  Primary Analysis Results
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Generated by Agent AI during {phase} phase
                </p>
              </div>

              <div className="p-6">
                <CopilotResponse
                  content={analysisText}
                  sources={sources}
                  confidenceScore={0.94}
                  isStreaming={isExecuting}
                  onSourceClick={(sourceId) => {
                    console.log('User clicked source:', sourceId);
                    // Handle source navigation
                  }}
                  showConfidenceMetrics={true}
                />
              </div>
            </div>

            {/* Status Info Card */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Current Phase:</strong> {phase} ({progress}%)
              </p>
              <p className="text-sm text-blue-800 mt-1">
                <strong>Status:</strong>{' '}
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Example 6: Custom Hook Integration with Error Handling
 *
 * Shows advanced hook usage with error handling and callbacks.
 */
export const AdvancedHookIntegrationExample: React.FC = () => {
  const [connectionErrors, setConnectionErrors] = useState<string[]>([]);
  const [phaseHistory, setPhaseHistory] = useState<string[]>(['DataPrep']);

  const { status, phase, progress, error, isConnected, connect, disconnect } =
    useAgentStatus({
      autoConnect: true,
      reconnectInterval: 5000,
      maxReconnectAttempts: 15,
      heartbeatInterval: 20000,
      onError: (err) => {
        console.error('Agent error:', err);
        setConnectionErrors((prev) => [...prev.slice(-4), err.message]);
      },
      onPhaseChange: (newPhase) => {
        console.log(`Phase transitioned to: ${newPhase}`);
        setPhaseHistory((prev) => [...prev, newPhase]);
      },
    });

  return (
    <div className="p-8 space-y-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-2xl font-bold mb-4">Advanced Hook Integration</h2>

        {/* Status Section */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div>
            <p className="text-sm text-gray-600">Status</p>
            <p className="text-lg font-semibold text-gray-900">{status}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Phase</p>
            <p className="text-lg font-semibold text-gray-900">{phase}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Progress</p>
            <p className="text-lg font-semibold text-gray-900">{progress}%</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Connected</p>
            <p
              className={`text-lg font-semibold ${
                isConnected ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {isConnected ? 'Yes' : 'No'}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={connect}
            disabled={isConnected}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          >
            Connect
          </button>
          <button
            onClick={disconnect}
            disabled={!isConnected}
            className="px-4 py-2 bg-red-600 text-white rounded disabled:opacity-50"
          >
            Disconnect
          </button>
        </div>

        {/* Error Display */}
        {connectionErrors.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded p-4 mb-6">
            <h3 className="font-semibold text-red-900 mb-2">Recent Errors</h3>
            <ul className="space-y-1 text-sm text-red-800">
              {connectionErrors.map((err, idx) => (
                <li key={idx}>• {err}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Phase History */}
        {phaseHistory.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded p-4">
            <h3 className="font-semibold text-blue-900 mb-2">Phase History</h3>
            <div className="flex gap-2 flex-wrap text-sm">
              {phaseHistory.map((p, idx) => (
                <span
                  key={idx}
                  className="bg-blue-200 text-blue-800 px-2 py-1 rounded"
                >
                  {p}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Example 7: Responsive Multi-Panel Layout
 *
 * Shows how to arrange components responsively.
 */
export const ResponsiveLayoutExample: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Top Bar */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold">ResearchFlow</h1>
            <AgentStatus compact={true} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        {/* 3-Column Desktop, 1-Column Mobile */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Column 1 */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">Execution Status</h3>
            <AgentStatus
              compact={false}
              showDetails={true}
              className="text-sm"
            />
          </div>

          {/* Column 2-3 */}
          <div className="md:col-span-2 bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">Analysis Results</h3>
            <BasicCopilotResponseExample />
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * Export all examples as a demonstration suite
 */
export const AllExamples = {
  BasicAgentStatus: BasicAgentStatusExample,
  CompactAgentStatus: CompactAgentStatusExample,
  BasicCopilotResponse: BasicCopilotResponseExample,
  StreamingCopilotResponse: StreamingCopilotResponseExample,
  FullDashboard: FullDashboardExample,
  AdvancedHookIntegration: AdvancedHookIntegrationExample,
  ResponsiveLayout: ResponsiveLayoutExample,
};
