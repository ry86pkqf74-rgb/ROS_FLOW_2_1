/**
 * Unit Tests - DataVisualizationAgent
 * 
 * Tests the Python DataVisualizationAgent functionality via API calls.
 * Since the agent runs in the Python worker service, these tests call
 * the FastAPI endpoints to validate functionality.
 */

import { describe, test, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import request from 'supertest';

// Test configuration
const TEST_CONFIG = {
  WORKER_URL: process.env.WORKER_URL || 'http://localhost:8000',
  TIMEOUT: 30000, // 30 seconds
};

// Check if worker service is available
async function isWorkerAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${TEST_CONFIG.WORKER_URL}/health`, { 
      signal: AbortSignal.timeout(5000) 
    });
    return response.ok;
  } catch {
    return false;
  }
}

describe('DataVisualizationAgent', () => {
  let workerAvailable = false;

  beforeAll(async () => {
    workerAvailable = await isWorkerAvailable();
    if (!workerAvailable) {
      console.warn(`Worker service not available at ${TEST_CONFIG.WORKER_URL}`);
      console.warn('Some tests will be skipped. Start worker with: cd services/worker && python -m uvicorn src.main:app');
    }
  });

  describe('Service Health and Capabilities', () => {
    test('should return visualization service health', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/health`);
      expect(response.ok).toBe(true);

      const health = await response.json();
      expect(health).toHaveProperty('available');
      expect(health).toHaveProperty('agent');
      expect(health.agent).toBe('DataVisualizationAgent');
    });

    test('should return available chart types and capabilities', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/capabilities`);
      expect(response.ok).toBe(true);

      const capabilities = await response.json();
      expect(capabilities).toHaveProperty('chart_types');
      expect(capabilities.chart_types).toContain('bar_chart');
      expect(capabilities.chart_types).toContain('line_chart');
      expect(capabilities.chart_types).toContain('scatter_plot');
      expect(capabilities.chart_types).toContain('box_plot');
      
      expect(capabilities).toHaveProperty('journal_styles');
      expect(capabilities.journal_styles).toContain('nature');
      expect(capabilities.journal_styles).toContain('jama');
      
      expect(capabilities).toHaveProperty('color_palettes');
      expect(capabilities.color_palettes).toContain('colorblind_safe');
      
      expect(capabilities).toHaveProperty('export_formats');
      expect(capabilities.export_formats).toContain('png');
      expect(capabilities.export_formats).toContain('svg');
    });
  });

  describe('Bar Chart Generation', () => {
    test('should generate basic bar chart', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          group: ['Control', 'Treatment A', 'Treatment B'],
          value: [5.2, 6.8, 7.3],
        },
        title: 'Treatment Effectiveness',
        x_label: 'Treatment Group',
        y_label: 'Outcome Score',
        dpi: 150, // Lower DPI for faster test
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
        signal: AbortSignal.timeout(TEST_CONFIG.TIMEOUT),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('figure_id');
      expect(result).toHaveProperty('image_base64');
      expect(result).toHaveProperty('format', 'png');
      expect(result).toHaveProperty('width');
      expect(result).toHaveProperty('height');
      expect(result).toHaveProperty('caption');
      expect(result).toHaveProperty('alt_text');
      
      // Verify image data
      expect(result.image_base64).toBeTruthy();
      expect(result.image_base64.length).toBeGreaterThan(1000); // Should have substantial image data
      
      // Verify metadata
      expect(result.width).toBeGreaterThan(0);
      expect(result.height).toBeGreaterThan(0);
      expect(result.caption).toContain('bar chart');
      expect(result.alt_text).toContain('showing');
    }, TEST_CONFIG.TIMEOUT);

    test('should generate bar chart with error bars', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          group: ['A', 'B', 'C'],
          value: [10, 15, 12],
          error: [1.2, 1.8, 1.5],
        },
        title: 'Results with Error Bars',
        show_error_bars: true,
        error_bar_type: 'std',
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('figure_id');
      expect(result).toHaveProperty('image_base64');
      expect(result.alt_text).toContain('error bar');
    }, TEST_CONFIG.TIMEOUT);

    test('should apply journal styling', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          group: ['Group 1', 'Group 2'],
          value: [8.5, 9.2],
        },
        title: 'Nature Style Chart',
        journal_style: 'nature',
        color_palette: 'colorblind_safe',
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('rendering_info');
      expect(result.rendering_info).toHaveProperty('journal_style', 'nature');
      expect(result.rendering_info).toHaveProperty('color_palette', 'colorblind_safe');
    }, TEST_CONFIG.TIMEOUT);
  });

  describe('Line Chart Generation', () => {
    test('should generate line chart with multiple series', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          time: [0, 1, 2, 3, 4, 5],
          series1: [10, 12, 11, 14, 13, 15],
          series2: [8, 10, 9, 12, 11, 13],
        },
        title: 'Time Series Comparison',
        x_label: 'Time (weeks)',
        y_label: 'Score',
        show_markers: true,
        line_width: 2,
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/line-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('figure_id');
      expect(result).toHaveProperty('image_base64');
      expect(result.caption).toContain('line chart');
      expect(result.alt_text).toContain('series');
    }, TEST_CONFIG.TIMEOUT);

    test('should generate line chart with confidence bands', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          x: [1, 2, 3, 4, 5],
          y: [2, 4, 3, 5, 6],
          ci_lower: [1.5, 3.5, 2.5, 4.5, 5.5],
          ci_upper: [2.5, 4.5, 3.5, 5.5, 6.5],
        },
        title: 'Line Chart with Confidence Intervals',
        show_confidence_bands: true,
        confidence_level: 0.95,
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/line-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result.alt_text).toContain('confidence');
      expect(result).toHaveProperty('data_summary');
      expect(result.data_summary).toHaveProperty('confidence_level', 0.95);
    }, TEST_CONFIG.TIMEOUT);
  });

  describe('Scatter Plot Generation', () => {
    test('should generate scatter plot with correlation', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          x: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
          y: [2, 4, 5, 4, 6, 7, 8, 7, 9, 10],
        },
        title: 'Correlation Analysis',
        x_label: 'Variable X',
        y_label: 'Variable Y',
        show_trendline: true,
        show_correlation: true,
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/scatter-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('figure_id');
      expect(result).toHaveProperty('data_summary');
      expect(result.data_summary).toHaveProperty('correlation');
      expect(result.alt_text).toContain('scatter plot');
    }, TEST_CONFIG.TIMEOUT);
  });

  describe('Box Plot Generation', () => {
    test('should generate box plot with outliers', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          group: ['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B', 'C', 'C', 'C', 'C', 'C'],
          value: [1, 2, 3, 4, 10, 2, 3, 4, 5, 6, 3, 4, 5, 6, 7], // Outlier at value=10
        },
        title: 'Distribution Comparison',
        y_label: 'Values',
        show_outliers: true,
        show_means: true,
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/box-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('figure_id');
      expect(result.caption).toContain('box plot');
      expect(result).toHaveProperty('data_summary');
      expect(result.data_summary).toHaveProperty('n_groups');
    }, TEST_CONFIG.TIMEOUT);
  });

  describe('Advanced Chart Types', () => {
    test('should generate Kaplan-Meier survival curve', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          time: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
          event: [1, 0, 1, 1, 0, 1, 0, 1, 1, 0], // 1=event, 0=censored
          group: ['A', 'A', 'A', 'A', 'A', 'B', 'B', 'B', 'B', 'B'],
        },
        title: 'Survival Analysis',
        time_label: 'Time (months)',
        show_risk_table: true,
        show_confidence_intervals: true,
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/kaplan-meier`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      if (response.ok) {
        const result = await response.json();
        expect(result).toHaveProperty('figure_id');
        expect(result.caption).toContain('Kaplan-Meier');
        expect(result.alt_text).toContain('survival');
      } else {
        // KM curves require specialized libraries, may not be available
        expect(response.status).toBe(503);
      }
    }, TEST_CONFIG.TIMEOUT);

    test('should generate forest plot', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          study: ['Study A', 'Study B', 'Study C'],
          effect: [0.85, 0.92, 0.78],
          ci_lower: [0.72, 0.80, 0.65],
          ci_upper: [1.01, 1.06, 0.93],
          weight: [0.3, 0.4, 0.3],
        },
        title: 'Meta-Analysis Results',
        effect_measure: 'Odds Ratio',
        show_summary: true,
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/forest-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      if (response.ok) {
        const result = await response.json();
        expect(result).toHaveProperty('figure_id');
        expect(result.caption).toContain('forest plot');
        expect(result.alt_text).toContain('meta-analysis');
      } else {
        // Forest plots are specialized, may return 503
        expect([200, 503]).toContain(response.status);
      }
    }, TEST_CONFIG.TIMEOUT);
  });

  describe('Error Handling and Validation', () => {
    test('should handle missing required data', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const invalidRequest = {
        data: {}, // Empty data
        title: 'Invalid Chart',
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidRequest),
      });

      expect(response.ok).toBe(false);
      expect([400, 422]).toContain(response.status);

      const error = await response.json();
      expect(error).toHaveProperty('detail');
    });

    test('should handle mismatched data dimensions', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const mismatchedRequest = {
        data: {
          group: ['A', 'B', 'C'], // 3 elements
          value: [1, 2],         // 2 elements - mismatch!
        },
        title: 'Mismatched Data',
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mismatchedRequest),
      });

      expect(response.ok).toBe(false);
      expect([400, 422]).toContain(response.status);

      const error = await response.json();
      expect(error.detail || error.message).toMatch(/dimension|length|mismatch/i);
    });

    test('should handle invalid DPI values', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const invalidDpiRequest = {
        data: {
          group: ['A', 'B'],
          value: [1, 2],
        },
        dpi: 50, // Too low
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(invalidDpiRequest),
      });

      // Should either reject low DPI or clamp to minimum
      if (!response.ok) {
        expect([400, 422]).toContain(response.status);
      } else {
        const result = await response.json();
        expect(result.rendering_info.dpi).toBeGreaterThanOrEqual(72);
      }
    });

    test('should handle timeout for complex charts', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      // Create a very large dataset that might timeout
      const largeDataset = {
        data: {
          x: Array.from({ length: 50000 }, (_, i) => i),
          y: Array.from({ length: 50000 }, () => Math.random()),
        },
        title: 'Large Dataset Test',
        dpi: 300, // High DPI for extra processing
      };

      try {
        const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/scatter-plot`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(largeDataset),
          signal: AbortSignal.timeout(15000), // 15 second timeout
        });

        // Should either complete or timeout gracefully
        if (response.ok) {
          const result = await response.json();
          expect(result).toHaveProperty('figure_id');
        } else {
          // Accept timeout or processing error
          expect([408, 422, 500]).toContain(response.status);
        }
      } catch (error) {
        // Timeout is acceptable for this test
        expect(error.name).toBe('AbortError');
      }
    }, 20000);
  });

  describe('Quality and Accessibility', () => {
    test('should generate accessible alt text', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          category: ['Category A', 'Category B', 'Category C'],
          count: [25, 30, 20],
        },
        title: 'Distribution of Categories',
        x_label: 'Category',
        y_label: 'Count',
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      
      // Alt text should be descriptive and informative
      expect(result.alt_text).toBeTruthy();
      expect(result.alt_text.length).toBeGreaterThan(20);
      expect(result.alt_text).toContain('bar chart');
      expect(result.alt_text).toContain('Category');
      
      // Should describe the data
      expect(result.alt_text).toMatch(/\d+/); // Should contain numbers
    });

    test('should use colorblind-safe palette when requested', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          group: ['Group 1', 'Group 2', 'Group 3'],
          value: [10, 15, 12],
        },
        color_palette: 'colorblind_safe',
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result.rendering_info).toHaveProperty('color_palette', 'colorblind_safe');
    });

    test('should include data summary for reproducibility', async () => {
      if (!workerAvailable) {
        console.warn('Skipping test - worker not available');
        return;
      }

      const chartRequest = {
        data: {
          values: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        },
        title: 'Data Summary Test',
        dpi: 150,
      };

      const response = await fetch(`${TEST_CONFIG.WORKER_URL}/api/visualization/bar-chart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(chartRequest),
      });

      expect(response.ok).toBe(true);

      const result = await response.json();
      expect(result).toHaveProperty('data_summary');
      expect(result.data_summary).toHaveProperty('n_observations');
      expect(result.data_summary.n_observations).toBeGreaterThan(0);
      
      // Should have hash for reproducibility
      expect(result).toHaveProperty('data_hash');
      expect(result.data_hash).toBeTruthy();
    });
  });
});"