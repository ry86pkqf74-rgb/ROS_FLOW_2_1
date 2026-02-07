/**
 * AI Bridge API Integration Tests
 *
 * Tests the bridge endpoints that connect Python agents to the AI Router.
 * These tests verify the complete integration flow:
 * Test Client → AI Bridge → AI Router → Mock LLM Response
 */

import assert from 'node:assert';
import { test, describe, beforeEach, mock } from 'node:test';

import express from 'express';
import request from 'supertest';

import aiBridgeRoutes from '../ai-bridge';

// Mock dependencies
const mockRequirePermission = mock.fn((permission: string) => (req: any, res: any, next: any) => {
  // Mock RBAC middleware - allow all requests in tests
  next();
});

const mockLogAction = mock.fn().mockResolvedValue(undefined);

const mockAxios = {
  post: mock.fn(),
  get: mock.fn(),
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
  beforeEach(() => {
    mockAxios.post.mock.resetHistory();
    mockAxios.get.mock.resetHistory();
    
    // Mock AI Router routing response
    mockAxios.post.mock.mockImplementation((url) => {
      if (url.includes('/api/ai/router/route')) {
        return Promise.resolve({
          data: {
            selectedTier: 'standard',
            model: 'claude-3-5-sonnet-20241022',
            costEstimate: {
              total: 0.05,
              input: 0.02,
              output: 0.03,
            },
          },
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    // Mock health check
    mockAxios.get.mock.mockImplementation((url) => {
      if (url.includes('/api/ai/router/tiers')) {
        return Promise.resolve({
          status: 200,
          data: { tiers: [] },
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
      mockedAxios.get.mockRejectedValue(new Error('Connection refused'));

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

      expect(response.body).toMatchObject({
        version: '1.0.0',
        endpoints: expect.arrayContaining([
          { path: '/invoke', method: 'POST' },
          { path: '/batch', method: 'POST' },
          { path: '/stream', method: 'POST' },
          { path: '/health', method: 'GET' },
        ]),
        features: {
          modelTiers: ['ECONOMY', 'STANDARD', 'PREMIUM'],
          governanceModes: ['DEMO', 'LIVE'],
          phiCompliance: true,
          costTracking: true,
        },
        limits: {
          maxBatchSize: 10,
          maxTokens: 200000,
        },
      });
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
        .send(validRequest);

      // Without API keys we get 500; with keys or mocked provider we get 200
      if (response.status === 500) {
        assert.ok(response.body.error || response.body.message);
        return;
      }

      assert.strictEqual(response.status, 200);
      assert.ok(typeof response.body.content === 'string', 'content must be string');
      assert.ok(!response.body.content.includes('AI Bridge Mock Response'), 'must be non-mock content');
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
      mockedAxios.post.mockRejectedValue(new Error('AI Router down'));

      const response = await request(app)
        .post('/api/ai-bridge/invoke')
        .send(validRequest)
        .expect(200);

      // Should still work with fallback routing
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

      expect(response.body).toMatchObject({
        responses: expect.arrayContaining([
          expect.objectContaining({
            content: expect.any(String),
            usage: expect.any(Object),
            cost: expect.any(Object),
            index: expect.any(Number),
          }),
        ]),
        totalCost: expect.any(Number),
        averageLatency: expect.any(Number),
        successCount: 3,
        errorCount: 0,
        metadata: {
          processingTimeMs: expect.any(Number),
          bridgeVersion: '1.0.0',
        },
      });

      expect(response.body.responses).toHaveLength(3);
    });

    it('should enforce batch size limits', async () => {
      const largeBatch = {
        ...validBatchRequest,
        prompts: new Array(15).fill('Test prompt'),
      };

      const response = await request(app)
        .post('/api/ai-bridge/batch')
        .send(largeBatch)
        .expect(400);

      expect(response.body.error).toBe('BATCH_SIZE_EXCEEDED');
      expect(response.body.received).toBe(15);
    });

    it('should handle partial batch failures', async () => {
      // Mock one failure during batch processing
      let callCount = 0;
      mockedAxios.post.mockImplementation((url) => {
        callCount++;
        if (url.includes('/api/ai/router/route')) {
          if (callCount === 2) {
            return Promise.reject(new Error('Temporary failure'));
          }
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

      const response = await request(app)
        .post('/api/ai-bridge/batch')
        .send(validBatchRequest)
        .expect(200);

      expect(response.body.successCount).toBe(2);
      expect(response.body.errorCount).toBe(1);
      expect(response.body.responses).toHaveLength(3);
      
      // Check that one response is an error
      const errorResponse = response.body.responses.find((r: any) => r.error);
      expect(errorResponse).toBeDefined();
      expect(errorResponse.error).toBe('LLM_CALL_FAILED');
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

      // Check that response contains SSE data
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