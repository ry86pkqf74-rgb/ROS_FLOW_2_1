/**
 * FAVES API Routes Tests
 *
 * Tests for Fair, Appropriate, Valid, Effective, Safe compliance API
 * Phase 10: Transparency & Compliance
 */

import express from 'express';
import request from 'supertest';
import { describe, it, expect, beforeEach, vi } from 'vitest';

import favesRoutes from '../faves';

// Mock dependencies
vi.mock('../../../db.js', () => ({
  db: {
    execute: vi.fn(),
  },
}));

vi.mock('../../middleware/rbac', () => ({
  requireRole: () => (req: any, res: any, next: any) => next(),
}));

vi.mock('../../services/event-bus', () => ({
  eventBus: {
    emit: vi.fn(),
  },
}));

// Test app setup
function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/faves', favesRoutes);
  return app;
}

describe('FAVES API Routes', () => {
  let app: express.Application;

  beforeEach(() => {
    app = createTestApp();
    vi.clearAllMocks();
  });

  describe('GET /api/faves/evaluations', () => {
    it('should return list of evaluations', async () => {
      const { db } = await import('../../../db.js');
      
      (db.execute as any).mockResolvedValueOnce({
        rows: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            model_id: '660e8400-e29b-41d4-a716-446655440001',
            model_version: '1.0.0',
            overall_status: 'PASS',
            overall_score: 87.5,
            deployment_allowed: true,
            evaluated_at: '2026-02-01T10:00:00Z',
          },
        ],
      });

      (db.execute as any).mockResolvedValueOnce({
        rows: [{ total: '1' }],
      });

      const response = await request(app)
        .get('/api/faves/evaluations')
        .expect(200);

      expect(response.body).toHaveProperty('evaluations');
      expect(response.body).toHaveProperty('pagination');
      expect(response.body.evaluations).toBeInstanceOf(Array);
    });

    it('should accept query parameters', async () => {
      const { db } = await import('../../../db.js');
      
      (db.execute as any).mockResolvedValue({ rows: [] });

      await request(app)
        .get('/api/faves/evaluations')
        .query({ limit: 10, offset: 0, deployment_allowed: 'true' })
        .expect(200);

      expect(db.execute).toHaveBeenCalled();
    });
  });

  describe('GET /api/faves/evaluations/:id', () => {
    it('should return evaluation details', async () => {
      const { db } = await import('../../../db.js');
      const evalId = '550e8400-e29b-41d4-a716-446655440000';
      
      (db.execute as any)
        .mockResolvedValueOnce({
          rows: [
            {
              id: evalId,
              model_id: '660e8400-e29b-41d4-a716-446655440001',
              overall_status: 'PASS',
              overall_score: 87.5,
            },
          ],
        })
        .mockResolvedValueOnce({
          rows: [],
        });

      const response = await request(app)
        .get(`/api/faves/evaluations/${evalId}`)
        .expect(200);

      expect(response.body).toHaveProperty('evaluation');
      expect(response.body).toHaveProperty('artifacts');
      expect(response.body.evaluation.id).toBe(evalId);
    });

    it('should return 404 for non-existent evaluation', async () => {
      const { db } = await import('../../../db.js');
      
      (db.execute as any).mockResolvedValue({ rows: [] });

      const response = await request(app)
        .get('/api/faves/evaluations/550e8400-e29b-41d4-a716-446655440999')
        .expect(404);

      expect(response.body).toHaveProperty('error');
    });
  });

  describe('POST /api/faves/evaluations', () => {
    it('should create new evaluation', async () => {
      const { db } = await import('../../../db.js');
      const { eventBus } = await import('../../services/event-bus');
      
      const newEval = {
        model_id: '660e8400-e29b-41d4-a716-446655440001',
        model_version: '1.0.0',
        evaluation_type: 'PRE_DEPLOYMENT',
      };

      // Mock model exists check
      (db.execute as any).mockResolvedValueOnce({
        rows: [{ id: newEval.model_id, current_version: '1.0.0' }],
      });

      // Mock insert
      (db.execute as any).mockResolvedValueOnce({
        rows: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            ...newEval,
            overall_status: 'NOT_EVALUATED',
          },
        ],
      });

      const response = await request(app)
        .post('/api/faves/evaluations')
        .send(newEval)
        .expect(201);

      expect(response.body).toHaveProperty('id');
      expect(response.body.model_id).toBe(newEval.model_id);
      expect(eventBus.emit).toHaveBeenCalledWith(
        'faves:evaluation_created',
        expect.any(Object)
      );
    });

    it('should validate request body', async () => {
      const response = await request(app)
        .post('/api/faves/evaluations')
        .send({ invalid: 'data' })
        .expect(400);

      expect(response.body).toHaveProperty('error');
    });

    it('should return 400 if model not found', async () => {
      const { db } = await import('../../../db.js');
      
      (db.execute as any).mockResolvedValue({ rows: [] });

      const response = await request(app)
        .post('/api/faves/evaluations')
        .send({
          model_id: '660e8400-e29b-41d4-a716-446655440999',
          model_version: '1.0.0',
          evaluation_type: 'PRE_DEPLOYMENT',
        })
        .expect(400);

      expect(response.body.error).toBe('Model not found in registry');
    });
  });

  describe('POST /api/faves/evaluations/:id/dimensions', () => {
    it('should submit dimension results', async () => {
      const { db } = await import('../../../db.js');
      const { eventBus } = await import('../../services/event-bus');
      const evalId = '550e8400-e29b-41d4-a716-446655440000';
      
      const dimensionResults = [
        {
          dimension: 'FAIR',
          status: 'PASS',
          score: 85,
          metrics: [
            {
              metric_name: 'demographic_parity_gap',
              value: 0.08,
              threshold: 0.1,
              passed: true,
            },
          ],
          missing_requirements: [],
          recommendations: [],
        },
        {
          dimension: 'APPROPRIATE',
          status: 'PASS',
          score: 90,
          metrics: [],
          missing_requirements: [],
          recommendations: [],
        },
        {
          dimension: 'VALID',
          status: 'PASS',
          score: 88,
          metrics: [],
          missing_requirements: [],
          recommendations: [],
        },
        {
          dimension: 'EFFECTIVE',
          status: 'PASS',
          score: 86,
          metrics: [],
          missing_requirements: [],
          recommendations: [],
        },
        {
          dimension: 'SAFE',
          status: 'PASS',
          score: 89,
          metrics: [],
          missing_requirements: [],
          recommendations: [],
        },
      ];

      // Mock evaluation exists
      (db.execute as any).mockResolvedValueOnce({
        rows: [{ id: evalId }],
      });

      // Mock update
      (db.execute as any).mockResolvedValueOnce({
        rows: [
          {
            id: evalId,
            overall_status: 'PASS',
            deployment_allowed: true,
          },
        ],
      });

      const response = await request(app)
        .post(`/api/faves/evaluations/${evalId}/dimensions`)
        .send(dimensionResults)
        .expect(200);

      expect(response.body).toHaveProperty('id');
      expect(response.body.deployment_allowed).toBe(true);
      expect(eventBus.emit).toHaveBeenCalledWith(
        'faves:evaluation_passed',
        expect.any(Object)
      );
    });

    it('should return 404 if evaluation not found', async () => {
      const { db } = await import('../../../db.js');
      
      (db.execute as any).mockResolvedValue({ rows: [] });

      const response = await request(app)
        .post('/api/faves/evaluations/550e8400-e29b-41d4-a716-446655440999/dimensions')
        .send([])
        .expect(404);

      expect(response.body.error).toBe('FAVES evaluation not found');
    });
  });

  describe('POST /api/faves/evaluations/:id/artifacts', () => {
    it('should add artifacts to evaluation', async () => {
      const { db } = await import('../../../db.js');
      const evalId = '550e8400-e29b-41d4-a716-446655440000';
      
      const artifacts = [
        {
          artifact_name: 'fairness_analysis.md',
          artifact_path: 'docs/faves/fairness_analysis.md',
          artifact_type: 'DOCUMENTATION',
          faves_dimension: 'FAIR',
          is_required: true,
        },
      ];

      // Mock evaluation exists
      (db.execute as any).mockResolvedValueOnce({
        rows: [{ id: evalId }],
      });

      // Mock insert
      (db.execute as any).mockResolvedValue({
        rows: [
          {
            id: '770e8400-e29b-41d4-a716-446655440000',
            evaluation_id: evalId,
            ...artifacts[0],
          },
        ],
      });

      const response = await request(app)
        .post(`/api/faves/evaluations/${evalId}/artifacts`)
        .send(artifacts)
        .expect(201);

      expect(response.body).toHaveProperty('artifacts');
      expect(response.body.artifacts).toBeInstanceOf(Array);
    });
  });

  describe('GET /api/faves/gate/:modelId', () => {
    it('should check deployment gate for model', async () => {
      const { db } = await import('../../../db.js');
      const modelId = '660e8400-e29b-41d4-a716-446655440001';
      
      (db.execute as any).mockResolvedValue({
        rows: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            model_id: modelId,
            model_version: '1.0.0',
            overall_status: 'PASS',
            overall_score: 87.5,
            deployment_allowed: true,
            evaluated_at: new Date().toISOString(),
            fair_score: 85,
            appropriate_score: 90,
            valid_score: 88,
            effective_score: 86,
            safe_score: 89,
          },
        ],
      });

      const response = await request(app)
        .get(`/api/faves/gate/${modelId}`)
        .expect(200);

      expect(response.body).toHaveProperty('gate_status');
      expect(response.body).toHaveProperty('deployment_allowed');
      expect(response.body).toHaveProperty('dimension_scores');
      expect(response.body.gate_status).toBe('PASS');
      expect(response.body.deployment_allowed).toBe(true);
    });

    it('should return no evaluation status if not evaluated', async () => {
      const { db } = await import('../../../db.js');
      const modelId = '660e8400-e29b-41d4-a716-446655440999';
      
      (db.execute as any).mockResolvedValue({ rows: [] });

      const response = await request(app)
        .get(`/api/faves/gate/${modelId}`)
        .expect(200);

      expect(response.body.gate_status).toBe('NO_EVALUATION');
      expect(response.body.deployment_allowed).toBe(false);
    });

    it('should flag stale evaluations', async () => {
      const { db } = await import('../../../db.js');
      const modelId = '660e8400-e29b-41d4-a716-446655440001';
      
      // Evaluation from 91 days ago
      const staleDate = new Date();
      staleDate.setDate(staleDate.getDate() - 91);
      
      (db.execute as any).mockResolvedValue({
        rows: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            model_id: modelId,
            deployment_allowed: true,
            evaluated_at: staleDate.toISOString(),
          },
        ],
      });

      const response = await request(app)
        .get(`/api/faves/gate/${modelId}`)
        .expect(200);

      expect(response.body.is_stale).toBe(true);
      expect(response.body.deployment_allowed).toBe(false);
    });
  });

  describe('POST /api/faves/gate/:modelId/override', () => {
    it('should request gate override', async () => {
      const { db } = await import('../../../db.js');
      const { eventBus } = await import('../../services/event-bus');
      const modelId = '660e8400-e29b-41d4-a716-446655440001';
      
      (db.execute as any).mockResolvedValue({ rows: [] });

      const response = await request(app)
        .post(`/api/faves/gate/${modelId}/override`)
        .send({
          reason: 'Critical bug fix required. Minor fairness gap will be addressed in next version scheduled for next week.',
          risk_acknowledgment: true,
        })
        .expect(200);

      expect(response.body).toHaveProperty('message');
      expect(response.body.status).toBe('PENDING_APPROVAL');
      expect(eventBus.emit).toHaveBeenCalledWith(
        'faves:override_requested',
        expect.any(Object)
      );
    });

    it('should reject short override reasons', async () => {
      const modelId = '660e8400-e29b-41d4-a716-446655440001';
      
      const response = await request(app)
        .post(`/api/faves/gate/${modelId}/override`)
        .send({
          reason: 'Too short',
          risk_acknowledgment: true,
        })
        .expect(400);

      expect(response.body.error).toContain('50 characters');
    });

    it('should require risk acknowledgment', async () => {
      const modelId = '660e8400-e29b-41d4-a716-446655440001';
      
      const response = await request(app)
        .post(`/api/faves/gate/${modelId}/override`)
        .send({
          reason: 'This is a sufficiently long reason for the override request that meets the minimum character requirement.',
        })
        .expect(400);

      expect(response.body.error).toContain('Risk acknowledgment');
    });
  });

  describe('GET /api/faves/stats', () => {
    it('should return FAVES statistics', async () => {
      const { db } = await import('../../../db.js');
      
      // Mock stats query
      (db.execute as any).mockResolvedValueOnce({
        rows: [
          {
            total_evaluations: '25',
            passed_count: '18',
            failed_count: '7',
            models_evaluated: '10',
            avg_overall_score: '82.5',
            avg_fair_score: '80',
            avg_appropriate_score: '85',
            avg_valid_score: '83',
            avg_effective_score: '81',
            avg_safe_score: '84',
          },
        ],
      });

      // Mock trend query
      (db.execute as any).mockResolvedValueOnce({
        rows: [],
      });

      const response = await request(app)
        .get('/api/faves/stats')
        .expect(200);

      expect(response.body).toHaveProperty('summary');
      expect(response.body).toHaveProperty('trend');
      expect(response.body).toHaveProperty('thresholds');
      expect(response.body.summary.total_evaluations).toBe('25');
    });
  });

  describe('GET /api/faves/models/:modelId/history', () => {
    it('should return evaluation history for model', async () => {
      const { db } = await import('../../../db.js');
      const modelId = '660e8400-e29b-41d4-a716-446655440001';
      
      (db.execute as any).mockResolvedValue({
        rows: [
          {
            id: '550e8400-e29b-41d4-a716-446655440000',
            model_version: '1.0.0',
            overall_score: 87.5,
            deployment_allowed: true,
          },
          {
            id: '550e8400-e29b-41d4-a716-446655440001',
            model_version: '0.9.0',
            overall_score: 82.0,
            deployment_allowed: true,
          },
        ],
      });

      const response = await request(app)
        .get(`/api/faves/models/${modelId}/history`)
        .expect(200);

      expect(response.body).toHaveProperty('model_id');
      expect(response.body).toHaveProperty('history');
      expect(response.body.history).toBeInstanceOf(Array);
      expect(response.body.history.length).toBe(2);
    });
  });
});
