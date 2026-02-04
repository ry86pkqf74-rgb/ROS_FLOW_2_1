/**
 * Statistical Analysis Utility Functions
 * Helper functions for test selection, validation, and result formatting
 */

import type {
  StatisticalTestType,
  VariableType,
  VariableRole,
  AnalysisVariable,
  StatisticalTestConfig,
  ValidationResult,
  ValidationError,
  EffectSize,
  TestTypeInfo,
} from '../types/statistical-analysis';

// ============================================================================
// Test Selection Logic
// ============================================================================

/**
 * Get appropriate statistical test based on study design
 */
export function suggestStatisticalTest(params: {
  dependentVariableType: VariableType;
  independentVariableType: VariableType;
  numberOfGroups: number;
  pairedData: boolean;
  normalDistribution: boolean;
}): StatisticalTestType[] {
  const {
    dependentVariableType,
    independentVariableType,
    numberOfGroups,
    pairedData,
    normalDistribution,
  } = params;

  const suggestions: StatisticalTestType[] = [];

  // Continuous dependent variable
  if (dependentVariableType === 'continuous') {
    if (independentVariableType === 'binary' || independentVariableType === 'categorical') {
      if (numberOfGroups === 2) {
        if (pairedData) {
          suggestions.push(normalDistribution ? 't-test-paired' : 'wilcoxon');
        } else {
          suggestions.push(normalDistribution ? 't-test-independent' : 'mann-whitney');
        }
      } else if (numberOfGroups > 2) {
        if (pairedData) {
          suggestions.push(normalDistribution ? 'anova-repeated-measures' : 'friedman');
        } else {
          suggestions.push(normalDistribution ? 'anova-one-way' : 'kruskal-wallis');
        }
      }
    } else if (independentVariableType === 'continuous') {
      suggestions.push('correlation-pearson', 'regression-linear');
      if (!normalDistribution) {
        suggestions.push('correlation-spearman');
      }
    }
  }

  // Categorical dependent variable
  if (dependentVariableType === 'categorical' || dependentVariableType === 'binary') {
    if (independentVariableType === 'categorical' || independentVariableType === 'binary') {
      suggestions.push('chi-square', 'fisher-exact');
    } else if (independentVariableType === 'continuous') {
      suggestions.push('regression-logistic');
    }
  }

  return suggestions;
}

/**
 * Get test type information
 */
export function getTestTypeInfo(testType: StatisticalTestType): TestTypeInfo {
  const testInfo: Record<StatisticalTestType, TestTypeInfo> = {
    't-test-independent': {
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
      effectSizes: ["Cohen's d", 'Hedge\'s g'],
    },
    't-test-paired': {
      type: 't-test-paired',
      name: 'Paired Samples t-test',
      description: 'Compares means between two related/paired measurements',
      requiredVariables: [
        { role: 'dependent', type: ['continuous'], minCount: 2, maxCount: 2 },
      ],
      assumptions: ['Normality of difference scores', 'Independence of pairs'],
      useCase: 'When comparing pre-post measurements or matched pairs',
      examples: ['Pre-test vs post-test scores', 'Left vs right measurements'],
      effectSizes: ["Cohen's d"],
    },
    't-test-one-sample': {
      type: 't-test-one-sample',
      name: 'One-Sample t-test',
      description: 'Compares sample mean to a known population value',
      requiredVariables: [
        { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
      ],
      assumptions: ['Normality of distribution', 'Independence of observations'],
      useCase: 'When comparing sample mean to a theoretical or population mean',
      examples: ['Test if average IQ differs from 100', 'Test if coin is fair'],
      effectSizes: ["Cohen's d"],
    },
    'anova-one-way': {
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
      examples: ['Drug A vs Drug B vs Placebo', 'Three different teaching methods'],
      effectSizes: ['Eta squared', 'Omega squared'],
    },
    'anova-repeated-measures': {
      type: 'anova-repeated-measures',
      name: 'Repeated Measures ANOVA',
      description: 'Compares means across three or more related measurements',
      requiredVariables: [
        { role: 'dependent', type: ['continuous'], minCount: 3 },
      ],
      assumptions: [
        'Normality of distributions',
        'Sphericity',
        'Independence of observations',
      ],
      useCase: 'When comparing multiple time points or conditions within subjects',
      examples: ['Measurements at baseline, 3 months, 6 months', 'Performance across 4 tasks'],
      effectSizes: ['Partial eta squared'],
    },
    'chi-square': {
      type: 'chi-square',
      name: 'Chi-Square Test of Independence',
      description: 'Tests association between two categorical variables',
      requiredVariables: [
        { role: 'dependent', type: ['categorical', 'binary'], minCount: 1, maxCount: 1 },
        { role: 'independent', type: ['categorical', 'binary'], minCount: 1, maxCount: 1 },
      ],
      assumptions: [
        'Independence of observations',
        'Expected cell frequencies ≥ 5',
        'Mutually exclusive categories',
      ],
      useCase: 'When examining relationship between categorical variables',
      examples: ['Gender vs treatment preference', 'Smoking status vs disease outcome'],
      effectSizes: ["Cramér's V", 'Phi coefficient'],
    },
    'fisher-exact': {
      type: 'fisher-exact',
      name: "Fisher's Exact Test",
      description: 'Tests association in 2x2 contingency tables',
      requiredVariables: [
        { role: 'dependent', type: ['binary'], minCount: 1, maxCount: 1 },
        { role: 'independent', type: ['binary'], minCount: 1, maxCount: 1 },
      ],
      assumptions: ['Independence of observations', 'Mutually exclusive categories'],
      useCase: 'When sample size is small or expected frequencies < 5',
      examples: ['Treatment response (yes/no) vs group', 'Presence/absence vs exposure'],
      effectSizes: ['Odds ratio'],
    },
    'mann-whitney': {
      type: 'mann-whitney',
      name: 'Mann-Whitney U Test',
      description: 'Non-parametric test comparing two independent groups',
      requiredVariables: [
        { role: 'dependent', type: ['continuous', 'ordinal'], minCount: 1, maxCount: 1 },
        { role: 'grouping', type: ['binary', 'categorical'], minCount: 1, maxCount: 1 },
      ],
      assumptions: ['Independence of observations', 'Ordinal or continuous data'],
      useCase: 'Alternative to t-test when normality assumption violated',
      examples: ['Non-normal outcomes between groups', 'Ordinal Likert scale comparisons'],
      effectSizes: ['r (rank-biserial correlation)'],
    },
    'wilcoxon': {
      type: 'wilcoxon',
      name: 'Wilcoxon Signed-Rank Test',
      description: 'Non-parametric test for paired samples',
      requiredVariables: [
        { role: 'dependent', type: ['continuous', 'ordinal'], minCount: 2, maxCount: 2 },
      ],
      assumptions: ['Symmetric distribution of differences', 'Ordinal or continuous data'],
      useCase: 'Alternative to paired t-test when normality violated',
      examples: ['Pre-post measurements with non-normal differences', 'Matched pairs comparison'],
      effectSizes: ['r (effect size correlation)'],
    },
    'kruskal-wallis': {
      type: 'kruskal-wallis',
      name: 'Kruskal-Wallis Test',
      description: 'Non-parametric test for multiple independent groups',
      requiredVariables: [
        { role: 'dependent', type: ['continuous', 'ordinal'], minCount: 1, maxCount: 1 },
        { role: 'grouping', type: ['categorical'], minCount: 1, maxCount: 1 },
      ],
      assumptions: ['Independence of observations', 'Ordinal or continuous data'],
      useCase: 'Alternative to one-way ANOVA when normality violated',
      examples: ['Comparing 3+ groups on non-normal outcome', 'Ordinal responses across groups'],
      effectSizes: ['Epsilon squared'],
    },
    'friedman': {
      type: 'friedman',
      name: 'Friedman Test',
      description: 'Non-parametric test for repeated measures',
      requiredVariables: [
        { role: 'dependent', type: ['continuous', 'ordinal'], minCount: 3 },
      ],
      assumptions: ['Ordinal or continuous data', 'Related measurements'],
      useCase: 'Alternative to repeated measures ANOVA when normality violated',
      examples: ['Multiple time points with non-normal data', 'Ranked preferences across conditions'],
      effectSizes: ['Kendall\'s W'],
    },
    'correlation-pearson': {
      type: 'correlation-pearson',
      name: 'Pearson Correlation',
      description: 'Tests linear relationship between two continuous variables',
      requiredVariables: [
        { role: 'dependent', type: ['continuous'], minCount: 2, maxCount: 2 },
      ],
      assumptions: ['Linearity', 'Bivariate normality', 'Homoscedasticity'],
      useCase: 'When examining linear association between continuous variables',
      examples: ['Height vs weight', 'Age vs reaction time'],
      effectSizes: ['r (correlation coefficient)'],
    },
    'correlation-spearman': {
      type: 'correlation-spearman',
      name: 'Spearman Correlation',
      description: 'Tests monotonic relationship between variables',
      requiredVariables: [
        { role: 'dependent', type: ['continuous', 'ordinal'], minCount: 2, maxCount: 2 },
      ],
      assumptions: ['Monotonic relationship', 'Ordinal or continuous data'],
      useCase: 'Alternative to Pearson when non-linear or non-normal',
      examples: ['Ordinal variables association', 'Non-linear relationships'],
      effectSizes: ['rho (Spearman coefficient)'],
    },
    'regression-linear': {
      type: 'regression-linear',
      name: 'Linear Regression',
      description: 'Models relationship between continuous outcome and predictor(s)',
      requiredVariables: [
        { role: 'dependent', type: ['continuous'], minCount: 1, maxCount: 1 },
        { role: 'independent', type: ['continuous', 'categorical'], minCount: 1 },
      ],
      assumptions: [
        'Linearity',
        'Independence of errors',
        'Homoscedasticity',
        'Normality of residuals',
        'No multicollinearity',
      ],
      useCase: 'When predicting continuous outcome from predictor(s)',
      examples: ['Predicting weight from height', 'Multiple predictors of performance'],
      effectSizes: ['R²', 'Adjusted R²'],
    },
    'regression-logistic': {
      type: 'regression-logistic',
      name: 'Logistic Regression',
      description: 'Models relationship between binary outcome and predictor(s)',
      requiredVariables: [
        { role: 'dependent', type: ['binary'], minCount: 1, maxCount: 1 },
        { role: 'independent', type: ['continuous', 'categorical'], minCount: 1 },
      ],
      assumptions: [
        'Independence of observations',
        'Linear relationship between continuous predictors and log-odds',
        'No multicollinearity',
      ],
      useCase: 'When predicting binary outcome from predictor(s)',
      examples: ['Disease presence/absence prediction', 'Treatment success/failure'],
      effectSizes: ['Odds ratios', "Nagelkerke R²"],
    },
  };

  return testInfo[testType];
}

// ============================================================================
// Validation Functions
// ============================================================================

/**
 * Validate statistical analysis configuration
 */
export function validateAnalysisConfig(
  config: StatisticalTestConfig
): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  // Validate test type
  if (!config.testType) {
    errors.push({
      field: 'testType',
      message: 'Test type is required',
      severity: 'error',
    });
  }

  // Validate confidence level
  if (config.confidenceLevel < 0 || config.confidenceLevel > 1) {
    errors.push({
      field: 'confidenceLevel',
      message: 'Confidence level must be between 0 and 1',
      severity: 'error',
      suggestion: 'Use 0.95 for 95% confidence',
    });
  }

  // Validate alpha
  if (config.alpha < 0 || config.alpha > 1) {
    errors.push({
      field: 'alpha',
      message: 'Alpha level must be between 0 and 1',
      severity: 'error',
      suggestion: 'Typically 0.05 or 0.01',
    });
  }

  // Warn about liberal alpha
  if (config.alpha > 0.10) {
    warnings.push({
      field: 'alpha',
      message: 'Alpha level is unusually high',
      severity: 'warning',
      suggestion: 'Consider using α = 0.05 for standard significance testing',
    });
  }

  // Validate variables
  if (!config.variables || config.variables.length === 0) {
    errors.push({
      field: 'variables',
      message: 'At least one variable is required',
      severity: 'error',
    });
  } else {
    const testInfo = getTestTypeInfo(config.testType);
    
    // Check required variables
    for (const reqVar of testInfo.requiredVariables) {
      const matchingVars = config.variables.filter(
        (v) => v.role === reqVar.role && reqVar.type.includes(v.type)
      );

      if (matchingVars.length < reqVar.minCount) {
        errors.push({
          field: 'variables',
          message: `Test requires at least ${reqVar.minCount} ${reqVar.role} variable(s) of type ${reqVar.type.join(' or ')}`,
          severity: 'error',
        });
      }

      if (reqVar.maxCount && matchingVars.length > reqVar.maxCount) {
        errors.push({
          field: 'variables',
          message: `Test allows maximum ${reqVar.maxCount} ${reqVar.role} variable(s)`,
          severity: 'error',
        });
      }
    }

    // Check for duplicate variables
    const varNames = config.variables.map((v) => v.name);
    const duplicates = varNames.filter((v, i) => varNames.indexOf(v) !== i);
    if (duplicates.length > 0) {
      errors.push({
        field: 'variables',
        message: `Duplicate variables: ${duplicates.join(', ')}`,
        severity: 'error',
      });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ============================================================================
// Result Formatting Functions
// ============================================================================

/**
 * Format p-value for display
 */
export function formatPValue(pValue: number, decimals: number = 3): string {
  if (pValue < 0.001) {
    return 'p < .001';
  }
  return `p = ${pValue.toFixed(decimals).replace(/^0\./, '.')}`;
}

/**
 * Format confidence interval
 */
export function formatConfidenceInterval(
  ci: [number, number],
  decimals: number = 2
): string {
  return `[${ci[0].toFixed(decimals)}, ${ci[1].toFixed(decimals)}]`;
}

/**
 * Interpret effect size
 */
export function interpretEffectSize(effectSize: EffectSize): string {
  const { interpretation, value, name } = effectSize;
  
  let description = '';
  switch (interpretation) {
    case 'negligible':
      description = 'negligible practical significance';
      break;
    case 'small':
      description = 'small practical effect';
      break;
    case 'medium':
      description = 'moderate practical effect';
      break;
    case 'large':
      description = 'large practical effect';
      break;
  }

  return `${name} = ${value.toFixed(2)} indicates ${description}`;
}

/**
 * Format degrees of freedom
 */
export function formatDegreesOfFreedom(df: number | [number, number]): string {
  if (Array.isArray(df)) {
    return `df = ${df[0]}, ${df[1]}`;
  }
  return `df = ${df}`;
}

/**
 * Create APA-style test result string
 */
export function formatAPATestResult(params: {
  statisticName: string;
  statistic: number;
  df: number | [number, number];
  pValue: number;
  effectSize?: EffectSize;
}): string {
  const { statisticName, statistic, df, pValue, effectSize } = params;

  let result = `${statisticName}`;
  
  // Add degrees of freedom
  if (Array.isArray(df)) {
    result += `(${df[0]}, ${df[1]})`;
  } else {
    result += `(${df})`;
  }

  // Add statistic value
  result += ` = ${statistic.toFixed(2)}`;

  // Add p-value
  result += `, ${formatPValue(pValue)}`;

  // Add effect size if provided
  if (effectSize) {
    result += `, ${effectSize.name} = ${effectSize.value.toFixed(2)}`;
  }

  return result;
}

export default {
  suggestStatisticalTest,
  getTestTypeInfo,
  validateAnalysisConfig,
  formatPValue,
  formatConfidenceInterval,
  interpretEffectSize,
  formatDegreesOfFreedom,
  formatAPATestResult,
};
