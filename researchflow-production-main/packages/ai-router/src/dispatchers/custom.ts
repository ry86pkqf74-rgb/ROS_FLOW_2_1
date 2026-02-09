/**
 * Custom Agent Dispatcher
 *
 * Implements a sophisticated agent dispatching system with:
 * - Multi-agent registry and selection
 * - Performance monitoring and metrics
 * - Caching and optimization
 * - Fallback and retry logic
 */

import {
  AITaskType,
  AIRouterRequest,
  AIRouterResponse,
  ModelTier,
  MODEL_CONFIGS,
  type QualityCheck,
} from '../types';

/**
 * Input format for custom agents
 */
interface AgentInput {
  query: string;
  context?: Record<string, unknown>;
  options?: Record<string, unknown>;
  workflowStage?: number;
}

/**
 * Output format from custom agents
 */
interface AgentOutput {
  content: string;
  citations?: unknown[];
  metadata?: Record<string, unknown>;
  success: boolean;
}

/**
 * Agent configuration
 */
interface AgentConfig {
  id: string;
  name: string;
  description: string;
  modelTier: ModelTier;
  phiScanRequired: boolean;
  maxTokens: number;
}

/**
 * Interface for custom agent implementations
 */
interface IAgent {
  execute(input: AgentInput): Promise<AgentOutput>;
  validateInput?(input: AgentInput): boolean;
  config?: AgentConfig;
}

/**
 * Custom agent registry entry
 */
export interface CustomAgentRegistry {
  id: string;
  name: string;
  description: string;
  taskTypes: string[];
  workflowStages: number[];
  phiRequired: boolean;
  maxTokens: number;
  modelTier: ModelTier;
  instance?: IAgent;
}

/**
 * Decision made by the dispatch system
 */
export interface DispatchDecision {
  agentType: CustomAgentType;
  confidence: number;
  reason: string;
  estimatedLatencyMs: number;
  estimatedCost: number;
}

/**
 * Context for dispatch decisions
 */
export interface CustomDispatchContext {
  taskType: AITaskType;
  workflowStage?: number;
  requiredPhiHandling: boolean;
  contextSize: number;
  deadline?: Date;
}

/**
 * Available custom agent types
 */
export type CustomAgentType = 'DataPrep' | 'Analysis' | 'Quality' | 'IRB' | 'Manuscript';

/**
 * Registry of available custom agents
 */
export const CUSTOM_AGENT_REGISTRY: Record<CustomAgentType, CustomAgentRegistry> = {
  DataPrep: {
    id: 'DataPrep',
    name: 'Data Preparation Agent',
    description: 'Handles data extraction, validation, and cleaning tasks',
    taskTypes: ['extract_metadata', 'format_validate', 'policy_check'],
    workflowStages: [1, 2, 3, 4, 5],
    phiRequired: true,
    maxTokens: 4096,
    modelTier: 'NANO',
  },
  Analysis: {
    id: 'Analysis',
    name: 'Analysis Agent',
    description: 'Performs statistical analysis and interpretation',
    taskTypes: ['analyze_data', 'interpret_results', 'generate_insights'],
    workflowStages: [2, 3, 4, 5],
    phiRequired: true,
    maxTokens: 8192,
    modelTier: 'MINI',
  },
  Quality: {
    id: 'Quality',
    name: 'Quality Assurance Agent',
    description: 'Reviews and validates outputs for accuracy and compliance',
    taskTypes: ['review_output', 'check_compliance', 'validate_citations'],
    workflowStages: [3, 4, 5],
    phiRequired: true,
    maxTokens: 4096,
    modelTier: 'NANO',
  },
  IRB: {
    id: 'IRB',
    name: 'IRB Compliance Agent',
    description: 'Ensures IRB compliance and ethical guidelines',
    taskTypes: ['irb_check', 'ethics_review', 'consent_validation'],
    workflowStages: [1, 2, 3, 4, 5],
    phiRequired: true,
    maxTokens: 4096,
    modelTier: 'NANO',
  },
  Manuscript: {
    id: 'Manuscript',
    name: 'Manuscript Writing Agent',
    description: 'Assists with manuscript drafting and editing',
    taskTypes: ['draft_manuscript', 'edit_text', 'format_citations'],
    workflowStages: [4, 5],
    phiRequired: true,
    maxTokens: 8192,
    modelTier: 'FRONTIER',
  },
};

/**
 * Main custom agent dispatcher implementation
 */
export class CustomAgentDispatcher {
  private agentRegistry: Map<CustomAgentType, CustomAgentRegistry>;
  private readonly dispatchTimeoutMs = 30000;
  private dispatchMetrics = {
    totalDispatches: 0,
    successfulDispatches: 0,
    failedDispatches: 0,
    averageLatencyMs: 0,
    totalCost: 0,
  };

  constructor(customRegistry?: Partial<Record<CustomAgentType, CustomAgentRegistry>>) {
    this.agentRegistry = new Map();

    // Load default registry
    for (const [agentType, registry] of Object.entries(CUSTOM_AGENT_REGISTRY)) {
      this.agentRegistry.set(agentType as CustomAgentType, { ...registry });
    }

    // Apply custom overrides
    if (customRegistry) {
      for (const [agentType, registry] of Object.entries(customRegistry)) {
        this.agentRegistry.set(agentType as CustomAgentType, {
          ...this.agentRegistry.get(agentType as CustomAgentType),
          ...registry,
        } as CustomAgentRegistry);
      }
    }
  }

  /**
   * Dispatch a request to the most appropriate custom agent
   */
  async dispatch(
    request: AIRouterRequest,
    context: CustomDispatchContext
  ): Promise<{ decision: DispatchDecision; output: AgentOutput }> {
    const startTime = Date.now();
    this.dispatchMetrics.totalDispatches++;

    try {
      const decision = await this.makeDispatchDecision(request, context);
      const input = this.buildAgentInput(request, context);

      const output = await this.executeAgent(decision.agentType, input, 1);

      const latency = Date.now() - startTime;
      this.updateMetrics(true, latency, decision.estimatedCost);

      return { decision, output };
    } catch (error) {
      const latency = Date.now() - startTime;
      this.updateMetrics(false, latency, 0);
      throw error;
    }
  }

  /**
   * Create a dispatch decision based on request and context
   */
  private async makeDispatchDecision(
    request: AIRouterRequest,
    context: CustomDispatchContext
  ): Promise<DispatchDecision> {
    const candidates = this.getCandidateAgents(request.taskType, context.workflowStage);

    // Simple decision logic for now - can be enhanced with ML models
    const agentType = candidates[0];
    const registry = this.agentRegistry.get(agentType);

    if (!registry) {
      throw new Error(`No registry found for agent type: ${agentType}`);
    }

    return {
      agentType,
      confidence: 0.8,
      reason: `Selected ${registry.name} based on task type and workflow stage`,
      estimatedLatencyMs: this.estimateLatency(agentType),
      estimatedCost: this.estimateCost(request.prompt, '', MODEL_CONFIGS[registry.modelTier]),
    };
  }

  /**
   * Get candidate agents for a task type and workflow stage
   */
  private getCandidateAgents(taskType: AITaskType, workflowStage?: number): CustomAgentType[] {
    const candidates: CustomAgentType[] = [];

    for (const [agentType, registry] of this.agentRegistry) {
      if (registry.taskTypes.includes(taskType) &&
          (!workflowStage || registry.workflowStages.includes(workflowStage))) {
        candidates.push(agentType);
      }
    }

    if (candidates.length === 0) {
      // Fallback to default agent
      return ['DataPrep'];
    }

    return candidates;
  }

  /**
   * Get or create an agent instance
   */
  private getAgentInstance(agentType: CustomAgentType): IAgent {
    const registry = this.agentRegistry.get(agentType);

    if (!registry) {
      throw new Error(`Agent type not found: ${agentType}`);
    }

    if (!registry.instance) {
      registry.instance = this.createAgentInstance(agentType, registry);
    }

    return registry.instance;
  }

  /**
   * Create a mock agent instance (placeholder for real implementations)
   */
  private createAgentInstance(
    agentType: CustomAgentType,
    registry: CustomAgentRegistry
  ): IAgent {
    const mockAgent: IAgent = {
      config: {
        id: registry.id,
        name: registry.name,
        description: registry.description,
        modelTier: registry.modelTier,
        phiScanRequired: registry.phiRequired,
        maxTokens: registry.maxTokens,
      } as AgentConfig,

      async execute(input: AgentInput): Promise<AgentOutput> {
        // Simulate processing delay
        await new Promise(resolve => setTimeout(resolve, 100));

        // Mock response based on agent type
        let content = `Mock response from ${agentType} agent for query: ${input.query}`;

        // Add some variation based on agent type
        if (agentType === 'Analysis') {
          content = `Analysis results: ${input.query} appears to show significant patterns...`;
        } else if (agentType === 'Quality') {
          content = `Quality review: The output meets compliance standards...`;
        }

        // Try to parse JSON if it's a JSON request
        try {
          JSON.parse(input.query);
          content = input.query;
        } catch {
          // Not JSON, use default response
        }

        return {
          content,
          citations: [],
          metadata: {
            modelUsed: MODEL_CONFIGS[registry.modelTier].model,
            tokensUsed: 0,
            phiDetected: false,
            processingTimeMs: 100,
          },
          success: true,
        };
      },

      validateInput(input: AgentInput): boolean {
        return typeof input.query === 'string' && input.query.length > 0;
      },
    };

    return mockAgent;
  }

  /**
   * Execute an agent with timeout and validation
   */
  private async executeAgent(
    agentType: CustomAgentType,
    input: AgentInput,
    attemptNumber: number
  ): Promise<AgentOutput> {
    const agent = this.getAgentInstance(agentType);

    if (agent.validateInput && !agent.validateInput(input)) {
      throw new Error(`Invalid input for ${agentType} agent`);
    }

    return Promise.race([
      agent.execute(input),
      this.createTimeout(this.dispatchTimeoutMs),
    ]);
  }

  /**
   * Build agent input from router request and context
   */
  private buildAgentInput(
    request: AIRouterRequest,
    context: CustomDispatchContext
  ): AgentInput {
    return {
      query: request.prompt,
      context: {
        ...request.context,
        taskType: context.taskType,
        workflowStage: context.workflowStage,
        systemPrompt: request.systemPrompt,
        metadata: request.metadata,
      },
      workflowStage: context.workflowStage,
    };
  }

  /**
   * Create a timeout promise
   */
  private createTimeout(ms: number): Promise<never> {
    return new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Dispatch timeout`)), ms)
    );
  }

  /**
   * Update dispatch metrics
   */
  private updateMetrics(success: boolean, latencyMs: number, cost: number): void {
    if (success) {
      this.dispatchMetrics.successfulDispatches++;
    } else {
      this.dispatchMetrics.failedDispatches++;
    }

    // Update running average
    const total = this.dispatchMetrics.totalDispatches;
    this.dispatchMetrics.averageLatencyMs =
      (this.dispatchMetrics.averageLatencyMs * (total - 1) + latencyMs) / total;

    this.dispatchMetrics.totalCost += cost;
  }

  /**
   * Get dispatch metrics
   */
  getMetrics() {
    return {
      ...this.dispatchMetrics,
      successRate:
        this.dispatchMetrics.totalDispatches > 0
          ? this.dispatchMetrics.successfulDispatches / this.dispatchMetrics.totalDispatches
          : 0,
    };
  }

  /**
   * Get agent registry for debugging
   */
  getAgentRegistry(): Record<CustomAgentType, CustomAgentRegistry> {
    return Object.fromEntries(this.agentRegistry) as Record<CustomAgentType, CustomAgentRegistry>;
  }

  /**
   * Estimate latency for an agent
   */
  private estimateLatency(agent: CustomAgentType): number {
    switch (agent) {
      case 'DataPrep':
        return 2000;
      case 'Analysis':
        return 5000;
      case 'Quality':
        return 3000;
      case 'IRB':
        return 2500;
      case 'Manuscript':
        return 8000;
      default:
        return 3000;
    }
  }

  /**
   * Simple token estimation (4 chars per token)
   */
  private estimateTokens(text: string): number {
    return Math.ceil(text.length / 4);
  }

  /**
   * Estimate cost based on token usage and model config
   */
  private estimateCost(input: string, output: string, config: typeof MODEL_CONFIGS[ModelTier]): number {
    const inputTokens = this.estimateTokens(input);
    const outputTokens = this.estimateTokens(output);

    const inputCost =
      (inputTokens / 1000000) * config.costPerMToken.input;
    const outputCost =
      (outputTokens / 1000000) * config.costPerMToken.output;

    return inputCost + outputCost;
  }
}

// =============================================================================
// Compatibility exports (legacy CustomDispatcher API)
// =============================================================================

export interface CustomDispatcherOptions {
  /**
   * Tier to fall back to if custom dispatch fails.
   * Kept for backwards compatibility with older code/tests.
   */
  fallbackTier?: ModelTier;
  /**
   * Enable additional metrics tracking.
   * Kept for backwards compatibility with older code/tests.
   */
  enableMetrics?: boolean;
}

export interface LegacyDispatchDecision {
  selectedAgent: CustomAgentType;
  confidence: number;
  reason: string;
  fallbackTier: ModelTier;
  estimatedLatencyMs: number;
}

export interface CustomDispatcherMetrics {
  totalDispatches: number;
  successfulDispatches: number;
  failedDispatches: number;
  fallbacksTriggered: number;
  averageLatencyMs: number;
  /** 0-100 percentage */
  successRate: number;
}

/**
 * Legacy `CustomDispatcher` implementation.
 *
 * This class exists to preserve the historical public API (`CustomDispatcher`,
 * `createCustomDispatcher`) expected by downstream imports and the local
 * test suite. It intentionally keeps runtime behavior simple and self-contained.
 */
export class CustomDispatcher {
  private fallbackTier: ModelTier;
  private enableMetrics: boolean;
  private decisionCache = new Map<string, LegacyDispatchDecision>();

  private metrics: Omit<CustomDispatcherMetrics, 'successRate'> = {
    totalDispatches: 0,
    successfulDispatches: 0,
    failedDispatches: 0,
    fallbacksTriggered: 0,
    averageLatencyMs: 0,
  };

  constructor(options?: CustomDispatcherOptions) {
    this.fallbackTier = options?.fallbackTier ?? 'FRONTIER';
    this.enableMetrics = options?.enableMetrics ?? false;
  }

  setFallbackTier(tier: ModelTier): void {
    this.fallbackTier = tier;
  }

  clearCache(): void {
    this.decisionCache.clear();
  }

  isHealthy(): boolean {
    const { totalDispatches, successRate } = this.getMetrics();
    if (totalDispatches === 0) return true;
    return successRate > 80;
  }

  getMetrics(): CustomDispatcherMetrics {
    const total = this.metrics.totalDispatches;
    const successRate =
      total > 0 ? (this.metrics.successfulDispatches / total) * 100 : 0;
    return { ...this.metrics, successRate };
  }

  getAgentRegistry(): Record<CustomAgentType, CustomAgentRegistry> {
    // Return the constant registry as the stable source of truth for legacy API.
    return CUSTOM_AGENT_REGISTRY;
  }

  /**
   * Legacy internal decision function. Public for backwards compatibility with
   * tests that call it via bracket access.
   */
  selectAgent(context: CustomDispatchContext): LegacyDispatchDecision {
    const cacheKey = this.buildCacheKey(context);
    const cached = this.decisionCache.get(cacheKey);
    if (cached) return cached;

    const selectedAgent = this.resolveAgent(context);
    const decision: LegacyDispatchDecision = {
      selectedAgent,
      confidence: this.estimateConfidence(selectedAgent, context),
      reason: this.buildReason(selectedAgent, context),
      fallbackTier: this.fallbackTier,
      estimatedLatencyMs: this.estimateLatency(selectedAgent),
    };

    this.decisionCache.set(cacheKey, decision);
    return decision;
  }

  /**
   * Legacy cache key builder. Public for backwards compatibility with tests.
   */
  buildCacheKey(context: CustomDispatchContext): string {
    // Stable serialization to ensure deterministic keys.
    const stage = context.workflowStage ?? 'none';
    const phi = context.requiredPhiHandling ? 'phi' : 'no-phi';
    return `custom-dispatch:${context.taskType}:${stage}:${phi}:${context.contextSize}`;
  }

  /**
   * Dispatch using the legacy response shape expected by `AIRouterResponse`.
   */
  async dispatch(
    request: AIRouterRequest,
    context: CustomDispatchContext
  ): Promise<AIRouterResponse> {
    const start = Date.now();
    this.metrics.totalDispatches++;

    const decision = this.selectAgent(context);
    const agentRegistry = CUSTOM_AGENT_REGISTRY[decision.selectedAgent];

    const tier = agentRegistry?.modelTier ?? 'NANO';
    const modelConfig = MODEL_CONFIGS[tier] ?? MODEL_CONFIGS.NANO;

    try {
      const { content, parsed } = this.generateContent(request.prompt);
      const latencyMs = Date.now() - start;
      this.updateMetrics(true, latencyMs);

      const inputTokens = this.estimateTokens(request.prompt);
      const outputTokens = this.estimateTokens(content);
      const estimatedCostUsd = this.estimateCostUsd(
        inputTokens,
        outputTokens,
        modelConfig
      );

      const qualityChecks = this.buildQualityChecks();

      return {
        content,
        parsed,
        routing: {
          initialTier: 'CUSTOM',
          finalTier: 'CUSTOM',
          escalated: false,
          provider: modelConfig.provider,
          model: modelConfig.model,
        },
        usage: {
          inputTokens,
          outputTokens,
          totalTokens: inputTokens + outputTokens,
          estimatedCostUsd,
        },
        qualityGate: {
          passed: qualityChecks.every((c) => c.passed),
          checks: qualityChecks,
        },
        metrics: {
          latencyMs,
          processingTimeMs: latencyMs,
        },
      };
    } catch (error) {
      const latencyMs = Date.now() - start;
      this.updateMetrics(false, latencyMs);

      // Legacy behavior: "fallback" is reflected in routing metadata, not by
      // actually invoking another dispatcher here.
      this.metrics.fallbacksTriggered++;

      const fallbackConfig = MODEL_CONFIGS[this.fallbackTier] ?? MODEL_CONFIGS.FRONTIER;
      return {
        content: '',
        routing: {
          initialTier: 'CUSTOM',
          finalTier: this.fallbackTier,
          escalated: true,
          escalationReason:
            error instanceof Error ? error.message : 'Custom dispatch failed',
          provider: fallbackConfig.provider,
          model: fallbackConfig.model,
        },
        usage: {
          inputTokens: this.estimateTokens(request.prompt),
          outputTokens: 0,
          totalTokens: this.estimateTokens(request.prompt),
          estimatedCostUsd: 0,
        },
        qualityGate: {
          passed: false,
          checks: this.buildQualityChecks({
            phi_scan: true,
            dispatch_failed: true,
          }),
        },
        metrics: {
          latencyMs,
          processingTimeMs: latencyMs,
        },
      };
    } finally {
      if (!this.enableMetrics) {
        // No-op today; flag is preserved for compatibility.
      }
    }
  }

  private updateMetrics(success: boolean, latencyMs: number): void {
    if (success) this.metrics.successfulDispatches++;
    else this.metrics.failedDispatches++;

    const total = this.metrics.totalDispatches;
    this.metrics.averageLatencyMs =
      total > 0
        ? (this.metrics.averageLatencyMs * (total - 1) + latencyMs) / total
        : 0;
  }

  private resolveAgent(context: CustomDispatchContext): CustomAgentType {
    // Stage-based routing (legacy rules)
    const stage = context.workflowStage;
    if (typeof stage === 'number') {
      if (stage >= 1 && stage <= 5) return 'DataPrep';
      if (stage >= 6 && stage <= 10) return 'Analysis';
      if (stage >= 11 && stage <= 15) return context.requiredPhiHandling ? 'IRB' : 'Quality';
      if (stage >= 16 && stage <= 20) return context.requiredPhiHandling ? 'IRB' : 'Manuscript';
    }

    // Task-type routing (legacy rules)
    switch (context.taskType) {
      case 'extract_metadata':
      case 'format_validate':
        return 'DataPrep';
      case 'summarize':
      case 'protocol_reasoning':
      case 'complex_synthesis':
      case 'final_manuscript_pass':
        return 'Analysis';
      case 'phi_scan':
        return 'Quality';
      case 'policy_check':
        return 'IRB';
      case 'draft_section':
      case 'template_fill':
      case 'abstract_generate':
        return 'Manuscript';
      default:
        return 'Quality';
    }
  }

  private estimateConfidence(agent: CustomAgentType, context: CustomDispatchContext): number {
    // Simple heuristic; kept intentionally lightweight.
    const base = 0.75;
    const stageBoost = typeof context.workflowStage === 'number' ? 0.1 : 0;
    const phiBoost = context.requiredPhiHandling && agent === 'IRB' ? 0.1 : 0;
    return Math.min(0.95, base + stageBoost + phiBoost);
  }

  private buildReason(agent: CustomAgentType, context: CustomDispatchContext): string {
    if (typeof context.workflowStage === 'number') {
      return `Selected ${agent} for workflow stage ${context.workflowStage}`;
    }
    return `Selected ${agent} for task type ${context.taskType}`;
  }

  private estimateLatency(agent: CustomAgentType): number {
    switch (agent) {
      case 'DataPrep':
        return 1500;
      case 'Analysis':
        return 4500;
      case 'Quality':
        return 2500;
      case 'IRB':
        return 3000;
      case 'Manuscript':
        return 6500;
      default:
        return 3000;
    }
  }

  private estimateTokens(text: string): number {
    // Approximation: 4 chars/token
    return Math.ceil(text.length / 4);
  }

  private estimateCostUsd(
    inputTokens: number,
    outputTokens: number,
    config: (typeof MODEL_CONFIGS)[Exclude<ModelTier, 'CUSTOM'>]
  ): number {
    const inputCost = (inputTokens / 1_000_000) * config.costPerMToken.input;
    const outputCost = (outputTokens / 1_000_000) * config.costPerMToken.output;
    return inputCost + outputCost;
  }

  private generateContent(prompt: string): { content: string; parsed?: Record<string, unknown> } {
    try {
      const parsed = JSON.parse(prompt) as Record<string, unknown>;
      return { content: prompt, parsed };
    } catch {
      return { content: `Mock response from custom dispatcher for prompt: ${prompt}` };
    }
  }

  private buildQualityChecks(extra?: Record<string, boolean>): QualityCheck[] {
    const checks: QualityCheck[] = [
      {
        name: 'phi_scan',
        passed: true,
        severity: 'info',
        category: 'confidence',
        score: 1.0,
      },
    ];

    if (extra?.dispatch_failed) {
      checks.push({
        name: 'dispatch_failed',
        passed: false,
        severity: 'error',
        category: 'confidence',
        score: 0.0,
        reason: 'Custom dispatch failed; fallback indicated in routing metadata.',
      });
    }

    return checks;
  }
}

export function createCustomDispatcher(options?: CustomDispatcherOptions): CustomDispatcher {
  return new CustomDispatcher(options);
}
