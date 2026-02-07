/**
 * Chat Agent Service
 *
 * Core service for AI-powered workflow chat agents.
 * Handles:
 * - LLM provider integration (OpenAI, Anthropic)
 * - PHI scanning and governance
 * - Session and message management
 * - Action parsing and proposal
 */

import { chatRepository, ChatSession, ChatMessage, ChatAction } from '../../repositories/chat.repository';
import { scanForPHI, getGovernanceDecision, type PHIScanResult } from '../../utils/phi-scanner';

import {
  getSystemPrompt,
  buildPrompt,
  parseActions,
  cleanResponse,
  ACTION_TYPE_MAP,
  type AgentType,
} from './prompts';

// Types
export interface ChatAgentConfig {
  model?: string;
  temperature?: number;
  maxTokens?: number;
  provider?: 'openai' | 'anthropic';
}

export interface SendMessageInput {
  agentType: AgentType;
  artifactType: string;
  artifactId: string;
  content: string;
  userId: string;
  projectId?: string;
  context?: {
    artifactContent?: string;
    artifactMetadata?: Record<string, unknown>;
    projectContext?: Record<string, unknown>;
  };
}

export interface CostMetrics {
  provider: string;
  model: string;
  tokensIn: number;
  tokensOut: number;
  latencyMs: number;
  costUsd: number;
}

export interface SendMessageResult {
  session: ChatSession;
  userMessage: ChatMessage;
  assistantMessage: ChatMessage;
  actions: ChatAction[];
  governance: {
    mode: 'DEMO' | 'LIVE';
    phiScan: PHIScanResult;
    decision: {
      allowed: boolean;
      reason: string;
      warning?: string;
    };
  };
  cost?: CostMetrics;
}

// Default configuration
const DEFAULT_CONFIG: ChatAgentConfig = {
  model: process.env.CHAT_AGENT_MODEL || 'gpt-4',
  temperature: 0.7,
  maxTokens: 2000,
  provider: (process.env.CHAT_AGENT_PROVIDER as 'openai' | 'anthropic') || 'openai',
};

const WORKER_URL = process.env.WORKER_URL || 'http://worker:8000';
const RAG_GUIDANCE_TOP_K = 3;

async function fetchFeedbackGuidance(agentType: AgentType, userMessage: string): Promise<string[]> {
  try {
    const query = `${agentType} ${userMessage.slice(0, 200)}`.trim();
    const res = await fetch(`${WORKER_URL}/agents/rag/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        collection: 'ai_feedback_guidance',
        query,
        top_k: RAG_GUIDANCE_TOP_K,
      }),
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) return [];
    const data = (await res.json()) as { results?: Array<{ content?: string }> };
    const results = data.results ?? [];
    return results.map((r) => (r.content ?? '').trim()).filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * ChatAgentService class
 */
export class ChatAgentService {
  private config: ChatAgentConfig;
  private governanceMode: 'DEMO' | 'LIVE';
  private lastCostMetrics?: CostMetrics;

  constructor(config?: Partial<ChatAgentConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.governanceMode = (process.env.GOVERNANCE_MODE?.toUpperCase() as 'DEMO' | 'LIVE') || 'DEMO';
  }

  /**
   * Get the cost metrics from the last LLM call
   */
  getLastCostMetrics(): CostMetrics | undefined {
    return this.lastCostMetrics;
  }

  /**
   * Send a message to the chat agent and get a response
   */
  async sendMessage(input: SendMessageInput): Promise<SendMessageResult> {
    // 1. PHI Scanning
    const phiScan = scanForPHI(input.content);
    const decision = getGovernanceDecision(phiScan, this.governanceMode);

    // 2. Governance check
    if (!decision.allowed) {
      throw new ChatAgentError('PHI_BLOCKED', decision.reason, { phiScan });
    }

    // 3. Get or create session
    const session = await chatRepository.findOrCreateSession({
      projectId: input.projectId,
      artifactType: input.artifactType,
      artifactId: input.artifactId,
      agentType: input.agentType,
      createdBy: input.userId,
    });

    // 4. Get conversation history
    const history = await chatRepository.getSessionMessages(session.id);

    // 5. Store user message
    const userMessage = await chatRepository.createMessage({
      sessionId: session.id,
      role: 'user',
      authorId: input.userId,
      content: input.content,
      metadata: { context: input.context },
      phiDetected: phiScan.hasPHI,
    });

    // 6. Build prompt with context
    let systemPrompt = getSystemPrompt(input.agentType);
    const guidanceSnippets = await fetchFeedbackGuidance(input.agentType, input.content);
    if (guidanceSnippets.length > 0) {
      systemPrompt =
        `## Known failure modes / guidance (from feedback)\n${guidanceSnippets.join('\n\n')}\n\n---\n\n` +
        systemPrompt;
    }
    const userPrompt = buildPrompt(input.agentType, input.content, {
      ...input.context,
      conversationHistory: history.map(m => ({ role: m.role, content: m.content })),
    });

    // 7. Call LLM
    let aiResponse: string;
    try {
      aiResponse = await this.callLLM(systemPrompt, userPrompt, history);
    } catch (error) {
      throw new ChatAgentError(
        'LLM_ERROR',
        `Failed to get response from ${this.config.provider}: ${error instanceof Error ? error.message : 'Unknown error'}`,
        { provider: this.config.provider }
      );
    }

    // 8. Parse actions from response
    const parsedActions = parseActions(aiResponse);
    const cleanedResponse = cleanResponse(aiResponse);

    // 9. Store assistant message
    const assistantMessage = await chatRepository.createMessage({
      sessionId: session.id,
      role: 'assistant',
      content: cleanedResponse,
      metadata: {
        model: this.config.model,
        provider: this.config.provider,
        hasActions: parsedActions.length > 0,
        rawResponse: aiResponse,
      },
    });

    // 10. Store proposed actions
    const actions: ChatAction[] = [];
    for (const action of parsedActions) {
      const dbAction = await chatRepository.createAction({
        messageId: assistantMessage.id,
        actionType: ACTION_TYPE_MAP[action.type] || action.type,
        payload: {
          type: action.type,
          section: action.section,
          name: action.name,
          content: action.content,
        },
      });
      actions.push(dbAction);
    }

    return {
      session,
      userMessage,
      assistantMessage,
      actions,
      governance: {
        mode: this.governanceMode,
        phiScan,
        decision,
      },
      cost: this.lastCostMetrics,
    };
  }

  /**
   * Call the LLM provider
   */
  private async callLLM(
    systemPrompt: string,
    userPrompt: string,
    history: ChatMessage[]
  ): Promise<string> {
    const messages = [
      { role: 'system' as const, content: systemPrompt },
      ...history.map(m => ({
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content,
      })),
      { role: 'user' as const, content: userPrompt },
    ];

    if (this.config.provider === 'anthropic') {
      return this.callAnthropic(messages);
    }

    return this.callOpenAI(messages);
  }

  /**
   * Call OpenAI API
   */
  private async callOpenAI(
    messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>
  ): Promise<string> {
    const apiKey = process.env.OPENAI_API_KEY;

    if (!apiKey) {
      // Return mock response if no API key
      this.lastCostMetrics = {
        provider: 'mock',
        model: 'mock',
        tokensIn: 0,
        tokensOut: 0,
        latencyMs: 0,
        costUsd: 0,
      };
      return this.getMockResponse(messages);
    }

    const startTime = Date.now();
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: this.config.model,
        messages,
        temperature: this.config.temperature,
        max_tokens: this.config.maxTokens,
      }),
    });

    const latencyMs = Date.now() - startTime;

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`OpenAI API error: ${error}`);
    }

    const data = await response.json();

    // Extract token usage from response
    const tokensIn = data.usage?.prompt_tokens || 0;
    const tokensOut = data.usage?.completion_tokens || 0;

    // Calculate cost
    const model = this.config.model || 'gpt-4';
    const costUsd = this.calculateOpenAICost(model, tokensIn, tokensOut);

    this.lastCostMetrics = {
      provider: 'openai',
      model,
      tokensIn,
      tokensOut,
      latencyMs,
      costUsd,
    };

    return data.choices[0]?.message?.content || '';
  }

  /**
   * Calculate OpenAI cost based on model and token usage
   */
  private calculateOpenAICost(model: string, tokensIn: number, tokensOut: number): number {
    // Pricing per million tokens
    const pricing: Record<string, { input: number; output: number }> = {
      'gpt-4': { input: 30.0, output: 60.0 },
      'gpt-4-turbo': { input: 10.0, output: 30.0 },
      'gpt-4o': { input: 5.0, output: 15.0 },
      'gpt-4o-mini': { input: 0.15, output: 0.6 },
      'gpt-3.5-turbo': { input: 0.5, output: 1.5 },
    };

    const modelPricing = pricing[model] || pricing['gpt-4'];
    return (
      (tokensIn / 1_000_000) * modelPricing.input +
      (tokensOut / 1_000_000) * modelPricing.output
    );
  }

  /**
   * Call Anthropic API
   */
  private async callAnthropic(
    messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>
  ): Promise<string> {
    const apiKey = process.env.ANTHROPIC_API_KEY;

    if (!apiKey) {
      // Return mock response if no API key
      this.lastCostMetrics = {
        provider: 'mock',
        model: 'mock',
        tokensIn: 0,
        tokensOut: 0,
        latencyMs: 0,
        costUsd: 0,
      };
      return this.getMockResponse(messages);
    }

    // Extract system message
    const systemMessage = messages.find(m => m.role === 'system')?.content || '';
    const conversationMessages = messages
      .filter(m => m.role !== 'system')
      .map(m => ({ role: m.role as 'user' | 'assistant', content: m.content }));

    const model = this.config.model?.includes('claude') ? this.config.model : 'claude-3-haiku-20240307';
    const startTime = Date.now();

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model,
        system: systemMessage,
        messages: conversationMessages,
        max_tokens: this.config.maxTokens,
        temperature: this.config.temperature,
      }),
    });

    const latencyMs = Date.now() - startTime;

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Anthropic API error: ${error}`);
    }

    const data = await response.json();

    // Extract token usage from response
    const tokensIn = data.usage?.input_tokens || 0;
    const tokensOut = data.usage?.output_tokens || 0;

    // Calculate cost
    const costUsd = this.calculateAnthropicCost(model, tokensIn, tokensOut);

    this.lastCostMetrics = {
      provider: 'anthropic',
      model,
      tokensIn,
      tokensOut,
      latencyMs,
      costUsd,
    };

    return data.content[0]?.text || '';
  }

  /**
   * Calculate Anthropic cost based on model and token usage
   */
  private calculateAnthropicCost(model: string, tokensIn: number, tokensOut: number): number {
    // Pricing per million tokens
    const pricing: Record<string, { input: number; output: number }> = {
      'claude-3-opus-20240229': { input: 15.0, output: 75.0 },
      'claude-3-sonnet-20240229': { input: 3.0, output: 15.0 },
      'claude-3-haiku-20240307': { input: 0.25, output: 1.25 },
      'claude-3-5-sonnet-20241022': { input: 3.0, output: 15.0 },
      'claude-sonnet-4-5-20250929': { input: 3.0, output: 15.0 },
      'claude-opus-4-5-20251101': { input: 15.0, output: 75.0 },
      'claude-haiku-4-5-20251001': { input: 0.25, output: 1.25 },
    };

    const modelPricing = pricing[model] || pricing['claude-3-haiku-20240307'];
    return (
      (tokensIn / 1_000_000) * modelPricing.input +
      (tokensOut / 1_000_000) * modelPricing.output
    );
  }

  /**
   * Get mock response for testing without API keys
   */
  private getMockResponse(
    messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>
  ): string {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user')?.content || '';
    const systemPrompt = messages.find(m => m.role === 'system')?.content || '';

    // Determine agent type from system prompt
    let agentType = 'manuscript';
    if (systemPrompt.includes('IRB')) agentType = 'irb';
    else if (systemPrompt.includes('statistical')) agentType = 'analysis';

    return `I understand your request regarding the ${agentType} document.

Based on your message: "${lastUserMessage.substring(0, 100)}${lastUserMessage.length > 100 ? '...' : ''}"

Here's my analysis and suggested approach:

1. **Initial Assessment**: Your request has been noted and I've analyzed the context.
2. **Recommendations**: I would suggest reviewing the relevant sections for potential improvements.
3. **Next Steps**: Consider the following edits to enhance clarity and compliance.

<action type="patch" section="draft">
[Suggested edit would appear here based on your specific request]
</action>

**Note**: This is a mock response. Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for full AI capabilities.`;
  }

  /**
   * Get session with messages
   */
  async getSessionWithMessages(sessionId: string): Promise<{
    session: ChatSession;
    messages: Array<ChatMessage & { actions?: ChatAction[] }>;
  }> {
    const session = await chatRepository.getSessionById(sessionId);
    const messages = await chatRepository.getSessionMessages(sessionId);

    // Attach actions to assistant messages
    const messagesWithActions = await Promise.all(
      messages.map(async message => {
        if (message.role === 'assistant') {
          const actions = await chatRepository.getMessageActions(message.id);
          return { ...message, actions };
        }
        return message;
      })
    );

    return { session, messages: messagesWithActions };
  }
}

/**
 * Custom error class for chat agent errors
 */
export class ChatAgentError extends Error {
  code: string;
  details?: Record<string, unknown>;

  constructor(code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ChatAgentError';
    this.code = code;
    this.details = details;
  }
}

// Export singleton instance
export const chatAgentService = new ChatAgentService();

export default chatAgentService;
