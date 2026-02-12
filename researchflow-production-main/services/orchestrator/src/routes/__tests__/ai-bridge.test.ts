/**
 * AI Bridge API Integration Tests
 *
 * Tests the bridge endpoints that connect Python agents to the AI Router.
 * These tests verify the complete integration flow:
 * Test Client → AI Bridge → AI Router → Mock LLM Response
 */

import assert from 'node:assert';
import { beforeEach, describe, expect, it, test, vi } from 'vitest';

import express from 'express';
import request from 'supertest';

// --- Mock infrastructure-dependent modules BEFORE importing the route ---

// Mock axios so the route doesn't make real HTTP calls
const mockAxiosGet = vi.fn();
const mockAxiosPost = vi.fn();
vi.mock('axios', () => ({
  default: {
    get: (...args: any[]) => mockAxiosGet(...args),
    post: (...args: any[]) => mockAxiosPost(...args),
    create: vi.fn(() => ({
      get: (...args: any[]) => mockAxiosGet(...args),
      post: (...args: any[]) => mockAxiosPost(...args),
    })),
    isAxiosError: vi.fn(() => false),
  },
}));

// Mock RBAC middleware — allow all requests
vi.mock('../../middleware/rbac', () => ({
  requirePermission: () => (_req: any, _res: any, next: any) => next(),
}));

// Mock audit service
vi.mock('../../services/audit-service', () => ({
  logAction: vi.fn(() => Promise.resolve()),
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    logError: vi.fn(),
    debug: vi.fn(),
  }),
}));

// Mock middleware that may have side effects
const mockValidateBatch = vi.fn(() => ({ valid: true, errors: [] }));
const mockOptimizeBatch = vi.fn((requests: any[]) => [{
  requests,
  processingStrategy: 'parallel' as const,
}]);
vi.mock('../../middleware/ai-bridge-batch-optimizer', () => ({
  getBatchOptimizer: vi.fn(() => ({
    validateBatch: (...args: any[]) => mockValidateBatch(...args),
    optimizeBatch: (...args: any[]) => mockOptimizeBatch(...args),
    getProcessingRecommendations: vi.fn(() => ({
      totalEstimatedCost: 0.01,
      estimatedDuration: '1s',
    })),
  })),
}));
// Connection pool mock — provides both `request` (used by getAIRouting) and `getStats`
const mockPoolRequest = vi.fn();
vi.mock('../../middleware/ai-bridge-connection-pool', () => ({
  getConnectionPool: vi.fn(() => ({
    request: (...args: any[]) => mockPoolRequest(...args),
    getStats: vi.fn(() => ({})),
  })),
}));
vi.mock('../../middleware/ai-bridge-error-handler', () => ({
  enhancedErrorHandlerMiddleware: (_req: any, _res: any, next: any) => next(),
  getAIBridgeErrorHandler: vi.fn(() => ({
    handleError: vi.fn(),
  })),
}));
vi.mock('../../middleware/ai-bridge-metrics', () => ({
  aiBridgeMetricsMiddleware: (_req: any, _res: any, next: any) => next(),
  metricsRegistry: { metrics: vi.fn(() => ''), contentType: 'text/plain' },
}));
vi.mock('../../middleware/ai-bridge-rate-limiter', () => ({
  rateLimitMiddleware: (_req: any, _res: any, next: any) => next(),
  costProtectionMiddleware: (_req: any, _res: any, next: any) => next(),
  circuitBreakerMiddleware: (_req: any, _res: any, next: any) => next(),
  recordCircuitBreakerOutcome: vi.fn(),
}));
vi.mock('../../middleware/ai-bridge-protection', () => ({
  rateLimitMiddleware: (_req: any, _res: any, next: any) => next(),
  costProtectionMiddleware: (_req: any, _res: any, next: any) => next(),
  circuitBreakerMiddleware: (_req: any, _res: any, next: any) => next(),
  recordCircuitBreakerOutcome: vi.fn(),
  updateCostTracking: vi.fn(),
}));

// Mock the LLM provider so the route never calls real APIs
const mockCallRealLLM = vi.fn();
const mockStreamRealLLM = vi.fn();
vi.mock('../../services/ai-bridge-llm', () => ({
  callRealLLMProvider: (...args: any[]) => mockCallRealLLM(...args),
  streamRealLLMProvider: (...args: any[]) => mockStreamRealLLM(...args),
}));

import aiBridgeRoutes from '../ai-bridge';

// Alias for backward compat with existing test code
const mockAxios = {
  post: mockAxiosPost,
  get: mockAxiosGet,
};

// Create test app factory
function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use((req, res, next) => {
    // Mock authenticated user
    req.user = {
      id: 'test-user-123',
      email: 'test@example.com',
      role: 'RESEARCHER',
    };
    next();
  });
  app.use('/api/ai-bridge', aiBridgeRoutes);
  return app;
}

describe('AI Bridge API', () => {
  let app: ReturnType<typeof createTestApp>;

  beforeEach(() => {
    app = createTestApp();
    mockAxios.post.mockReset();
    mockAxios.get.mockReset();
    mockPoolRequest.mockReset();
    mockCallRealLLM.mockReset();
    mockStreamRealLLM.mockReset();
    mockValidateBatch.mockReset();
    mockOptimizeBatch.mockReset();

    // Default batch optimizer behaviour
    mockValidateBatch.mockReturnValue({ valid: true, errors: [] });
    mockOptimizeBatch.mockImplementation((requests: any[]) => [{
      requests,
      processingStrategy: 'parallel' as const,
    }]);

    // Default: connection pool request returns AI Router routing
    mockPoolRequest.mockResolvedValue({
      data: {
        selectedTier: 'standard',
        model: 'claude-3-5-sonnet-20241022',
        costEstimate: { total: 0.05, input: 0.02, output: 0.03 },
      },
    });

    // Default: LLM provider returns a mock response
    mockCallRealLLM.mockResolvedValue({
      content: 'AI Bridge response for testing.',
      usage: { totalTokens: 150, promptTokens: 100, completionTokens: 50 },
      cost: { total: 0.003, input: 0.002, output: 0.001 },
      finishReason: 'stop',
    });

    // Default: Stream LLM returns an async iterable of chunks.
    // The route reads event.response.{content,usage,cost,finishReason} on 'done'.
    mockStreamRealLLM.mockReturnValue((async function* () {
      yield { type: 'content', content: 'Streamed ' };
      yield { type: 'content', content: 'response.' };
      yield {
        type: 'done',
        response: {
          content: 'Streamed response.',
          usage: { totalTokens: 50, promptTokens: 30, completionTokens: 20 },
          cost: { total: 0.001, input: 0.0005, output: 0.0005 },
          finishReason: 'stop',
        },
      };
    })());

    // Default: health check via axios succeeds
    mockAxios.get.mockImplementation((url: string) => {
      if (url.includes('/api/ai/router/tiers')) {
        return Promise.resolve({ status: 200, data: { tiers: [] } });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    // Default: axios post (used by some internal paths)
    mockAxios.post.mockImplementation((url: string) => {
      if (url.includes('/api/ai/router/route')) {
        return Promise.resolve({
          data: {
            selectedTier: 'standard',
            model: 'claude-3-5-sonnet-20241022',
            costEstimate: { total: 0.05, input: 0.02, output: 0.03 },
          },
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
  });

  describe('GET /api/ai-bridge/smoke', () => {
    test('should return realProvider and message', async () => {
      const app = createTestApp();
      const response = await request(app)
        .get('/api/ai-bridge/smoke')
        .expect(200);

      assert.strictEqual(typeof response.body.realProvider, 'boolean');
      assert.ok(typeof response.body.message === 'string' || response.body.providers);
      if (response.body.providers) {
        assert.strictEqual(typeof response.body.providers.anthropic, 'boolean');
        assert.strictEqual(typeof response.body.providers.openai, 'boolean');
      }
    });
  });

  describe('GET /api/ai-bridge/health', () => {
    test('should return health status', async () => {
      const app = createTestApp();
      const response = await request(app)
        .get('/api/ai-bridge/health')
        .expect(200);

      assert.strictEqual(response.body.status, 'healthy');
      assert(typeof response.body.timestamp === 'string');
      assert.strictEqual(response.body.bridge.version, '1.0.0');
      assert.strictEqual(response.body.bridge.healthy, true);
    });

    it('should handle AI Router being down', async () => {
      mockAxios.get.mockRejectedValue(new Error('Connection refused'));

      const response = await request(app)
        .get('/api/ai-bridge/health')
        .expect(503);

      expect(response.body.status).toBe('degraded');
      expect(response.body.dependencies.aiRouter.healthy).toBe(false);
    });
  });

  describe('GET /api/ai-bridge/capabilities', () => {
    it('should return bridge capabilities', async () => {
      const response = await request(app)
        .get('/api/ai-bridge/capabilities')
        .expect(200);

      expect(response.body.version).toBe('1.0.0');
      expect(response.body.endpoints).toBeDefined();
      expect(response.body.endpoints.length).toBeGreaterThanOrEqual(4);
      // Verify key endpoints exist (shape may include description field)
      const paths = response.body.endpoints.map((e: any) => e.path);
      expect(paths).toContain('/invoke');
      expect(paths).toContain('/batch');
      expect(paths).toContain('/stream');
      expect(paths).toContain('/health');
      expect(response.body.features).toBeDefined();
      expect(response.body.limits).toBeDefined();
    });
  });

  describe('POST /api/ai-bridge/invoke', () => {
    const validRequest = {
      prompt: 'Analyze this clinical data for potential PHI.',
      options: {
        taskType: 'phi_redaction',
        stageId: 5,
        modelTier: 'PREMIUM',
        governanceMode: 'LIVE',
        requirePhiCompliance: true,
      },
      metadata: {
        agentId: 'irb-agent-001',
        projectId: 'project-123',
        runId: 'run-456',
        threadId: 'thread-789',
        stageRange: [1, 20],
        currentStage: 5,
      },
    };

    it('should return response shape (content, usage, cost, model, tier, finishReason) and non-mock content when provider is available', async () => {
      const response = await request(app)
        .post('/api/ai-bridge/invoke')
        .send(validRequest)
        .expect(200);

      assert.ok(typeof response.body.content === 'string', 'content must be string');
      assert.ok(response.body.usage?.totalTokens !== undefined);
      assert.ok(response.body.usage?.promptTokens !== undefined);
      assert.ok(response.body.usage?.completionTokens !== undefined);
      assert.ok(typeof response.body.cost?.total === 'number');
      assert.ok(typeof response.body.model === 'string');
      assert.ok(typeof response.body.tier === 'string');
      assert.ok(typeof response.body.finishReason === 'string');
      assert.ok(response.body.metadata?.requestId);
      assert.ok(response.body.metadata?.bridgeVersion === '1.0.0');
    });

    it('should validate request body', async () => {
      const invalidRequest = {
        // Missing prompt
        options: {
          taskType: 'analysis',
        },
      };

      const response = await request(app)
        .post('/api/ai-bridge/invoke')
        .send(invalidRequest)
        .expect(400);

      expect(response.body.error).toBe('VALIDATION_ERROR');
      expect(response.body.details).toBeDefined();
    });

    it('should require authentication', async () => {
      const appNoAuth = express();
      appNoAuth.use(express.json());
      // No user mock - req.user is undefined
      appNoAuth.use('/api/ai-bridge', aiBridgeRoutes);

      const response = await request(appNoAuth)
        .post('/api/ai-bridge/invoke')
        .send(validRequest)
        .expect(401);

      expect(response.body.error).toBe('AUTHENTICATION_REQUIRED');
    });

    it('should handle AI Router failures gracefully', async () => {
      // getAIRouting catches the pool error and returns default routing,
      // so the LLM call (mocked) still succeeds → expect 200 with fallback values.
      mockPoolRequest.mockRejectedValue(new Error('AI Router down'));

      const response = await request(app)
        .post('/api/ai-bridge/invoke')
        .send(validRequest)
        .expect(200);

      expect(response.body.content).toBeDefined();
      // Fallback routing uses 'standard' tier and default model
      expect(response.body.tier).toBe('standard');
      expect(response.body.model).toBe('claude-3-5-sonnet-20241022');
    });
  });

  describe('POST /api/ai-bridge/batch', () => {
    const validBatchRequest = {
      prompts: [
        'Summarize this research paper.',
        'Extract key findings from the data.',
        'Generate hypothesis based on results.',
      ],
      options: {
        taskType: 'summarization',
        modelTier: 'STANDARD',
        governanceMode: 'DEMO',
      },
      metadata: {
        agentId: 'manuscript-agent',
        projectId: 'project-123',
        runId: 'batch-run-456',
        threadId: 'thread-batch',
        stageRange: [10, 15],
        currentStage: 12,
      },
    };

    it('should process batch requests', async () => {
      const response = await request(app)
        .post('/api/ai-bridge/batch')
        .send(validBatchRequest)
        .expect(200);

      expect(response.body.responses).toBeDefined();
      expect(response.body.responses).toHaveLength(3);
      expect(response.body.successCount).toBe(3);
      expect(response.body.errorCount).toBe(0);
      expect(response.body.metadata?.bridgeVersion).toBe('1.0.0');
    });

    it('should enforce batch size limits', async () => {
      // Make the batch optimizer reject oversized batches
      mockValidateBatch.mockReturnValueOnce({
        valid: false,
        errors: ['Batch size 15 exceeds maximum of 10'],
      });

      const largeBatch = {
        ...validBatchRequest,
        prompts: new Array(15).fill('Test prompt'),
      };

      const response = await request(app)
        .post('/api/ai-bridge/batch')
        .send(largeBatch)
        .expect(400);

      expect(response.body.error).toBe('BATCH_VALIDATION_FAILED');
    });

    it('should handle partial batch failures', async () => {
      // Simulate one LLM call failing
      let callCount = 0;
      mockCallRealLLM.mockImplementation(() => {
        callCount++;
        if (callCount === 2) {
          return Promise.reject(new Error('Temporary failure'));
        }
        return Promise.resolve({
          content: 'AI Bridge response.',
          usage: { totalTokens: 50, promptTokens: 30, completionTokens: 20 },
          cost: { total: 0.001, input: 0.0005, output: 0.0005 },
          finishReason: 'stop',
        });
      });

      const response = await request(app)
        .post('/api/ai-bridge/batch')
        .send(validBatchRequest)
        .expect(200);

      expect(response.body.successCount).toBe(2);
      expect(response.body.errorCount).toBe(1);
      expect(response.body.responses).toHaveLength(3);

      // One response should be an error
      const errorResponse = response.body.responses.find((r: any) => r.error);
      expect(errorResponse).toBeDefined();
    });
  });

  describe('POST /api/ai-bridge/stream', () => {
    const validStreamRequest = {
      prompt: 'Generate a comprehensive analysis of the study results.',
      options: {
        taskType: 'data_analysis',
        modelTier: 'PREMIUM',
        governanceMode: 'LIVE',
      },
      metadata: {
        agentId: 'analysis-agent',
        projectId: 'project-123',
        runId: 'stream-run-789',
        threadId: 'thread-stream',
        stageRange: [6, 8],
        currentStage: 7,
      },
    };

    it('should stream LLM responses', async () => {
      const response = await request(app)
        .post('/api/ai-bridge/stream')
        .send(validStreamRequest)
        .expect(200);

      // Check SSE headers
      expect(response.headers['content-type']).toBe('text/event-stream');
      expect(response.headers['cache-control']).toBe('no-cache');
      expect(response.headers.connection).toBe('keep-alive');

      // Check that response contains full SSE lifecycle
      const responseText = response.text;
      expect(responseText).toContain('data: ');
      expect(responseText).toContain('"type":"status"');
      expect(responseText).toContain('"type":"content"');
      expect(responseText).toContain('"type":"complete"');
      expect(responseText).toContain('data: [DONE]');
    });

    it('should include streaming metadata', async () => {
      const response = await request(app)
        .post('/api/ai-bridge/stream')
        .send(validStreamRequest)
        .expect(200);

      const lines = response.text.split('\n');
      const statusLine = lines.find(line => 
        line.startsWith('data: ') && line.includes('"type":"status"')
      );
      
      expect(statusLine).toBeDefined();
      const statusData = JSON.parse(statusLine!.substring(6));
      expect(statusData).toMatchObject({
        type: 'status',
        status: 'starting',
        tier: 'standard',
        model: 'claude-3-5-sonnet-20241022',
      });
    });
  });
});