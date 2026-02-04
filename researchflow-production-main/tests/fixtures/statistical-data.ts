/**
 * Test Fixtures for Statistical Analysis
 * Mock API responses and sample data for testing Stage 7 components
 */

import type {
  StatisticalTestConfig,
  StatisticalAnalysisResult,
  TestTypeInfo,
  DatasetMetadata,
  DescriptiveStats,
  HypothesisTestResult,
  AssumptionCheck,
  EffectSize,
} from '../../services/web/src/types/statistical-analysis';

// ============================================================================
// Mock Dataset Metadata
// ============================================================================

export const mockDatasetMetadata: DatasetMetadata = {
  id: 'dataset_test_001',
  rowCount: 150,
  columns: [
    {
      name: 'participant_id',
      type: 'categorical',
      count: 150,
      nullCount: 0,
      uniqueCount: 150,
      sampleValues: ['P001', 'P002', 'P003', 'P004', 'P005'],
      suitable: false,
      issues: ['Identifier column - not suitable for analysis'],
    },
    {
      name: 'age',
      type: 'continuous',
      count: 150,
      nullCount: 0,
      uniqueCount: 45,
      sampleValues: [25, 30, 35, 40, 45],
      suitable: true,
    },
    {
      name: 'gender',
      type: 'binary',
      count: 150,
      nullCount: 0,
      uniqueCount: 2,
      sampleValues: ['Male', 'Female'],
      suitable: true,
    },
    {
      name: 'treatment_group',
      type: 'binary',
      count: 150,
      nullCount: 0,
      uniqueCount: 2,
      sampleValues: ['Treatment', 'Control'],
      suitable: true,
    },
    {
      name: 'blood_pressure_baseline',
      type: 'continuous',
      count: 150,
      nullCount: 0,
      uniqueCount: 78,
      sampleValues: [120, 125, 130, 135, 140],
      suitable: true,
    },
    {
      name: 'blood_pressure_followup',
      type: 'continuous',
      count: 150,
      nullCount: 5,
      uniqueCount: 72,
      sampleValues: [115, 120, 125, 130, 135],
      suitable: true,
      issues: ['5 missing values'],
    },
    {
      name: 'education_level',
      type: 'categorical',
      count: 150,
      nullCount: 0,
      uniqueCount: 4,
      sampleValues: ['High School', 'Bachelor', 'Master', 'PhD'],
      suitable: true,
    },
    {
      name: 'symptom_severity',
      type: 'ordinal',
      count: 150,
      nullCount: 0,
      uniqueCount: 5,
      sampleValues: ['None', 'Mild', 'Moderate', 'Severe', 'Very Severe'],
      suitable: true,
    },
  ],
  qualityScore: 92,
  qualityIssues: [
    '5 missing values in blood_pressure_followup',
    'Consider handling missing data before analysis',
  ],
};

// ============================================================================
// Mock Test Type Info
// ============================================================================

export const mockTestTypeInfo: TestTypeInfo[] = [
  {
    type: 't-test-independent',
    name: 'Independent Samples t-test',
    description: 'Compares means between two independent groups',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
      { role: 'grouping', type: ['binary', 'categorical'], minCount: 1, maxCount: 1 },
    ],
    assumptions: [
      'Independence of observations',
      'Normality of distributions',
      'Homogeneity of variances',
    ],
    useCase: 'When comparing two independent groups on a continuous outcome',
    examples: [
      'Treatment vs control group on symptom scores',
      'Male vs female on blood pressure',
    ],
    effectSizes: ["Cohen's d", "Hedge's g"],
  },
  {
    type: 't-test-paired',
    name: 'Paired Samples t-test',
    description: 'Compares means between two related measurements',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 2, maxCount: 2 },
    ],
    assumptions: ['Normality of difference scores', 'Independence of pairs'],
    useCase: 'When comparing pre-post measurements or matched pairs',
    examples: ['Pre-test vs post-test scores', 'Before vs after treatment'],
    effectSizes: ["Cohen's d"],
  },
  {
    type: 'anova-one-way',
    name: 'One-Way ANOVA',
    description: 'Compares means across three or more independent groups',
    requiredVariables: [
      { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
      { role: 'grouping', type: ['categorical'], minCount: 1, maxCount: 1 },
    ],
    assumptions: [
      'Independence of observations',
      'Normality within groups',
      'Homogeneity of variances',
    ],
    useCase: 'When comparing multiple independent groups on continuous outcome',
    examples: ['Three teaching methods on exam scores', 'Drug A vs Drug B vs Placebo'],
    effectSizes: ['Eta squared', 'Omega squared'],
  },
];

// ============================================================================
// Mock Test Configurations
// ============================================================================

export const mockIndependentTTestConfig: StatisticalTestConfig = {
  testType: 't-test-independent',
  variables: [
    {
      name: 'blood_pressure_followup',
      type: 'continuous',
      role: 'dependent',
      label: 'Blood Pressure (Follow-up)',
    },
    {
      name: 'treatment_group',
      type: 'binary',
      role: 'grouping',
      label: 'Treatment Group',
    },
  ],
  confidenceLevel: 0.95,
  alpha: 0.05,
  multipleComparisonCorrection: 'none',
  options: {
    tails: 'two',
    equalVariance: true,
  },
};

export const mockPairedTTestConfig: StatisticalTestConfig = {
  testType: 't-test-paired',
  variables: [
    {
      name: 'blood_pressure_baseline',
      type: 'continuous',
      role: 'dependent',
      label: 'Blood Pressure (Baseline)',
    },
    {
      name: 'blood_pressure_followup',
      type: 'continuous',
      role: 'dependent',
      label: 'Blood Pressure (Follow-up)',
    },
  ],
  confidenceLevel: 0.95,
  alpha: 0.05,
  multipleComparisonCorrection: 'none',
  options: {
    tails: 'two',
  },
};

export const mockANOVAConfig: StatisticalTestConfig = {
  testType: 'anova-one-way',
  variables: [
    {
      name: 'blood_pressure_followup',
      type: 'continuous',
      role: 'dependent',
      label: 'Blood Pressure',
    },
    {
      name: 'education_level',
      type: 'categorical',
      role: 'grouping',
      label: 'Education Level',
    },
  ],
  confidenceLevel: 0.95,
  alpha: 0.05,
  multipleComparisonCorrection: 'bonferroni',
  options: {
    postHoc: 'tukey',
  },
};

// ============================================================================
// Mock Analysis Results
// ============================================================================

const mockDescriptiveStats: DescriptiveStats[] = [
  {
    variable: 'blood_pressure_followup (Treatment)',
    n: 75,
    mean: 128.4,
    sd: 12.3,
    se: 1.42,
    min: 105.0,
    max: 158.0,
    median: 127.0,
    iqr: 15.5,
    q1: 120.25,
    q3: 135.75,
    skewness: 0.15,
    kurtosis: -0.42,
    ci95: [125.6, 131.2],
  },
  {
    variable: 'blood_pressure_followup (Control)',
    n: 70,
    mean: 135.7,
    sd: 14.1,
    se: 1.68,
    min: 110.0,
    max: 170.0,
    median: 134.5,
    iqr: 18.0,
    q1: 126.75,
    q3: 144.75,
    skewness: 0.22,
    kurtosis: -0.35,
    ci95: [132.3, 139.1],
  },
];

const mockEffectSize: EffectSize = {
  name: "Cohen's d",
  value: 0.56,
  confidenceInterval: [0.17, 0.95],
  interpretation: 'medium',
  guidelines: "Cohen's conventions (small: 0.2, medium: 0.5, large: 0.8)",
};

const mockHypothesisTest: HypothesisTestResult = {
  statistic: -2.85,
  statisticName: 't',
  pValue: 0.005,
  degreesOfFreedom: 143,
  significant: true,
  confidenceInterval: [-12.4, -2.2],
  effectSize: mockEffectSize,
};

const mockAssumptionChecks: AssumptionCheck[] = [
  {
    name: 'Normality (Treatment Group)',
    description: 'Data should follow normal distribution',
    passed: true,
    statistic: 0.976,
    pValue: 0.234,
    interpretation: 'Data appears normally distributed (Shapiro-Wilk p > .05)',
    severity: 'none',
  },
  {
    name: 'Normality (Control Group)',
    description: 'Data should follow normal distribution',
    passed: true,
    statistic: 0.982,
    pValue: 0.412,
    interpretation: 'Data appears normally distributed (Shapiro-Wilk p > .05)',
    severity: 'none',
  },
  {
    name: 'Homogeneity of Variances',
    description: 'Groups should have equal variances',
    passed: true,
    statistic: 1.82,
    pValue: 0.180,
    interpretation: "Variances are approximately equal (Levene's test p > .05)",
    severity: 'none',
  },
  {
    name: 'Independence of Observations',
    description: 'Observations should be independent',
    passed: true,
    interpretation: 'Based on study design: Independent groups, single measurement per participant',
    severity: 'none',
  },
];

export const mockAnalysisResult: StatisticalAnalysisResult = {
  id: 'analysis_mock_001',
  researchId: 'research_mock_001',
  config: mockIndependentTTestConfig,
  descriptiveStats: mockDescriptiveStats,
  hypothesisTest: mockHypothesisTest,
  assumptions: mockAssumptionChecks,
  visualizations: [
    {
      type: 'boxplot',
      title: 'Blood Pressure by Treatment Group',
      data: {
        groups: ['Treatment', 'Control'],
        values: [[128.4], [135.7]],
      },
    },
    {
      type: 'qq-plot',
      title: 'Q-Q Plot: Blood Pressure (Treatment Group)',
      data: {
        theoretical: [120, 125, 130, 135, 140],
        observed: [121, 126, 128, 134, 139],
      },
    },
  ],
  apaFormatted: [
    {
      section: 'descriptive',
      text: 'The treatment group (M = 128.40, SD = 12.30) had lower blood pressure than the control group (M = 135.70, SD = 14.10).',
      includeInManuscript: true,
    },
    {
      section: 'inferential',
      text: "An independent-samples t-test was conducted to compare blood pressure levels between treatment and control groups. There was a significant difference in blood pressure for treatment (M = 128.40, SD = 12.30) and control groups (M = 135.70, SD = 14.10); t(143) = -2.85, p = .005, d = 0.56.",
      includeInManuscript: true,
    },
    {
      section: 'effect-size',
      text: "The effect size (Cohen's d = 0.56) indicates a medium practical effect.",
      includeInManuscript: true,
    },
  ],
  interpretation:
    'The treatment group had significantly lower blood pressure than the control group. The mean difference of 7.3 mmHg is both statistically significant and clinically meaningful. The medium effect size suggests this difference has practical importance.',
  recommendations: [
    'Report effect size in addition to p-value',
    'Consider clinical significance: 7.3 mmHg reduction may be clinically meaningful',
    'All assumptions were met - results are reliable',
    'Consider replication in larger sample',
  ],
  warnings: [],
  createdAt: '2024-01-15T10:30:00Z',
  duration: 1243,
};

// ============================================================================
// Mock Analysis with Assumption Violations
// ============================================================================

export const mockAnalysisWithViolations: StatisticalAnalysisResult = {
  ...mockAnalysisResult,
  id: 'analysis_mock_002',
  assumptions: [
    {
      name: 'Normality (Treatment Group)',
      description: 'Data should follow normal distribution',
      passed: false,
      statistic: 0.892,
      pValue: 0.021,
      interpretation: 'Significant deviation from normality detected (Shapiro-Wilk p < .05)',
      recommendation: 'Consider using Mann-Whitney U test (non-parametric alternative)',
      severity: 'moderate',
    },
    {
      name: 'Normality (Control Group)',
      description: 'Data should follow normal distribution',
      passed: true,
      statistic: 0.976,
      pValue: 0.234,
      interpretation: 'Data appears normally distributed',
      severity: 'none',
    },
    {
      name: 'Homogeneity of Variances',
      description: 'Groups should have equal variances',
      passed: false,
      statistic: 8.42,
      pValue: 0.004,
      interpretation: "Significant difference in variances detected (Levene's test p < .05)",
      recommendation: "Use Welch's t-test which does not assume equal variances",
      severity: 'moderate',
    },
  ],
  warnings: [
    'Normality assumption violated in treatment group',
    'Homogeneity of variances violated',
    'Consider using non-parametric alternative (Mann-Whitney U test)',
    "Alternatively, use Welch's t-test for unequal variances",
  ],
};

// ============================================================================
// Export all fixtures
// ============================================================================

export const fixtures = {
  datasetMetadata: mockDatasetMetadata,
  testTypes: mockTestTypeInfo,
  configs: {
    independentTTest: mockIndependentTTestConfig,
    pairedTTest: mockPairedTTestConfig,
    anova: mockANOVAConfig,
  },
  results: {
    standard: mockAnalysisResult,
    withViolations: mockAnalysisWithViolations,
  },
};

export default fixtures;
