/**
 * AI Router Package
 *
 * Cost-optimized multi-model routing with quality gating and PHI protection.
 *
 * @packageDocumentation
 */
/* eslint-disable @typescript-eslint/no-require-imports -- dynamic lazy loading */

// Types
export * from './src/types';

// Services
export { ModelRouterService, getModelRouter } from './src/model-router.service';
export { QualityGateService, getQualityGate } from './src/quality-gate.service';
export type { QualityGateResult } from './src/quality-gate.service';
export { PhiGateService, getPhiGate } from './src/phi-gate.service';
export {
  PromptCacheService,
  getPromptCache,
  initializeDefaultTemplates,
  DEFAULT_TEMPLATES,
} from './src/prompt-cache.service';
export type { StructuredPrompt, PromptTemplate } from './src/prompt-cache.service';

// Notion AI Logger
export {
  NotionAILogger,
  getNotionLogger,
  logAIUsage,
  shutdownLogger,
  type AIUsageLogEntry,
  type NotionLoggerConfig,
  type BudgetStatus,
} from './src/notion';

// Wrapped Providers with Logging
export {
  ClaudeProvider,
  getClaudeProvider,
  claudeComplete,
  OpenAIProvider,
  getOpenAIProvider,
  openaiComplete,
  openaiCompleteJSON,
  type ClaudeRequestOptions,
  type ClaudeResponse,
  type OpenAIRequestOptions,
  type OpenAIResponse,
  // Qwen Local Provider
  QwenLocalProvider,
  LOCAL_ELIGIBLE_TASKS,
  LOCAL_BLOCKED_TASKS,
  shouldUseLocal,
  type QwenLocalConfig,
  type QwenCompletionRequest,
  type QwenCompletionResponse,
  // Mercury Coder Provider (Inception Labs - Ultra-fast Diffusion LLM)
  MercuryCoderProvider,
  getMercuryCoderProvider,
  type MercuryCoderRequestOptions,
  type MercuryResponse,
  type MercuryEndpoint,
  type MercuryModel,
  type MercuryChatMessage,
  type MercuryFIMRequest,
  type MercuryApplyRequest,
  type MercuryEditRequest,
  type MercuryStructuredOutputSchema,
} from './src/providers';

// Agent Roster
export {
  TOOL_REGISTRY,
  AGENT_ROSTER,
  getAgentForTaskType,
  getHighRiskAgents,
  getPhiSafeTools,
  getToolsByCostTier,
  type AITool,
  type ToolCapabilities,
  type AgentRole,
  type OrchestratorAgent,
} from './src/agents';

// Watermark Service
export {
  WatermarkService,
  getWatermarkService,
  isWatermarkingEnabled,
  type WatermarkMetadata,
  type WatermarkConfig,
  type WatermarkVerification,
} from './src/watermark.service';

// Middleware - Trace Emitter for Insights
export {
  emitTraceEvent,
  withTraceEmitter,
  checkTraceEmitterHealth,
  shutdownTraceEmitter,
  type TraceEmitterOptions,
  type TraceContext,
  // NOTE: AIRouterResponse is already exported from ./src/types via export *.
  // The middleware's AIRouterResponse<T> is a different interface; import it
  // directly from '@researchflow/ai-router/middleware' if needed.
} from './src/middleware';

// Package version
export const AI_ROUTER_VERSION = '2.2.0';

/**
 * Quick start helper - creates a configured router instance
 */
export function createRouter(config?: {
  anthropicApiKey?: string;
  openaiApiKey?: string;
  mercuryApiKey?: string;
  defaultTier?: 'LOCAL' | 'NANO' | 'MINI' | 'FRONTIER' | 'MERCURY';
  escalationEnabled?: boolean;
  maxEscalations?: number;
  localModelEnabled?: boolean;
  localModelEndpoint?: string;
  localModelName?: string;
}) {
  const { getModelRouter } = require('./src/model-router.service');
  return getModelRouter(config);
}

/**
 * Default export for convenience
 */
export default {
  createRouter,
  getModelRouter: () => require('./src/model-router.service').getModelRouter(),
  getQualityGate: () => require('./src/quality-gate.service').getQualityGate(),
  getPhiGate: () => require('./src/phi-gate.service').getPhiGate(),
  getPromptCache: () => require('./src/prompt-cache.service').getPromptCache(),
  getNotionLogger: () => require('./src/notion').getNotionLogger(),
  getClaudeProvider: () => require('./src/providers').getClaudeProvider(),
  getOpenAIProvider: () => require('./src/providers').getOpenAIProvider(),
  getMercuryCoderProvider: () => require('./src/providers').getMercuryCoderProvider(),
};
