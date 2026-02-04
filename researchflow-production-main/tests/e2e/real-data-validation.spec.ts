/**
 * Real Data E2E Validation Tests
 *
 * End-to-end tests using actual clinical and research datasets to validate
 * the complete statistical analysis workflow under realistic conditions.
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

// Real dataset configurations for testing
const REAL_DATASETS = {
  clinical_trial: {
    name: 'COVID-19 Treatment Efficacy Study',
    file: 'tests/fixtures/real-data/covid_treatment_study.csv',
    rows: 1247,
    expectedTests: ['t-test-independent', 'chi-square', 'regression-logistic'],
    primaryOutcome: 'recovery_time',
    groupingVar: 'treatment_group',
    description: 'Multi-center randomized controlled trial data'
  },
  longitudinal_study: {
    name: 'Pediatric Growth Longitudinal Study',
    file: 'tests/fixtures/real-data/pediatric_growth_5yr.csv',
    rows: 2891,
    expectedTests: ['anova-repeated-measures', 'regression-linear', 'correlation-pearson'],
    primaryOutcome: 'height_z_score',
    groupingVar: 'intervention_group',
    description: '5-year longitudinal growth study'
  },
  observational_cohort: {
    name: 'Cardiovascular Risk Factors Study',
    file: 'tests/fixtures/real-data/cardio_risk_cohort.csv',
    rows: 15670,
    expectedTests: ['regression-logistic', 'survival-analysis', 'chi-square'],
    primaryOutcome: 'cardiovascular_event',
    groupingVar: 'risk_category',
    description: 'Large observational cohort study'
  },
  biomarker_study: {
    name: 'Biomarker Validation Study',
    file: 'tests/fixtures/real-data/biomarker_validation.csv',
    rows: 892,
    expectedTests: ['correlation-spearman', 'roc-analysis', 't-test-paired'],
    primaryOutcome: 'biomarker_level',
    groupingVar: 'disease_status',
    description: 'Diagnostic biomarker validation'
  }
};

test.describe('Real Data Validation - Clinical Datasets', () => {
  test.beforeEach(async ({ page }) => {
    // Set longer timeout for real data processing
    test.setTimeout(120000); // 2 minutes
    
    await page.goto('/statistical-analysis');
    await expect(page.locator('h1')).toContainText('Statistical Analysis');
  });

  test('COVID-19 Treatment Study - Complete Analysis Workflow', async ({ page }) => {
    const dataset = REAL_DATASETS.clinical_trial;
    
    await test.step('Upload real clinical trial dataset', async () => {
      // Upload the actual dataset
      await page.click('button:has-text("Upload Dataset")');
      
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(dataset.file);
      
      // Wait for upload and processing
      await expect(page.locator('[data-testid="upload-progress"]')).toBeVisible();
      await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 30000 });
      
      // Verify dataset information
      await expect(page.locator('[data-testid="dataset-name"]')).toContainText(dataset.name);
      await expect(page.locator('[data-testid="dataset-rows"]')).toContainText(`${dataset.rows} rows`);
    });

    await test.step('Validate data quality assessment', async () => {
      // Check data quality metrics
      const qualityScore = await page.locator('[data-testid="quality-score-value"]').textContent();
      expect(parseInt(qualityScore || '0')).toBeGreaterThan(80);
      
      // Review column analysis
      await expect(page.locator('[data-testid="column-summary"]')).toBeVisible();
      
      // Check for data quality issues
      const issues = await page.locator('[data-testid="quality-issues"]').count();
      if (issues > 0) {
        console.log('Data quality issues detected - expected for real data');
      }
    });

    await test.step('Configure primary efficacy analysis', async () => {
      await page.click('text=Test Selection');
      
      // Select appropriate test for primary outcome
      await page.click(`text=${dataset.expectedTests[0].replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}`);
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', dataset.primaryOutcome);
      await page.selectOption('[data-testid="grouping-variable"]', dataset.groupingVar);
      
      // Configure analysis options
      await page.click('text=Options');
      await page.selectOption('[data-testid="confidence-level"]', '0.95');
      await page.selectOption('[data-testid="alpha-level"]', '0.05');
      await page.selectOption('[data-testid="multiple-comparison"]', 'fdr');
    });

    await test.step('Execute analysis with real data', async () => {
      await page.click('text=Review');
      
      // Verify configuration summary
      await expect(page.locator('[data-testid="config-summary"]')).toBeVisible();
      
      const startTime = Date.now();
      await page.click('button:has-text("Run Statistical Analysis")');
      
      // Monitor analysis progress
      await expect(page.locator('[data-testid="analysis-progress"]')).toBeVisible();
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 60000 });
      
      const analysisTime = Date.now() - startTime;
      console.log(`Analysis completed in ${analysisTime}ms`);
      expect(analysisTime).toBeLessThan(45000); // Should complete within 45 seconds
    });

    await test.step('Validate results with real data characteristics', async () => {
      // Check that results make clinical sense
      await expect(page.locator('[data-testid="results-summary"]')).toBeVisible();
      
      // Verify statistical significance interpretation
      const pValue = await page.locator('[data-testid="p-value"]').textContent();
      const isSignificant = await page.locator('[data-testid="significance-badge"]').textContent();
      
      // Results should be clinically interpretable
      await expect(page.locator('[data-testid="clinical-interpretation"]')).toBeVisible();
      
      // Check descriptive statistics are reasonable
      await page.click('text=Descriptive');
      const meanValue = await page.locator('[data-testid="mean-value"]').first().textContent();
      expect(parseFloat(meanValue || '0')).toBeGreaterThan(0);
    });

    await test.step('Verify diagnostic plots with real data', async () => {
      await page.click('text=Visualizations');
      
      // Q-Q plot should show real data distribution
      await expect(page.locator('[data-testid="qq-plot"]')).toBeVisible();
      
      // Histogram should show actual data distribution
      await expect(page.locator('[data-testid="histogram"]')).toBeVisible();
      
      // Box plots should show real group comparisons
      await expect(page.locator('[data-testid="boxplot"]')).toBeVisible();
    });

    await test.step('Generate publication-ready report', async () => {
      await page.click('text=Export');
      await page.click('button:has-text("Custom Export")');
      
      // Configure for publication
      await page.click('[data-testid="format-pdf"]');
      await page.selectOption('[data-testid="template-select"]', 'nature');
      
      // Include all clinical sections
      await page.check('[data-testid="include-clinical-significance"]');
      await page.check('[data-testid="include-effect-sizes"]');
      
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("Export PDF Report")');
      const download = await downloadPromise;
      
      expect(download.suggestedFilename()).toMatch(/covid.*treatment.*\.pdf/i);
      
      // Verify file size is reasonable (real data should produce substantial report)
      const downloadPath = await download.path();
      if (downloadPath) {
        const stats = fs.statSync(downloadPath);
        expect(stats.size).toBeGreaterThan(100000); // At least 100KB for real data report
      }
    });
  });

  test('Longitudinal Study - Repeated Measures Analysis', async ({ page }) => {
    const dataset = REAL_DATASETS.longitudinal_study;
    
    await test.step('Process longitudinal dataset', async () => {
      await page.click('button:has-text("Upload Dataset")');
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(dataset.file);
      
      await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 45000 });
      await expect(page.locator('[data-testid="dataset-rows"]')).toContainText(`${dataset.rows} rows`);
    });

    await test.step('Configure repeated measures ANOVA', async () => {
      await page.click('text=Test Selection');
      await page.click('text=Repeated Measures ANOVA');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', dataset.primaryOutcome);
      await page.selectOption('[data-testid="within-subject-factor"]', 'time_point');
      await page.selectOption('[data-testid="between-subject-factor"]', dataset.groupingVar);
    });

    await test.step('Execute longitudinal analysis', async () => {
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 90000 });
    });

    await test.step('Validate longitudinal results', async () => {
      // Check for time effects
      await expect(page.locator('[data-testid="time-effect"]')).toBeVisible();
      
      // Check for group by time interaction
      await expect(page.locator('[data-testid="interaction-effect"]')).toBeVisible();
      
      // Verify sphericity assumption testing
      await page.click('text=Assumptions');
      await expect(page.locator('[data-testid="sphericity-test"]')).toBeVisible();
    });
  });

  test('Large Observational Cohort - Performance Validation', async ({ page }) => {
    const dataset = REAL_DATASETS.observational_cohort;
    
    await test.step('Handle large dataset upload', async () => {
      await page.click('button:has-text("Upload Dataset")');
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(dataset.file);
      
      // Should handle large file efficiently
      await expect(page.locator('[data-testid="upload-progress"]')).toBeVisible();
      await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 120000 });
      
      // Verify large dataset handling
      await expect(page.locator('[data-testid="dataset-rows"]')).toContainText('15,670 rows');
    });

    await test.step('Configure logistic regression for large data', async () => {
      await page.click('text=Test Selection');
      await page.click('text=Logistic Regression');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', dataset.primaryOutcome);
      
      // Add multiple predictors
      await page.selectOption('[data-testid="independent-variable-1"]', 'age');
      await page.selectOption('[data-testid="independent-variable-2"]', 'bmi');
      await page.selectOption('[data-testid="independent-variable-3"]', 'smoking_status');
    });

    await test.step('Performance test with large dataset', async () => {
      await page.click('text=Options');
      await page.check('[data-testid="bootstrap-confidence-intervals"]');
      await page.fill('[data-testid="bootstrap-iterations"]', '1000');
      
      await page.click('text=Review');
      
      const startTime = Date.now();
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 180000 }); // 3 minutes for large data
      
      const analysisTime = Date.now() - startTime;
      console.log(`Large dataset analysis completed in ${analysisTime}ms`);
      expect(analysisTime).toBeLessThan(120000); // Should complete within 2 minutes
    });

    await test.step('Validate large dataset results', async () => {
      // Should handle visualization of large datasets efficiently
      await page.click('text=Visualizations');
      await expect(page.locator('[data-testid="scatter-plot"]')).toBeVisible();
      
      // Check that results tables are paginated/virtualized
      await page.click('text=Descriptive');
      await expect(page.locator('[data-testid="results-pagination"]')).toBeVisible();
    });
  });

  test('Biomarker Study - Advanced Statistics Validation', async ({ page }) => {
    const dataset = REAL_DATASETS.biomarker_study;
    
    await test.step('Process biomarker dataset', async () => {
      await page.click('button:has-text("Upload Dataset")');
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles(dataset.file);
      
      await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 30000 });
    });

    await test.step('Configure ROC analysis', async () => {
      await page.click('text=Test Selection');
      await page.click('text=ROC Analysis');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="predictor-variable"]', dataset.primaryOutcome);
      await page.selectOption('[data-testid="outcome-variable"]', dataset.groupingVar);
    });

    await test.step('Execute ROC analysis', async () => {
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 45000 });
    });

    await test.step('Validate ROC results', async () => {
      // Check AUC value
      await expect(page.locator('[data-testid="auc-value"]')).toBeVisible();
      
      // Verify confidence interval
      await expect(page.locator('[data-testid="auc-confidence-interval"]')).toBeVisible();
      
      // Check ROC curve visualization
      await page.click('text=Visualizations');
      await expect(page.locator('[data-testid="roc-curve"]')).toBeVisible();
      
      // Verify optimal cutoff point
      await expect(page.locator('[data-testid="optimal-cutoff"]')).toBeVisible();
    });
  });
});

test.describe('Real Data Edge Cases and Error Handling', () => {
  test('Handle missing data scenarios', async ({ page }) => {
    await page.goto('/statistical-analysis');
    
    // Upload dataset with significant missing data
    await page.click('button:has-text("Upload Dataset")');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/real-data/missing_data_study.csv');
    
    await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 30000 });
    
    // Should detect missing data issues
    await expect(page.locator('[data-testid="missing-data-warning"]')).toBeVisible();
    await expect(page.locator('text=25% missing values detected')).toBeVisible();
    
    // Should offer imputation options
    await expect(page.locator('[data-testid="imputation-options"]')).toBeVisible();
    
    // Test analysis with missing data
    await page.click('text=Test Selection');
    await page.click('text=Independent Samples t-test');
    
    await page.click('text=Variables');
    await page.selectOption('[data-testid="dependent-variable"]', 'outcome_with_missing');
    await page.selectOption('[data-testid="grouping-variable"]', 'treatment_group');
    
    await page.click('text=Review');
    
    // Should warn about listwise deletion
    await expect(page.locator('[data-testid="missing-data-impact"]')).toBeVisible();
    
    await page.click('button:has-text("Run Statistical Analysis")');
    await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 45000 });
    
    // Results should note sample size reduction
    await expect(page.locator('[data-testid="effective-sample-size"]')).toBeVisible();
  });

  test('Handle extreme outliers in real data', async ({ page }) => {
    await page.goto('/statistical-analysis');
    
    // Upload dataset with known outliers
    await page.click('button:has-text("Upload Dataset")');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/real-data/outliers_study.csv');
    
    await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 30000 });
    
    // Should detect outliers
    await expect(page.locator('[data-testid="outliers-detected"]')).toBeVisible();
    
    // Configure analysis
    await page.click('text=Test Selection');
    await page.click('text=Independent Samples t-test');
    
    await page.click('text=Variables');
    await page.selectOption('[data-testid="dependent-variable"]', 'outcome_with_outliers');
    await page.selectOption('[data-testid="grouping-variable"]', 'group');
    
    await page.click('text=Options');
    await page.check('[data-testid="robust-statistics"]');
    
    await page.click('text=Review');
    await page.click('button:has-text("Run Statistical Analysis")');
    
    await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 45000 });
    
    // Should provide robust statistics
    await expect(page.locator('[data-testid="robust-mean"]')).toBeVisible();
    await expect(page.locator('[data-testid="outlier-influence"]')).toBeVisible();
  });

  test('Handle non-normal distributions', async ({ page }) => {
    await page.goto('/statistical-analysis');
    
    // Upload dataset with skewed distributions
    await page.click('button:has-text("Upload Dataset")');
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('tests/fixtures/real-data/skewed_distribution.csv');
    
    await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 30000 });
    
    // Configure t-test (will violate normality)
    await page.click('text=Test Selection');
    await page.click('text=Independent Samples t-test');
    
    await page.click('text=Variables');
    await page.selectOption('[data-testid="dependent-variable"]', 'skewed_outcome');
    await page.selectOption('[data-testid="grouping-variable"]', 'group');
    
    await page.click('text=Review');
    await page.click('button:has-text("Run Statistical Analysis")');
    
    await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 45000 });
    
    // Should detect normality violation
    await page.click('text=Assumptions');
    await expect(page.locator('[data-testid="normality-violation"]')).toBeVisible();
    
    // Should recommend non-parametric alternative
    await expect(page.locator('[data-testid="nonparametric-recommendation"]')).toBeVisible();
    await expect(page.locator('text=Mann-Whitney U test')).toBeVisible();
  });
});

test.describe('Real Data Performance Benchmarks', () => {
  test('Benchmark analysis performance across dataset sizes', async ({ page }) => {
    const performanceResults = [];
    
    for (const [key, dataset] of Object.entries(REAL_DATASETS)) {
      await test.step(`Benchmark ${dataset.name} (${dataset.rows} rows)`, async () => {
        await page.goto('/statistical-analysis');
        
        await page.click('button:has-text("Upload Dataset")');
        const fileInput = page.locator('input[type="file"]');
        await fileInput.setInputFiles(dataset.file);
        
        const uploadStart = Date.now();
        await expect(page.locator('text=Upload complete')).toBeVisible({ timeout: 120000 });
        const uploadTime = Date.now() - uploadStart;
        
        // Configure basic analysis
        await page.click('text=Test Selection');
        await page.click('text=Independent Samples t-test');
        
        await page.click('text=Variables');
        await page.selectOption('[data-testid="dependent-variable"]', dataset.primaryOutcome);
        await page.selectOption('[data-testid="grouping-variable"]', dataset.groupingVar);
        
        await page.click('text=Review');
        
        const analysisStart = Date.now();
        await page.click('button:has-text("Run Statistical Analysis")');
        await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 180000 });
        const analysisTime = Date.now() - analysisStart;
        
        performanceResults.push({
          dataset: dataset.name,
          rows: dataset.rows,
          uploadTime,
          analysisTime,
          totalTime: uploadTime + analysisTime
        });
        
        console.log(`${dataset.name}: Upload ${uploadTime}ms, Analysis ${analysisTime}ms`);
      });
    }
    
    // Validate performance scales appropriately
    console.log('Performance Results:', performanceResults);
    
    // Check that performance doesn't degrade dramatically with size
    const smallDataset = performanceResults.find(r => r.rows < 1000);
    const largeDataset = performanceResults.find(r => r.rows > 10000);
    
    if (smallDataset && largeDataset) {
      const performanceRatio = largeDataset.analysisTime / smallDataset.analysisTime;
      expect(performanceRatio).toBeLessThan(5); // Should not be more than 5x slower
    }
  });
});

// Utility function to validate statistical results make sense
async function validateStatisticalSensibility(page: any, testType: string) {
  switch (testType) {
    case 't-test-independent':
      // Check that means are different if significant
      const significant = await page.locator('[data-testid="significance-badge"]').textContent();
      if (significant?.includes('Significant')) {
        const pValue = await page.locator('[data-testid="p-value"]').textContent();
        expect(parseFloat(pValue?.replace(/[^\d.]/g, '') || '1')).toBeLessThan(0.05);
      }
      break;
      
    case 'anova-one-way':
      // Check F-statistic is positive
      const fStat = await page.locator('[data-testid="f-statistic"]').textContent();
      expect(parseFloat(fStat || '0')).toBeGreaterThan(0);
      break;
      
    case 'correlation-pearson':
      // Check correlation is between -1 and 1
      const correlation = await page.locator('[data-testid="correlation-coefficient"]').textContent();
      const r = parseFloat(correlation || '0');
      expect(r).toBeGreaterThanOrEqual(-1);
      expect(r).toBeLessThanOrEqual(1);
      break;
  }
}