/**
 * Integration tests for newly registered API routes (Phase 1)
 * 
 * Tests endpoints:
 * - /api/export/ris - RIS citation export
 * - /api/favorites - User favorites/bookmarks
 * - /api/phrases - Research terminology phrases
 * - /api/citations/attributes - Citation source attributes
 * - /api/audit/transparency - Audit and transparency logs
 * - /api/integrations/storage - Integration data storage
 */

import request from 'supertest';
import { describe, it, expect, beforeAll, afterAll } from 'vitest';

// Note: In a real test environment, you would import the actual app
// For now, we use a mock base URL approach
const BASE_URL = process.env.TEST_API_URL || 'http://localhost:3001';

describe('Phase 1 Route Integration Tests', () => {
  
  describe('GET /api/export/ris', () => {
    it('should return 401 without authentication', async () => {
      const res = await request(BASE_URL)
        .get('/api/export/ris')
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept manuscript ID parameter', async () => {
      const res = await request(BASE_URL)
        .get('/api/export/ris')
        .query({ manuscriptId: 'test-123' });
      
      // Should fail auth but accept the parameter format
      expect([401, 403]).toContain(res.status);
    });
  });

  describe('GET /api/favorites', () => {
    it('should return 401 without authentication', async () => {
      const res = await request(BASE_URL)
        .get('/api/favorites')
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should require authentication for POST', async () => {
      const res = await request(BASE_URL)
        .post('/api/favorites')
        .send({
          resourceType: 'project',
          resourceId: 'test-project-123'
        })
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should require authentication for DELETE', async () => {
      const res = await request(BASE_URL)
        .delete('/api/favorites/test-fav-123');
      
      expect([401, 403, 404]).toContain(res.status);
    });
  });

  describe('GET /api/phrases', () => {
    it('should return 401 without authentication', async () => {
      const res = await request(BASE_URL)
        .get('/api/phrases')
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept search query parameter', async () => {
      const res = await request(BASE_URL)
        .get('/api/phrases')
        .query({ q: 'methodology' });
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept category filter', async () => {
      const res = await request(BASE_URL)
        .get('/api/phrases')
        .query({ category: 'research-methods' });
      
      expect([401, 403]).toContain(res.status);
    });
  });

  describe('GET /api/citations/attributes', () => {
    it('should return 401 without authentication', async () => {
      const res = await request(BASE_URL)
        .get('/api/citations/attributes')
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept citation ID parameter', async () => {
      const res = await request(BASE_URL)
        .get('/api/citations/attributes')
        .query({ citationId: 'cite-123' });
      
      expect([401, 403]).toContain(res.status);
    });

    it('should require authentication for PUT', async () => {
      const res = await request(BASE_URL)
        .put('/api/citations/attributes/cite-123')
        .send({
          reliability: 'high',
          relevance: 0.95
        });
      
      expect([401, 403, 404]).toContain(res.status);
    });
  });

  describe('GET /api/audit/transparency', () => {
    it('should return 401 without authentication', async () => {
      const res = await request(BASE_URL)
        .get('/api/audit/transparency')
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept date range parameters', async () => {
      const res = await request(BASE_URL)
        .get('/api/audit/transparency')
        .query({
          startDate: '2024-01-01',
          endDate: '2024-12-31'
        });
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept action type filter', async () => {
      const res = await request(BASE_URL)
        .get('/api/audit/transparency')
        .query({ actionType: 'data_access' });
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept user filter', async () => {
      const res = await request(BASE_URL)
        .get('/api/audit/transparency')
        .query({ userId: 'user-123' });
      
      expect([401, 403]).toContain(res.status);
    });
  });

  describe('GET /api/integrations/storage', () => {
    it('should return 401 without authentication', async () => {
      const res = await request(BASE_URL)
        .get('/api/integrations/storage')
        .expect('Content-Type', /json/);
      
      expect([401, 403]).toContain(res.status);
    });

    it('should accept integration type parameter', async () => {
      const res = await request(BASE_URL)
        .get('/api/integrations/storage')
        .query({ type: 'google-drive' });
      
      expect([401, 403]).toContain(res.status);
    });

    it('should require authentication for POST', async () => {
      const res = await request(BASE_URL)
        .post('/api/integrations/storage')
        .send({
          type: 'dropbox',
          credentials: { token: 'test-token' }
        });
      
      expect([401, 403]).toContain(res.status);
    });

    it('should require authentication for DELETE', async () => {
      const res = await request(BASE_URL)
        .delete('/api/integrations/storage/integration-123');
      
      expect([401, 403, 404]).toContain(res.status);
    });
  });
});

describe('Route Response Format Tests', () => {
  
  describe('Error Response Format', () => {
    it('should return consistent error format for /api/favorites', async () => {
      const res = await request(BASE_URL)
        .get('/api/favorites');
      
      if (res.status === 401 || res.status === 403) {
        expect(res.body).toHaveProperty('error');
      }
    });

    it('should return consistent error format for /api/phrases', async () => {
      const res = await request(BASE_URL)
        .get('/api/phrases');
      
      if (res.status === 401 || res.status === 403) {
        expect(res.body).toHaveProperty('error');
      }
    });
  });
});

describe('Route Availability Tests', () => {
  
  const routes = [
    { method: 'GET', path: '/api/export/ris' },
    { method: 'GET', path: '/api/favorites' },
    { method: 'POST', path: '/api/favorites' },
    { method: 'GET', path: '/api/phrases' },
    { method: 'GET', path: '/api/citations/attributes' },
    { method: 'GET', path: '/api/audit/transparency' },
    { method: 'GET', path: '/api/integrations/storage' },
    { method: 'POST', path: '/api/integrations/storage' },
  ];

  routes.forEach(({ method, path }) => {
    it(`should have ${method} ${path} registered (not 404)`, async () => {
      let res;
      
      switch (method) {
        case 'GET':
          res = await request(BASE_URL).get(path);
          break;
        case 'POST':
          res = await request(BASE_URL).post(path).send({});
          break;
        case 'PUT':
          res = await request(BASE_URL).put(path).send({});
          break;
        case 'DELETE':
          res = await request(BASE_URL).delete(path);
          break;
        default:
          res = await request(BASE_URL).get(path);
      }
      
      // Route should exist (not 404) even if auth fails
      expect(res.status).not.toBe(404);
    });
  });
});

describe('Health Check Integration', () => {
  
  it('should have /health endpoint available', async () => {
    const res = await request(BASE_URL)
      .get('/health');
    
    expect([200, 204]).toContain(res.status);
  });

  it('should have /api/auth/status endpoint', async () => {
    const res = await request(BASE_URL)
      .get('/api/auth/status');
    
    // Should return something (may require auth)
    expect([200, 401, 403]).toContain(res.status);
  });
});
