import { ModelRouterService, type AIRouterResponse, getMercuryCoderProvider, type MercuryResponse } from '@researchflow/ai-router';
import { chatRepository } from '../../repositories/chat.repository';
import { getGovernanceDecision, scanForPHI, type PHIScanResult } from '../../utils/phi-scanner';
import {
  getAgentById,
  getAgentsForStage,
  listAgents,
  STAGE_DESCRIPTIONS,
  type PhaseAgentDefinition,
} from './registry';
import { phaseRagService, type RagContextItem } from './rag.service';

export interface PhaseChatInput {
  stage: number;
  query: string;
  topic?: string;
  context?: Record<string, unknown>;
  agentId?: string;
  userId?: string;
  conversationId?: string;
  /** Use Mercury realtime mode for near-instant responses */
  useMercuryRealtime?: boolean;
  /** Use Mercury for this request (automatic if LIVE mode + low-latency task) */
  useMercury?: boolean;
}

export interface PhaseChatResult {
  stage: number;
  stageDescription: string;
  agent: PhaseAgentDefinition;
  sessionId: string;
  response: AIRouterResponse;
  ragContext: RagContextItem[];
  governance: {
    mode: 'DEMO' | 'LIVE';
    phiScan: PHIScanResult;
    decision: {
      allowed: boolean;
      reason: string;
      warning?: string;
    };
  };
  /** Mercury-specific metrics (if Mercury was used) */
  mercury?: {
    used: boolean;
    realtime: boolean;
    latencyMs: number;
    tokensPerSecond: number;
  };
}

// Task types that benefit from Mercury's realtime mode
const MERCURY_REALTIME_TASK_TYPES = [
  'classify',
  'extract_metadata',
  'template_fill',
  'policy_check',
  'summarize',
];

export class PhaseChatService {
  private router: ModelRouterService;
  private governanceMode: 'DEMO' | 'LIVE';
  private mercuryEnabled: boolean;

  constructor(router?: ModelRouterService) {
    this.router =
      router ||
      new ModelRouterService({
        defaultTier: process.env.PHASE_CHAT_DEFAULT_TIER as any || 'MINI',
        localModelEnabled: process.env.LOCAL_MODEL_ENABLED === 'true',
        localModelEndpoint: process.env.LOCAL_MODEL_ENDPOINT,
        localModelName: process.env.LOCAL_MODEL_NAME,
      });

    this.governanceMode = (process.env.GOVERNANCE_MODE?.toUpperCase() as 'DEMO' | 'LIVE') || 'DEMO';
    
    // Enable Mercury if we have an API key and we're in LIVE mode
    const mercuryKey =
      process.env.MERCURY_API_KEY ||
      process.env.INCEPTION_API_KEY ||
      process.env.INCEPTIONLABS_API_KEY;
    this.mercuryEnabled = !!mercuryKey && process.env.MERCURY_ENABLED !== 'false';
  }

  listAgents() {
    return listAgents();
  }

  async sendMessage(input: PhaseChatInput): Promise<PhaseChatResult> {
    if (input.stage < 1 || input.stage > 20 || Number.isNaN(input.stage)) {
      throw new Error('Invalid stage. Stage must be between 1 and 20.');
    }

    // PHI gate first
    const phiScan = scanForPHI(input.query);
    const decision = getGovernanceDecision(phiScan, this.governanceMode);
    if (!decision.allowed) {
      throw new Error(`PHI blocked: ${decision.reason}`);
    }

    const agentsForStage = getAgentsForStage(input.stage);
    const agent =
      (input.agentId && getAgentById(input.agentId)) ||
      agentsForStage[0];

    if (!agent) {
      throw new Error(`No agent configured for stage ${input.stage}`);
    }

    // Persist chat session/messages to reuse history and feedback
    const session = await chatRepository.findOrCreateSession({
      artifactType: 'phase',
      artifactId: `stage-${input.stage}`,
      agentType: 'phase',
      createdBy: input.userId || 'system',
      title: `Stage ${input.stage}: ${STAGE_DESCRIPTIONS[input.stage] || 'Unknown stage'}`,
    });

    const userMessage = await chatRepository.createMessage({
      sessionId: session.id,
      role: 'user',
      authorId: input.userId,
      content: input.query,
      metadata: {
        topic: input.topic,
        context: input.context || {},
        agentId: agent.id,
        stage: input.stage,
      },
      phiDetected: phiScan.hasPHI,
    });

    // Retrieve contextual snippets (RAG) for this agent/stage
    const ragContext = await phaseRagService.retrieve(agent.knowledgeBase as any, input.query, {
      topK: 4,
    });

    const systemPrompt = this.buildSystemPrompt(agent, input.stage, input.topic, ragContext);
    const userPrompt = this.buildUserPrompt(input.query, input.topic, ragContext);

    // Determine if we should use Mercury
    const shouldUseMercury = this.shouldUseMercury(agent, input);
    const useRealtime = input.useMercuryRealtime ?? MERCURY_REALTIME_TASK_TYPES.includes(agent.taskType);

    let aiResponse: AIRouterResponse;
    let mercuryMetrics: PhaseChatResult['mercury'];

    if (shouldUseMercury) {
      // Use Mercury for ultra-fast responses
      const mercuryResult = await this.sendMercuryMessage(
        systemPrompt,
        userPrompt,
        agent,
        input,
        useRealtime
      );
      
      aiResponse = mercuryResult.response;
      mercuryMetrics = mercuryResult.metrics;
    } else {
      // Use standard router
      try {
        aiResponse = await this.router.route({
          taskType: agent.taskType,
          prompt: userPrompt,
          systemPrompt,
          responseFormat: 'text',
          maxTokens: agent.maxTokens,
          forceTier: this.preferredTier(agent.modelTier),
          metadata: {
            stageId: input.stage,
            sessionId: session.id,
            userId: input.userId,
          },
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown AI router error';
        throw new Error(`Phase chat AI routing failed: ${message}`);
      }
    }

    // Store assistant message with routing + RAG metadata
    await chatRepository.createMessage({
      sessionId: session.id,
      role: 'assistant',
      content: aiResponse.content,
      metadata: {
        agentId: agent.id,
        stage: input.stage,
        routing: aiResponse.routing,
        qualityGate: aiResponse.qualityGate,
        ragContext,
        source: shouldUseMercury ? 'phase-chat-mercury' : 'phase-chat',
        parentMessageId: userMessage.id,
        mercuryMetrics,
      },
    });

    return {
      stage: input.stage,
      stageDescription: STAGE_DESCRIPTIONS[input.stage] || 'Unknown stage',
      agent,
      sessionId: session.id,
      response: aiResponse,
      ragContext,
      governance: {
        mode: this.governanceMode,
        phiScan,
        decision,
      },
      mercury: mercuryMetrics,
    };
  }

  /**
   * Send message via Mercury's ultra-fast diffusion LLM
   */
  private async sendMercuryMessage(
    systemPrompt: string,
    userPrompt: string,
    agent: PhaseAgentDefinition,
    input: PhaseChatInput,
    realtime: boolean
  ): Promise<{ response: AIRouterResponse; metrics: PhaseChatResult['mercury'] }> {
    const mercury = getMercuryCoderProvider();

    const mercuryResponse = await mercury.chat(
      [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      {
        realtime,
        temperature: this.getMercuryTemperature(agent.taskType),
        max_tokens: agent.maxTokens,
        agentId: agent.id,
        phaseId: input.stage,
        userId: input.userId,
        sessionId: input.conversationId,
        taskType: agent.taskType,
        metadata: {
          topic: input.topic,
          agentName: agent.name,
        },
      }
    );

    // Convert Mercury response to AIRouterResponse format
    const aiResponse: AIRouterResponse = {
      content: mercuryResponse.content,
      routing: {
        provider: 'mercury',
        model: mercuryResponse.model,
        tier: 'MERCURY' as any,
        taskType: agent.taskType,
        latencyMs: mercuryResponse.metrics.latencyMs,
      },
      usage: {
        inputTokens: mercuryResponse.usage.inputTokens,
        outputTokens: mercuryResponse.usage.outputTokens,
        totalTokens: mercuryResponse.usage.totalTokens,
        estimatedCostUsd: mercuryResponse.usage.estimatedCostUsd,
      },
      qualityGate: {
        passed: true,
        checks: [],
      },
    };

    return {
      response: aiResponse,
      metrics: {
        used: true,
        realtime: mercuryResponse.realtime,
        latencyMs: mercuryResponse.metrics.latencyMs,
        tokensPerSecond: mercuryResponse.metrics.tokensPerSecond,
      },
    };
  }

  /**
   * Determine if Mercury should be used for this request
   */
  private shouldUseMercury(agent: PhaseAgentDefinition, input: PhaseChatInput): boolean {
    // Explicitly requested
    if (input.useMercury === true) return true;
    if (input.useMercury === false) return false;

    // Mercury not available
    if (!this.mercuryEnabled) return false;

    // In LIVE mode, use Mercury for low-latency tasks
    if (this.governanceMode === 'LIVE') {
      // Use Mercury for realtime-friendly task types
      if (MERCURY_REALTIME_TASK_TYPES.includes(agent.taskType)) {
        return true;
      }
    }

    // Explicitly requested realtime mode
    if (input.useMercuryRealtime) return true;

    return false;
  }

  /**
   * Get appropriate temperature for Mercury based on task type
   */
  private getMercuryTemperature(taskType: string): number {
    const temperatures: Record<string, number> = {
      'classify': 0.3,
      'extract_metadata': 0.2,
      'template_fill': 0.3,
      'policy_check': 0.2,
      'summarize': 0.5,
      'abstract_generate': 0.6,
      'draft_section': 0.7,
      'protocol_reasoning': 0.5,
      'complex_synthesis': 0.6,
    };
    return temperatures[taskType] ?? 0.5;
  }

  private preferredTier(agentTier: PhaseAgentDefinition['modelTier']) {
    if (process.env.PREFERRED_PHASE_TIER === 'LOCAL') {
      return 'LOCAL';
    }
    return agentTier;
  }

  private buildSystemPrompt(
    agent: PhaseAgentDefinition,
    stage: number,
    topic: string | undefined,
    ragContext: RagContextItem[]
  ) {
    const stageDescription = STAGE_DESCRIPTIONS[stage] || 'workflow stage';
    const contextSnippet = ragContext
      .slice(0, 3)
      .map((c, idx) => `Context ${idx + 1}: ${c.content}`)
      .join('\n\n');

    return [
      `You are the ${agent.name} for ResearchFlow stage ${stage}: ${stageDescription}.`,
      `Your task type is ${agent.taskType} and you must follow PHI safety rules.`,
      topic ? `Focus topic: ${topic}` : '',
      contextSnippet ? `Use these RAG context snippets when relevant:\n${contextSnippet}` : '',
      'Respond concisely and include actionable next steps.',
    ]
      .filter(Boolean)
      .join('\n\n');
  }

  private buildUserPrompt(
    query: string,
    topic: string | undefined,
    ragContext: RagContextItem[]
  ) {
    const citations = ragContext
      .map((c) => `- [${c.id || 'context'}] ${c.content}`)
      .join('\n');

    return [
      topic ? `Topic: ${topic}` : '',
      `User query: ${query}`,
      ragContext.length ? `Relevant context:\n${citations}` : '',
      'Return a helpful answer and proposed actions if applicable.',
    ]
      .filter(Boolean)
      .join('\n\n');
  }
}

export const phaseChatService = new PhaseChatService();
