/**
 * AI Router Bridge for LangGraph Agent Integration
 *
 * This bridge connects LangGraph agents (Python worker) to the
 * AI Router (TypeScript orchestrator) for LLM calls.
 *
 * Features:
 * - Model tier selection (Economy/Standard/Premium)
 * - PHI-compliant model routing
 * - Cost tracking and budget management
 * - Streaming and batch support
 * - Error handling with fallbacks
 */

import axios from 'axios';
import * as z from 'zod';

// Validation schemas — single source of truth for tier values
const ModelTierSchema = z.enum(['LOCAL', 'NANO', 'MINI', 'FRONTIER', 'CUSTOM']);
export type ModelTier = z.infer<typeof ModelTierSchema>;

const ModelOptionsSchema = z.object({
  taskType: z.string(),
  stageId: z.number().optional(),
  modelTier: ModelTierSchema.optional(),
  governanceMode: z.enum(['DEMO', 'LIVE']).optional(),
  requirePhiCompliance: z.boolean().optional(),
  budgetLimit: z.number().positive().optional(),
  maxTokens: z.number().positive().optional(),
  temperature: z.number().min(0).max(2).optional(),
  streamResponse: z.boolean().optional(),
});

// Derive ModelOptions from the Zod schema — single source of truth
export type ModelOptions = z.infer<typeof ModelOptionsSchema>;

export interface LLMResponse {
  content: string;
  usage: {
    totalTokens: number;
    promptTokens: number;
    completionTokens: number;
  };
  cost: {
    total: number;
    input: number;
    output: number;
  };
  model: string;
  tier: string;
  finishReason: string;
  metadata?: Record<string, any>;
}

export interface BridgeConfig {
  orchestratorUrl: string;
  defaultTier: ModelTier;
  phiCompliantOnly: boolean;
  maxRetries: number;
  timeoutMs: number;
  costTrackingEnabled: boolean;
  streamingEnabled: boolean;
}

// Typed response from the AI Router routing endpoint
const RoutingApiResponseSchema = z.object({
  selectedTier: ModelTierSchema,
  model: z.string(),
  costEstimate: z.object({ total: z.number() }),
});

// ModelOptionsSchema and ModelOptions type are defined above the interfaces

const LLMResponseSchema = z.object({
  content: z.string(),
  usage: z.object({
    totalTokens: z.number(),
    promptTokens: z.number(),
    completionTokens: z.number(),
  }),
  cost: z.object({
    total: z.number(),
    input: z.number(),
    output: z.number(),
  }),
  model: z.string(),
  tier: z.string(),
  finishReason: z.string(),
  metadata: z.record(z.any()).optional(),
});

/**
 * AI Router Bridge for LangGraph Agents
 *
 * Handles communication between Python LangGraph agents and
 * the TypeScript AI Router service.
 */
export class AIRouterBridge {
  private config: BridgeConfig;
  private totalCost: number = 0;
  private requestCount: number = 0;

  constructor(config: Partial<BridgeConfig> = {}) {
    this.config = {
      orchestratorUrl: config.orchestratorUrl || 'http://localhost:3001',
      defaultTier: config.defaultTier || 'MINI',
      phiCompliantOnly: config.phiCompliantOnly ?? true,
      maxRetries: config.maxRetries || 3,
      timeoutMs: config.timeoutMs || 30000,
      costTrackingEnabled: config.costTrackingEnabled ?? true,
      streamingEnabled: config.streamingEnabled ?? false,
      ...config,
    };
  }

  /**
   * Single LLM invocation
   */
  async invoke(
    prompt: string,
    options: ModelOptions = { taskType: 'general' }
  ): Promise<LLMResponse> {
    const validatedOptions = ModelOptionsSchema.parse(options);

    // Step 1: Get routing recommendation
    const routingResponse = await this.getRouting(prompt, validatedOptions);

    // Step 2: Make LLM call with routing
    const llmResponse = await this.callLLM(prompt, {
      ...validatedOptions,
      modelTier: routingResponse.selectedTier,
      model: routingResponse.model,
    });

    // Step 3: Track costs if enabled
    if (this.config.costTrackingEnabled) {
      this.totalCost += llmResponse.cost.total;
      this.requestCount += 1;
    }

    return llmResponse;
  }

  /**
   * Streaming LLM invocation (generator)
   */
  async* streamInvoke(
    prompt: string,
    options: ModelOptions = { taskType: 'general' }
  ): AsyncGenerator<string, LLMResponse, unknown> {
    if (!this.config.streamingEnabled) {
      throw new Error('Streaming is disabled in bridge configuration');
    }

    const validatedOptions = ModelOptionsSchema.parse(options);

    // Get routing first
    const routingResponse = await this.getRouting(prompt, validatedOptions);

    // Create streaming request
    const response = await axios.post(
      `${this.config.orchestratorUrl}/api/ai/stream`,
      {
        prompt,
        ...validatedOptions,
        modelTier: routingResponse.selectedTier,
        model: routingResponse.model,
        stream: true,
      },
      {
        timeout: this.config.timeoutMs,
        responseType: 'stream',
      }
    );

    let content = '';
    const chunks: string[] = [];

    // Process streaming response
    for await (const chunk of response.data) {
      const chunkStr = chunk.toString();
      
      if (chunkStr.startsWith('data: ')) {
        const data = chunkStr.slice(6);
        
        if (data === '[DONE]') {
          break;
        }

        try {
          const parsed = JSON.parse(data);
          if (parsed.content) {
            chunks.push(parsed.content);
            content += parsed.content;
            yield parsed.content;
          }
        } catch (e) {
          // Skip invalid JSON chunks
        }
      }
    }

    // Return final response
    return {
      content,
      usage: {
        totalTokens: Math.ceil(content.length / 4), // Rough estimate
        promptTokens: Math.ceil(prompt.length / 4),
        completionTokens: Math.ceil(content.length / 4),
      },
      cost: {
        total: 0, // Calculated later
        input: 0,
        output: 0,
      },
      model: routingResponse.model,
      tier: routingResponse.selectedTier,
      finishReason: 'stop',
    };
  }

  /**
   * Batch LLM invocation
   */
  async batchInvoke(
    prompts: string[],
    options: ModelOptions = { taskType: 'general' }
  ): Promise<LLMResponse[]> {
    const validatedOptions = ModelOptionsSchema.parse(options);

    // Process prompts in parallel (with concurrency limit)
    const batchSize = 5; // Limit concurrent requests
    const results: LLMResponse[] = [];

    for (let i = 0; i < prompts.length; i += batchSize) {
      const batch = prompts.slice(i, i + batchSize);
      const batchPromises = batch.map((prompt) =>
        this.invoke(prompt, options)
      );

      const batchResults = await Promise.allSettled(batchPromises);

      for (const result of batchResults) {
        if (result.status === 'fulfilled') {
          results.push(result.value);
        } else {
          // Handle failed requests
          results.push({
            content: 'Error: Request failed',
            usage: { totalTokens: 0, promptTokens: 0, completionTokens: 0 },
            cost: { total: 0, input: 0, output: 0 },
            model: 'unknown',
            tier: 'unknown',
            finishReason: 'error',
            metadata: { error: result.reason },
          });
        }
      }
    }

    return results;
  }

  /**
   * Get cost statistics
   */
  getCostStats(): {
    totalCost: number;
    requestCount: number;
    averageCostPerRequest: number;
  } {
    return {
      totalCost: this.totalCost,
      requestCount: this.requestCount,
      averageCostPerRequest:
        this.requestCount > 0 ? this.totalCost / this.requestCount : 0,
    };
  }

  /**
   * Reset cost tracking
   */
  resetCostTracking(): void {
    this.totalCost = 0;
    this.requestCount = 0;
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{
    status: 'healthy' | 'unhealthy';
    orchestratorReachable: boolean;
    aiRouterAvailable: boolean;
    latencyMs: number;
  }> {
    const startTime = Date.now();

    try {
      const response = await axios.get(
        `${this.config.orchestratorUrl}/health`,
        { timeout: 5000 }
      );

      const latency = Date.now() - startTime;

      return {
        status: response.status === 200 ? 'healthy' : 'unhealthy',
        orchestratorReachable: true,
        aiRouterAvailable: response.data?.services?.ai_router === 'healthy',
        latencyMs: latency,
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        orchestratorReachable: false,
        aiRouterAvailable: false,
        latencyMs: Date.now() - startTime,
      };
    }
  }

  // =====================================================================
  // Private Methods
  // =====================================================================

  /**
   * Get AI Router routing recommendation
   */
  private async getRouting(
    prompt: string,
    options: ModelOptions
  ): Promise<{
    selectedTier: ModelTier;
    model: string;
    estimatedCost: number;
  }> {
    const estimatedInputTokens = Math.ceil(prompt.length / 4); // Rough estimate
    const estimatedOutputTokens = Math.ceil(estimatedInputTokens * 0.5);

    try {
      const response = await axios.post(
        `${this.config.orchestratorUrl}/api/ai/router/route`,
        {
          taskType: options.taskType,
          estimatedInputTokens,
          estimatedOutputTokens,
          governanceMode: options.governanceMode || 'DEMO',
          preferredTier: options.modelTier || this.config.defaultTier,
          budgetLimit: options.budgetLimit,
          requirePhiCompliance: options.requirePhiCompliance ?? this.config.phiCompliantOnly,
          stageId: options.stageId,
        },
        { timeout: this.config.timeoutMs }
      );

      const parsed = RoutingApiResponseSchema.parse(response.data);
      return {
        selectedTier: parsed.selectedTier,
        model: parsed.model,
        estimatedCost: parsed.costEstimate.total,
      };
    } catch (error) {
      console.warn('[AIRouterBridge] Routing failed, using defaults:', error);
      
      // Fallback to default routing
      return {
        selectedTier: this.config.defaultTier,
        model: 'claude-3-5-sonnet-20241022', // Default fallback
        estimatedCost: 0.01, // Conservative estimate
      };
    }
  }

  /**
   * Make actual LLM call
   */
  private async callLLM(
    prompt: string,
    options: ModelOptions & { model?: string }
  ): Promise<LLMResponse> {
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= this.config.maxRetries; attempt++) {
      try {
        const response = await axios.post(
          `${this.config.orchestratorUrl}/api/ai/invoke`,
          {
            prompt,
            model: options.model,
            modelTier: options.modelTier,
            taskType: options.taskType,
            maxTokens: options.maxTokens || 4096,
            temperature: options.temperature || 0.7,
            governanceMode: options.governanceMode || 'DEMO',
            stageId: options.stageId,
          },
          { timeout: this.config.timeoutMs }
        );

        // Validate and return response
        const validated: LLMResponse = LLMResponseSchema.parse(response.data) as LLMResponse;
        return validated;
      } catch (error) {
        lastError = error as Error;
        
        if (error instanceof axios.AxiosError) {
          // Don't retry on client errors (4xx)
          if (error.response?.status && error.response.status < 500) {
            throw error;
          }
        }

        // Wait before retry (exponential backoff)
        if (attempt < this.config.maxRetries) {
          await new Promise((resolve) =>
            setTimeout(resolve, Math.pow(2, attempt) * 1000)
          );
        }
      }
    }

    throw lastError || new Error('Max retries exceeded');
  }
}

/**
 * Factory function to create AI Router Bridge from environment
 */
export function createAIRouterBridge(
  config: Partial<BridgeConfig> = {}
): AIRouterBridge {
  const parsedTier = ModelTierSchema.safeParse(process.env.AI_DEFAULT_TIER);
  const envConfig: Partial<BridgeConfig> = {
    orchestratorUrl: process.env.AI_ROUTER_URL || 'http://localhost:3001',
    defaultTier: parsedTier.success ? parsedTier.data : 'MINI',
    phiCompliantOnly: process.env.PHI_COMPLIANT_ONLY === 'true',
    maxRetries: parseInt(process.env.AI_MAX_RETRIES || '3'),
    timeoutMs: parseInt(process.env.AI_TIMEOUT_MS || '30000'),
    costTrackingEnabled: process.env.AI_COST_TRACKING !== 'false',
    streamingEnabled: process.env.AI_STREAMING_ENABLED === 'true',
  };

  return new AIRouterBridge({ ...envConfig, ...config });
}

// Default export
export default AIRouterBridge;