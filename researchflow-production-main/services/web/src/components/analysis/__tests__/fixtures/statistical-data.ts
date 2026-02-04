/**
 * Test Data Fixtures for Statistical Analysis Components
 *
 * Mock data for testing statistical analysis UI components.
 */

import {
  DatasetMetadata,
  StatisticalAnalysisResult,
  StatisticalTestConfig,
  Visualization
} from '@/types/statistical-analysis';

// Mock Dataset Metadata
export const mockDatasetMetadata: DatasetMetadata = {
  id: 'test-clinical-trial',
  rowCount: 500,
  qualityScore: 85,
  qualityIssues: [
    'Some missing values in baseline_score column',
    '2 potential outliers detected in age variable'
  ],
  columns: [
    {
      name: 'patient_id',
      type: 'categorical',
      count: 500,
      nullCount: 0,
      uniqueCount: 500,
      sampleValues: ['P001', 'P002', 'P003', 'P004', 'P005'],
      suitable: false,
      issues: ['Identifier column - not suitable for analysis']
    },
    {
      name: 'age',
      type: 'continuous',
      count: 500,
      nullCount: 0,
      uniqueCount: 45,
      sampleValues: [25, 34, 45, 67, 52],
      suitable: true
    },
    {
      name: 'sex',
      type: 'binary',
      count: 500,
      nullCount: 0,
      uniqueCount: 2,
      sampleValues: ['Male', 'Female'],
      suitable: true
    },
    {
      name: 'treatment_group',
      type: 'binary',
      count: 500,
      nullCount: 0,
      uniqueCount: 2,
      sampleValues: ['Treatment', 'Control'],
      suitable: true
    },
    {
      name: 'baseline_score',
      type: 'continuous',
      count: 485,
      nullCount: 15,
      uniqueCount: 120,
      sampleValues: [12.5, 18.2, 24.1, 31.6, 9.8],
      suitable: true
    },
    {
      name: 'outcome_score',
      type: 'continuous',
      count: 500,
      nullCount: 0,
      uniqueCount: 156,
      sampleValues: [15.2, 22.1, 28.4, 35.2, 11.3],
      suitable: true
    },
    {
      name: 'response',
      type: 'binary',
      count: 500,
      nullCount: 0,
      uniqueCount: 2,
      sampleValues: ['Yes', 'No'],
      suitable: true
    }
  ]
};

// Mock Analysis Configuration
export const mockAnalysisConfig: StatisticalTestConfig = {
  testType: 't-test-independent',
  variables: [
    {
      name: 'outcome_score',
      type: 'continuous',
      role: 'dependent',
      label: 'Outcome Score',
      required: true
    },
    {
      name: 'treatment_group',
      type: 'binary',
      role: 'grouping',
      label: 'Treatment Group',
      required: true
    }
  ],
  confidenceLevel: 0.95,
  alpha: 0.05,
  multipleComparisonCorrection: 'none',
  options: {
    tails: 'two',
    equalVariance: true,
    bootstrap: false
  }
};

// Mock Visualizations
export const mockVisualizations: Visualization[] = [
  {
    type: 'qq-plot',
    title: 'Q-Q Plot for Normality Check',
    data: {
      observed: [
        -2.1, -1.8, -1.5, -1.2, -0.9, -0.6, -0.3, 0.0, 0.3, 0.6, 0.9, 1.2, 1.5, 1.8, 2.1
      ],
      theoretical: [
        -2.0, -1.7, -1.4, -1.1, -0.8, -0.5, -0.2, 0.1, 0.4, 0.7, 1.0, 1.3, 1.6, 1.9, 2.2
      ],
      confidence_bands: [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
    },
    config: {
      showConfidenceBands: true,
      showReferenceLine: true
    }
  },
  {
    type: 'histogram',
    title: 'Distribution of Outcome Scores',
    data: {
      bins: [5, 10, 15, 20, 25, 30, 35, 40, 45],
      counts: [12, 28, 45, 67, 89, 98, 76, 43, 21],
      density: [0.024, 0.056, 0.09, 0.134, 0.178, 0.196, 0.152, 0.086, 0.042],
      normal_curve: [0.02, 0.045, 0.085, 0.125, 0.165, 0.18, 0.15, 0.09, 0.04]
    }
  },
  {
    type: 'boxplot',
    title: 'Outcome Scores by Treatment Group',
    data: {
      groups: [
        {
          name: 'Control',
          min: 8.2,
          q1: 15.6,
          median: 22.1,
          q3: 28.9,
          max: 36.4,
          outliers: [5.1, 41.2]
        },
        {
          name: 'Treatment',
          min: 12.1,
          q1: 19.8,
          median: 26.5,
          q3: 33.2,
          max: 41.8,
          outliers: [7.2]
        }
      ]
    }
  },
  {
    type: 'scatter',
    title: 'Baseline vs Outcome Scores',
    data: {
      x: [12.5, 18.2, 24.1, 31.6, 9.8, 15.2, 22.1, 28.4, 35.2, 11.3],
      y: [15.2, 22.1, 28.4, 35.2, 11.3, 18.5, 25.6, 31.8, 38.9, 14.2],
      groups: ['Treatment', 'Control', 'Treatment', 'Control', 'Treatment', 'Control', 'Treatment', 'Control', 'Treatment', 'Control'],
      xLabel: 'Baseline Score',
      yLabel: 'Outcome Score',
      regression_line: [
        { x: 8, y: 12.1 },
        { x: 40, y: 42.3 }
      ]
    }
  }
];

// Mock Analysis Results
export const mockAnalysisResults: StatisticalAnalysisResult = {
  id: 'analysis-12345',
  researchId: 'research-67890',
  config: mockAnalysisConfig,
  descriptiveStats: [
    {
      variable: 'outcome_score_control',
      n: 250,
      mean: 22.45,
      sd: 8.12,
      se: 0.51,
      min: 8.2,
      max: 36.4,
      median: 22.1,
      iqr: 13.3,
      q1: 15.6,
      q3: 28.9,
      skewness: 0.12,
      kurtosis: -0.08,
      ci95: [21.45, 23.45]
    },
    {
      variable: 'outcome_score_treatment',
      n: 250,
      mean: 26.82,
      sd: 7.94,
      se: 0.50,
      min: 12.1,
      max: 41.8,
      median: 26.5,
      iqr: 13.4,
      q1: 19.8,
      q3: 33.2,
      skewness: 0.08,
      kurtosis: -0.12,
      ci95: [25.84, 27.80]
    }
  ],
  hypothesisTest: {
    statistic: 6.34,
    statisticName: 't',
    pValue: 0.0001,
    degreesOfFreedom: 498,
    significant: true,
    confidenceInterval: [2.89, 5.85],
    effectSize: {
      name: "Cohen's d",
      value: 0.57,
      confidenceInterval: [0.39, 0.75],
      interpretation: 'medium',
      guidelines: "Cohen's conventions (1988)"
    }
  },
  assumptions: [
    {
      name: 'Normality',
      description: 'Data should be approximately normally distributed',
      passed: true,
      statistic: 0.98,
      pValue: 0.245,
      interpretation: 'The Shapiro-Wilk test suggests data is approximately normal (W = 0.98, p = 0.245)',
      severity: 'none'
    },
    {
      name: 'Equal Variances',
      description: 'Groups should have similar variances',
      passed: true,
      statistic: 1.05,
      pValue: 0.689,
      interpretation: 'Levene\'s test indicates equal variances assumption is met (F = 1.05, p = 0.689)',
      severity: 'none'
    },
    {
      name: 'Independence',
      description: 'Observations should be independent',
      passed: true,
      interpretation: 'Random sampling and study design support independence assumption',
      severity: 'none'
    }
  ],
  visualizations: mockVisualizations,
  apaFormatted: [
    {
      section: 'descriptive',
      text: 'Descriptive statistics showed that participants in the treatment group (M = 26.82, SD = 7.94) had higher outcome scores compared to the control group (M = 22.45, SD = 8.12).',
      includeInManuscript: true
    },
    {
      section: 'inferential',
      text: 'An independent samples t-test revealed a statistically significant difference between treatment and control groups, t(498) = 6.34, p < .001, 95% CI [2.89, 5.85], d = 0.57.',
      includeInManuscript: true
    },
    {
      section: 'effect-size',
      text: 'The effect size was medium according to Cohen\'s conventions (d = 0.57, 95% CI [0.39, 0.75]).',
      includeInManuscript: true
    }
  ],
  interpretation: 'The analysis reveals a statistically significant and practically meaningful difference between treatment and control groups. Participants receiving the treatment showed higher outcome scores with a medium effect size (Cohen\'s d = 0.57). All statistical assumptions were met, supporting the validity of these findings.',
  recommendations: [
    'The significant treatment effect with medium effect size suggests clinical relevance',
    'Consider conducting a power analysis for future studies to determine optimal sample sizes',
    'Examine potential moderators that might influence treatment effectiveness',
    'Replicate findings in an independent sample to confirm robustness'
  ],
  warnings: [
    'Some missing values were excluded from analysis (n=15)',
    'Two potential outliers were identified but retained in analysis'
  ],
  createdAt: '2024-01-15T10:30:00Z',
  duration: 2340
};

// Mock Export Configurations
export const mockExportConfigurations = {
  fullReport: {
    format: 'pdf' as const,
    sections: {
      descriptiveStats: true,
      hypothesisTest: true,
      effectSizes: true,
      assumptions: true,
      visualizations: true,
      apaText: true
    },
    template: 'default'
  },
  quickSummary: {
    format: 'docx' as const,
    sections: {
      descriptiveStats: true,
      hypothesisTest: true,
      effectSizes: true,
      assumptions: false,
      visualizations: false,
      apaText: true
    },
    template: 'minimal'
  },
  dataOnly: {
    format: 'csv' as const,
    sections: {
      descriptiveStats: true,
      hypothesisTest: true,
      effectSizes: false,
      assumptions: false,
      visualizations: false,
      apaText: false
    }
  }
};

// Mock Validation Results
export const mockValidationResults = {
  valid: {
    valid: true,
    errors: [],
    warnings: [
      {
        field: 'baseline_score',
        message: 'Variable has 3% missing values - consider imputation',
        severity: 'warning' as const,
        suggestion: 'Use multiple imputation or exclude cases with missing values'
      }
    ]
  },
  invalid: {
    valid: false,
    errors: [
      {
        field: 'variables',
        message: 'Dependent variable must be continuous for t-test',
        severity: 'error' as const,
        suggestion: 'Select a continuous outcome variable or choose a different test'
      }
    ],
    warnings: []
  }
};

export default {
  mockDatasetMetadata,
  mockAnalysisConfig,
  mockAnalysisResults,
  mockVisualizations,
  mockExportConfigurations,
  mockValidationResults
};