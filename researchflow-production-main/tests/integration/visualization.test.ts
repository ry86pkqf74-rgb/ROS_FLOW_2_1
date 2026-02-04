/**
 * Integration Tests - Data Visualization System
 * 
 * Tests the complete visualization pipeline:
 * - Chart generation via worker service
 * - Database storage and retrieval
 * - PHI scanning integration
 * - API endpoint functionality
 * - Figure management operations
 */

import { describe, test, expect, beforeEach, afterEach, vi, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import { Pool } from 'pg';
import { app } from '../../services/orchestrator/src/app';
import { createFiguresService, type FigureCreateInput } from '../../services/orchestrator/src/services/figures.service';

// Test configuration
const TEST_CONFIG = {
  WORKER_URL: process.env.WORKER_URL || 'http://localhost:8000',
  DB_URL: process.env.TEST_DATABASE_URL || process.env.DATABASE_URL,
  TIMEOUT: 30000, // 30 seconds for chart generation
};

// Test database connection
let testPool: Pool;
let figuresService: any;

beforeAll(async () => {
  if (!TEST_CONFIG.DB_URL) {
    throw new Error('TEST_DATABASE_URL or DATABASE_URL required for integration tests');
  }
  
  testPool = new Pool({ connectionString: TEST_CONFIG.DB_URL });
  figuresService = createFiguresService(testPool);
  
  // Ensure figures table exists
  try {
    await testPool.query('SELECT 1 FROM figures LIMIT 1');
  } catch (error) {
    console.warn('Figures table may not exist, some tests may fail');
  }
});

afterAll(async () => {
  await testPool?.end();
});

describe('Data Visualization Integration', () => {
  let testResearchId: string;
  let createdFigureIds: string[] = [];

  beforeEach(() => {
    testResearchId = `test_research_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    createdFigureIds = [];
  });

  afterEach(async () => {
    // Cleanup created figures
    for (const figureId of createdFigureIds) {
      try {
        await figuresService?.deleteFigure(figureId);
      } catch (error) {
        // Ignore cleanup errors
      }
    }
  });

  describe('Chart Generation API', () => {
    test('should generate bar chart successfully', async () => {
      const chartData = {
        chart_type: 'bar_chart',
        data: {
          group: ['Control', 'Treatment A', 'Treatment B'],
          value: [5.2, 6.8, 7.3],
          error: [0.8, 1.1, 0.9],
        },
        config: {
          title: 'Treatment Effectiveness',
          x_label: 'Group',
          y_label: 'Pain Score (0-10)',
          show_error_bars: true,
          dpi: 150, // Lower DPI for faster test
        },
        research_id: testResearchId,
      };

      const response = await request(app)\n        .post('/api/visualization/generate')\n        .send(chartData)\n        .expect(200);\n\n      expect(response.body).toHaveProperty('status', 'completed');\n      expect(response.body).toHaveProperty('request_id');\n      expect(response.body).toHaveProperty('result');\n      expect(response.body.result).toHaveProperty('figure_id');\n      expect(response.body.result).toHaveProperty('image_base64');\n      \n      // Should include database info if storage succeeded\n      if (response.body.result.database_id) {\n        createdFigureIds.push(response.body.result.database_id);\n        expect(response.body.result).toHaveProperty('stored_at');\n      }\n    }, TEST_CONFIG.TIMEOUT);\n\n    test('should generate line chart with confidence bands', async () => {\n      const chartData = {\n        chart_type: 'line_chart',\n        data: {\n          time: [0, 1, 2, 3, 4, 5, 6],\n          value: [10, 12, 11, 14, 13, 15, 16],\n          ci_lower: [8, 10, 9, 12, 11, 13, 14],\n          ci_upper: [12, 14, 13, 16, 15, 17, 18],\n        },\n        config: {\n          title: 'Recovery Timeline',\n          x_label: 'Time (weeks)',\n          y_label: 'Outcome Score',\n          show_confidence_bands: true,\n          journal_style: 'nature',\n          color_palette: 'colorblind_safe',\n        },\n        research_id: testResearchId,\n      };\n\n      const response = await request(app)\n        .post('/api/visualization/generate')\n        .send(chartData)\n        .expect(200);\n\n      expect(response.body.result).toHaveProperty('figure_id');\n      expect(response.body.result).toHaveProperty('caption');\n      expect(response.body.result).toHaveProperty('alt_text');\n      \n      if (response.body.result.database_id) {\n        createdFigureIds.push(response.body.result.database_id);\n      }\n    }, TEST_CONFIG.TIMEOUT);\n\n    test('should handle invalid chart data', async () => {\n      const invalidData = {\n        chart_type: 'bar_chart',\n        data: {}, // Empty data\n        config: {},\n        research_id: testResearchId,\n      };\n\n      const response = await request(app)\n        .post('/api/visualization/generate')\n        .send(invalidData)\n        .expect(400);\n\n      expect(response.body).toHaveProperty('error');\n      expect(response.body.error).toContain('VISUALIZATION_FAILED');\n    });\n\n    test('should validate request schema', async () => {\n      const invalidRequest = {\n        chart_type: 'invalid_chart_type',\n        data: { x: [1, 2, 3] },\n      };\n\n      const response = await request(app)\n        .post('/api/visualization/generate')\n        .send(invalidRequest)\n        .expect(400);\n\n      expect(response.body).toHaveProperty('error', 'INVALID_REQUEST');\n      expect(response.body).toHaveProperty('details');\n    });\n  });\n\n  describe('Figure Management API', () => {\n    let sampleFigureId: string;\n\n    beforeEach(async () => {\n      // Create a sample figure for testing\n      if (figuresService) {\n        const figureInput: FigureCreateInput = {\n          research_id: testResearchId,\n          figure_type: 'bar_chart',\n          title: 'Test Chart',\n          caption: 'A test chart for API testing',\n          alt_text: 'Bar chart showing test data',\n          image_data: Buffer.from('fake-image-data'),\n          image_format: 'png',\n          width: 800,\n          height: 600,\n          dpi: 300,\n          generated_by: 'test_suite',\n        };\n\n        const figure = await figuresService.createFigure(figureInput);\n        sampleFigureId = figure.id;\n        createdFigureIds.push(sampleFigureId);\n      }\n    });\n\n    test('should list figures for research project', async () => {\n      if (!figuresService) {\n        console.warn('Skipping database test - figures service not available');\n        return;\n      }\n\n      const response = await request(app)\n        .get(`/api/visualization/figures/${testResearchId}`)\n        .expect(200);\n\n      expect(response.body).toHaveProperty('research_id', testResearchId);\n      expect(response.body).toHaveProperty('figures');\n      expect(response.body).toHaveProperty('total');\n      expect(response.body.figures).toBeInstanceOf(Array);\n      expect(response.body.figures.length).toBeGreaterThan(0);\n      \n      // Figures should not include image data in list\n      const figure = response.body.figures[0];\n      expect(figure).not.toHaveProperty('image_data');\n      expect(figure).toHaveProperty('has_image_data', true);\n    });\n\n    test('should get specific figure by ID', async () => {\n      if (!figuresService || !sampleFigureId) {\n        console.warn('Skipping database test - figures service not available');\n        return;\n      }\n\n      // Get figure without image data\n      const response1 = await request(app)\n        .get(`/api/visualization/figure/${sampleFigureId}`)\n        .expect(200);\n\n      expect(response1.body).toHaveProperty('id', sampleFigureId);\n      expect(response1.body).toHaveProperty('figure_type', 'bar_chart');\n      expect(response1.body).toHaveProperty('title', 'Test Chart');\n      expect(response1.body).not.toHaveProperty('image_data');\n\n      // Get figure with image data\n      const response2 = await request(app)\n        .get(`/api/visualization/figure/${sampleFigureId}?include_image=true`)\n        .expect(200);\n\n      expect(response2.body).toHaveProperty('image_data');\n      expect(typeof response2.body.image_data).toBe('string');\n    });\n\n    test('should return 404 for non-existent figure', async () => {\n      const fakeId = 'fake-figure-id';\n\n      await request(app)\n        .get(`/api/visualization/figure/${fakeId}`)\n        .expect(404);\n    });\n\n    test('should delete figure', async () => {\n      if (!figuresService || !sampleFigureId) {\n        console.warn('Skipping database test - figures service not available');\n        return;\n      }\n\n      const response = await request(app)\n        .delete(`/api/visualization/figure/${sampleFigureId}`)\n        .expect(200);\n\n      expect(response.body).toHaveProperty('success', true);\n      expect(response.body).toHaveProperty('figure_id', sampleFigureId);\n\n      // Verify figure is deleted\n      await request(app)\n        .get(`/api/visualization/figure/${sampleFigureId}`)\n        .expect(404);\n\n      // Remove from cleanup list since it's already deleted\n      createdFigureIds = createdFigureIds.filter(id => id !== sampleFigureId);\n    });\n\n    test('should get figure statistics', async () => {\n      if (!figuresService) {\n        console.warn('Skipping database test - figures service not available');\n        return;\n      }\n\n      const response = await request(app)\n        .get(`/api/visualization/stats/${testResearchId}`)\n        .expect(200);\n\n      expect(response.body).toHaveProperty('research_id', testResearchId);\n      expect(response.body).toHaveProperty('statistics');\n      expect(response.body.statistics).toHaveProperty('total');\n      expect(response.body.statistics).toHaveProperty('by_type');\n      expect(response.body.statistics).toHaveProperty('by_status');\n      expect(response.body.statistics).toHaveProperty('size_mb');\n    });\n\n    test('should update PHI scan results', async () => {\n      if (!figuresService || !sampleFigureId) {\n        console.warn('Skipping database test - figures service not available');\n        return;\n      }\n\n      const phiScanUpdate = {\n        phi_scan_status: 'PASS',\n        phi_risk_level: 'SAFE',\n        phi_findings: [],\n      };\n\n      const response = await request(app)\n        .patch(`/api/visualization/figure/${sampleFigureId}/phi-scan`)\n        .send(phiScanUpdate)\n        .expect(200);\n\n      expect(response.body).toHaveProperty('success', true);\n      expect(response.body).toHaveProperty('phi_scan_status', 'PASS');\n      expect(response.body).toHaveProperty('phi_risk_level', 'SAFE');\n    });\n  });\n\n  describe('Service Health and Capabilities', () => {\n    test('should return visualization capabilities', async () => {\n      const response = await request(app)\n        .get('/api/visualization/capabilities')\n        .expect(200);\n\n      expect(response.body).toHaveProperty('chart_types');\n      expect(response.body.chart_types).toBeInstanceOf(Array);\n      expect(response.body.chart_types).toContain('bar_chart');\n      expect(response.body.chart_types).toContain('line_chart');\n      \n      expect(response.body).toHaveProperty('journal_styles');\n      expect(response.body).toHaveProperty('color_palettes');\n      expect(response.body).toHaveProperty('export_formats');\n    });\n\n    test('should return service health status', async () => {\n      const response = await request(app)\n        .get('/api/visualization/health')\n        .expect(200);\n\n      expect(response.body).toHaveProperty('service', 'visualization');\n      expect(response.body).toHaveProperty('stage', 8);\n      expect(response.body).toHaveProperty('worker_status');\n      expect(response.body).toHaveProperty('timestamp');\n      \n      // Status should be healthy or degraded\n      expect(['healthy', 'degraded']).toContain(response.body.status);\n    });\n  });\n\n  describe('Error Handling', () => {\n    test('should handle worker service unavailable', async () => {\n      // Mock worker service failure by using invalid URL\n      const originalEnv = process.env.WORKER_URL;\n      process.env.WORKER_URL = 'http://invalid-url:9999';\n      \n      const chartData = {\n        chart_type: 'bar_chart',\n        data: { group: ['A', 'B'], value: [1, 2] },\n        research_id: testResearchId,\n      };\n\n      const response = await request(app)\n        .post('/api/visualization/generate')\n        .send(chartData)\n        .expect(503);\n\n      expect(response.body).toHaveProperty('error', 'SERVICE_UNAVAILABLE');\n      \n      // Restore original environment\n      process.env.WORKER_URL = originalEnv;\n    });\n\n    test('should handle database unavailable gracefully', async () => {\n      // If database is not available, list should still work\n      const response = await request(app)\n        .get('/api/visualization/figures/nonexistent-research')\n        .expect(res => {\n          // Either 200 (working) or 503 (database unavailable)\n          expect([200, 503]).toContain(res.status);\n        });\n\n      if (response.status === 503) {\n        expect(response.body).toHaveProperty('error', 'DATABASE_UNAVAILABLE');\n      }\n    });\n  });\n\n  describe('Performance and Load', () => {\n    test('should handle multiple concurrent chart requests', async () => {\n      const requests = Array.from({ length: 3 }, (_, i) => {\n        return request(app)\n          .post('/api/visualization/generate')\n          .send({\n            chart_type: 'bar_chart',\n            data: {\n              group: [`A${i}`, `B${i}`, `C${i}`],\n              value: [Math.random() * 10, Math.random() * 10, Math.random() * 10],\n            },\n            config: {\n              title: `Concurrent Test Chart ${i}`,\n              dpi: 72, // Minimal DPI for speed\n            },\n            research_id: `${testResearchId}_concurrent_${i}`,\n          });\n      });\n\n      const responses = await Promise.all(requests);\n      \n      // All should succeed\n      responses.forEach(response => {\n        expect(response.status).toBe(200);\n        expect(response.body).toHaveProperty('status', 'completed');\n        \n        // Track created figures for cleanup\n        if (response.body.result?.database_id) {\n          createdFigureIds.push(response.body.result.database_id);\n        }\n      });\n    }, TEST_CONFIG.TIMEOUT * 2);\n\n    test('should respect timeout limits', async () => {\n      // This test might be skipped if worker is too fast\n      const chartData = {\n        chart_type: 'scatter_plot',\n        data: {\n          x: Array.from({ length: 10000 }, () => Math.random()),\n          y: Array.from({ length: 10000 }, () => Math.random()),\n        },\n        config: {\n          title: 'Large Dataset Test',\n          dpi: 300,\n        },\n        research_id: testResearchId,\n      };\n\n      // Should complete within reasonable time\n      const startTime = Date.now();\n      const response = await request(app)\n        .post('/api/visualization/generate')\n        .send(chartData)\n        .timeout(TEST_CONFIG.TIMEOUT);\n      \n      const duration = Date.now() - startTime;\n      \n      if (response.status === 200) {\n        expect(duration).toBeLessThan(TEST_CONFIG.TIMEOUT);\n        expect(response.body).toHaveProperty('duration_ms');\n        expect(response.body.duration_ms).toBeGreaterThan(0);\n        \n        if (response.body.result?.database_id) {\n          createdFigureIds.push(response.body.result.database_id);\n        }\n      }\n    }, TEST_CONFIG.TIMEOUT + 5000);\n  });\n});"