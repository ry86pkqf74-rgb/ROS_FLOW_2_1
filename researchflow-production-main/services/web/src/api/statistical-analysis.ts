/**
 * Statistical Analysis API Client
 * 
 * Frontend API client for Stage 7 Statistical Analysis.
 * Communicates with orchestrator service.
 */

import { apiRequest } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

export interface StudyData {
  groups?: string[];
  outcomes: Record<string, number[]>;
  covariates?: Record<string, (number | string)[]>;
  metadata?: Record<string, any>;
}

export interface AnalysisOptions {
  test_type?: 
    | 't_test_independent'
    | 't_test_paired'
    | 'mann_whitney'
    | 'wilcoxon'
    | 'anova_oneway'
    | 'kruskal_wallis'
    | 'chi_square';
  confidence_level?: number;
  alpha?: number;
  calculate_effect_size?: boolean;
  check_assumptions?: boolean;
  generate_visualizations?: boolean;
}

export interface StatisticalAnalysisRequest {
  study_data: StudyData;
  options?: AnalysisOptions;
}

export interface DescriptiveStats {
  variable_name: string;
  n: number;
  missing: number;
  mean: number;
  median: number;
  std: number;
  min_value: number;
  max_value: number;
  q25: number;
  q75: number;
  iqr: number;
  skewness?: number;
  kurtosis?: number;
  group_name?: string;
}

export interface HypothesisTestResult {
  test_name: string;
  test_type: string;
  statistic: number;
  p_value: number;
  df?: number | [number, number];
  ci_lower?: number;
  ci_upper?: number;
  interpretation: string;
  is_significant?: boolean;
}

export interface EffectSize {
  cohens_d?: number;
  hedges_g?: number;
  eta_squared?: number;
  magnitude?: string;
  interpretation: string;
}

export interface AssumptionCheckResult {
  test_type: string;
  normality?: Record<string, any>;
  homogeneity?: Record<string, any>;
  independence?: Record<string, any>;
  passed: boolean;
  warnings?: string[];
  remediation_suggestions?: string[];
}

export interface FigureSpec {
  figure_type: string;
  title: string;
  data: Record<string, any>;
  caption?: string;
  x_label?: string;
  y_label?: string;
}

export interface StatisticalResult {
  descriptive: DescriptiveStats[];
  inferential?: HypothesisTestResult;
  effect_sizes?: EffectSize;
  assumptions?: AssumptionCheckResult;
  tables?: string[];
  figure_specs?: FigureSpec[];
}

export interface StatisticalAnalysisResponse {
  request_id: string;
  research_id: string;
  status: 'completed' | 'failed' | 'running';
  result?: StatisticalResult;
  duration_ms: number;
  error?: string;
}

export interface ValidationResponse {
  request_id: string;
  valid: boolean;
  warnings: string[];
  errors: string[];
  metadata: {
    sample_size: number;
    outcome_variables: number;
    has_groups: boolean;
    has_covariates: boolean;
  };
}

export interface StatisticalTest {
  type: string;
  name: string;
  description: string;
  assumptions: string[];
  sample_size_min: number;
  groups: number | string;
}

export interface HealthCheckResponse {
  status: string;
  service: string;
  stage: number;
  worker_url: string;
  worker_status: string;
  timestamp: string;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Execute statistical analysis for a research project
 */
export async function executeStatisticalAnalysis(
  researchId: string,
  request: StatisticalAnalysisRequest
): Promise<StatisticalAnalysisResponse> {
  const response = await apiRequest(
    'POST',
    `/api/research/${researchId}/stage/7/execute`,
    request
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Statistical analysis failed');
  }

  return response.json();
}

/**
 * Validate study data before analysis
 */
export async function validateStudyData(
  data: StudyData
): Promise<ValidationResponse> {
  const response = await apiRequest(
    'POST',
    '/api/analysis/statistical/validate',
    data
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Validation failed');
  }

  return response.json();
}

/**
 * Get list of available statistical tests
 */
export async function getAvailableTests(): Promise<{ tests: StatisticalTest[] }> {
  const response = await apiRequest(
    'GET',
    '/api/analysis/statistical/tests'
  );

  if (!response.ok) {
    throw new Error('Failed to fetch available tests');
  }

  return response.json();
}

/**
 * Check health of statistical analysis service
 */
export async function checkStatisticalAnalysisHealth(): Promise<HealthCheckResponse> {
  const response = await apiRequest(
    'GET',
    '/api/analysis/statistical/health'
  );

  if (!response.ok) {
    throw new Error('Health check failed');
  }

  return response.json();
}

/**
 * Helper: Create study data from model configuration
 */
export function createStudyDataFromModel(
  model: {
    dependentVariable?: string;
    independentVariables: string[];
    groupingVariable?: string;
  },
  datasetValues: Record<string, any[]>
): StudyData {
  const studyData: StudyData = {
    outcomes: {},
    metadata: {},
  };

  // Add dependent variable as outcome
  if (model.dependentVariable && datasetValues[model.dependentVariable]) {
    studyData.outcomes[model.dependentVariable] = datasetValues[model.dependentVariable];
  }

  // Add grouping variable if present
  if (model.groupingVariable && datasetValues[model.groupingVariable]) {
    studyData.groups = datasetValues[model.groupingVariable];
  }

  // Add independent variables as covariates
  if (model.independentVariables.length > 0) {
    studyData.covariates = {};
    for (const varName of model.independentVariables) {
      if (datasetValues[varName]) {
        studyData.covariates[varName] = datasetValues[varName];
      }
    }
  }

  return studyData;
}

/**
 * Helper: Map model type to test type
 */
export function mapModelTypeToTestType(
  modelType: string
): AnalysisOptions['test_type'] | undefined {
  const mapping: Record<string, AnalysisOptions['test_type']> = {
    't_test_independent': 't_test_independent',
    't_test_paired': 't_test_paired',
    'mann_whitney': 'mann_whitney',
    'wilcoxon': 'wilcoxon',
    'anova_one_way': 'anova_oneway',
    'anova_oneway': 'anova_oneway',
    'kruskal_wallis': 'kruskal_wallis',
    'chi_square_independence': 'chi_square',
    'chi_square': 'chi_square',
  };

  return mapping[modelType];
}
