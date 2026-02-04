/**
 * Cost Envelope Utility (Bundle B - Cost Instrumentation)
 *
 * Provides utilities for tracking AI inference costs and setting
 * standardized response headers for cost visibility in E2E tests.
 *
 * Headers emitted:
 * - X-Ros-Provider: AI provider (openai, anthropic, mercury, etc.)
 * - X-Ros-Model: Model used for inference
 * - X-Ros-Tokens-In: Input tokens consumed
 * - X-Ros-Tokens-Out: Output tokens generated
 * - X-Ros-Tokens-Cached: Cached tokens (if applicable)
 * - X-Ros-Latency-Ms: Inference latency in milliseconds
 * - X-Ros-Cost-Usd: Estimated cost in USD
 */

import type { Response } from 'express';

// =============================================================================
// Types
// =============================================================================

export interface CostEnvelope {
  provider: string;
  model: string;
  tokensIn: number;
  tokensOut: number;
  tokensCached?: number;
  latencyMs: number;
  costUsd: number;
}

export interface ModelPricing {
  inputPerMToken: number;
  outputPerMToken: number;
  cachedPerMToken?: number;
}

// =============================================================================
// Model Pricing Table (USD per million tokens)
// =============================================================================

const MODEL_PRICING: Record<string, ModelPricing> = {
  // OpenAI models
  'gpt-4': { inputPerMToken: 30.0, outputPerMToken: 60.0 },
  'gpt-4-turbo': { inputPerMToken: 10.0, outputPerMToken: 30.0 },
  'gpt-4-turbo-preview': { inputPerMToken: 10.0, outputPerMToken: 30.0 },
  'gpt-4o': { inputPerMToken: 5.0, outputPerMToken: 15.0 },
  'gpt-4o-mini': { inputPerMToken: 0.15, outputPerMToken: 0.6 },
  'gpt-3.5-turbo': { inputPerMToken: 0.5, outputPerMToken: 1.5 },

  // Anthropic models
  'claude-3-opus-20240229': { inputPerMToken: 15.0, outputPerMToken: 75.0 },
  'claude-3-sonnet-20240229': { inputPerMToken: 3.0, outputPerMToken: 15.0 },
  'claude-3-haiku-20240307': { inputPerMToken: 0.25, outputPerMToken: 1.25 },
  'claude-3-5-sonnet-20241022': { inputPerMToken: 3.0, outputPerMToken: 15.0 },
  'claude-sonnet-4-5-20250929': { inputPerMToken: 3.0, outputPerMToken: 15.0 },
  'claude-opus-4-5-20251101': { inputPerMToken: 15.0, outputPerMToken: 75.0 },
  'claude-haiku-4-5-20251001': { inputPerMToken: 0.25, outputPerMToken: 1.25 },

  // Mercury/Inception Labs models (ultra-fast diffusion LLM)
  'mercury-coder-small': { inputPerMToken: 0.1, outputPerMToken: 0.4, cachedPerMToken: 0.025 },
  'mercury-coder': { inputPerMToken: 0.25, outputPerMToken: 1.0, cachedPerMToken: 0.0625 },

  // Ollama/local models (free)
  'llama3': { inputPerMToken: 0, outputPerMToken: 0 },
  'llama3.1': { inputPerMToken: 0, outputPerMToken: 0 },
  'llama3.2': { inputPerMToken: 0, outputPerMToken: 0 },
  'mistral': { inputPerMToken: 0, outputPerMToken: 0 },
  'codellama': { inputPerMToken: 0, outputPerMToken: 0 },
  'phi3': { inputPerMToken: 0, outputPerMToken: 0 },

  // Default fallback
  default: { inputPerMToken: 1.0, outputPerMToken: 3.0 },
};

// =============================================================================
// Provider Detection
// =============================================================================

export function detectProvider(model: string): string {
  const modelLower = model.toLowerCase();

  if (modelLower.includes('gpt-') || modelLower.includes('o1-')) {
    return 'openai';
  }
  if (modelLower.includes('claude')) {
    return 'anthropic';
  }
  if (modelLower.includes('mercury')) {
    return 'mercury';
  }
  if (
    modelLower.includes('llama') ||
    modelLower.includes('mistral') ||
    modelLower.includes('phi') ||
    modelLower.includes('codellama')
  ) {
    return 'ollama';
  }

  return 'unknown';
}

// =============================================================================
// Cost Calculation
// =============================================================================

export function calculateCost(
  model: string,
  tokensIn: number,
  tokensOut: number,
  tokensCached?: number
): number {
  const pricing = MODEL_PRICING[model] || MODEL_PRICING.default;

  let cost = (tokensIn / 1_000_000) * pricing.inputPerMToken;
  cost += (tokensOut / 1_000_000) * pricing.outputPerMToken;

  if (tokensCached && pricing.cachedPerMToken) {
    // Cached tokens reduce input cost
    cost -= (tokensCached / 1_000_000) * (pricing.inputPerMToken - pricing.cachedPerMToken);
  }

  return Math.max(0, cost);
}

// =============================================================================
// Header Setting
// =============================================================================

/**
 * Set X-Ros-* headers on the response for cost tracking
 */
export function setCostHeaders(res: Response, envelope: CostEnvelope): void {
  res.setHeader('X-Ros-Provider', envelope.provider);
  res.setHeader('X-Ros-Model', envelope.model);
  res.setHeader('X-Ros-Tokens-In', String(envelope.tokensIn));
  res.setHeader('X-Ros-Tokens-Out', String(envelope.tokensOut));

  if (envelope.tokensCached !== undefined && envelope.tokensCached > 0) {
    res.setHeader('X-Ros-Tokens-Cached', String(envelope.tokensCached));
  }

  res.setHeader('X-Ros-Latency-Ms', String(Math.round(envelope.latencyMs)));
  res.setHeader('X-Ros-Cost-Usd', envelope.costUsd.toFixed(6));
}

/**
 * Create a cost envelope from AI response data
 */
export function createCostEnvelope(params: {
  model: string;
  tokensIn: number;
  tokensOut: number;
  tokensCached?: number;
  latencyMs: number;
  provider?: string;
  costUsd?: number;
}): CostEnvelope {
  const provider = params.provider || detectProvider(params.model);
  const costUsd =
    params.costUsd ??
    calculateCost(params.model, params.tokensIn, params.tokensOut, params.tokensCached);

  return {
    provider,
    model: params.model,
    tokensIn: params.tokensIn,
    tokensOut: params.tokensOut,
    tokensCached: params.tokensCached,
    latencyMs: params.latencyMs,
    costUsd,
  };
}

/**
 * Convenience function to set cost headers from AI response
 */
export function attachCostEnvelope(
  res: Response,
  params: {
    model: string;
    tokensIn: number;
    tokensOut: number;
    tokensCached?: number;
    latencyMs: number;
    provider?: string;
    costUsd?: number;
  }
): CostEnvelope {
  const envelope = createCostEnvelope(params);
  setCostHeaders(res, envelope);
  return envelope;
}

// =============================================================================
// Cost Aggregation (for tests)
// =============================================================================

export interface CostReport {
  totalCostUsd: number;
  totalTokensIn: number;
  totalTokensOut: number;
  totalLatencyMs: number;
  callCount: number;
  costByProvider: Record<string, number>;
  costByModel: Record<string, number>;
  calls: CostEnvelope[];
}

export function createEmptyCostReport(): CostReport {
  return {
    totalCostUsd: 0,
    totalTokensIn: 0,
    totalTokensOut: 0,
    totalLatencyMs: 0,
    callCount: 0,
    costByProvider: {},
    costByModel: {},
    calls: [],
  };
}

export function aggregateCost(report: CostReport, envelope: CostEnvelope): CostReport {
  report.totalCostUsd += envelope.costUsd;
  report.totalTokensIn += envelope.tokensIn;
  report.totalTokensOut += envelope.tokensOut;
  report.totalLatencyMs += envelope.latencyMs;
  report.callCount++;

  report.costByProvider[envelope.provider] =
    (report.costByProvider[envelope.provider] || 0) + envelope.costUsd;

  report.costByModel[envelope.model] =
    (report.costByModel[envelope.model] || 0) + envelope.costUsd;

  report.calls.push(envelope);

  return report;
}

export default {
  setCostHeaders,
  createCostEnvelope,
  attachCostEnvelope,
  calculateCost,
  detectProvider,
  createEmptyCostReport,
  aggregateCost,
};
