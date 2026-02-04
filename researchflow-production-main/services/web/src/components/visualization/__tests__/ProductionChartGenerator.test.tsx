/**
 * Production Chart Generator Tests
 * 
 * Comprehensive tests for the enhanced production chart generator component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, Mock } from 'vitest';
import ProductionChartGenerator from '../ProductionChartGenerator';
import * as useVisualizationModule from '../../../hooks/useVisualization';

// Mock the useVisualization hook
const mockUseVisualization = {
  generateChart: vi.fn(),
  getCapabilities: vi.fn(),
  getHealth: vi.fn(),
  loading: false,
  error: null,
  capabilities: {
    chart_types: ['bar_chart', 'line_chart', 'scatter_plot', 'box_plot'],
    journal_styles: ['nature', 'jama', 'nejm'],
    color_palettes: ['colorblind_safe', 'viridis', 'grayscale'],
    export_formats: ['png', 'svg', 'pdf'],
    dpi_options: [72, 150, 300, 600]
  },
  health: {
    status: 'healthy',
    components: {
      worker: { status: 'healthy', url: 'test', latency: 100 },
      database: { healthy: true },
      cache: { status: 'healthy' },
      metrics: { healthy: true }
    },
    configuration: {
      cacheEnabled: true,
      rateLimitEnabled: true,
      maxDataPoints: 10000,
      maxConcurrentJobs: 5
    },
    timestamp: new Date().toISOString()
  },
  clearError: vi.fn()
};

vi.mock('../../../hooks/useVisualization', () => ({
  useVisualization: () => mockUseVisualization
}));

// Mock the Chart.js/Plotly components to avoid rendering issues in tests
vi.mock('react-plotly.js', () => ({
  default: ({ data, layout, config, ...props }: any) => (
    <div data-testid="plotly-chart" {...props}>
      Mock Chart: {JSON.stringify({ data, layout, config })}
    </div>
  )
}));

describe('ProductionChartGenerator', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseVisualization.getCapabilities.mockResolvedValue(mockUseVisualization.capabilities);
    mockUseVisualization.getHealth.mockResolvedValue(mockUseVisualization.health);
  });

  describe('Component Rendering', () => {
    it('renders the chart generator interface', () => {
      render(<ProductionChartGenerator />);
      
      expect(screen.getByText('Chart Configuration')).toBeInTheDocument();
      expect(screen.getByText('Performance Stats')).toBeInTheDocument();
      expect(screen.getByText('System Health')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /generate chart/i })).toBeInTheDocument();
    });

    it('displays all configuration options', () => {
      render(<ProductionChartGenerator />);
      
      expect(screen.getByLabelText('Chart Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Journal Style')).toBeInTheDocument();
      expect(screen.getByLabelText('Quality Profile')).toBeInTheDocument();
      expect(screen.getByLabelText('Chart Title')).toBeInTheDocument();
      expect(screen.getByLabelText('Research ID')).toBeInTheDocument();
    });

    it('shows system health indicators', () => {
      render(<ProductionChartGenerator />);
      
      expect(screen.getByText('System Health')).toBeInTheDocument();
      expect(screen.getByText('Worker')).toBeInTheDocument();
      expect(screen.getByText('Database')).toBeInTheDocument();
      expect(screen.getByText('Cache')).toBeInTheDocument();
    });
  });

  describe('Chart Generation', () => {
    it('generates a chart with default settings', async () => {
      const mockResponse = {
        request_id: 'test-123',
        research_id: 'demo-research-001',
        status: 'completed',
        result: {
          success: true,
          figure_id: 'fig-123',
          image_base64: 'base64-image-data',
          format: 'png',
          width: 800,
          height: 600,
          dpi: 150,
          caption: 'Sample Chart',
          alt_text: 'A sample bar chart',
          metadata: { generated_at: new Date().toISOString() }
        },
        duration_ms: 1250,
        cached: false
      };

      mockUseVisualization.generateChart.mockResolvedValue(mockResponse);

      render(<ProductionChartGenerator />);
      
      const generateButton = screen.getByRole('button', { name: /generate chart/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockUseVisualization.generateChart).toHaveBeenCalledWith(
          expect.objectContaining({
            chart_type: 'bar_chart',
            research_id: 'demo-research-001',
            config: expect.objectContaining({
              journal_style: 'nature',
              quality_profile: 'presentation'
            })
          })
        );
      });
    });

    it('handles chart generation errors gracefully', async () => {
      const mockError = {
        error: 'VALIDATION_ERROR',
        message: 'Invalid chart configuration',
        errorId: 'err-123',
        timestamp: new Date().toISOString(),
        suggestions: ['Check your data format', 'Try a different chart type'],
        retryable: true
      };

      mockUseVisualization.error = mockError;
      mockUseVisualization.generateChart.mockRejectedValue(new Error('Chart generation failed'));

      render(<ProductionChartGenerator />);
      
      expect(screen.getByText('Configuration Issues:')).toBeInTheDocument();
      expect(screen.getByText('Invalid chart configuration')).toBeInTheDocument();
      expect(screen.getByText('Check your data format')).toBeInTheDocument();
    });

    it('displays loading state during generation', async () => {
      mockUseVisualization.loading = true;

      render(<ProductionChartGenerator />);
      
      const generateButton = screen.getByRole('button', { name: /generating.../i });
      expect(generateButton).toBeDisabled();
      expect(screen.getByText('Generating...')).toBeInTheDocument();
    });
  });

  describe('Configuration Options', () => {
    it('allows changing chart type', async () => {
      render(<ProductionChartGenerator />);
      
      const chartTypeSelect = screen.getByLabelText('Chart Type');
      await user.click(chartTypeSelect);
      
      // Check if chart type options are available
      await waitFor(() => {
        expect(screen.getByText('Line Chart')).toBeInTheDocument();
      });
    });

    it('allows changing journal style', async () => {
      render(<ProductionChartGenerator />);
      
      const journalStyleSelect = screen.getByLabelText('Journal Style');
      await user.click(journalStyleSelect);
      
      await waitFor(() => {
        expect(screen.getByText('JAMA')).toBeInTheDocument();
        expect(screen.getByText('NEJM')).toBeInTheDocument();
      });
    });

    it('updates quality profile description', async () => {
      render(<ProductionChartGenerator />);
      
      const qualitySelect = screen.getByLabelText('Quality Profile');
      await user.click(qualitySelect);
      
      const publicationOption = screen.getByText('Publication');
      await user.click(publicationOption);
      
      expect(screen.getByText('Maximum quality for journal submissions')).toBeInTheDocument();
    });

    it('allows custom chart title input', async () => {
      render(<ProductionChartGenerator />);
      
      const titleInput = screen.getByLabelText('Chart Title');
      await user.clear(titleInput);
      await user.type(titleInput, 'My Custom Chart Title');
      
      expect(titleInput).toHaveValue('My Custom Chart Title');
    });
  });

  describe('Tabs Navigation', () => {
    it('switches between result tabs', async () => {
      render(<ProductionChartGenerator />);
      
      const dataTab = screen.getByRole('tab', { name: /sample data/i });
      await user.click(dataTab);
      
      expect(screen.getByText(/Sample Data for/i)).toBeInTheDocument();
    });

    it('shows custom data tab', async () => {
      render(<ProductionChartGenerator />);
      
      const customTab = screen.getByRole('tab', { name: /custom data/i });
      await user.click(customTab);
      
      expect(screen.getByPlaceholderText('Enter custom JSON data...')).toBeInTheDocument();
    });

    it('displays generation history', async () => {
      render(<ProductionChartGenerator />);
      
      const historyTab = screen.getByRole('tab', { name: /history/i });
      await user.click(historyTab);
      
      expect(screen.getByText('Generation History')).toBeInTheDocument();
    });
  });

  describe('Performance Stats', () => {
    it('displays initial performance metrics', () => {
      render(<ProductionChartGenerator />);
      
      expect(screen.getByText('Charts Generated')).toBeInTheDocument();
      expect(screen.getByText('Avg Generation Time')).toBeInTheDocument();
      expect(screen.getByText('Cache Hits')).toBeInTheDocument();
      expect(screen.getByText('Cache Rate')).toBeInTheDocument();
    });

    it('updates performance stats after chart generation', async () => {
      const mockResponse = {
        request_id: 'test-123',
        research_id: 'demo-research-001',
        status: 'completed',
        result: {
          success: true,
          figure_id: 'fig-123',
          image_base64: 'base64-image-data',
          format: 'png',
          width: 800,
          height: 600,
          dpi: 150,
          caption: 'Sample Chart',
          alt_text: 'A sample bar chart',
          metadata: { generated_at: new Date().toISOString() }
        },
        duration_ms: 1250,
        cached: true
      };

      mockUseVisualization.generateChart.mockResolvedValue(mockResponse);

      render(<ProductionChartGenerator />);
      
      const generateButton = screen.getByRole('button', { name: /generate chart/i });
      await user.click(generateButton);

      await waitFor(() => {
        // Performance stats should update
        const statsElements = screen.getAllByText('1');
        expect(statsElements.length).toBeGreaterThan(0);
      });
    });
  });

  describe('System Health Monitoring', () => {
    it('displays healthy system status', () => {
      render(<ProductionChartGenerator />);
      
      const healthyBadges = screen.getAllByText('healthy');
      expect(healthyBadges.length).toBeGreaterThan(0);
    });

    it('shows unhealthy system components', () => {
      const unhealthyHealth = {
        ...mockUseVisualization.health,
        components: {
          ...mockUseVisualization.health.components,
          worker: { status: 'unhealthy', url: 'test', latency: 5000 },
          database: { healthy: false }
        }
      };

      mockUseVisualization.health = unhealthyHealth;

      render(<ProductionChartGenerator />);
      
      expect(screen.getByText('unhealthy')).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('displays error messages with suggestions', () => {
      const mockError = {
        error: 'RATE_LIMIT_EXCEEDED',
        message: 'Too many requests',
        errorId: 'err-123',
        timestamp: new Date().toISOString(),
        suggestions: ['Wait before retrying', 'Check your usage limits'],
        retryable: true
      };

      mockUseVisualization.error = mockError;

      render(<ProductionChartGenerator />);
      
      expect(screen.getByText('Too many requests')).toBeInTheDocument();
      expect(screen.getByText('Wait before retrying')).toBeInTheDocument();
    });

    it('allows dismissing errors', async () => {
      const mockError = {
        error: 'TEST_ERROR',
        message: 'Test error message',
        errorId: 'err-123',
        timestamp: new Date().toISOString(),
        suggestions: [],
        retryable: true
      };

      mockUseVisualization.error = mockError;

      render(<ProductionChartGenerator />);
      
      const dismissButton = screen.getByRole('button', { name: /dismiss/i });
      await user.click(dismissButton);
      
      expect(mockUseVisualization.clearError).toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      render(<ProductionChartGenerator />);
      
      expect(screen.getByLabelText('Chart Type')).toBeInTheDocument();
      expect(screen.getByLabelText('Journal Style')).toBeInTheDocument();
      expect(screen.getByLabelText('Quality Profile')).toBeInTheDocument();
    });

    it('supports keyboard navigation', async () => {
      render(<ProductionChartGenerator />);
      
      const chartTypeSelect = screen.getByLabelText('Chart Type');
      chartTypeSelect.focus();
      
      expect(document.activeElement).toBe(chartTypeSelect);
    });
  });

  describe('Integration', () => {
    it('loads capabilities on mount', () => {
      render(<ProductionChartGenerator />);
      
      expect(mockUseVisualization.getCapabilities).toHaveBeenCalled();
      expect(mockUseVisualization.getHealth).toHaveBeenCalled();
    });

    it('uses backend capabilities for dropdowns', async () => {
      render(<ProductionChartGenerator />);
      
      // Wait for capabilities to load
      await waitFor(() => {
        const chartTypeSelect = screen.getByLabelText('Chart Type');
        expect(chartTypeSelect).toBeInTheDocument();
      });
    });
  });
});