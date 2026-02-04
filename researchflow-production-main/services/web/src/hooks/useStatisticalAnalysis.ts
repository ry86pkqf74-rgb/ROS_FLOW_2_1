/**
 * React Hook for Stage 7: Statistical Analysis
 *
 * Provides API integration for statistical analysis workflow including:
 * - Test configuration validation
 * - Analysis execution
 * - Results caching and management
 * - Dataset metadata fetching
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiRequest } from '@/lib/queryClient';
import { useToast } from '@/hooks/use-toast';
import type {
  StatisticalTestConfig,
  ExecuteAnalysisRequest,
  ExecuteAnalysisResponse,
  StatisticalAnalysisResult,
  ValidateAnalysisResponse,
  GetDatasetMetadataResponse,
  AvailableTestsResponse,
  ExportAnalysisRequest,
  ExportAnalysisResponse,
} from '@/types/statistical-analysis';

/**
 * Hook for fetching available statistical tests
 */
export function useAvailableTests() {
  return useQuery<AvailableTestsResponse>({
    queryKey: ['/api/statistical-tests'],
    queryFn: async () => {
      const response = await apiRequest('GET', '/api/statistical-tests');
      return response.json();
    },
    staleTime: 300000, // 5 minutes - tests info doesn't change often
  });
}

/**
 * Hook for fetching dataset metadata for variable selection
 */
export function useDatasetMetadata(datasetId: string | undefined) {
  return useQuery<GetDatasetMetadataResponse>({
    queryKey: ['/api/datasets', datasetId, 'metadata'],
    queryFn: async () => {
      if (!datasetId) {
        throw new Error('Dataset ID is required');
      }
      const response = await apiRequest('GET', `/api/datasets/${datasetId}/metadata`);
      return response.json();
    },
    enabled: !!datasetId,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook for validating analysis configuration
 */
export function useValidateAnalysis() {
  return useMutation<ValidateAnalysisResponse, Error, StatisticalTestConfig>({
    mutationFn: async (config) => {
      const response = await apiRequest('POST', '/api/statistical-analysis/validate', config);
      return response.json();
    },
  });
}

/**
 * Hook for executing statistical analysis (Stage 7)
 */
export function useExecuteStatisticalAnalysis() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation<ExecuteAnalysisResponse, Error, ExecuteAnalysisRequest>({
    mutationFn: async (request) => {
      const { researchId, config, datasetId, includeVisualizations = true } = request;
      
      const response = await apiRequest(
        'POST',
        `/api/research/${researchId}/stage/7/execute`,
        {
          config,
          datasetId,
          includeVisualizations,
        }
      );
      
      return response.json();
    },
    onSuccess: (data, variables) => {
      if (data.success) {
        toast({
          title: 'Analysis Complete',
          description: `Statistical analysis completed in ${data.result.duration}ms`,
        });

        // Invalidate and refetch related queries
        queryClient.invalidateQueries({
          queryKey: ['/api/research', variables.researchId, 'stage', 7],
        });

        // Cache the result
        queryClient.setQueryData(
          ['/api/research', variables.researchId, 'stage', 7, 'result', data.result.id],
          data.result
        );
      } else {
        toast({
          title: 'Analysis Failed',
          description: data.message || 'An error occurred during analysis',
          variant: 'destructive',
        });
      }
    },
    onError: (error) => {
      toast({
        title: 'Analysis Error',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for fetching previous analysis results
 */
export function useAnalysisResults(researchId: string, analysisId?: string) {
  return useQuery<StatisticalAnalysisResult>({
    queryKey: ['/api/research', researchId, 'stage', 7, 'result', analysisId],
    queryFn: async () => {
      if (!analysisId) {
        throw new Error('Analysis ID is required');
      }
      const response = await apiRequest(
        'GET',
        `/api/research/${researchId}/stage/7/results/${analysisId}`
      );
      return response.json();
    },
    enabled: !!researchId && !!analysisId,
    staleTime: 300000, // 5 minutes - analysis results don't change
  });
}

/**
 * Hook for listing all analyses for a research project
 */
export function useListAnalyses(researchId: string) {
  return useQuery<{ analyses: StatisticalAnalysisResult[] }>({
    queryKey: ['/api/research', researchId, 'stage', 7, 'analyses'],
    queryFn: async () => {
      const response = await apiRequest(
        'GET',
        `/api/research/${researchId}/stage/7/analyses`
      );
      return response.json();
    },
    enabled: !!researchId,
  });
}

/**
 * Hook for exporting analysis results
 */
export function useExportAnalysis() {
  const { toast } = useToast();

  return useMutation<ExportAnalysisResponse, Error, ExportAnalysisRequest>({
    mutationFn: async (request) => {
      const response = await apiRequest(
        'POST',
        '/api/statistical-analysis/export',
        request
      );
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast({
          title: 'Export Ready',
          description: `Download ready: ${data.filename}`,
        });

        // Trigger download
        window.open(data.downloadUrl, '_blank');
      } else {
        toast({
          title: 'Export Failed',
          description: data.message || 'Failed to export analysis',
          variant: 'destructive',
        });
      }
    },
    onError: (error) => {
      toast({
        title: 'Export Error',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for deleting an analysis result
 */
export function useDeleteAnalysis() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  return useMutation<void, Error, { researchId: string; analysisId: string }>({
    mutationFn: async ({ researchId, analysisId }) => {
      await apiRequest(
        'DELETE',
        `/api/research/${researchId}/stage/7/results/${analysisId}`
      );
    },
    onSuccess: (_, variables) => {
      toast({
        title: 'Analysis Deleted',
        description: 'Analysis has been removed',
      });

      // Invalidate list query
      queryClient.invalidateQueries({
        queryKey: ['/api/research', variables.researchId, 'stage', 7, 'analyses'],
      });
    },
    onError: (error) => {
      toast({
        title: 'Delete Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for saving analysis configuration as draft
 */
export function useSaveAnalysisDraft() {
  const queryClient = useQueryClient();

  return useMutation<
    { success: boolean; draftId: string },
    Error,
    { researchId: string; config: StatisticalTestConfig; name?: string }
  >({
    mutationFn: async ({ researchId, config, name }) => {
      const response = await apiRequest(
        'POST',
        `/api/research/${researchId}/stage/7/drafts`,
        { config, name }
      );
      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['/api/research', variables.researchId, 'stage', 7, 'drafts'],
      });
    },
  });
}

/**
 * Hook for loading saved analysis drafts
 */
export function useAnalysisDrafts(researchId: string) {
  return useQuery<{
    drafts: Array<{
      id: string;
      name: string;
      config: StatisticalTestConfig;
      createdAt: string;
      updatedAt: string;
    }>;
  }>({
    queryKey: ['/api/research', researchId, 'stage', 7, 'drafts'],
    queryFn: async () => {
      const response = await apiRequest(
        'GET',
        `/api/research/${researchId}/stage/7/drafts`
      );
      return response.json();
    },
    enabled: !!researchId,
  });
}

export default {
  useAvailableTests,
  useDatasetMetadata,
  useValidateAnalysis,
  useExecuteStatisticalAnalysis,
  useAnalysisResults,
  useListAnalyses,
  useExportAnalysis,
  useDeleteAnalysis,
  useSaveAnalysisDraft,
  useAnalysisDrafts,
};
