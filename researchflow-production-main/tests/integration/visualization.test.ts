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

      const response = await request(app)
        .post('/api/visualization/generate')
        .send(chartData)
        .expect(200);

      expect(response.body).toHaveProperty('status', 'completed');
      expect(response.body).toHaveProperty('request_id');
      expect(response.body).toHaveProperty('result');
      expect(response.body.result).toHaveProperty('figure_id');
      expect(response.body.result).toHaveProperty('image_base64');
      
      // Should include database info if storage succeeded
      if (response.body.result.database_id) {
        createdFigureIds.push(response.body.result.database_id);
        expect(response.body.result).toHaveProperty('stored_at');
      }
    }, TEST_CONFIG.TIMEOUT);

    test('should generate line chart with confidence bands', async () => {
      const chartData = {
        chart_type: 'line_chart',
        data: {
          time: [0, 1, 2, 3, 4, 5, 6],
          value: [10, 12, 11, 14, 13, 15, 16],
          ci_lower: [8, 10, 9, 12, 11, 13, 14],
          ci_upper: [12, 14, 13, 16, 15, 17, 18],
        },
        config: {
          title: 'Recovery Timeline',
          x_label: 'Time (weeks)',
          y_label: 'Outcome Score',
          show_confidence_bands: true,
          journal_style: 'nature',
          color_palette: 'colorblind_safe',
        },
        research_id: testResearchId,
      };

      const response = await request(app)
        .post('/api/visualization/generate')
        .send(chartData)
        .expect(200);

      expect(response.body.result).toHaveProperty('figure_id');
      expect(response.body.result).toHaveProperty('caption');
      expect(response.body.result).toHaveProperty('alt_text');
      
      if (response.body.result.database_id) {
        createdFigureIds.push(response.body.result.database_id);
      }
    }, TEST_CONFIG.TIMEOUT);

    test('should handle invalid chart data', async () => {
      const invalidData = {
        chart_type: 'bar_chart',
        data: {}, // Empty data
        config: {},
        research_id: testResearchId,
      };

      const response = await request(app)
        .post('/api/visualization/generate')
        .send(invalidData)
        .expect(400);

      expect(response.body).toHaveProperty('error');
      expect(response.body.error).toContain('VISUALIZATION_FAILED');
    });

    test('should validate request schema', async () => {
      const invalidRequest = {
        chart_type: 'invalid_chart_type',
        data: { x: [1, 2, 3] },
      };

      const response = await request(app)
        .post('/api/visualization/generate')
        .send(invalidRequest)
        .expect(400);

      expect(response.body).toHaveProperty('error', 'INVALID_REQUEST');
      expect(response.body).toHaveProperty('details');
    });
  });

  describe('Figure Management API', () => {
    let sampleFigureId: string;

    beforeEach(async () => {
      // Create a sample figure for testing
      if (figuresService) {
        const figureInput: FigureCreateInput = {
          research_id: testResearchId,
          figure_type: 'bar_chart',
          title: 'Test Chart',
          caption: 'A test chart for API testing',
          alt_text: 'Bar chart showing test data',
          image_data: Buffer.from('fake-image-data'),
          image_format: 'png',
          width: 800,
          height: 600,
          dpi: 300,
          generated_by: 'test_suite',
        };

        const figure = await figuresService.createFigure(figureInput);
        sampleFigureId = figure.id;
        createdFigureIds.push(sampleFigureId);
      }
    });

    test('should list figures for research project', async () => {
      if (!figuresService) {
        console.warn('Skipping database test - figures service not available');
        return;
      }

      const response = await request(app)
        .get(`/api/visualization/figures/${testResearchId}`)
        .expect(200);

      expect(response.body).toHaveProperty('research_id', testResearchId);
      expect(response.body).toHaveProperty('figures');
      expect(response.body).toHaveProperty('total');
      expect(response.body.figures).toBeInstanceOf(Array);
      expect(response.body.figures.length).toBeGreaterThan(0);
      
      // Figures should not include image data in list
      const figure = response.body.figures[0];
      expect(figure).not.toHaveProperty('image_data');
      expect(figure).toHaveProperty('has_image_data', true);
    });

    test('should get specific figure by ID', async () => {
      if (!figuresService || !sampleFigureId) {
        console.warn('Skipping database test - figures service not available');
        return;
      }

      // Get figure without image data
      const response1 = await request(app)
        .get(`/api/visualization/figure/${sampleFigureId}`)
        .expect(200);

      expect(response1.body).toHaveProperty('id', sampleFigureId);
      expect(response1.body).toHaveProperty('figure_type', 'bar_chart');
      expect(response1.body).toHaveProperty('title', 'Test Chart');
      expect(response1.body).not.toHaveProperty('image_data');

      // Get figure with image data
      const response2 = await request(app)
        .get(`/api/visualization/figure/${sampleFigureId}?include_image=true`)
        .expect(200);

      expect(response2.body).toHaveProperty('image_data');
      expect(typeof response2.body.image_data).toBe('string');
    });

    test('should return 404 for non-existent figure', async () => {
      const fakeId = 'fake-figure-id';

      await request(app)
        .get(`/api/visualization/figure/${fakeId}`)
        .expect(404);
    });

    test('should delete figure', async () => {
      if (!figuresService || !sampleFigureId) {
        console.warn('Skipping database test - figures service not available');
        return;
      }

      const response = await request(app)
        .delete(`/api/visualization/figure/${sampleFigureId}`)
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('figure_id', sampleFigureId);

      // Verify figure is deleted
      await request(app)
        .get(`/api/visualization/figure/${sampleFigureId}`)
        .expect(404);

      // Remove from cleanup list since it's already deleted
      createdFigureIds = createdFigureIds.filter(id => id !== sampleFigureId);
    });

    test('should get figure statistics', async () => {
      if (!figuresService) {
        console.warn('Skipping database test - figures service not available');
        return;
      }

      const response = await request(app)
        .get(`/api/visualization/stats/${testResearchId}`)
        .expect(200);

      expect(response.body).toHaveProperty('research_id', testResearchId);
      expect(response.body).toHaveProperty('statistics');
      expect(response.body.statistics).toHaveProperty('total');
      expect(response.body.statistics).toHaveProperty('by_type');
      expect(response.body.statistics).toHaveProperty('by_status');
      expect(response.body.statistics).toHaveProperty('size_mb');
    });

    test('should update PHI scan results', async () => {
      if (!figuresService || !sampleFigureId) {
        console.warn('Skipping database test - figures service not available');
        return;
      }

      const phiScanUpdate = {
        phi_scan_status: 'PASS',
        phi_risk_level: 'SAFE',
        phi_findings: [],
      };

      const response = await request(app)
        .patch(`/api/visualization/figure/${sampleFigureId}/phi-scan`)
        .send(phiScanUpdate)
        .expect(200);

      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('phi_scan_status', 'PASS');
      expect(response.body).toHaveProperty('phi_risk_level', 'SAFE');
    });
  });

  describe('Service Health and Capabilities', () => {
    test('should return visualization capabilities', async () => {
      const response = await request(app)
        .get('/api/visualization/capabilities')
        .expect(200);

      expect(response.body).toHaveProperty('chart_types');
      expect(response.body.chart_types).toBeInstanceOf(Array);
      expect(response.body.chart_types).toContain('bar_chart');
      expect(response.body.chart_types).toContain('line_chart');
      
      expect(response.body).toHaveProperty('journal_styles');
      expect(response.body).toHaveProperty('color_palettes');
      expect(response.body).toHaveProperty('export_formats');
    });

    test('should return service health status', async () => {
      const response = await request(app)
        .get('/api/visualization/health')
        .expect(200);

      expect(response.body).toHaveProperty('service', 'visualization');
      expect(response.body).toHaveProperty('stage', 8);
      expect(response.body).toHaveProperty('worker_status');
      expect(response.body).toHaveProperty('timestamp');
      
      // Status should be healthy or degraded
      expect(['healthy', 'degraded']).toContain(response.body.status);
    });
  });

  describe('Error Handling', () => {
    test('should handle worker service unavailable', async () => {
      // Mock worker service failure by using invalid URL
      const originalEnv = process.env.WORKER_URL;
      process.env.WORKER_URL = 'http://invalid-url:9999';
      
      const chartData = {
        chart_type: 'bar_chart',
        data: { group: ['A', 'B'], value: [1, 2] },
        research_id: testResearchId,
      };

      const response = await request(app)
        .post('/api/visualization/generate')
        .send(chartData)
        .expect(503);

      expect(response.body).toHaveProperty('error', 'SERVICE_UNAVAILABLE');
      
      // Restore original environment
      process.env.WORKER_URL = originalEnv;
    });

    test('should handle database unavailable gracefully', async () => {
      // If database is not available, list should still work
      const response = await request(app)
        .get('/api/visualization/figures/nonexistent-research')
        .expect(res => {
          // Either 200 (working) or 503 (database unavailable)
          expect([200, 503]).toContain(res.status);
        });

      if (response.status === 503) {
        expect(response.body).toHaveProperty('error', 'DATABASE_UNAVAILABLE');
      }
    });
  });

  describe('Performance and Load', () => {
    test('should handle multiple concurrent chart requests', async () => {
      const requests = Array.from({ length: 3 }, (_, i) => {
        return request(app)
          .post('/api/visualization/generate')
          .send({
            chart_type: 'bar_chart',
            data: {
              group: [`A${i}`, `B${i}`, `C${i}`],
              value: [Math.random() * 10, Math.random() * 10, Math.random() * 10],
            },
            config: {
              title: `Concurrent Test Chart ${i}`,
              dpi: 72, // Minimal DPI for speed
            },
            research_id: `${testResearchId}_concurrent_${i}`,
          });
      });

      const responses = await Promise.all(requests);
      
      // All should succeed
      responses.forEach(response => {
        expect(response.status).toBe(200);
        expect(response.body).toHaveProperty('status', 'completed');
        
        // Track created figures for cleanup
        if (response.body.result?.database_id) {
          createdFigureIds.push(response.body.result.database_id);
        }
      });
    }, TEST_CONFIG.TIMEOUT * 2);

    test('should respect timeout limits', async () => {
      // This test might be skipped if worker is too fast
      const chartData = {
        chart_type: 'scatter_plot',
        data: {
          x: Array.from({ length: 10000 }, () => Math.random()),
          y: Array.from({ length: 10000 }, () => Math.random()),
        },
        config: {
          title: 'Large Dataset Test',
          dpi: 300,
        },
        research_id: testResearchId,
      };

      // Should complete within reasonable time
      const startTime = Date.now();
      const response = await request(app)
        .post('/api/visualization/generate')
        .send(chartData)
        .timeout(TEST_CONFIG.TIMEOUT);
      
      const duration = Date.now() - startTime;
      
      if (response.status === 200) {
        expect(duration).toBeLessThan(TEST_CONFIG.TIMEOUT);
        expect(response.body).toHaveProperty('duration_ms');
        expect(response.body.duration_ms).toBeGreaterThan(0);
        
        if (response.body.result?.database_id) {
          createdFigureIds.push(response.body.result.database_id);
        }
      }
    }, TEST_CONFIG.TIMEOUT + 5000);
  });
});