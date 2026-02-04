import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle, Circle, AlertTriangle, BarChart3 } from 'lucide-react';
import { StudyData, TestType, AnalysisOptions, StatisticalResult } from '@/types/statistical-analysis';
import { DataInputPanel } from './forms/DataInputPanel';
import { TestSelectionPanel } from './forms/TestSelectionPanel';
import { OptionsConfigPanel } from './forms/OptionsConfigPanel';
import { ResultsContainer } from './results/ResultsContainer';
import { useStatisticalAnalysis } from '@/hooks/useStatisticalAnalysis';

interface StatisticalAnalysisWorkflowProps {
  initialData?: StudyData;
  researchId: string;
  onComplete?: (results: StatisticalResult) => void;
}

type WorkflowStep = 'data-input' | 'test-selection' | 'configuration' | 'results';

interface WorkflowState {
  step: WorkflowStep;
  data: StudyData | null;
  selectedTest: TestType | null;
  analysisOptions: AnalysisOptions;
  results: StatisticalResult | null;
  loading: boolean;
  errors: string[];
}

const WORKFLOW_STEPS = [
  { key: 'data-input', label: 'Data Input', description: 'Upload or enter your data' },
  { key: 'test-selection', label: 'Test Selection', description: 'Choose statistical test' },
  { key: 'configuration', label: 'Configuration', description: 'Set analysis options' },
  { key: 'results', label: 'Results', description: 'View and export results' }
] as const;

export default function StatisticalAnalysisWorkflow({ 
  initialData, 
  researchId, 
  onComplete 
}: StatisticalAnalysisWorkflowProps) {
  const [state, setState] = useState<WorkflowState>({
    step: 'data-input',
    data: initialData || null,
    selectedTest: null,
    analysisOptions: {
      alpha: 0.05,
      confidenceLevel: 0.95,
      effectSizeCalculation: true,
      assumptionChecking: true,
      postHocTests: 'auto',
      multipleComparisonCorrection: 'benjamini_hochberg',
      powerAnalysis: true,
      clinicalSignificance: {
        enabled: true,
        domain: 'general'
      },
      visualizations: ['qq_plot', 'histogram', 'boxplot'],
      exportFormats: ['latex', 'csv', 'json']
    },
    results: null,
    loading: false,
    errors: []
  });

  const { runAnalysis, isLoading } = useStatisticalAnalysis();

  const updateState = useCallback((updates: Partial<WorkflowState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  const handleDataChange = useCallback((data: StudyData) => {
    updateState({ 
      data, 
      errors: [],
      selectedTest: null, // Reset test selection when data changes
      results: null // Clear previous results
    });
  }, [updateState]);

  const handleTestSelection = useCallback((testType: TestType) => {
    updateState({ 
      selectedTest: testType,
      errors: []
    });
  }, [updateState]);

  const handleOptionsChange = useCallback((options: AnalysisOptions) => {
    updateState({ analysisOptions: options });
  }, [updateState]);

  const handleRunAnalysis = useCallback(async () => {
    if (!state.data || !state.selectedTest) {
      updateState({ errors: ['Please complete data input and test selection'] });
      return;
    }

    updateState({ loading: true, errors: [] });

    try {
      const analysisRequest = {
        study_data: {
          groups: state.data.groups,
          outcomes: state.data.outcomes,
          covariates: state.data.covariates,
          metadata: {
            ...state.data.metadata,
            research_id: researchId
          }
        },
        options: {
          test_type: state.selectedTest,
          ...state.analysisOptions
        }
      };

      const results = await runAnalysis(researchId, analysisRequest);
      
      updateState({ 
        results, 
        loading: false, 
        step: 'results',
        errors: []
      });

      if (onComplete) {
        onComplete(results);
      }
    } catch (error) {
      updateState({ 
        loading: false,
        errors: [error instanceof Error ? error.message : 'Analysis failed']
      });
    }
  }, [state.data, state.selectedTest, state.analysisOptions, researchId, runAnalysis, updateState, onComplete]);

  const goToStep = useCallback((step: WorkflowStep) => {
    updateState({ step, errors: [] });
  }, [updateState]);

  const canProceedToStep = useCallback((targetStep: WorkflowStep): boolean => {
    switch (targetStep) {
      case 'data-input':
        return true;
      case 'test-selection':
        return state.data !== null;
      case 'configuration':
        return state.data !== null && state.selectedTest !== null;
      case 'results':
        return state.results !== null;
      default:
        return false;
    }
  }, [state.data, state.selectedTest, state.results]);

  const getStepProgress = (): number => {
    const stepIndex = WORKFLOW_STEPS.findIndex(s => s.key === state.step);
    return ((stepIndex + 1) / WORKFLOW_STEPS.length) * 100;
  };

  const getStepIcon = (stepKey: string) => {
    if (state.step === stepKey) {
      return <Circle className=\"h-5 w-5 text-blue-600 fill-current\" />;
    }
    if (canProceedToStep(stepKey as WorkflowStep)) {
      return <CheckCircle className=\"h-5 w-5 text-green-600\" />;
    }
    return <Circle className=\"h-5 w-5 text-gray-400\" />;
  };

  return (
    <div className=\"max-w-6xl mx-auto p-6 space-y-6\">
      {/* Header */}
      <div className=\"bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg\">
        <div className=\"flex items-center gap-3 mb-4\">
          <BarChart3 className=\"h-8 w-8 text-blue-600\" />
          <div>
            <h1 className=\"text-2xl font-bold text-gray-900\">Statistical Analysis Workflow</h1>
            <p className=\"text-gray-600\">Professional statistical analysis with automatic test selection and assumption checking</p>
          </div>
        </div>
        
        {/* Progress Indicator */}
        <div className=\"space-y-3\">
          <div className=\"flex justify-between text-sm font-medium text-gray-700\">
            <span>Progress</span>
            <span>{Math.round(getStepProgress())}% Complete</span>
          </div>
          <Progress value={getStepProgress()} className=\"h-2\" />
          
          {/* Step Navigation */}
          <div className=\"flex justify-between items-center pt-2\">
            {WORKFLOW_STEPS.map((step, index) => (
              <div key={step.key} className=\"flex items-center\">
                <button
                  onClick={() => canProceedToStep(step.key as WorkflowStep) && goToStep(step.key as WorkflowStep)}
                  disabled={!canProceedToStep(step.key as WorkflowStep)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                    state.step === step.key
                      ? 'bg-blue-100 text-blue-700'
                      : canProceedToStep(step.key as WorkflowStep)
                      ? 'hover:bg-gray-100 text-gray-700'
                      : 'text-gray-400 cursor-not-allowed'
                  }`}
                >
                  {getStepIcon(step.key)}
                  <div className=\"text-left\">
                    <div className=\"font-medium\">{step.label}</div>
                    <div className=\"text-xs opacity-75\">{step.description}</div>
                  </div>
                </button>
                {index < WORKFLOW_STEPS.length - 1 && (
                  <div className=\"w-8 h-px bg-gray-300 mx-2\" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Error Display */}
      {state.errors.length > 0 && (
        <Alert variant=\"destructive\">
          <AlertTriangle className=\"h-4 w-4\" />
          <AlertDescription>
            {state.errors.map((error, index) => (
              <div key={index}>{error}</div>
            ))}
          </AlertDescription>
        </Alert>
      )}

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle className=\"flex items-center gap-2\">
            {getStepIcon(state.step)}
            {WORKFLOW_STEPS.find(s => s.key === state.step)?.label}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {state.step === 'data-input' && (
            <DataInputPanel
              onDataChange={handleDataChange}
              initialData={state.data}
              onNext={() => canProceedToStep('test-selection') && goToStep('test-selection')}
            />
          )}

          {state.step === 'test-selection' && state.data && (
            <TestSelectionPanel
              data={state.data}
              onTestSelect={handleTestSelection}
              selectedTest={state.selectedTest}
              onNext={() => canProceedToStep('configuration') && goToStep('configuration')}
              onBack={() => goToStep('data-input')}
            />
          )}

          {state.step === 'configuration' && state.selectedTest && (
            <OptionsConfigPanel
              options={state.analysisOptions}
              onChange={handleOptionsChange}
              testType={state.selectedTest}
              onRunAnalysis={handleRunAnalysis}
              onBack={() => goToStep('test-selection')}
              loading={state.loading || isLoading}
            />
          )}

          {state.step === 'results' && state.results && (
            <ResultsContainer
              results={state.results}
              options={state.analysisOptions}
              onRerun={() => goToStep('configuration')}
              onNewAnalysis={() => {
                updateState({
                  step: 'data-input',
                  data: null,
                  selectedTest: null,
                  results: null,
                  errors: []
                });
              }}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}