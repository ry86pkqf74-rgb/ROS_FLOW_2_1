/**
 * Mercury Coder Provider (Inception Labs)
 * 
 * Ultra-fast diffusion LLM for code generation, completion, and editing.
 * Supports 4 specialized endpoints + realtime mode:
 * 
 * ENDPOINTS:
 * - v1/chat/completions (128K context) - Standard chat/reasoning + realtime mode
 * - v1/fim/completions (32K context) - Fill-in-middle autocomplete
 * - v1/apply/completions (32K context) - Apply code edits with intelligent merging
 * - v1/edit/completions (32K context) - Next-edit prediction
 * 
 * FEATURES:
 * - Realtime mode: Near-instant responses for voice assistants, chatbots, automations
 * - Structured Outputs: JSON schema enforcement for typed responses
 * - 5-10x faster than GPT-4o mini (1000+ tokens/sec via discrete diffusion)
 * 
 * @see https://docs.inceptionlabs.ai
 */

import { logAIUsage, type AIUsageLogEntry } from '../notion/notionLogger';
import type { AITaskType, ModelTier } from '../types';

// ============================================================================
// Types
// ============================================================================

export type MercuryEndpoint = 'chat' | 'fim' | 'apply' | 'edit';
export type MercuryModel = 'mercury' | 'mercury-coder' | 'mercury-coder-small';

export interface MercuryCoderRequestOptions {
  /** Endpoint to use */
  endpoint?: MercuryEndpoint;
  /** Task type for routing and logging */
  taskType?: AITaskType | string;
  /** Model tier override */
  tier?: ModelTier;
  /** Research ID for tracking */
  researchId?: string;
  /** User ID for tracking */
  userId?: string;
  /** Session ID for grouping calls */
  sessionId?: string;
  /** Agent ID if called from an agent */
  agentId?: string;
  /** Phase/stage ID for workflow tracking */
  phaseId?: number;
  /** Enable realtime mode for near-instant responses */
  realtime?: boolean;
  /** Enable diffusion visualization (streams noisy tokens being refined) */
  diffusing?: boolean;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

export interface MercuryChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * FIM Request - Fill-in-Middle for code autocomplete
 * Uses prompt (code before cursor) + suffix (code after cursor)
 */
export interface MercuryFIMRequest {
  /** Code before the cursor (the "prompt" in FIM terminology) */
  prompt: string;
  /** Code after the cursor */
  suffix: string;
  /** Maximum tokens to generate */
  max_tokens?: number;
  /** Temperature (0-2), lower = more deterministic */
  temperature?: number;
  /** Stop sequences */
  stop?: string[];
}

/**
 * Apply Edit Request - Intelligent code merging
 * Uses special tags: <|original_code|> and <|update_snippet|>
 */
export interface MercuryApplyRequest {
  /** Original code to modify */
  originalCode: string;
  /** Update snippet with // ... existing code ... markers */
  updateSnippet: string;
  /** Maximum tokens for the edited code */
  max_tokens?: number;
  /** Language hint */
  language?: string;
}

/**
 * Next Edit Request - Predicts next logical edit
 * Uses special format with recently_viewed_code_snippets, current_file_content, edit_diff_history
 */
export interface MercuryEditRequest {
  /** Current file path */
  currentFilePath: string;
  /** Full current file content */
  currentFileContent: string;
  /** Code region to edit (subset of currentFileContent) */
  codeToEdit: string;
  /** Cursor position marker within codeToEdit */
  cursorPosition?: { line: number; column: number };
  /** Recently viewed code snippets for context */
  recentlyViewedSnippets?: string[];
  /** Recent edit diff history for pattern learning */
  editDiffHistory?: Array<{
    filePath: string;
    before: string;
    after: string;
  }>;
  /** Maximum tokens for predicted edit */
  max_tokens?: number;
}

/**
 * Structured Output Schema
 * Enforces JSON schema on responses
 */
export interface MercuryStructuredOutputSchema {
  name: string;
  strict?: boolean;
  schema: {
    type: 'object';
    properties: Record<string, {
      type: string;
      description?: string;
      enum?: string[];
      minimum?: number;
      maximum?: number;
      items?: { type: string };
    }>;
    required?: string[];
  };
}

export interface MercuryResponse {
  /** Generated text/code */
  content: string;
  /** Model used */
  model: string;
  /** Endpoint used */
  endpoint: MercuryEndpoint;
  /** Whether realtime mode was used */
  realtime: boolean;
  /** Usage statistics */
  usage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
    estimatedCostUsd: number;
  };
  /** Performance metrics */
  metrics: {
    latencyMs: number;
    tokensPerSecond: number;
  };
  /** Structured output (if JSON schema was used) */
  structured?: Record<string, unknown>;
  /** Raw API response */
  raw?: unknown;
}

// ============================================================================
// Cost Configuration
// ============================================================================

const MERCURY_PRICING = {
  // Per million tokens
  'mercury': { input: 0.25, output: 1.0 },
  'mercury-coder': { input: 0.25, output: 1.0 },
  'mercury-coder-small': { input: 0.25, output: 1.0 },
  default: { input: 0.25, output: 1.0 },
};

function calculateCost(model: string, inputTokens: number, outputTokens: number): number {
  const pricing = MERCURY_PRICING[model as keyof typeof MERCURY_PRICING] ?? MERCURY_PRICING.default;
  const inputCost = (inputTokens / 1_000_000) * pricing.input;
  const outputCost = (outputTokens / 1_000_000) * pricing.output;
  return Math.round((inputCost + outputCost) * 100000) / 100000;
}

// ============================================================================
// Mercury Coder Provider Class
// ============================================================================

export class MercuryCoderProvider {
  private apiKey: string;
  private baseUrl: string;
  private defaultModel: MercuryModel;
  private chatModel: MercuryModel;

  constructor(options?: {
    apiKey?: string;
    baseUrl?: string;
    defaultModel?: MercuryModel;
    chatModel?: MercuryModel;
  }) {
    this.apiKey =
      options?.apiKey ??
      process.env.MERCURY_API_KEY ??
      process.env.INCEPTION_API_KEY ??
      process.env.INCEPTIONLABS_API_KEY ??
      '';
    this.baseUrl =
      options?.baseUrl ??
      process.env.MERCURY_API_BASE_URL ??
      process.env.INCEPTION_API_BASE_URL ??
      'https://api.inceptionlabs.ai';
    this.defaultModel = options?.defaultModel ?? 'mercury-coder-small';
    this.chatModel = options?.chatModel ?? 'mercury'; // Use 'mercury' for chat/realtime

    if (!this.apiKey) {
      console.warn(
        '[MercuryCoderProvider] No API key found. Set MERCURY_API_KEY, INCEPTION_API_KEY, or INCEPTIONLABS_API_KEY.'
      );
    }
  }

  /**
   * Get the endpoint URL for a given endpoint type
   */
  private getEndpointUrl(endpoint: MercuryEndpoint): string {
    const endpoints: Record<MercuryEndpoint, string> = {
      chat: '/v1/chat/completions',
      fim: '/v1/fim/completions',
      apply: '/v1/apply/completions',
      edit: '/v1/edit/completions',
    };
    return `${this.baseUrl}${endpoints[endpoint]}`;
  }

  // ==========================================================================
  // CHAT ENDPOINT - Standard chat with optional realtime mode
  // ==========================================================================

  /**
   * Standard chat completion (128K context)
   * Supports realtime mode for near-instant responses
   * 
   * @example
   * // Standard chat
   * await provider.chat([{ role: 'user', content: 'Hello' }]);
   * 
   * // Realtime mode for low-latency
   * await provider.chat([{ role: 'user', content: 'Hello' }], { realtime: true });
   */
  async chat(
    messages: MercuryChatMessage[],
    options?: MercuryCoderRequestOptions & {
      model?: MercuryModel;
      temperature?: number;
      max_tokens?: number;
      tools?: unknown[];
      stream?: boolean;
      responseFormat?: { type: 'json_schema'; json_schema: MercuryStructuredOutputSchema };
    }
  ): Promise<MercuryResponse> {
    const startTime = Date.now();
    const model = options?.model ?? this.chatModel;
    const isRealtime = options?.realtime ?? false;

    const requestBody: Record<string, unknown> = {
      model,
      messages,
      temperature: options?.temperature ?? 0.7,
      max_tokens: options?.max_tokens ?? 4096,
      stream: options?.stream ?? false,
    };

    // Add realtime flag for near-instant responses
    if (isRealtime) {
      requestBody.realtime = true;
    }

    // Add diffusion visualization
    if (options?.diffusing) {
      requestBody.diffusing = true;
    }

    // Add tools if provided
    if (options?.tools) {
      requestBody.tools = options.tools;
    }

    // Add structured output schema
    if (options?.responseFormat) {
      requestBody.response_format = options.responseFormat;
    }

    const response = await fetch(this.getEndpointUrl('chat'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Mercury API error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    const latencyMs = Date.now() - startTime;
    const inputTokens = data.usage?.prompt_tokens ?? 0;
    const outputTokens = data.usage?.completion_tokens ?? 0;
    const content = data.choices?.[0]?.message?.content ?? '';

    // Parse structured output if JSON schema was used
    let structured: Record<string, unknown> | undefined;
    if (options?.responseFormat && content) {
      try {
        structured = JSON.parse(content);
      } catch {
        // Content wasn't valid JSON
      }
    }

    const result: MercuryResponse = {
      content,
      model: data.model ?? model,
      endpoint: 'chat',
      realtime: isRealtime,
      usage: {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        estimatedCostUsd: calculateCost(model, inputTokens, outputTokens),
      },
      metrics: {
        latencyMs,
        tokensPerSecond: outputTokens > 0 ? Math.round((outputTokens / latencyMs) * 1000) : 0,
      },
      structured,
      raw: data,
    };

    // Log to Notion if configured
    await this.logUsage(result, options);

    return result;
  }

  /**
   * Realtime chat - convenience wrapper for chat with realtime=true
   * Ideal for voice assistants, chatbots, real-time decision systems
   */
  async realtimeChat(
    messages: MercuryChatMessage[],
    options?: Omit<Parameters<typeof this.chat>[1], 'realtime'>
  ): Promise<MercuryResponse> {
    return this.chat(messages, { ...options, realtime: true });
  }

  // ==========================================================================
  // FIM ENDPOINT - Fill-in-Middle for autocomplete
  // ==========================================================================

  /**
   * Fill-in-Middle completion (32K context)
   * Ideal for autocomplete where you have code before and after cursor
   * 
   * @example
   * await provider.fim({
   *   prompt: 'def fibonacci(',
   *   suffix: 'return a + b'
   * });
   */
  async fim(
    request: MercuryFIMRequest,
    options?: MercuryCoderRequestOptions
  ): Promise<MercuryResponse> {
    const startTime = Date.now();
    const model = this.defaultModel;

    const response = await fetch(this.getEndpointUrl('fim'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model,
        prompt: request.prompt,
        suffix: request.suffix,
        max_tokens: request.max_tokens ?? 256,
        temperature: request.temperature ?? 0.2,
        stop: request.stop,
        ...(options?.diffusing && { diffusing: true }),
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Mercury FIM API error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    const latencyMs = Date.now() - startTime;
    const inputTokens = data.usage?.prompt_tokens ?? 0;
    const outputTokens = data.usage?.completion_tokens ?? 0;

    const result: MercuryResponse = {
      content: data.choices?.[0]?.text ?? data.choices?.[0]?.message?.content ?? '',
      model: data.model ?? model,
      endpoint: 'fim',
      realtime: false,
      usage: {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        estimatedCostUsd: calculateCost(model, inputTokens, outputTokens),
      },
      metrics: {
        latencyMs,
        tokensPerSecond: outputTokens > 0 ? Math.round((outputTokens / latencyMs) * 1000) : 0,
      },
      raw: data,
    };

    await this.logUsage(result, { ...options, taskType: 'autocomplete' });
    return result;
  }

  // ==========================================================================
  // APPLY ENDPOINT - Intelligent code merging
  // ==========================================================================

  /**
   * Apply code edits (32K context)
   * Intelligently merges update snippet into original code while preserving structure
   * 
   * @example
   * await provider.applyEdit({
   *   originalCode: 'class Calculator:\n    def add(self, a, b):\n        return a + b',
   *   updateSnippet: '// ... existing code ...\ndef multiply(self, a, b):\n    return a * b\n// ... existing code ...'
   * });
   */
  async applyEdit(
    request: MercuryApplyRequest,
    options?: MercuryCoderRequestOptions
  ): Promise<MercuryResponse> {
    const startTime = Date.now();
    const model = this.defaultModel;

    // Format the message content with special tags as per Inception API
    const messageContent = `<|original_code|>
${request.originalCode}
<|/original_code|>

<|update_snippet|>
${request.updateSnippet}
<|/update_snippet|>`;

    const response = await fetch(this.getEndpointUrl('apply'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: messageContent }],
        max_tokens: request.max_tokens ?? 4096,
        ...(request.language && { language: request.language }),
        ...(options?.diffusing && { diffusing: true }),
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Mercury Apply API error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    const latencyMs = Date.now() - startTime;
    const inputTokens = data.usage?.prompt_tokens ?? 0;
    const outputTokens = data.usage?.completion_tokens ?? 0;

    const result: MercuryResponse = {
      content: data.choices?.[0]?.message?.content ?? data.choices?.[0]?.text ?? '',
      model: data.model ?? model,
      endpoint: 'apply',
      realtime: false,
      usage: {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        estimatedCostUsd: calculateCost(model, inputTokens, outputTokens),
      },
      metrics: {
        latencyMs,
        tokensPerSecond: outputTokens > 0 ? Math.round((outputTokens / latencyMs) * 1000) : 0,
      },
      raw: data,
    };

    await this.logUsage(result, { ...options, taskType: 'apply-edit' });
    return result;
  }

  // ==========================================================================
  // EDIT ENDPOINT - NextEdit prediction
  // ==========================================================================

  /**
   * NextEdit prediction (32K context)
   * Predicts the next logical edit based on context and edit history
   * 
   * @example
   * await provider.nextEdit({
   *   currentFilePath: 'solver.py',
   *   currentFileContent: '...',
   *   codeToEdit: 'def flagAllNeighbors(board, row, col):...',
   *   editDiffHistory: [{ filePath: 'solver.py', before: '...', after: '...' }]
   * });
   */
  async nextEdit(
    request: MercuryEditRequest,
    options?: MercuryCoderRequestOptions
  ): Promise<MercuryResponse> {
    const startTime = Date.now();
    const model = this.defaultModel;

    // Build the special format for NextEdit as per Inception API
    const recentlyViewedSection = request.recentlyViewedSnippets?.length
      ? `<|recently_viewed_code_snippets|>\n${request.recentlyViewedSnippets.join('\n\n')}\n<|/recently_viewed_code_snippets|>`
      : '<|recently_viewed_code_snippets|>\n\n<|/recently_viewed_code_snippets|>';

    // Insert cursor marker if position provided
    let codeToEdit = request.codeToEdit;
    if (request.cursorPosition) {
      const lines = codeToEdit.split('\n');
      if (request.cursorPosition.line < lines.length) {
        const line = lines[request.cursorPosition.line];
        const col = Math.min(request.cursorPosition.column, line.length);
        lines[request.cursorPosition.line] = 
          line.slice(0, col) + '<|cursor|>' + line.slice(col);
        codeToEdit = lines.join('\n');
      }
    }

    const currentFileSection = `<|current_file_content|>
current_file_path: ${request.currentFilePath}
'''
${request.currentFileContent}
'''
<|code_to_edit|>
${codeToEdit}
<|/code_to_edit|>
<|/current_file_content|>`;

    // Build edit history section
    let editHistorySection = '<|edit_diff_history|>\n';
    if (request.editDiffHistory?.length) {
      for (const edit of request.editDiffHistory) {
        editHistorySection += `--- ${edit.filePath}\n+++ ${edit.filePath}\n`;
        editHistorySection += `@@ -1,1 +1,1 @@\n`;
        editHistorySection += `-${edit.before}\n+${edit.after}\n\n`;
      }
    }
    editHistorySection += '<|/edit_diff_history|>';

    const messageContent = `${recentlyViewedSection}\n\n${currentFileSection}\n\n${editHistorySection}`;

    const response = await fetch(this.getEndpointUrl('edit'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: messageContent }],
        max_tokens: request.max_tokens ?? 512,
        ...(options?.diffusing && { diffusing: true }),
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Mercury Edit API error: ${response.status} - ${error}`);
    }

    const data = await response.json();
    const latencyMs = Date.now() - startTime;
    const inputTokens = data.usage?.prompt_tokens ?? 0;
    const outputTokens = data.usage?.completion_tokens ?? 0;

    const result: MercuryResponse = {
      content: data.choices?.[0]?.message?.content ?? data.choices?.[0]?.text ?? '',
      model: data.model ?? model,
      endpoint: 'edit',
      realtime: false,
      usage: {
        inputTokens,
        outputTokens,
        totalTokens: inputTokens + outputTokens,
        estimatedCostUsd: calculateCost(model, inputTokens, outputTokens),
      },
      metrics: {
        latencyMs,
        tokensPerSecond: outputTokens > 0 ? Math.round((outputTokens / latencyMs) * 1000) : 0,
      },
      raw: data,
    };

    await this.logUsage(result, { ...options, taskType: 'next-edit' });
    return result;
  }

  // ==========================================================================
  // STRUCTURED OUTPUTS - JSON Schema enforcement
  // ==========================================================================

  /**
   * Chat with structured JSON output
   * Ensures response follows specified JSON schema
   * 
   * @example
   * await provider.structuredChat(
   *   [{ role: 'user', content: 'Analyze sentiment...' }],
   *   {
   *     name: 'Sentiment',
   *     strict: true,
   *     schema: {
   *       type: 'object',
   *       properties: {
   *         sentiment: { type: 'string', enum: ['positive', 'negative', 'neutral'] },
   *         confidence: { type: 'number', minimum: 0, maximum: 1 }
   *       },
   *       required: ['sentiment', 'confidence']
   *     }
   *   }
   * );
   */
  async structuredChat<T extends Record<string, unknown>>(
    messages: MercuryChatMessage[],
    schema: MercuryStructuredOutputSchema,
    options?: MercuryCoderRequestOptions & {
      model?: MercuryModel;
      temperature?: number;
      max_tokens?: number;
    }
  ): Promise<MercuryResponse & { structured: T }> {
    const result = await this.chat(messages, {
      ...options,
      responseFormat: {
        type: 'json_schema',
        json_schema: schema,
      },
    });

    return result as MercuryResponse & { structured: T };
  }

  // ==========================================================================
  // AGENT INTEGRATION METHODS
  // ==========================================================================

  /**
   * Agent-optimized chat with realtime mode and phase tracking
   * Designed for phase/stage specific chat agents
   */
  async agentChat(
    messages: MercuryChatMessage[],
    options: MercuryCoderRequestOptions & {
      agentId: string;
      phaseId?: number;
      model?: MercuryModel;
      temperature?: number;
      max_tokens?: number;
    }
  ): Promise<MercuryResponse> {
    return this.chat(messages, {
      ...options,
      realtime: true, // Always use realtime for agents
      taskType: options.taskType ?? 'agent-chat',
      metadata: {
        ...options.metadata,
        agentId: options.agentId,
        phaseId: options.phaseId,
      },
    });
  }

  /**
   * Analyze codebase structure using chat endpoint
   * Useful for RAG loops and code understanding
   */
  async analyzeCode(
    code: string,
    instruction: string,
    options?: MercuryCoderRequestOptions
  ): Promise<MercuryResponse> {
    return this.chat([
      {
        role: 'system',
        content: 'You are an expert code analyst. Analyze the provided code and respond to the instruction accurately and concisely.',
      },
      {
        role: 'user',
        content: `Code:\n\`\`\`\n${code}\n\`\`\`\n\nInstruction: ${instruction}`,
      },
    ], {
      ...options,
      temperature: 0.3,
      taskType: 'codebase-analysis',
    });
  }

  /**
   * Generate code from description
   */
  async generateCode(
    description: string,
    context?: string,
    options?: MercuryCoderRequestOptions & { language?: string }
  ): Promise<MercuryResponse> {
    const systemPrompt = options?.language
      ? `You are an expert ${options.language} developer. Generate clean, well-documented code.`
      : 'You are an expert software developer. Generate clean, well-documented code.';

    return this.chat([
      { role: 'system', content: systemPrompt },
      {
        role: 'user',
        content: context
          ? `Context:\n${context}\n\nGenerate code for: ${description}`
          : `Generate code for: ${description}`,
      },
    ], {
      ...options,
      temperature: 0.4,
      taskType: 'code-generation',
    });
  }

  /**
   * Quick code refactoring using Apply endpoint
   */
  async refactorCode(
    code: string,
    instruction: string,
    options?: MercuryCoderRequestOptions
  ): Promise<MercuryResponse> {
    // First, generate the update snippet using chat
    const planResponse = await this.chat([
      {
        role: 'system',
        content: 'You are an expert code refactoring assistant. Generate an update snippet that shows only the changed code with "// ... existing code ..." markers for unchanged sections.',
      },
      {
        role: 'user',
        content: `Original code:\n\`\`\`\n${code}\n\`\`\`\n\nRefactoring instruction: ${instruction}\n\nGenerate an update snippet with markers:`,
      },
    ], { temperature: 0.3, max_tokens: 2048 });

    // Then apply the edit
    return this.applyEdit({
      originalCode: code,
      updateSnippet: planResponse.content,
    }, {
      ...options,
      taskType: 'refactoring',
    });
  }

  // ==========================================================================
  // UTILITY METHODS
  // ==========================================================================

  /**
   * Log usage to Notion
   */
  private async logUsage(
    result: MercuryResponse,
    options?: MercuryCoderRequestOptions
  ): Promise<void> {
    try {
      const logEntry: AIUsageLogEntry = {
        tool: 'mercury-coder',
        provider: 'inception-labs',
        model: result.model,
        taskType: (options?.taskType as AITaskType) ?? 'code',
        inputTokens: result.usage.inputTokens,
        outputTokens: result.usage.outputTokens,
        totalTokens: result.usage.totalTokens,
        latencyMs: result.metrics.latencyMs,
        estimatedCostUsd: result.usage.estimatedCostUsd,
        researchId: options?.researchId,
        userId: options?.userId,
        sessionId: options?.sessionId,
        agentId: options?.agentId,
        metadata: {
          endpoint: result.endpoint,
          realtime: result.realtime,
          tokensPerSecond: result.metrics.tokensPerSecond,
          phaseId: options?.phaseId,
          ...options?.metadata,
        },
      };
      await logAIUsage(logEntry);
    } catch (error) {
      console.warn('[MercuryCoderProvider] Failed to log usage:', error);
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.chat([
        { role: 'user', content: 'Say "ok"' }
      ], { max_tokens: 10, realtime: true });
      return response.content.toLowerCase().includes('ok');
    } catch {
      return false;
    }
  }

  /**
   * Get provider info
   */
  getInfo() {
    return {
      name: 'Mercury Coder',
      provider: 'Inception Labs',
      baseUrl: this.baseUrl,
      defaultModel: this.defaultModel,
      chatModel: this.chatModel,
      endpoints: ['chat', 'fim', 'apply', 'edit'],
      features: ['realtime', 'structured-outputs', 'fim', 'apply-edit', 'next-edit'],
      pricing: MERCURY_PRICING,
    };
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

let instance: MercuryCoderProvider | null = null;

export function getMercuryCoderProvider(
  options?: ConstructorParameters<typeof MercuryCoderProvider>[0]
): MercuryCoderProvider {
  if (!instance) {
    instance = new MercuryCoderProvider(options);
  }
  return instance;
}

export default MercuryCoderProvider;
