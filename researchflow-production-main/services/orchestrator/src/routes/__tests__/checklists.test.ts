/**
 * Checklist Routes Test Suite
 * Tests for TRIPOD+AI and CONSORT-AI checklist management APIs
 */

import request from 'supertest';
import express from 'express';
import checklistsRouter from '../checklists';

describe('Checklists API Routes', () => {
  let app: express.Application;

  beforeAll(() => {
    app = express();
    app.use(express.json());
    app.use('/api/checklists', checklistsRouter);
  });

  describe('GET /api/checklists', () => {
    it('should list all available checklists', async () => {
      const response = await request(app)
        .get('/api/checklists')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.checklists).toBeDefined();
      expect(response.body.checklists.length).toBeGreaterThan(0);
      expect(response.body.checklists[0]).toHaveProperty('type');
      expect(response.body.checklists[0]).toHaveProperty('name');
      expect(response.body.checklists[0]).toHaveProperty('items');
    });

    it('should include TRIPOD+AI checklist', async () => {
      const response = await request(app)
        .get('/api/checklists')
        .expect(200);

      const tripodChecklist = response.body.checklists.find(
        (c: any) => c.type === 'tripod_ai'
      );
      expect(tripodChecklist).toBeDefined();
      expect(tripodChecklist.items).toBe(27);
    });

    it('should include CONSORT-AI checklist', async () => {
      const response = await request(app)
        .get('/api/checklists')
        .expect(200);

      const consortChecklist = response.body.checklists.find(
        (c: any) => c.type === 'consort_ai'
      );
      expect(consortChecklist).toBeDefined();
      expect(consortChecklist.items).toBe(12);
    });
  });

  describe('GET /api/checklists/:type', () => {
    it('should fetch TRIPOD+AI checklist with all items', async () => {
      const response = await request(app)
        .get('/api/checklists/tripod_ai')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.checklist).toBeDefined();
      expect(response.body.checklist.type).toBe('tripod_ai');
      expect(response.body.checklist.items.length).toBe(27);
      expect(response.body.checklist.completions.length).toBe(27);
    });

    it('should fetch CONSORT-AI checklist with all items', async () => {
      const response = await request(app)
        .get('/api/checklists/consort_ai')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.checklist).toBeDefined();
      expect(response.body.checklist.type).toBe('consort_ai');
      expect(response.body.checklist.items.length).toBe(12);
    });

    it('should reject invalid checklist type', async () => {
      const response = await request(app)
        .get('/api/checklists/invalid_type')
        .expect(400);

      expect(response.body.error).toBeDefined();
      expect(response.body.code).toBe('INVALID_CHECKLIST_TYPE');
    });

    it('should include metadata in response', async () => {
      const response = await request(app)
        .get('/api/checklists/tripod_ai')
        .expect(200);

      expect(response.body.metadata).toBeDefined();
      expect(response.body.metadata.sections).toBeGreaterThan(0);
      expect(response.body.metadata.requiredItems).toBeGreaterThan(0);
      expect(response.body.metadata.optionalItems).toBeGreaterThanOrEqual(0);
    });
  });

  describe('GET /api/checklists/:type/:itemId/guidance', () => {
    it('should fetch guidance for specific item', async () => {
      const response = await request(app)
        .get('/api/checklists/tripod_ai/T1/guidance')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.itemId).toBe('T1');
      expect(response.body.guidance).toBeDefined();
      expect(response.body.evidence_types).toBeDefined();
      expect(response.body.validation_rules).toBeDefined();
    });

    it('should return 404 for non-existent item', async () => {
      const response = await request(app)
        .get('/api/checklists/tripod_ai/INVALID/guidance')
        .expect(404);

      expect(response.body.error).toBeDefined();
      expect(response.body.code).toBe('ITEM_NOT_FOUND');
    });

    it('should include cross-references if available', async () => {
      const response = await request(app)
        .get('/api/checklists/consort_ai/CONSORT-AI-1/guidance')
        .expect(200);

      // CONSORT-AI items have cross-references to TRIPOD items
      if (response.body.cross_reference) {
        expect(response.body.cross_reference.tripod_item).toBeDefined();
      }
    });
  });

  describe('POST /api/checklists/:type/validate', () => {
    it('should validate empty completions as incomplete', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/validate')
        .send({ completions: [] })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.validation.valid).toBe(false);
      expect(response.body.validation.criticalIssues.length).toBeGreaterThan(0);
    });

    it('should return 400 for missing completions', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/validate')
        .send({})
        .expect(400);

      expect(response.body.error).toBeDefined();
      expect(response.body.code).toBe('MISSING_COMPLETIONS');
    });

    it('should calculate completeness percentage', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/validate')
        .send({ completions: [] })
        .expect(200);

      expect(response.body.validation.completeness).toBeDefined();
      expect(typeof response.body.validation.completeness).toBe('number');
      expect(response.body.validation.completeness).toBeGreaterThanOrEqual(0);
    });

    it('should identify required vs optional items', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/validate')
        .send({ completions: [] })
        .expect(200);

      expect(response.body.summary.requiredItems).toBeGreaterThan(0);
      expect(response.body.summary.totalItems).toBeDefined();
    });
  });

  describe('POST /api/checklists/:type/progress', () => {
    it('should calculate progress for empty completions', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/progress')
        .send({ completions: [] })
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.progress).toBeDefined();
      expect(response.body.progress.progressPercentage).toBe(0);
      expect(response.body.progress.completedItems).toBe(0);
    });

    it('should include progress by category', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/progress')
        .send({ completions: [] })
        .expect(200);

      expect(response.body.progress.byCategory).toBeDefined();
      expect(Object.keys(response.body.progress.byCategory).length).toBeGreaterThan(0);
    });

    it('should calculate category percentages', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/progress')
        .send({ completions: [] })
        .expect(200);

      Object.values(response.body.progress.byCategory).forEach((cat: any) => {
        expect(cat.percentage).toBeDefined();
        expect(typeof cat.percentage).toBe('number');
      });
    });
  });

  describe('POST /api/checklists/:type/export', () => {
    it('should export as JSON format', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/export')
        .send({
          completions: [],
          format: 'json'
        })
        .expect(200)
        .expect('Content-Type', /application\/json/);

      expect(response.text).toBeDefined();
      const data = JSON.parse(response.text);
      expect(data.checklistType).toBe('tripod_ai');
      expect(Array.isArray(data.items)).toBe(true);
    });

    it('should export as YAML format', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/export')
        .send({
          completions: [],
          format: 'yaml'
        })
        .expect(200)
        .expect('Content-Type', /application\/x-yaml/);

      expect(response.text).toBeDefined();
      expect(response.text).toContain('checklistType');
    });

    it('should export as CSV format', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/export')
        .send({
          completions: [],
          format: 'csv'
        })
        .expect(200)
        .expect('Content-Type', /text\/csv/);

      expect(response.text).toBeDefined();
      const lines = response.text.split('\n');
      expect(lines[0]).toContain('Item ID');
    });

    it('should set proper content-disposition header', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/export')
        .send({
          completions: [],
          format: 'json'
        })
        .expect(200);

      expect(response.headers['content-disposition']).toContain('attachment');
      expect(response.headers['content-disposition']).toContain('.json');
    });

    it('should reject invalid format', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/export')
        .send({
          completions: [],
          format: 'invalid'
        })
        .expect(400);

      expect(response.body.error).toBeDefined();
      expect(response.body.code).toBe('INVALID_FORMAT');
    });
  });

  describe('GET /api/checklists/compare/items', () => {
    it('should compare TRIPOD+AI and CONSORT-AI checklists', async () => {
      const response = await request(app)
        .get('/api/checklists/compare/items')
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.comparison).toBeDefined();
      expect(response.body.comparison.tripod_ai).toBeDefined();
      expect(response.body.comparison.consort_ai).toBeDefined();
    });

    it('should identify cross-references', async () => {
      const response = await request(app)
        .get('/api/checklists/compare/items')
        .expect(200);

      expect(response.body.comparison.crossReferences).toBeDefined();
      // CONSORT-AI items should reference TRIPOD+AI items
      const hasReferences = Object.keys(response.body.comparison.crossReferences).length > 0;
      expect(hasReferences).toBe(true);
    });

    it('should include category information', async () => {
      const response = await request(app)
        .get('/api/checklists/compare/items')
        .expect(200);

      expect(response.body.comparison.tripod_ai.categories).toBeDefined();
      expect(Array.isArray(response.body.comparison.tripod_ai.categories)).toBe(true);
      expect(response.body.comparison.consort_ai.categories).toBeDefined();
    });
  });

  describe('Error Handling', () => {
    it('should return 400 for invalid checklist type', async () => {
      const response = await request(app)
        .get('/api/checklists/invalid')
        .expect(400);

      expect(response.body.error).toBeDefined();
      expect(response.body.code).toBe('INVALID_CHECKLIST_TYPE');
    });

    it('should handle missing request body gracefully', async () => {
      const response = await request(app)
        .post('/api/checklists/tripod_ai/validate')
        .expect(400);

      expect(response.body.error).toBeDefined();
    });
  });
});
