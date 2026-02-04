/**
 * Statistical Analysis Hook
 *
 * React hook for managing statistical analysis operations including
 * configuration validation, execution, and result management.
 */

import { useState, useCallback } from 'react';
import {
  StatisticalTestConfig,
  StatisticalAnalysisResult,
  ValidationResult,
  ExecuteAnalysisRequest,
  DatasetMetadata,
  ExportAnalysisRequest
} from '@/types/statistical-analysis';

interface UseStatisticalAnalysisOptions {
  /** Base API URL for statistical analysis endpoints */
  baseUrl?: string;
  /** Default request timeout in milliseconds */
  timeout?: number;
}

interface UseStatisticalAnalysisReturn {
  /** Current analysis results */
  results: StatisticalAnalysisResult | null;
  /** Whether analysis is currently running */
  isLoading: boolean;
  /** Last error that occurred */
  error: string | null;
  /** Validate analysis configuration */
  validateConfig: (datasetId: string, config: StatisticalTestConfig) => Promise<ValidationResult>;
  /** Execute statistical analysis */
  executeAnalysis: (request: ExecuteAnalysisRequest) => Promise<StatisticalAnalysisResult>;
  /** Get dataset metadata */
  getDatasetMetadata: (datasetId: string) => Promise<DatasetMetadata>;
  /** Export analysis results */
  exportAnalysis: (request: ExportAnalysisRequest) => Promise<{ downloadUrl: string; filename: string }>;
  /** Clear current results */
  clearResults: () => void;
  /** Reset error state */
  clearError: () => void;
}

export function useStatisticalAnalysis(
  options: UseStatisticalAnalysisOptions = {}
): UseStatisticalAnalysisReturn {
  const { baseUrl = '/api/v1/statistical-analysis', timeout = 30000 } = options;

  const [results, setResults] = useState<StatisticalAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generic API request function with timeout and error handling
  const apiRequest = useCallback(async <T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(`${baseUrl}${endpoint}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (!data.success) {
        throw new Error(data.message || 'API request failed');
      }

      return data;
    } catch (err) {
      clearTimeout(timeoutId);
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          throw new Error(`Request timed out after ${timeout / 1000}s`);
        }
        throw err;
      }
      
      throw new Error('Unknown error occurred');
    }
  }, [baseUrl, timeout]);

  // Validate analysis configuration
  const validateConfig = useCallback(async (
    datasetId: string,
    config: StatisticalTestConfig
  ): Promise<ValidationResult> => {
    try {
      setError(null);
      
      const response = await apiRequest<{ validation: ValidationResult }>('/validate', {
        method: 'POST',
        body: JSON.stringify({
          datasetId,
          config
        })
      });

      return response.validation;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Validation failed';
      setError(errorMessage);
      
      // Return a failed validation result
      return {
        valid: false,
        errors: [{ field: 'general', message: errorMessage, severity: 'error' }],
        warnings: []
      };
    }
  }, [apiRequest]);

  // Execute statistical analysis
  const executeAnalysis = useCallback(async (
    request: ExecuteAnalysisRequest
  ): Promise<StatisticalAnalysisResult> => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await apiRequest<{ result: StatisticalAnalysisResult }>('/execute', {
        method: 'POST',
        body: JSON.stringify(request)
      });

      const analysisResult = response.result;
      setResults(analysisResult);
      
      return analysisResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis execution failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [apiRequest]);

  // Get dataset metadata
  const getDatasetMetadata = useCallback(async (
    datasetId: string
  ): Promise<DatasetMetadata> => {
    try {
      setError(null);

      const response = await apiRequest<{ metadata: DatasetMetadata }>(`/datasets/${datasetId}/metadata`);
      
      return response.metadata;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch dataset metadata';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [apiRequest]);

  // Export analysis results
  const exportAnalysis = useCallback(async (
    request: ExportAnalysisRequest
  ): Promise<{ downloadUrl: string; filename: string }> => {
    try {
      setError(null);

      const response = await apiRequest<{
        downloadUrl: string;
        filename: string;
        expiresAt: string;
      }>('/export', {
        method: 'POST',
        body: JSON.stringify(request)
      });

      return {
        downloadUrl: response.downloadUrl,
        filename: response.filename
      };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Export failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, [apiRequest]);

  // Clear current results
  const clearResults = useCallback(() => {
    setResults(null);
    setError(null);
  }, []);

  // Reset error state
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    results,
    isLoading,
    error,
    validateConfig,
    executeAnalysis,
    getDatasetMetadata,
    exportAnalysis,
    clearResults,
    clearError
  };
}

// Additional utility hooks for specific use cases

/**
 * Hook for managing multiple analyses
 */
export function useMultipleStatisticalAnalyses() {
  const [analyses, setAnalyses] = useState<Map<string, StatisticalAnalysisResult>>(new Map());
  const baseHook = useStatisticalAnalysis();

  const addAnalysis = useCallback((id: string, result: StatisticalAnalysisResult) => {
    setAnalyses(prev => new Map(prev.set(id, result)));
  }, []);

  const removeAnalysis = useCallback((id: string) => {
    setAnalyses(prev => {
      const newMap = new Map(prev);
      newMap.delete(id);
      return newMap;
    });
  }, []);

  const getAnalysis = useCallback((id: string) => {
    return analyses.get(id) || null;
  }, [analyses]);

  return {
    ...baseHook,
    analyses: Array.from(analyses.values()),
    analysesMap: analyses,
    addAnalysis,
    removeAnalysis,
    getAnalysis
  };
}

/**
 * Hook for analysis comparison
 */
export function useAnalysisComparison(analysisIds: string[]) {
  const [comparisons, setComparisons] = useState<{
    [key: string]: {
      effectSizes: number[];
      pValues: number[];
      sampleSizes: number[];
    };
  }>({});

  const { getAnalysis } = useMultipleStatisticalAnalyses();

  const compareAnalyses = useCallback(() => {
    const results = analysisIds.map(id => getAnalysis(id)).filter(Boolean);
    
    if (results.length < 2) return null;

    // Extract comparable metrics
    const comparison = {
      effectSizes: results
        .map(r => r?.hypothesisTest.effectSize?.value)
        .filter(Boolean) as number[],
      pValues: results.map(r => r?.hypothesisTest.pValue).filter(Boolean) as number[],
      sampleSizes: results
        .map(r => r?.descriptiveStats.reduce((sum, stat) => sum + stat.n, 0))
        .filter(Boolean) as number[]
    };

    setComparisons(prev => ({
      ...prev,
      [analysisIds.join('-')]: comparison
    }));

    return comparison;
  }, [analysisIds, getAnalysis]);

  return {
    comparisons,
    compareAnalyses
  };
}

export default useStatisticalAnalysis;