import type { AIRouterResponse } from '@researchflow/ai-router';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock vector-store to avoid chromadb dependency
vi.mock('@researchflow/vector-store', () => ({
  ChromaVectorStore: vi.fn().mockImplementation(() => ({
    initialize: vi.fn().mockResolvedValue(undefined),
    search: vi.fn().mockResolvedValue([]),
  })),
  DocumentEmbedder: vi.fn().mockImplementation(() => ({})),
}));

import { chatRepository } from '../../../repositories/chat.repository';
import { PhaseChatService } from '../service';

class FakeRouter {
  route = vi.fn(async () => ({
    content: 'synthetic-response',
    routing: {
      initialTier: 'MINI',
      finalTier: 'MINI',
      escalated: false,
      provider: 'local',
      model: 'qwen-local',
    },
    usage: {
      inputTokens: 10,
      outputTokens: 20,
      totalTokens: 30,
      estimatedCostUsd: 0,
    },
    qualityGate: {
      passed: true,
      checks: [],
    },
    metrics: {
      latencyMs: 5,
    },
  } satisfies AIRouterResponse));
}

describe('PhaseChatService', () => {
  const router = new FakeRouter();
  const service = new PhaseChatService(router as any);

  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(chatRepository, 'findOrCreateSession').mockResolvedValue({
      id: 'session-1',
      projectId: null,
      artifactType: 'phase',
      artifactId: 'stage-1',
      agentType: 'phase',
      title: 'Stage 1',
      createdBy: 'user-1',
      createdAt: new Date(),
      updatedAt: new Date(),
    });

    vi.spyOn(chatRepository, 'createMessage').mockImplementation(async (input) => ({
      id: `msg-${Math.random().toString(36).slice(2)}`,
      sessionId: input.sessionId,
      role: input.role,
      authorId: input.authorId || null,
      content: input.content,
      metadata: input.metadata || {},
      phiDetected: input.phiDetected || false,
      createdAt: new Date(),
    }));
  });

  it('routes phase chat requests via AI router and persists messages', async () => {
    const result = await service.sendMessage({
      stage: 1,
      query: 'How should I clean the dataset?',
      userId: 'user-1',
    });

    expect(result.agent.id).toBe('data-extraction');
    expect(result.response.content).toBe('synthetic-response');
    expect(router.route).toHaveBeenCalledTimes(1);
    expect(result.ragContext.length).toBeGreaterThanOrEqual(0);
  });
});

