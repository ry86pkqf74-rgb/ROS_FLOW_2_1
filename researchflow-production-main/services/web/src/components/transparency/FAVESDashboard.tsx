/**
 * FAVES Compliance Dashboard
 *
 * Displays FAVES (Fair, Appropriate, Valid, Effective, Safe) compliance
 * tracking for AI models. Shows evaluation status, scores, and deployment gates.
 *
 * Phase 10: Transparency & Compliance
 */

import React, { useState, useEffect, useCallback } from 'react';

// ============================================================================
// Types (matching backend API)
// ============================================================================

type FAVESDimension = 'FAIR' | 'APPROPRIATE' | 'VALID' | 'EFFECTIVE' | 'SAFE';
type FAVESStatus = 'PASS' | 'FAIL' | 'PARTIAL' | 'NOT_EVALUATED';

interface FAVESEvaluation {
  id: string;
  model_id: string;
  model_name?: string;
  model_version: string;
  evaluated_at: string;
  evaluated_by: string;
  overall_status: FAVESStatus;
  overall_score: number;
  deployment_allowed: boolean;
  
  // Dimension scores
  fair_score: number;
  fair_status: FAVESStatus;
  appropriate_score: number;
  appropriate_status: FAVESStatus;
  valid_score: number;
  valid_status: FAVESStatus;
  effective_score: number;
  effective_status: FAVESStatus;
  safe_score: number;
  safe_status: FAVESStatus;
  
  blocking_issues?: string[];
  ci_run_id?: string;
}

interface FAVESStats {
  summary: {
    total_evaluations: number;
    passed_count: number;
    failed_count: number;
    models_evaluated: number;
    avg_overall_score: number;
    avg_fair_score: number;
    avg_appropriate_score: number;
    avg_valid_score: number;
    avg_effective_score: number;
    avg_safe_score: number;
  };
  trend: Array<{
    date: string;
    evaluations: number;
    avg_score: number;
    passed: number;
  }>;
}

// ============================================================================
// API Client
// ============================================================================

const favesApi = {
  async getEvaluations(params?: { limit?: number; offset?: number; deployment_allowed?: boolean }) {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());
    if (params?.deployment_allowed !== undefined) {
      queryParams.set('deployment_allowed', params.deployment_allowed.toString());
    }

    const response = await fetch(`/api/faves/evaluations?${queryParams}`);
    if (!response.ok) throw new Error('Failed to fetch evaluations');
    return response.json();
  },

  async getStats() {
    const response = await fetch('/api/faves/stats');
    if (!response.ok) throw new Error('Failed to fetch stats');
    return response.json();
  },

  async getEvaluation(id: string) {
    const response = await fetch(`/api/faves/evaluations/${id}`);
    if (!response.ok) throw new Error('Failed to fetch evaluation');
    return response.json();
  },

  async checkGate(modelId: string, version?: string) {
    const queryParams = version ? `?version=${version}` : '';
    const response = await fetch(`/api/faves/gate/${modelId}${queryParams}`);
    if (!response.ok) throw new Error('Failed to check gate');
    return response.json();
  },
};

// ============================================================================
// Components
// ============================================================================

interface DimensionCardProps {
  dimension: FAVESDimension;
  status: FAVESStatus;
  score: number;
}

function DimensionCard({ dimension, status, score }: DimensionCardProps) {
  const dimensionInfo = {
    FAIR: {
      label: 'Fair',
      icon: '⚖️',
      description: 'Fairness across subgroups',
      color: 'blue',
    },
    APPROPRIATE: {
      label: 'Appropriate',
      icon: '🎯',
      description: 'Use case fit',
      color: 'purple',
    },
    VALID: {
      label: 'Valid',
      icon: '✓',
      description: 'Validation metrics',
      color: 'green',
    },
    EFFECTIVE: {
      label: 'Effective',
      icon: '💡',
      description: 'Clinical utility',
      color: 'amber',
    },
    SAFE: {
      label: 'Safe',
      icon: '🛡️',
      description: 'Safety analysis',
      color: 'red',
    },
  };

  const info = dimensionInfo[dimension];
  const statusColors = {
    PASS: 'bg-green-100 text-green-800 border-green-300',
    FAIL: 'bg-red-100 text-red-800 border-red-300',
    PARTIAL: 'bg-amber-100 text-amber-800 border-amber-300',
    NOT_EVALUATED: 'bg-gray-100 text-gray-800 border-gray-300',
  };

  return (
    <div className={`rounded-lg border-2 p-4 ${statusColors[status]}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{info.icon}</span>
          <div>
            <h3 className="font-semibold">{info.label}</h3>
            <p className="text-xs opacity-75">{info.description}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">{Math.round(score)}</div>
          <div className="text-xs">/ 100</div>
        </div>
      </div>
      <div className="mt-3">
        <div className="h-2 bg-white bg-opacity-50 rounded-full overflow-hidden">
          <div
            className="h-full bg-current rounded-full transition-all"
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
      <div className="mt-2 text-center">
        <span className="text-xs font-semibold px-2 py-1 rounded-full bg-white bg-opacity-50">
          {status}
        </span>
      </div>
    </div>
  );
}

interface EvaluationRowProps {
  evaluation: FAVESEvaluation;
  onClick: () => void;
}

function EvaluationRow({ evaluation, onClick }: EvaluationRowProps) {
  const statusIcon = evaluation.deployment_allowed ? '✅' : '❌';
  const statusColor = evaluation.deployment_allowed
    ? 'text-green-600'
    : 'text-red-600';

  return (
    <tr
      onClick={onClick}
      className="hover:bg-gray-50 cursor-pointer transition-colors"
    >
      <td className="px-4 py-3">
        <div className="font-medium text-gray-900">
          {evaluation.model_name || evaluation.model_id.substring(0, 8)}
        </div>
        <div className="text-xs text-gray-500">{evaluation.model_version}</div>
      </td>
      <td className="px-4 py-3 text-center">
        <span className={`text-2xl ${statusColor}`}>{statusIcon}</span>
      </td>
      <td className="px-4 py-3 text-center">
        <div className="text-lg font-semibold">{Math.round(evaluation.overall_score)}</div>
        <div className="text-xs text-gray-500">/ 100</div>
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-1">
          {(['fair', 'appropriate', 'valid', 'effective', 'safe'] as const).map((dim) => {
            const score = evaluation[`${dim}_score`];
            const status = evaluation[`${dim}_status`];
            const bgColor =
              status === 'PASS' ? 'bg-green-500' :
              status === 'FAIL' ? 'bg-red-500' :
              status === 'PARTIAL' ? 'bg-amber-500' :
              'bg-gray-300';
            
            return (
              <div
                key={dim}
                className={`w-12 h-6 ${bgColor} rounded flex items-center justify-center text-white text-xs font-semibold`}
                title={`${dim.toUpperCase()}: ${score}`}
              >
                {Math.round(score)}
              </div>
            );
          })}
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {new Date(evaluation.evaluated_at).toLocaleDateString()}
      </td>
    </tr>
  );
}

// ============================================================================
// Main Dashboard Component
// ============================================================================

export function FAVESDashboard() {
  const [evaluations, setEvaluations] = useState<FAVESEvaluation[]>([]);
  const [stats, setStats] = useState<FAVESStats | null>(null);
  const [selectedEvaluation, setSelectedEvaluation] = useState<FAVESEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [evalsResult, statsResult] = await Promise.all([
        favesApi.getEvaluations({ limit: 50 }),
        favesApi.getStats(),
      ]);

      setEvaluations(evalsResult.evaluations || []);
      setStats(statsResult);
    } catch (err: any) {
      setError(err.message || 'Failed to load FAVES data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredEvaluations = evaluations.filter((eval) => {
    if (filter === 'all') return true;
    if (filter === 'passed') return eval.deployment_allowed;
    if (filter === 'failed') return !eval.deployment_allowed;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-gray-500">
        <p className="mb-4">{error}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">FAVES Compliance</h1>
          <p className="text-gray-500 mt-1">
            Fair, Appropriate, Valid, Effective, Safe evaluation tracking
          </p>
        </div>
        <button
          onClick={fetchData}
          className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">
              {stats.summary.total_evaluations}
            </div>
            <div className="text-sm text-gray-500">Total Evaluations</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-green-600">
              {stats.summary.passed_count}
            </div>
            <div className="text-sm text-gray-500">Passed</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-red-600">
              {stats.summary.failed_count}
            </div>
            <div className="text-sm text-gray-500">Failed</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-blue-600">
              {stats.summary.models_evaluated}
            </div>
            <div className="text-sm text-gray-500">Models</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="text-2xl font-bold text-purple-600">
              {Math.round(stats.summary.avg_overall_score)}
            </div>
            <div className="text-sm text-gray-500">Avg Score</div>
          </div>
        </div>
      )}

      {/* Dimension Scores (if viewing specific evaluation) */}
      {selectedEvaluation && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              {selectedEvaluation.model_name || 'Model'} v{selectedEvaluation.model_version}
            </h2>
            <button
              onClick={() => setSelectedEvaluation(null)}
              className="text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <DimensionCard
              dimension="FAIR"
              status={selectedEvaluation.fair_status}
              score={selectedEvaluation.fair_score}
            />
            <DimensionCard
              dimension="APPROPRIATE"
              status={selectedEvaluation.appropriate_status}
              score={selectedEvaluation.appropriate_score}
            />
            <DimensionCard
              dimension="VALID"
              status={selectedEvaluation.valid_status}
              score={selectedEvaluation.valid_score}
            />
            <DimensionCard
              dimension="EFFECTIVE"
              status={selectedEvaluation.effective_status}
              score={selectedEvaluation.effective_score}
            />
            <DimensionCard
              dimension="SAFE"
              status={selectedEvaluation.safe_status}
              score={selectedEvaluation.safe_score}
            />
          </div>

          {selectedEvaluation.blocking_issues && selectedEvaluation.blocking_issues.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <h3 className="font-semibold text-red-900 mb-2">Blocking Issues</h3>
              <ul className="space-y-1">
                {selectedEvaluation.blocking_issues.map((issue, idx) => (
                  <li key={idx} className="text-sm text-red-800">• {issue}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
            <div>
              Evaluated by: {selectedEvaluation.evaluated_by}
            </div>
            <div>
              {new Date(selectedEvaluation.evaluated_at).toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['all', 'passed', 'failed'] as const).map((filterOption) => (
          <button
            key={filterOption}
            onClick={() => setFilter(filterOption)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              filter === filterOption
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
            {filterOption !== 'all' && (
              <span className="ml-2 px-1.5 py-0.5 text-xs bg-gray-100 rounded-full">
                {evaluations.filter((e) =>
                  filterOption === 'passed' ? e.deployment_allowed : !e.deployment_allowed
                ).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Evaluations Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Model
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                Gate
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                Score
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Dimensions
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Date
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {filteredEvaluations.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                  No evaluations found
                </td>
              </tr>
            ) : (
              filteredEvaluations.map((evaluation) => (
                <EvaluationRow
                  key={evaluation.id}
                  evaluation={evaluation}
                  onClick={() => setSelectedEvaluation(evaluation)}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default FAVESDashboard;
