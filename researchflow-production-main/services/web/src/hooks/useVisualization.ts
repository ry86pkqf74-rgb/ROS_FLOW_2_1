/**
 * useVisualization Hook - Enhanced Production Version
 * 
 * React hook for interacting with visualization API endpoints.
 * Handles chart generation, figure management, capabilities queries,
 * caching, monitoring, and error recovery.
 */

import { useState, useCallback, useEffect } from 'react';
import { useAuth } from './useAuth';
import { useToast } from './use-toast';

export interface ChartGenerationRequest {
  chart_type: string;
  data: Record<string, any>;
  config?: Record<string, any>;
  research_id?: string;
  metadata?: Record<string, any>;
}

export interface ChartGenerationResponse {
  request_id: string;
  research_id: string | null;
  status: string;
  result: {
    success: boolean;
    figure_id: string;
    image_base64: string;
    format: string;
    width: number;
    height: number;
    dpi: number;
    caption: string;
    alt_text: string;
    data_summary?: Record<string, any>;
    rendering_info?: Record<string, any>;
    metadata: Record<string, any>;
    duration_ms: number;
    database_id?: string;
    stored_at?: string;
  };
  duration_ms: number;
  cached?: boolean;
}

export interface Figure {
  id: string;
  research_id: string;
  artifact_id?: string;
  figure_type: string;
  title?: string;
  caption?: string;
  alt_text?: string;
  image_format: string;
  size_bytes: number;
  width?: number;
  height?: number;
  dpi: number;
  chart_config: Record<string, any>;
  journal_style?: string;
  color_palette?: string;
  generated_by: string;
  agent_version: string;
  phi_scan_status: 'PENDING' | 'PASS' | 'FAIL' | 'OVERRIDE';
  phi_risk_level?: string;
  phi_findings: any[];
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
  has_image_data?: boolean;
}

export interface FigureListResponse {
  research_id: string;
  figures: Figure[];
  total: number;
  pagination: {
    limit: number;
    offset: number;
  };
}

export interface FigureStatsResponse {
  research_id: string;
  statistics: {
    total: number;
    by_type: Record<string, number>;
    by_status: Record<string, number>;
    total_size_bytes: number;
    size_mb: string;
  };
  timestamp: string;
}

export interface DashboardMetrics {
  chartsGenerated24h: number;
  averageGenerationTime: number;
  cacheHitRate: number;
  errorRate: number;
  topChartTypes: Array<{ type: string; count: number; percentage: number }>;
  topJournalStyles: Array<{ style: string; count: number; percentage: number }>;
  workerStatus: string;
  databaseStatus: string;
  cacheStatus: string;
  queueDepth: number;
  activeJobs: number;
  memoryUsage: number;
  averageImageSize: number;
  successRate: number;
  timeouts: number;
}

export interface VisualizationCapabilities {
  chart_types: string[];
  journal_styles: string[];
  color_palettes: string[];
  export_formats: string[];
  dpi_options: number[];
}

export interface VisualizationHealth {
  status: string;
  service: string;
  stage: number;
  components: {
    worker: {
      status: string;
      url: string;
      latency: number;
    };
    database: {
      healthy: boolean;
      latency?: number;
    };
    cache: {
      status: string;
      latency?: number;
    };
    metrics: {
      healthy: boolean;
    };
  };
  configuration: {
    cacheEnabled: boolean;
    rateLimitEnabled: boolean;
    maxDataPoints: number;
    maxConcurrentJobs: number;
  };
  timestamp: string;
}

export interface VisualizationError {
  error: string;
  message: string;
  errorId: string;
  timestamp: string;
  suggestions: string[];
  retryable: boolean;
  details?: any;
}

export function useVisualization() {
  const { getToken } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<VisualizationError | null>(null);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [health, setHealth] = useState<VisualizationHealth | null>(null);
  const [capabilities, setCapabilities] = useState<VisualizationCapabilities | null>(null);

  const generateChart = useCallback(
    async (request: ChartGenerationRequest): Promise<ChartGenerationResponse> => {
      setLoading(true);
      setError(null);

      const startTime = Date.now();
      
      try {
        const token = await getToken();
        const response = await fetch('/api/visualization/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': `frontend_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData: VisualizationError = await response.json().catch(() => ({
            error: 'UNKNOWN_ERROR',
            message: `Chart generation failed: ${response.statusText}`,
            errorId: 'unknown',
            timestamp: new Date().toISOString(),
            suggestions: ['Try again in a moment', 'Check your internet connection'],
            retryable: true,
          }));
          
          setError(errorData);
          
          // Show user-friendly toast notification
          toast({
            title: 'Chart Generation Failed',
            description: errorData.message,
            variant: 'destructive',
          });
          
          throw new Error(errorData.message);
        }

        const data = await response.json();
        
        // Show success notification with cache info
        const duration = Date.now() - startTime;
        const cacheInfo = data.cached ? ' (from cache)' : '';
        
        toast({
          title: 'Chart Generated Successfully',
          description: `Generated ${request.chart_type.replace('_', ' ')} in ${duration}ms${cacheInfo}`,
          variant: 'default',
        });
        
        return data;
      } catch (err) {
        if (!error) { // Only set error if not already set above
          const fallbackError: VisualizationError = {
            error: 'NETWORK_ERROR',
            message: err instanceof Error ? err.message : 'Unknown error occurred',
            errorId: `client_${Date.now()}`,
            timestamp: new Date().toISOString(),
            suggestions: ['Check your internet connection', 'Try again in a moment'],
            retryable: true,
          };
          setError(fallbackError);
        }
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [getToken, toast, error]
  );

  const getCapabilities = useCallback(async (): Promise<VisualizationCapabilities> => {
    try {
      const response = await fetch('/api/visualization/capabilities', {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch capabilities: ${response.statusText}`);
      }

      const data = await response.json();
      setCapabilities(data);
      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      console.warn('Failed to fetch visualization capabilities:', error.message);
      
      // Return fallback capabilities
      const fallbackCapabilities = {
        chart_types: ['bar_chart', 'line_chart', 'scatter_plot', 'box_plot'],
        journal_styles: ['nature', 'jama', 'nejm'],
        color_palettes: ['colorblind_safe', 'viridis', 'grayscale'],
        export_formats: ['png', 'svg', 'pdf'],
        dpi_options: [72, 150, 300, 600],
      };
      
      setCapabilities(fallbackCapabilities);
      return fallbackCapabilities;
    }
  }, []);

  const getHealth = useCallback(async (): Promise<VisualizationHealth> => {
    try {
      const response = await fetch('/api/visualization/health', {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch health: ${response.statusText}`);
      }

      const data = await response.json();
      setHealth(data);
      return data;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      console.warn('Failed to fetch visualization health:', error.message);
      throw error;
    }
  }, []);

  const listFigures = useCallback(
    async (
      researchId: string,
      options: {
        figure_type?: string;
        phi_scan_status?: string;
        limit?: number;
        offset?: number;
      } = {}
    ): Promise<FigureListResponse> => {
      const token = await getToken();
      
      // Build query parameters
      const params = new URLSearchParams();
      if (options.figure_type) params.append('figure_type', options.figure_type);
      if (options.phi_scan_status) params.append('phi_scan_status', options.phi_scan_status);
      if (options.limit) params.append('limit', options.limit.toString());
      if (options.offset) params.append('offset', options.offset.toString());
      
      const queryString = params.toString() ? `?${params.toString()}` : '';
      
      const response = await fetch(`/api/visualization/figures/${researchId}${queryString}`, {
        method: 'GET',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to list figures: ${response.statusText}`);
      }

      return await response.json();
    },
    [getToken]
  );

  const getFigure = useCallback(
    async (figureId: string, includeImage: boolean = false): Promise<Figure & { image_data?: string }> => {
      const token = await getToken();
      const queryString = includeImage ? '?include_image=true' : '';
      
      const response = await fetch(`/api/visualization/figure/${figureId}${queryString}`, {
        method: 'GET',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get figure: ${response.statusText}`);
      }

      return await response.json();
    },
    [getToken]
  );

  const deleteFigure = useCallback(
    async (figureId: string) => {
      const token = await getToken();
      const response = await fetch(`/api/visualization/figure/${figureId}`, {
        method: 'DELETE',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete figure: ${response.statusText}`);
      }

      const result = await response.json();
      
      toast({
        title: 'Figure Deleted',
        description: 'Figure has been successfully deleted',
        variant: 'default',
      });

      return result;
    },
    [getToken, toast]
  );
  
  // New methods for enhanced functionality
  
  const getFigureStats = useCallback(
    async (researchId: string): Promise<FigureStatsResponse> => {
      const token = await getToken();
      const response = await fetch(`/api/visualization/stats/${researchId}`, {
        method: 'GET',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get figure statistics: ${response.statusText}`);
      }

      return await response.json();
    },
    [getToken]
  );
  
  const getDashboardMetrics = useCallback(async (): Promise<DashboardMetrics> => {
    try {
      const token = await getToken();
      const response = await fetch('/api/visualization/dashboard', {
        method: 'GET',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get dashboard metrics: ${response.statusText}`);
      }

      const data = await response.json();
      setMetrics(data.metrics);
      return data.metrics;
    } catch (err) {
      console.warn('Failed to fetch dashboard metrics:', err);
      throw err;
    }
  }, [getToken]);
  
  const clearCache = useCallback(async (): Promise<{ success: boolean; cleared_entries: number }> => {
    try {
      const token = await getToken();
      const response = await fetch('/api/visualization/cache/clear', {
        method: 'POST',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to clear cache: ${response.statusText}`);
      }

      const result = await response.json();
      
      toast({
        title: 'Cache Cleared',
        description: `Cleared ${result.cleared_entries} cache entries`,
        variant: 'default',
      });
      
      return result;
    } catch (err) {
      toast({
        title: 'Cache Clear Failed',
        description: 'Failed to clear visualization cache',
        variant: 'destructive',
      });
      throw err;
    }
  }, [getToken, toast]);
  
  // Auto-fetch capabilities on mount
  useEffect(() => {
    getCapabilities().catch(() => {
      // Silently handle capability fetch failure
    });
  }, [getCapabilities]);

  return {
    // Core functionality
    generateChart,
    getCapabilities,
    getHealth,
    listFigures,
    getFigure,
    deleteFigure,
    
    // Enhanced functionality
    getFigureStats,
    getDashboardMetrics,
    clearCache,
    
    // State
    loading,
    error,
    metrics,
    health,
    capabilities,
    
    // Utility functions
    clearError: () => setError(null),
    refreshMetrics: getDashboardMetrics,
    refreshHealth: getHealth,
  };
}
