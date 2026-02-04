/**
 * AI Bridge API Simple Test
 * 
 * Basic validation test for AI Bridge endpoints
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import request from 'supertest';
import express from 'express';
import aiBridgeRoutes from '../ai-bridge';

// Create simple test app
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

describe('AI Bridge Basic Tests', () => {
  test('should return capabilities', async () => {
    const app = createTestApp();
    const response = await request(app)
      .get('/api/ai-bridge/capabilities')
      .expect(200);

    assert.strictEqual(response.body.version, '1.0.0');
    assert(Array.isArray(response.body.endpoints));
    assert(response.body.features);
    assert(response.body.limits);
  });

  test('should return metrics endpoint', async () => {
    const app = createTestApp();
    const response = await request(app)
      .get('/api/ai-bridge/metrics')
      .expect(200);

    // Should return Prometheus metrics format
    assert(typeof response.text === 'string');
  });

  test('should reject unauthenticated requests', async () => {
    const app = express();
    app.use(express.json());
    // No user mock - req.user is undefined
    app.use('/api/ai-bridge', aiBridgeRoutes);

    await request(app)
      .post('/api/ai-bridge/invoke')
      .send({
        prompt: 'test',
        options: { taskType: 'test' }
      })
      .expect(401);
  });

  test('should validate request schema', async () => {
    const app = createTestApp();
    
    // Missing required fields
    const response = await request(app)
      .post('/api/ai-bridge/invoke')
      .send({
        // Missing prompt and options
      })
      .expect(400);

    assert.strictEqual(response.body.error, 'VALIDATION_ERROR');
  });
});