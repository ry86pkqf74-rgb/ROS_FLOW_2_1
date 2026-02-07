/**
 * Mercury Agent Integration Service
 * 
 * Integrates Mercury's ultra-fast diffusion LLM with phase/stage specific chat agents.
 * Provides:
 * - Realtime mode for low-latency agent responses
 * - Structured outputs for typed agent responses
 * - FIM for code autocomplete in development agents
 * - Apply/Edit for code refactoring agents
 * 
 * @see https://docs.inceptionlabs.ai
 */

import {
  MercuryCoderProvider,
  getMercuryCoderProvider,
  type MercuryChatMessage,
  type MercuryResponse,
  type MercuryStructuredOutputSchema,
  type MercuryCoderRequestOptions,
} from '@researchflow/ai-router';

import { getAgentById, getAgentsForStage, type PhaseAgentDefinition } from './phase-chat/registry';

// ============================================================================
// Types
// ============================================================================

export interface MercuryAgentConfig {
  /** Enable realtime mode for near-instant responses */
  realtimeEnabled: boolean;
  /** Default temperature for chat */
  defaultTemperature: number;
  /** Max tokens per response */
  maxTokens: number;
  /** Enable structured outputs */
  structuredOutputsEnabled: boolean;
}

export interface MercuryAgentRequest {
  /** Stage number (1-20) */
  stage: number;
  /** Agent ID (optional, uses first agent for stage if not provided) */
  agentId?: string;
  /** User query */
  query: string;
  /** System prompt override */
  systemPrompt?: string;
  /** Previous conversation messages */
  conversationHistory?: MercuryChatMessage[];
  /** User ID for tracking */
  userId?: string;
  /** Session ID for grouping */
  sessionId?: string;
  /** Research ID for tracking */
  researchId?: string;
  /** Use realtime mode (overrides config) */
  realtime?: boolean;
  /** Structured output schema */
  structuredSchema?: MercuryStructuredOutputSchema;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

export interface MercuryAgentResponse {
  /** Agent used */
  agent: PhaseAgentDefinition;
  /** Mercury response */
  response: MercuryResponse;
  /** Whether realtime mode was used */
  realtimeUsed: boolean;
  /** Structured output (if schema was provided) */
  structured?: Record<string, unknown>;
}

// Task type to Mercury capability mapping
const TASK_TYPE_CAPABILITIES: Record<string, {
  preferRealtime: boolean;
  suggestedTemperature: number;
  suggestedMaxTokens: number;
}> = {
  // Low-latency tasks - prefer realtime
  'classify': { preferRealtime: true, suggestedTemperature: 0.3, suggestedMaxTokens: 1024 },
  'extract_metadata': { preferRealtime: true, suggestedTemperature: 0.2, suggestedMaxTokens: 2048 },
  'template_fill': { preferRealtime: true, suggestedTemperature: 0.3, suggestedMaxTokens: 2048 },
  'policy_check': { preferRealtime: true, suggestedTemperature: 0.2, suggestedMaxTokens: 1024 },
  
  // Standard tasks
  'summarize': { preferRealtime: false, suggestedTemperature: 0.5, suggestedMaxTokens: 4096 },
  'abstract_generate': { preferRealtime: false, suggestedTemperature: 0.6, suggestedMaxTokens: 2048 },
  
  // Complex tasks - need more tokens/quality
  'draft_section': { preferRealtime: false, suggestedTemperature: 0.7, suggestedMaxTokens: 8192 },
  'protocol_reasoning': { preferRealtime: false, suggestedTemperature: 0.5, suggestedMaxTokens: 4096 },
  'complex_synthesis': { preferRealtime: false, suggestedTemperature: 0.6, suggestedMaxTokens: 8192 },
  
  // Default
  'default': { preferRealtime: true, suggestedTemperature: 0.5, suggestedMaxTokens: 4096 },
};

// Predefined structured output schemas for common agent tasks
export const AGENT_SCHEMAS = {
  // Classification result
  classification: {
    name: 'Classification',
    strict: true,
    schema: {
      type: 'object' as const,
      properties: {
        category: { type: 'string', description: 'The classification category' },
        confidence: { type: 'number', minimum: 0, maximum: 1, description: 'Confidence score' },
        reasoning: { type: 'string', description: 'Brief reasoning for the classification' },
      },
      required: ['category', 'confidence'],
    },
  },

  // Data extraction result
  extraction: {
    name: 'Extraction',
    strict: true,
    schema: {
      type: 'object' as const,
      properties: {
        entities: { type: 'array', items: { type: 'string' }, description: 'Extracted entities' },
        values: { type: 'array', items: { type: 'string' }, description: 'Extracted values' },
        metadata: { type: 'object', description: 'Additional metadata' },
      },
      required: ['entities'],
    },
  },

  // Sentiment analysis
  sentiment: {
    name: 'Sentiment',
    strict: true,
    schema: {
      type: 'object' as const,
      properties: {
        sentiment: { type: 'string', enum: ['positive', 'negative', 'neutral'] },
        confidence: { type: 'number', minimum: 0, maximum: 1 },
        keyPhrases: { type: 'array', items: { type: 'string' } },
      },
      required: ['sentiment', 'confidence', 'keyPhrases'],
    },
  },

  // Statistical analysis recommendation
  statisticalRecommendation: {
    name: 'StatisticalRecommendation',
    strict: true,
    schema: {
      type: 'object' as const,
      properties: {
        recommendedTest: { type: 'string', description: 'Recommended statistical test' },
        assumptions: { type: 'array', items: { type: 'string' }, description: 'Test assumptions' },
        alternatives: { type: 'array', items: { type: 'string' }, description: 'Alternative tests' },
        rationale: { type: 'string', description: 'Rationale for recommendation' },
      },
      required: ['recommendedTest', 'rationale'],
    },
  },

  // Cohort definition
  cohortDefinition: {
    name: 'CohortDefinition',
    strict: true,
    schema: {
      type: 'object' as const,
      properties: {
        inclusionCriteria: { type: 'array', items: { type: 'string' } },
        exclusionCriteria: { type: 'array', items: { type: 'string' } },
        estimatedSize: { type: 'number', description: 'Estimated cohort size' },
        rationale: { type: 'string' },
      },
      required: ['inclusionCriteria', 'exclusionCriteria'],
    },
  },

  // Action items
  actionItems: {
    name: 'ActionItems',
    strict: true,
    schema: {
      type: 'object' as const,
      properties: {
        items: {
          type: 'array',
          items: { type: 'string' },
          description: 'List of action items',
        },
        priority: { type: 'string', enum: ['high', 'medium', 'low'] },
        deadline: { type: 'string', description: 'Suggested deadline (ISO format)' },
      },
      required: ['items'],
    },
  },
};

// ============================================================================
// Mercury Agent Integration Service
// ============================================================================

export class MercuryAgentIntegrationService {
  private provider: MercuryCoderProvider;
  private config: MercuryAgentConfig;

  constructor(config?: Partial<MercuryAgentConfig>) {
    this.provider = getMercuryCoderProvider();
    this.config = {
      realtimeEnabled: config?.realtimeEnabled ?? true,
      defaultTemperature: config?.defaultTemperature ?? 0.5,
      maxTokens: config?.maxTokens ?? 4096,
      structuredOutputsEnabled: config?.structuredOutputsEnabled ?? true,
    };
  }

  /**
   * Send a message through a phase/stage agent using Mercury
   */
  async sendAgentMessage(request: MercuryAgentRequest): Promise<MercuryAgentResponse> {
    // Get the agent
    const agentsForStage = getAgentsForStage(request.stage);
    const agent = request.agentId
      ? getAgentById(request.agentId)
      : agentsForStage[0];

    if (!agent) {
      throw new Error(`No agent found for stage ${request.stage}${request.agentId ? ` with id ${request.agentId}` : ''}`);
    }

    // Get task-specific settings
    const taskSettings = TASK_TYPE_CAPABILITIES[agent.taskType] ?? TASK_TYPE_CAPABILITIES.default;

    // Determine if we should use realtime mode
    const useRealtime = request.realtime ?? (
      this.config.realtimeEnabled && taskSettings.preferRealtime
    );

    // Build messages
    const messages: MercuryChatMessage[] = [];

    // System prompt
    const systemPrompt = request.systemPrompt ?? this.buildDefaultSystemPrompt(agent, request.stage);
    messages.push({ role: 'system', content: systemPrompt });

    // Add conversation history
    if (request.conversationHistory?.length) {
      messages.push(...request.conversationHistory);
    }

    // Add user query
    messages.push({ role: 'user', content: request.query });

    // Make the request
    const options: MercuryCoderRequestOptions & {
      model?: 'mercury' | 'mercury-coder' | 'mercury-coder-small';
      temperature?: number;
      max_tokens?: number;
      responseFormat?: { type: 'json_schema'; json_schema: MercuryStructuredOutputSchema };
    } = {
      realtime: useRealtime,
      temperature: taskSettings.suggestedTemperature,
      max_tokens: Math.min(agent.maxTokens, taskSettings.suggestedMaxTokens),
      agentId: agent.id,
      phaseId: request.stage,
      userId: request.userId,
      sessionId: request.sessionId,
      researchId: request.researchId,
      taskType: agent.taskType,
      metadata: {
        agentName: agent.name,
        stageNumber: request.stage,
        ...request.metadata,
      },
    };

    // Add structured schema if provided
    if (request.structuredSchema && this.config.structuredOutputsEnabled) {
      options.responseFormat = {
        type: 'json_schema',
        json_schema: request.structuredSchema,
      };
    }

    const response = await this.provider.chat(messages, options);

    return {
      agent,
      response,
      realtimeUsed: useRealtime,
      structured: response.structured,
    };
  }

  /**
   * Realtime agent chat - for voice assistants, chatbots, low-latency workflows
   */
  async realtimeAgentChat(
    agentId: string,
    query: string,
    options?: {
      userId?: string;
      sessionId?: string;
      conversationHistory?: MercuryChatMessage[];
    }
  ): Promise<MercuryAgentResponse> {
    const agent = getAgentById(agentId);
    if (!agent) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    // Find stage for this agent
    const stage = this.findStageForAgent(agentId);

    return this.sendAgentMessage({
      stage,
      agentId,
      query,
      realtime: true,
      userId: options?.userId,
      sessionId: options?.sessionId,
      conversationHistory: options?.conversationHistory,
    });
  }

  /**
   * Structured agent response - for typed outputs
   */
  async structuredAgentChat<T extends Record<string, unknown>>(
    agentId: string,
    query: string,
    schema: MercuryStructuredOutputSchema,
    options?: {
      userId?: string;
      sessionId?: string;
    }
  ): Promise<MercuryAgentResponse & { structured: T }> {
    const agent = getAgentById(agentId);
    if (!agent) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    const stage = this.findStageForAgent(agentId);

    const result = await this.sendAgentMessage({
      stage,
      agentId,
      query,
      structuredSchema: schema,
      userId: options?.userId,
      sessionId: options?.sessionId,
    });

    return result as MercuryAgentResponse & { structured: T };
  }

  /**
   * Code autocomplete using FIM endpoint
   * For development-related agents
   */
  async codeAutocomplete(
    prefix: string,
    suffix: string,
    options?: {
      agentId?: string;
      userId?: string;
      sessionId?: string;
    }
  ): Promise<MercuryResponse> {
    return this.provider.fim({
      prompt: prefix,
      suffix,
      max_tokens: 256,
      temperature: 0.2,
    }, {
      agentId: options?.agentId,
      userId: options?.userId,
      sessionId: options?.sessionId,
      taskType: 'autocomplete',
    });
  }

  /**
   * Apply code edit using Apply endpoint
   * For code refactoring agents
   */
  async applyCodeEdit(
    originalCode: string,
    updateSnippet: string,
    options?: {
      agentId?: string;
      userId?: string;
      sessionId?: string;
      language?: string;
    }
  ): Promise<MercuryResponse> {
    return this.provider.applyEdit({
      originalCode,
      updateSnippet,
      language: options?.language,
    }, {
      agentId: options?.agentId,
      userId: options?.userId,
      sessionId: options?.sessionId,
      taskType: 'apply-edit',
    });
  }

  /**
   * Predict next edit using Edit endpoint
   * For intelligent code editing suggestions
   */
  async predictNextEdit(
    currentFilePath: string,
    currentFileContent: string,
    codeToEdit: string,
    editHistory?: Array<{ filePath: string; before: string; after: string }>,
    options?: {
      agentId?: string;
      userId?: string;
      sessionId?: string;
      cursorPosition?: { line: number; column: number };
    }
  ): Promise<MercuryResponse> {
    return this.provider.nextEdit({
      currentFilePath,
      currentFileContent,
      codeToEdit,
      editDiffHistory: editHistory,
      cursorPosition: options?.cursorPosition,
    }, {
      agentId: options?.agentId,
      userId: options?.userId,
      sessionId: options?.sessionId,
      taskType: 'next-edit',
    });
  }

  /**
   * Get agent with Mercury capabilities info
   */
  getAgentCapabilities(agentId: string) {
    const agent = getAgentById(agentId);
    if (!agent) {
      return null;
    }

    const taskSettings = TASK_TYPE_CAPABILITIES[agent.taskType] ?? TASK_TYPE_CAPABILITIES.default;

    return {
      agent,
      mercuryCapabilities: {
        realtimeRecommended: taskSettings.preferRealtime,
        suggestedTemperature: taskSettings.suggestedTemperature,
        suggestedMaxTokens: taskSettings.suggestedMaxTokens,
        structuredOutputsAvailable: this.config.structuredOutputsEnabled,
        fimAvailable: ['code', 'classify', 'template_fill'].includes(agent.taskType),
        applyEditAvailable: true,
        nextEditAvailable: true,
      },
    };
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    return this.provider.healthCheck();
  }

  // ==========================================================================
  // Private Methods
  // ==========================================================================

  private buildDefaultSystemPrompt(agent: PhaseAgentDefinition, stage: number): string {
    const stageDescriptions: Record<number, string> = {
      1: 'Data ingestion and cleaning',
      2: 'Data validation and de-duplication',
      3: 'Variable identification and mapping',
      4: 'Cohort definition and eligibility',
      5: 'Data quality verification',
      6: 'Descriptive statistics and profiling',
      7: 'Statistical analysis design',
      8: 'Model building and tuning',
      9: 'Results interpretation',
      10: 'Results synthesis and QC',
      11: 'Manuscript drafting (Introduction)',
      12: 'Manuscript drafting (Methods)',
      13: 'Manuscript drafting (Results)',
      14: 'Manuscript drafting (Discussion)',
      15: 'Abstract generation',
      16: 'Poster and presentation preparation',
      17: 'Submission planning',
      18: 'Compliance and IRB checks',
      19: 'Final QA',
      20: 'Production handoff',
    };

    const stageDescription = stageDescriptions[stage] ?? 'workflow stage';

    return [
      `You are the ${agent.name} for ResearchFlow.`,
      `Current stage: ${stage} - ${stageDescription}`,
      `Your task type: ${agent.taskType}`,
      agent.description ? `Description: ${agent.description}` : '',
      agent.stageHints?.length ? `Focus areas: ${agent.stageHints.join(', ')}` : '',
      'Respond concisely and include actionable next steps when appropriate.',
      'Follow PHI safety rules and do not include any protected health information.',
    ].filter(Boolean).join('\n');
  }

  private findStageForAgent(agentId: string): number {
    // Search through stages to find which one contains this agent
    const stageToAgents: Record<number, string[]> = {
      1: ['data-extraction'],
      2: ['data-validation', 'data-extraction'],
      3: ['variable-identification', 'data-extraction'],
      4: ['cohort-definition', 'variable-identification'],
      5: ['data-validation', 'cohort-definition'],
      6: ['descriptive-stats', 'statistical-analysis'],
      7: ['statistical-analysis', 'model-builder'],
      8: ['model-builder', 'statistical-analysis'],
      9: ['results-interpreter', 'statistical-analysis'],
      10: ['results-interpreter', 'model-builder'],
      11: ['introduction-writer', 'manuscript-drafting'],
      12: ['methods-writer', 'manuscript-drafting'],
      13: ['results-writer', 'manuscript-drafting'],
      14: ['discussion-writer', 'manuscript-drafting'],
      15: ['abstract-generator', 'research-brief'],
      16: ['poster-designer', 'presentation-prep'],
      17: ['conference-scout', 'presentation-prep'],
      18: ['cohort-definition', 'data-validation'],
      19: ['results-interpreter', 'data-validation'],
      20: ['manuscript-drafting', 'research-brief'],
    };

    for (const [stage, agents] of Object.entries(stageToAgents)) {
      if (agents.includes(agentId)) {
        return parseInt(stage, 10);
      }
    }

    return 1; // Default to stage 1
  }
}

// ============================================================================
// Singleton Instance
// ============================================================================

let serviceInstance: MercuryAgentIntegrationService | null = null;

export function getMercuryAgentIntegrationService(
  config?: Partial<MercuryAgentConfig>
): MercuryAgentIntegrationService {
  if (!serviceInstance) {
    serviceInstance = new MercuryAgentIntegrationService(config);
  }
  return serviceInstance;
}

export default MercuryAgentIntegrationService;
