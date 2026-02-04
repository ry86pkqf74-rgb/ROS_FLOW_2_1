/**
 * Statistical Analysis Types (Stage 7)
 *
 * Type definitions for statistical analysis workflow including test configuration,
 * execution, results, and validation.
 */

// ============================================================================
// Statistical Test Types
// ============================================================================

/**
 * Supported statistical test types
 */
export type StatisticalTestType =
  | 't-test-independent'
  | 't-test-paired'
  | 't-test-one-sample'
  | 'anova-one-way'
  | 'anova-repeated-measures'
  | 'chi-square'
  | 'fisher-exact'
  | 'mann-whitney'
  | 'wilcoxon'
  | 'kruskal-wallis'
  | 'friedman'
  | 'correlation-pearson'
  | 'correlation-spearman'
  | 'regression-linear'
  | 'regression-logistic';

/**
 * Variable types for analysis
 */
export type VariableType = 'continuous' | 'categorical' | 'ordinal' | 'binary';

/**
 * Variable role in analysis
 */
export type VariableRole = 'dependent' | 'independent' | 'grouping' | 'covariate';

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Variable configuration for analysis
 */
export interface AnalysisVariable {
  /** Column name in dataset */
  name: string;
  /** Variable type */
  type: VariableType;
  /** Role in analysis */
  role: VariableRole;
  /** Label for display */
  label?: string;
  /** Whether variable is required for selected test */
  required?: boolean;
}

/**
 * Statistical test configuration
 */
export interface StatisticalTestConfig {
  /** Type of statistical test */
  testType: StatisticalTestType;
  /** Variables involved in analysis */
  variables: AnalysisVariable[];
  /** Confidence level (e.g., 0.95 for 95%) */
  confidenceLevel: number;
  /** Alpha level for significance testing */
  alpha: number;
  /** Whether to apply multiple comparison correction */
  multipleComparisonCorrection?: 'bonferroni' | 'holm' | 'fdr' | 'none';
  /** Test-specific options */
  options?: {
    /** Two-tailed or one-tailed test */
    tails?: 'two' | 'one';
    /** Direction for one-tailed test */
    direction?: 'greater' | 'less';
    /** Whether to assume equal variances (t-test) */
    equalVariance?: boolean;
    /** Post-hoc test for ANOVA */
    postHoc?: 'tukey' | 'bonferroni' | 'scheffe' | 'none';
    /** Whether to bootstrap confidence intervals */
    bootstrap?: boolean;
    /** Number of bootstrap iterations */
    bootstrapIterations?: number;
  };
}

/**
 * Request payload for executing statistical analysis
 */
export interface ExecuteAnalysisRequest {
  /** Research/workflow ID */
  researchId: string;
  /** Test configuration */
  config: StatisticalTestConfig;
  /** Optional dataset override */
  datasetId?: string;
  /** Whether to include visualizations */
  includeVisualizations?: boolean;
}

// ============================================================================
// Results Types
// ============================================================================

/**
 * Descriptive statistics for a variable
 */
export interface DescriptiveStats {
  /** Variable name */
  variable: string;
  /** Sample size */
  n: number;
  /** Mean */
  mean: number;
  /** Standard deviation */
  sd: number;
  /** Standard error */
  se: number;
  /** Minimum value */
  min: number;
  /** Maximum value */
  max: number;
  /** Median */
  median: number;
  /** Interquartile range */
  iqr: number;
  /** 25th percentile */
  q1: number;
  /** 75th percentile */
  q3: number;
  /** Skewness */
  skewness: number;
  /** Kurtosis */
  kurtosis: number;
  /** 95% confidence interval for mean */
  ci95: [number, number];
}

/**
 * Hypothesis test result
 */
export interface HypothesisTestResult {
  /** Test statistic value */
  statistic: number;
  /** Test statistic name (e.g., "t", "F", "χ²") */
  statisticName: string;
  /** P-value */
  pValue: number;
  /** Degrees of freedom */
  degreesOfFreedom: number | [number, number];
  /** Whether result is significant at alpha level */
  significant: boolean;
  /** Confidence interval */
  confidenceInterval?: [number, number];
  /** Effect size (if applicable) */
  effectSize?: EffectSize;
  /** Post-hoc test results (for ANOVA) */
  postHoc?: PostHocResult[];
}

/**
 * Effect size metrics
 */
export interface EffectSize {
  /** Effect size name (e.g., "Cohen's d", "eta squared") */
  name: string;
  /** Effect size value */
  value: number;
  /** Confidence interval for effect size */
  confidenceInterval?: [number, number];
  /** Interpretation (small, medium, large) */
  interpretation: 'negligible' | 'small' | 'medium' | 'large';
  /** Interpretation guidelines used (e.g., "Cohen's conventions") */
  guidelines: string;
}

/**
 * Post-hoc comparison result
 */
export interface PostHocResult {
  /** Group 1 name */
  group1: string;
  /** Group 2 name */
  group2: string;
  /** Mean difference */
  meanDifference: number;
  /** Standard error */
  standardError: number;
  /** P-value */
  pValue: number;
  /** Adjusted p-value (after correction) */
  adjustedPValue: number;
  /** Whether significant after correction */
  significant: boolean;
  /** Confidence interval */
  confidenceInterval: [number, number];
}

/**
 * Assumption check result
 */
export interface AssumptionCheck {
  /** Assumption name */
  name: string;
  /** Description of the assumption */
  description: string;
  /** Whether assumption is met */
  passed: boolean;
  /** Test statistic (if applicable) */
  statistic?: number;
  /** P-value (if applicable) */
  pValue?: number;
  /** Interpretation */
  interpretation: string;
  /** Recommendation if violated */
  recommendation?: string;
  /** Severity of violation */
  severity?: 'none' | 'mild' | 'moderate' | 'severe';
}

/**
 * Visualization data
 */
export interface Visualization {
  /** Visualization type */
  type: 'histogram' | 'boxplot' | 'qq-plot' | 'scatter' | 'bar' | 'forest-plot';
  /** Chart title */
  title: string;
  /** Chart data (format depends on type) */
  data: any;
  /** Optional configuration */
  config?: Record<string, any>;
  /** Base64-encoded image (if pre-rendered) */
  imageBase64?: string;
}

/**
 * APA-formatted result text
 */
export interface APAFormattedResult {
  /** Section type */
  section: 'descriptive' | 'inferential' | 'effect-size' | 'assumptions';
  /** APA-formatted text */
  text: string;
  /** Whether to include in manuscript */
  includeInManuscript: boolean;
}

/**
 * Complete statistical analysis result
 */
export interface StatisticalAnalysisResult {
  /** Analysis ID */
  id: string;
  /** Research/workflow ID */
  researchId: string;
  /** Test configuration used */
  config: StatisticalTestConfig;
  /** Descriptive statistics */
  descriptiveStats: DescriptiveStats[];
  /** Hypothesis test results */
  hypothesisTest: HypothesisTestResult;
  /** Assumption checks */
  assumptions: AssumptionCheck[];
  /** Visualizations */
  visualizations: Visualization[];
  /** APA-formatted results */
  apaFormatted: APAFormattedResult[];
  /** Overall interpretation */
  interpretation: string;
  /** Recommendations */
  recommendations: string[];
  /** Warnings */
  warnings: string[];
  /** Timestamp */
  createdAt: string;
  /** Analysis duration (ms) */
  duration: number;
}

// ============================================================================
// Validation Types
// ============================================================================

/**
 * Validation error
 */
export interface ValidationError {
  /** Field that failed validation */
  field: string;
  /** Error message */
  message: string;
  /** Severity */
  severity: 'error' | 'warning';
  /** Suggested fix */
  suggestion?: string;
}

/**
 * Validation result
 */
export interface ValidationResult {
  /** Whether validation passed */
  valid: boolean;
  /** Validation errors */
  errors: ValidationError[];
  /** Validation warnings */
  warnings: ValidationError[];
}

/**
 * Dataset column metadata
 */
export interface DatasetColumn {
  /** Column name */
  name: string;
  /** Inferred data type */
  type: VariableType;
  /** Number of non-null values */
  count: number;
  /** Number of null values */
  nullCount: number;
  /** Number of unique values */
  uniqueCount: number;
  /** Sample values */
  sampleValues: any[];
  /** Whether suitable for analysis */
  suitable: boolean;
  /** Issues preventing use */
  issues?: string[];
}

/**
 * Dataset metadata for variable selection
 */
export interface DatasetMetadata {
  /** Dataset ID */
  id: string;
  /** Total rows */
  rowCount: number;
  /** Available columns */
  columns: DatasetColumn[];
  /** Dataset quality score (0-100) */
  qualityScore: number;
  /** Quality issues */
  qualityIssues: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

/**
 * Response from analysis execution endpoint
 */
export interface ExecuteAnalysisResponse {
  success: boolean;
  result: StatisticalAnalysisResult;
  message?: string;
}

/**
 * Response from validation endpoint
 */
export interface ValidateAnalysisResponse {
  success: boolean;
  validation: ValidationResult;
  message?: string;
}

/**
 * Response from dataset metadata endpoint
 */
export interface GetDatasetMetadataResponse {
  success: boolean;
  metadata: DatasetMetadata;
  message?: string;
}

/**
 * Response from available tests endpoint
 */
export interface AvailableTestsResponse {
  success: boolean;
  tests: TestTypeInfo[];
  message?: string;
}

/**
 * Test type information
 */
export interface TestTypeInfo {
  /** Test type identifier */
  type: StatisticalTestType;
  /** Display name */
  name: string;
  /** Description */
  description: string;
  /** Required variable roles */
  requiredVariables: {
    role: VariableRole;
    type: VariableType[];
    minCount: number;
    maxCount?: number;
  }[];
  /** Assumptions */
  assumptions: string[];
  /** When to use this test */
  useCase: string;
  /** Example studies */
  examples: string[];
  /** Supported effect sizes */
  effectSizes: string[];
}

// ============================================================================
// UI State Types
// ============================================================================

/**
 * Analysis form state
 */
export interface AnalysisFormState {
  /** Selected test type */
  testType: StatisticalTestType | null;
  /** Configured variables */
  variables: AnalysisVariable[];
  /** Confidence level */
  confidenceLevel: number;
  /** Alpha level */
  alpha: number;
  /** Multiple comparison correction */
  multipleComparisonCorrection: 'bonferroni' | 'holm' | 'fdr' | 'none';
  /** Test-specific options */
  options: StatisticalTestConfig['options'];
  /** Form validation state */
  validation: ValidationResult | null;
  /** Whether form is valid and ready to submit */
  isValid: boolean;
  /** Whether form has been modified */
  isDirty: boolean;
}

/**
 * Analysis execution state
 */
export interface AnalysisExecutionState {
  /** Whether analysis is running */
  isExecuting: boolean;
  /** Execution progress (0-100) */
  progress: number;
  /** Current step description */
  currentStep: string;
  /** Error if execution failed */
  error: string | null;
}

/**
 * Results display preferences
 */
export interface ResultsDisplayPreferences {
  /** Whether to show descriptive stats */
  showDescriptive: boolean;
  /** Whether to show hypothesis test */
  showHypothesisTest: boolean;
  /** Whether to show effect sizes */
  showEffectSizes: boolean;
  /** Whether to show assumptions */
  showAssumptions: boolean;
  /** Whether to show visualizations */
  showVisualizations: boolean;
  /** Whether to show APA formatted text */
  showAPAText: boolean;
  /** Visualization types to display */
  visualizationTypes: Visualization['type'][];
}

// ============================================================================
// Export/Download Types
// ============================================================================

/**
 * Export format options
 */
export type ExportFormat = 'json' | 'csv' | 'pdf' | 'docx' | 'html';

/**
 * Export request
 */
export interface ExportAnalysisRequest {
  /** Analysis ID */
  analysisId: string;
  /** Export format */
  format: ExportFormat;
  /** Sections to include */
  sections: {
    descriptiveStats: boolean;
    hypothesisTest: boolean;
    effectSizes: boolean;
    assumptions: boolean;
    visualizations: boolean;
    apaText: boolean;
  };
  /** Template to use (for PDF/DOCX) */
  template?: string;
}

/**
 * Export response
 */
export interface ExportAnalysisResponse {
  success: boolean;
  /** Download URL */
  downloadUrl: string;
  /** Filename */
  filename: string;
  /** Expiration timestamp */
  expiresAt: string;
  message?: string;
}
