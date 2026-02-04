/**
 * Statistical Analysis Integration
 *
 * Complete integration component that orchestrates the statistical analysis workflow
 * from configuration through results display and export.
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Calculator, RefreshCw, AlertCircle, CheckCircle, FileText } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import {
  StatisticalTestConfig,
  StatisticalAnalysisResult,
  DatasetMetadata,
  ValidationResult
} from '@/types/statistical-analysis';

import { useStatisticalAnalysis } from '@/hooks/use-statistical-analysis';
import StatisticalAnalysisForm from './StatisticalAnalysisForm';
import StatisticalResults from './StatisticalResults';
import StatisticalExportPanel from './StatisticalExportPanel';

interface StatisticalAnalysisIntegrationProps {
  /** Dataset ID to analyze */
  datasetId: string;
  /** Research/workflow ID */
  researchId: string;
  /** Called when analysis is completed */
  onAnalysisComplete?: (results: StatisticalAnalysisResult) => void;
  /** Called when analysis is exported */
  onExport?: (filename: string, downloadUrl: string) => void;
  /** Initial configuration (for editing existing analysis) */
  initialConfig?: StatisticalTestConfig;
  /** Whether to show advanced options */
  showAdvanced?: boolean;
}

type WorkflowStep = 'loading' | 'configure' | 'executing' | 'results' | 'export' | 'error';

interface WorkflowState {
  step: WorkflowStep;
  progress: number;
  datasetMetadata: DatasetMetadata | null;
  config: StatisticalTestConfig | null;
  validation: ValidationResult | null;
  results: StatisticalAnalysisResult | null;
  error: string | null;
  currentOperation: string;
}

export function StatisticalAnalysisIntegration({
  datasetId,
  researchId,
  onAnalysisComplete,
  onExport,
  initialConfig,
  showAdvanced = false
}: StatisticalAnalysisIntegrationProps) {
  const {
    isLoading,
    error: hookError,
    validateConfig,
    executeAnalysis,
    getDatasetMetadata,
    exportAnalysis,
    clearError
  } = useStatisticalAnalysis();

  const [workflowState, setWorkflowState] = useState<WorkflowState>({
    step: 'loading',
    progress: 0,
    datasetMetadata: null,
    config: initialConfig || null,
    validation: null,
    results: null,
    error: null,
    currentOperation: 'Loading dataset...'
  });

  // Update workflow state helper
  const updateWorkflowState = useCallback((updates: Partial<WorkflowState>) => {
    setWorkflowState(prev => ({ ...prev, ...updates }));
  }, []);

  // Initialize component - load dataset metadata
  useEffect(() => {
    const loadDataset = async () => {
      try {
        updateWorkflowState({ 
          step: 'loading', 
          currentOperation: 'Loading dataset metadata...',
          progress: 20
        });

        const metadata = await getDatasetMetadata(datasetId);
        
        updateWorkflowState({
          step: 'configure',
          datasetMetadata: metadata,
          progress: 100,
          error: null
        });
      } catch (err) {
        updateWorkflowState({
          step: 'error',
          error: err instanceof Error ? err.message : 'Failed to load dataset',
          progress: 0
        });
      }
    };

    loadDataset();
  }, [datasetId, getDatasetMetadata, updateWorkflowState]);

  // Handle configuration submission
  const handleConfigSubmit = useCallback(async (config: StatisticalTestConfig) => {
    try {
      updateWorkflowState({
        step: 'executing',
        config,
        progress: 0,
        currentOperation: 'Validating configuration...',
        error: null
      });

      // Final validation
      const validation = await validateConfig(datasetId, config);
      
      if (!validation.valid) {
        updateWorkflowState({
          step: 'configure',
          validation,
          error: 'Configuration validation failed'
        });
        return;
      }

      updateWorkflowState({
        progress: 20,
        currentOperation: 'Executing statistical analysis...'
      });

      // Execute analysis
      const analysisRequest = {
        researchId,
        config,
        datasetId,
        includeVisualizations: true
      };

      // Simulate progress updates during execution
      const progressInterval = setInterval(() => {
        updateWorkflowState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 5, 90)
        }));
      }, 500);

      const results = await executeAnalysis(analysisRequest);
      
      clearInterval(progressInterval);

      updateWorkflowState({
        step: 'results',
        results,
        progress: 100,
        currentOperation: 'Analysis completed successfully!'
      });

      onAnalysisComplete?.(results);

    } catch (err) {
      updateWorkflowState({
        step: 'error',
        error: err instanceof Error ? err.message : 'Analysis execution failed',
        progress: 0
      });
    }
  }, [datasetId, researchId, validateConfig, executeAnalysis, onAnalysisComplete, updateWorkflowState]);

  // Handle validation changes during configuration
  const handleValidationChange = useCallback((validation: ValidationResult) => {
    updateWorkflowState({ validation });
  }, [updateWorkflowState]);

  // Handle export
  const handleExport = useCallback(async (sections: Record<string, boolean>) => {
    if (!workflowState.results) return;

    try {
      updateWorkflowState({
        currentOperation: 'Generating export...'
      });

      const exportRequest = {
        analysisId: workflowState.results.id,
        format: 'pdf' as const,
        sections: {
          descriptiveStats: sections.descriptiveStats || false,
          hypothesisTest: sections.hypothesisTest || false,
          effectSizes: sections.effectSizes || false,
          assumptions: sections.assumptions || false,
          visualizations: sections.visualizations || false,
          apaText: sections.apaText || false
        }
      };

      const { downloadUrl, filename } = await exportAnalysis(exportRequest);
      
      onExport?.(filename, downloadUrl);

    } catch (err) {
      updateWorkflowState({
        error: err instanceof Error ? err.message : 'Export failed'
      });
    }
  }, [workflowState.results, exportAnalysis, onExport, updateWorkflowState]);

  // Handle retry after error
  const handleRetry = useCallback(() => {
    clearError();
    updateWorkflowState({
      step: workflowState.config ? 'configure' : 'loading',
      error: null,
      progress: 0
    });
  }, [clearError, workflowState.config, updateWorkflowState]);

  // Start new analysis
  const handleNewAnalysis = useCallback(() => {
    updateWorkflowState({
      step: 'configure',
      config: null,
      validation: null,
      results: null,
      error: null,
      progress: 0
    });
  }, [updateWorkflowState]);

  // Render workflow progress
  const renderProgress = () => {
    const steps = [
      { key: 'loading', label: 'Loading', icon: RefreshCw },
      { key: 'configure', label: 'Configure', icon: FileText },
      { key: 'executing', label: 'Executing', icon: Calculator },
      { key: 'results', label: 'Results', icon: CheckCircle }
    ];

    const currentStepIndex = steps.findIndex(s => s.key === workflowState.step);
    
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center text-sm">
          <span className="font-medium">{workflowState.currentOperation}</span>
          <span>{workflowState.progress}%</span>
        </div>
        
        <Progress value={workflowState.progress} className="h-2" />
        
        <div className="flex justify-between items-center">
          {steps.map((step, index) => {
            const Icon = step.icon;
            const isActive = index === currentStepIndex;
            const isComplete = index < currentStepIndex || workflowState.step === 'results';
            
            return (
              <div key={step.key} className="flex items-center">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                  isActive 
                    ? 'border-blue-500 bg-blue-50 text-blue-600'
                    : isComplete
                    ? 'border-green-500 bg-green-50 text-green-600'
                    : 'border-gray-300 bg-gray-50 text-gray-400'
                }`}>
                  <Icon className="h-4 w-4" />
                </div>
                <span className={`ml-2 text-sm ${
                  isActive || isComplete ? 'text-gray-900' : 'text-gray-500'
                }`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header with Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Calculator className="h-6 w-6" />
                Statistical Analysis
              </CardTitle>
              <p className="text-sm text-gray-500 mt-1">
                Dataset: {workflowState.datasetMetadata?.id || datasetId}
                {workflowState.results && (
                  <>
                    {' • '}
                    <Badge variant={workflowState.results.hypothesisTest.significant ? "default" : "outline"}>
                      {workflowState.results.hypothesisTest.significant ? 'Significant' : 'Not Significant'}
                    </Badge>
                  </>
                )}
              </p>
            </div>
            
            <div className="flex gap-2">
              {workflowState.step === 'results' && (
                <Button variant="outline" onClick={handleNewAnalysis}>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  New Analysis
                </Button>
              )}
              
              {workflowState.step === 'error' && (
                <Button variant="outline" onClick={handleRetry}>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  Retry
                </Button>
              )}
            </div>
          </div>
          
          {(['loading', 'executing'].includes(workflowState.step) || isLoading) && (
            <div className="mt-4">
              {renderProgress()}
            </div>
          )}
        </CardHeader>
      </Card>

      {/* Error Display */}
      {(workflowState.error || hookError) && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {workflowState.error || hookError}
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content */}
      {workflowState.step === 'configure' && workflowState.datasetMetadata && (
        <StatisticalAnalysisForm
          datasetMetadata={workflowState.datasetMetadata}
          initialConfig={workflowState.config || undefined}
          onSubmit={handleConfigSubmit}
          onValidationChange={handleValidationChange}
          disabled={isLoading}
        />
      )}

      {workflowState.step === 'results' && workflowState.results && (
        <Tabs defaultValue="results" className="space-y-4">
          <TabsList>
            <TabsTrigger value="results">Results</TabsTrigger>
            <TabsTrigger value="export">Export</TabsTrigger>
          </TabsList>

          <TabsContent value="results">
            <StatisticalResults
              results={workflowState.results}
              onExport={handleExport}
              onCopy={(content, format) => {
                navigator.clipboard.writeText(content);
                // Could add toast notification here
              }}
            />
          </TabsContent>

          <TabsContent value="export">
            <StatisticalExportPanel
              results={workflowState.results}
              onExport={async (request) => {
                const result = await exportAnalysis(request);
                onExport?.(result.filename, result.downloadUrl);
                return result;
              }}
              isExporting={isLoading}
            />
          </TabsContent>
        </Tabs>
      )}

      {/* Loading State */}
      {workflowState.step === 'loading' && (
        <Card>
          <CardContent className="py-12 text-center">
            <RefreshCw className="h-12 w-12 mx-auto mb-4 text-blue-500 animate-spin" />
            <h3 className="text-lg font-semibold mb-2">Loading Dataset</h3>
            <p className="text-gray-500">Analyzing dataset structure and preparing configuration...</p>
          </CardContent>
        </Card>
      )}

      {/* Execution State */}
      {workflowState.step === 'executing' && (
        <Card>
          <CardContent className="py-12 text-center">
            <Calculator className="h-12 w-12 mx-auto mb-4 text-blue-500" />
            <h3 className="text-lg font-semibold mb-2">Running Analysis</h3>
            <p className="text-gray-500">{workflowState.currentOperation}</p>
            <div className="mt-4 max-w-xs mx-auto">
              {renderProgress()}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default StatisticalAnalysisIntegration;