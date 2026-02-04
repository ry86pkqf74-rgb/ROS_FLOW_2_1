/**
 * Qwen3 Local Provider for ResearchFlow AI Router
 * 
 * Integrates local Qwen3-Coder model (via Ollama/Docker) as a tier
 * in the AI routing system for code-related tasks.
 * 
 * @module packages/ai-router/src/providers/qwen-local
 */

export interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface ModelConfig {
  name: string;
  contextWindow: number;
  maxTokens: number;
}

export interface CompletionRequest {
  messages: Message[];
  temperature?: number;
  maxTokens?: number;
  stopSequences?: string[];
}

export interface CompletionResponse {
  content: string;
  model: string;
  provider: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  latency: number;
  cost: number;
}

export interface AIProvider {
  initialize(): Promise<void>;
  complete(request: CompletionRequest): Promise<CompletionResponse>;
  isAvailable(): boolean;
  getTier(): string;
  getConfig(): ModelConfig;
  shutdown(): void;
}

export interface QwenLocalConfig extends ModelConfig {
  endpoint: string;
  model: string;
  temperature?: number;
  healthCheckIntervalMs?: number;
  timeoutMs?: number;
}

interface OllamaResponse {
  model: string;
  message?: {
    role: string;
    content: string;
  };
  done: boolean;
  total_duration?: number;
  load_duration?: number;
  prompt_eval_count?: number;
  prompt_eval_duration?: number;
  eval_count?: number;
  eval_duration?: number;
}

interface OllamaTagsResponse {
  models: Array<{
    name: string;
    model: string;
    modified_at: string;
    size: number;
    digest: string;
  }>;
}

export class QwenLocalProvider implements AIProvider {
  private config: Required<QwenLocalConfig>;
  private healthCheckInterval: NodeJS.Timeout | null = null;
  private isHealthy: boolean = false;
  private lastHealthCheck: Date | null = null;
  private consecutiveFailures: number = 0;

  constructor(config: Partial<QwenLocalConfig> = {}) {
    this.config = {
      name: config.name || 'qwen3-coder-local',
      endpoint: config.endpoint || process.env.LOCAL_MODEL_ENDPOINT || 'http://localhost:11434',
      model: config.model || process.env.LOCAL_MODEL_NAME || 'ai/qwen3-coder:latest',
      contextWindow: config.contextWindow || 32768,
      maxTokens: config.maxTokens || 8192,
      temperature: config.temperature || 0.1,
      healthCheckIntervalMs: config.healthCheckIntervalMs || 30000,
      timeoutMs: config.timeoutMs || 120000, // 2 minutes for large requests
    };
  }

  async initialize(): Promise<void> {
    console.log(`[QwenLocal] Initializing provider...`);
    console.log(`[QwenLocal] Endpoint: ${this.config.endpoint}`);
    console.log(`[QwenLocal] Model: ${this.config.model}`);

    // Initial health check
    await this.checkHealth();

    // Set up periodic health checks
    this.healthCheckInterval = setInterval(
      () => this.checkHealth(),
      this.config.healthCheckIntervalMs
    );

    if (this.isHealthy) {
      console.log(`[QwenLocal] ✅ Provider initialized successfully`);
    } else {
      console.warn(`[QwenLocal] ⚠️ Provider initialized but model not available`);
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${this.config.endpoint}/api/tags`, {
        method: 'GET',
        signal: controller.signal,
      });

      clearTimeout(timeout);

      if (response.ok) {
        const data: OllamaTagsResponse = await response.json();
        
        // Check if our model is available
        const modelAvailable = data.models?.some(
          (m) => m.name === this.config.model || 
                 m.name.includes('qwen3-coder') ||
                 m.model === this.config.model
        ) ?? false;

        if (modelAvailable) {
          this.isHealthy = true;
          this.consecutiveFailures = 0;
        } else {
          console.warn(`[QwenLocal] Model ${this.config.model} not found in available models`);
          console.warn(`[QwenLocal] Available models:`, data.models?.map(m => m.name));
          this.isHealthy = false;
        }
      } else {
        this.isHealthy = false;
        this.consecutiveFailures++;
      }
    } catch (error) {
      this.isHealthy = false;
      this.consecutiveFailures++;
      
      if (this.consecutiveFailures <= 3) {
        console.warn(`[QwenLocal] Health check failed (${this.consecutiveFailures}/3):`, 
          error instanceof Error ? error.message : 'Unknown error');
      }
    }

    this.lastHealthCheck = new Date();
    return this.isHealthy;
  }

  async complete(request: CompletionRequest): Promise<CompletionResponse> {
    if (!this.isHealthy) {
      // Try one more health check before giving up
      await this.checkHealth();
      if (!this.isHealthy) {
        throw new Error('Qwen3 local model is not available. Ensure Ollama is running.');
      }
    }

    const startTime = Date.now();

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.config.timeoutMs);

    try {
      const response = await fetch(`${this.config.endpoint}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          model: this.config.model,
          messages: request.messages.map(m => ({
            role: m.role,
            content: m.content,
          })),
          stream: false,
          options: {
            temperature: request.temperature ?? this.config.temperature,
            num_predict: request.maxTokens ?? this.config.maxTokens,
            stop: request.stopSequences,
          },
        }),
      });

      clearTimeout(timeout);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Qwen3 request failed (${response.status}): ${errorText}`);
      }

      const data: OllamaResponse = await response.json();
      const latency = Date.now() - startTime;

      const promptTokens = data.prompt_eval_count ?? this.estimateTokens(request.messages);
      const completionTokens = data.eval_count ?? this.estimateTokens([{ role: 'assistant', content: data.message?.content ?? '' }]);

      return {
        content: data.message?.content ?? '',
        model: this.config.model,
        provider: 'qwen-local',
        usage: {
          promptTokens,
          completionTokens,
          totalTokens: promptTokens + completionTokens,
        },
        latency,
        cost: 0, // Local inference = no API cost
      };
    } catch (error) {
      clearTimeout(timeout);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Qwen3 request timed out after ${this.config.timeoutMs}ms`);
      }

      // Mark as unhealthy on error
      this.isHealthy = false;
      throw error;
    }
  }

  /**
   * Rough token estimation (4 chars ≈ 1 token)
   */
  private estimateTokens(messages: Message[]): number {
    const totalChars = messages.reduce((sum, m) => sum + m.content.length, 0);
    return Math.ceil(totalChars / 4);
  }

  isAvailable(): boolean {
    return this.isHealthy;
  }

  getTier(): string {
    return 'LOCAL';
  }

  getConfig(): ModelConfig {
    return {
      name: this.config.name,
      contextWindow: this.config.contextWindow,
      maxTokens: this.config.maxTokens,
    };
  }

  getHealthStatus(): { healthy: boolean; lastCheck: Date | null; failures: number } {
    return {
      healthy: this.isHealthy,
      lastCheck: this.lastHealthCheck,
      failures: this.consecutiveFailures,
    };
  }

  shutdown(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
    console.log('[QwenLocal] Provider shut down');
  }
}

/**
 * Task types eligible for local model processing
 */
export const LOCAL_ELIGIBLE_TASKS = new Set([
  'code_review',
  'code_refactor',
  'lint_fix',
  'syntax_check',
  'documentation',
  'docstring_generation',
  'unit_test_generation',
  'code_explanation',
  'type_annotation',
  'variable_rename',
  'extract_function',
  'simplify_conditional',
  'remove_dead_code',
  'add_error_handling',
  'convert_syntax',
]);

/**
 * Check if a task type should prefer local processing
 */
export function shouldUseLocal(
  taskType: string,
  options: {
    requiresAudit?: boolean;
    preferLocal?: boolean;
    estimatedTokens?: number;
  } = {}
): boolean {
  const { requiresAudit = false, preferLocal = true, estimatedTokens = 0 } = options;

  // Never use local for audited tasks (PHI compliance)
  if (requiresAudit) {
    return false;
  }

  // Don't use local if explicitly disabled
  if (!preferLocal) {
    return false;
  }

  // Check if task type is eligible
  if (!LOCAL_ELIGIBLE_TASKS.has(taskType)) {
    return false;
  }

  // Check context window limits
  const MAX_LOCAL_CONTEXT = 24000; // Leave buffer from 32K
  if (estimatedTokens > MAX_LOCAL_CONTEXT) {
    return false;
  }

  return true;
}

export default QwenLocalProvider;

/**
 * Task types that should NEVER use local model processing
 * (require cloud APIs for compliance, audit trails, or capability reasons)
 */
export const LOCAL_BLOCKED_TASKS = new Set([
  'phi_scan',
  'phi_redaction',
  'medical_extraction',
  'clinical_reasoning',
  'regulatory_review',
  'audit_trail',
  'compliance_check',
  'sensitive_classification',
  'hipaa_validation',
  'pii_detection',
  'research_synthesis',
  'statistical_analysis',
  'manuscript_generation',
  'peer_review_assist',
]);
