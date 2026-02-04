/**
 * End-to-End Tests for Statistical Analysis Workflow
 *
 * Comprehensive E2E tests that validate the complete statistical analysis workflow
 * from data upload through results export.
 */

import { test, expect } from '@playwright/test';

test.describe('Statistical Analysis Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to statistical analysis page
    await page.goto('/statistical-analysis');
    
    // Wait for page to load
    await expect(page.locator('h1')).toContainText('Statistical Analysis');
  });

  test('complete independent t-test workflow', async ({ page }) => {
    // Step 1: Upload or select dataset
    await test.step('Select dataset', async () => {
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
      await expect(page.locator('[data-testid="dataset-info"]')).toContainText('500 rows');
    });

    // Step 2: Configure analysis
    await test.step('Configure t-test analysis', async () => {
      // Select test type
      await page.click('text=Test Selection');
      await page.click('text=Independent Samples t-test');
      
      // Assign variables
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
      await page.selectOption('[data-testid="grouping-variable"]', 'treatment_group');
      
      // Configure options
      await page.click('text=Options');
      await page.selectOption('[data-testid="confidence-level"]', '0.95');
      await page.selectOption('[data-testid="alpha-level"]', '0.05');
      
      // Review and submit
      await page.click('text=Review');
      await expect(page.locator('[data-testid="config-summary"]')).toContainText('Independent Samples t-test');
    });

    // Step 3: Execute analysis
    await test.step('Execute analysis', async () => {
      await page.click('button:has-text("Run Statistical Analysis")');
      
      // Wait for analysis to complete
      await expect(page.locator('[data-testid="analysis-progress"]')).toBeVisible();
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });
    });

    // Step 4: Verify results
    await test.step('Review results', async () => {
      // Check results are displayed
      await expect(page.locator('[data-testid="results-summary"]')).toBeVisible();
      await expect(page.locator('[data-testid="hypothesis-test"]')).toContainText('t-test');
      
      // Check descriptive statistics
      await page.click('text=Descriptive');
      await expect(page.locator('[data-testid="descriptive-stats-table"]')).toBeVisible();
      
      // Check visualizations
      await page.click('text=Visualizations');
      await expect(page.locator('[data-testid="qq-plot"]')).toBeVisible();
      await expect(page.locator('[data-testid="histogram"]')).toBeVisible();
    });

    // Step 5: Export results
    await test.step('Export results', async () => {
      await page.click('text=Export');
      await page.click('button:has-text("Full Report")');
      
      // Verify download
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("Export PDF Report")');
      const download = await downloadPromise;
      
      expect(download.suggestedFilename()).toMatch(/statistical-analysis.*\.pdf/);
    });
  });

  test('ANOVA analysis workflow', async ({ page }) => {
    // Test ANOVA workflow with multiple groups
    await test.step('Configure ANOVA', async () => {
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
      
      await page.click('text=Test Selection');
      await page.click('text=One-Way ANOVA');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
      await page.selectOption('[data-testid="grouping-variable"]', 'treatment_arm'); // Assuming multi-arm trial
    });

    await test.step('Execute ANOVA', async () => {
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });
    });

    await test.step('Verify post-hoc tests', async () => {
      await page.click('text=Inferential');
      await expect(page.locator('[data-testid="post-hoc-table"]')).toBeVisible();
      await expect(page.locator('text=Tukey')).toBeVisible(); // Default post-hoc test
    });
  });

  test('correlation analysis workflow', async ({ page }) => {
    await test.step('Configure correlation', async () => {
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
      
      await page.click('text=Test Selection');
      await page.click('text=Pearson Correlation');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="variable-1"]', 'baseline_score');
      await page.selectOption('[data-testid="variable-2"]', 'outcome_score');
    });

    await test.step('Execute correlation', async () => {
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });
    });

    await test.step('Verify correlation results', async () => {
      await expect(page.locator('[data-testid="correlation-coefficient"]')).toBeVisible();
      await expect(page.locator('[data-testid="correlation-interpretation"]')).toBeVisible();
      
      // Check scatter plot
      await page.click('text=Visualizations');
      await expect(page.locator('[data-testid="scatter-plot"]')).toBeVisible();
    });
  });

  test('regression analysis workflow', async ({ page }) => {
    await test.step('Configure regression', async () => {
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
      
      await page.click('text=Test Selection');
      await page.click('text=Linear Regression');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
      await page.selectOption('[data-testid="independent-variable-1"]', 'age');
      await page.selectOption('[data-testid="independent-variable-2"]', 'baseline_score');
    });

    await test.step('Execute regression', async () => {
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });
    });

    await test.step('Verify regression results', async () => {
      await expect(page.locator('[data-testid="r-squared"]')).toBeVisible();
      await expect(page.locator('[data-testid="coefficients-table"]')).toBeVisible();
      await expect(page.locator('[data-testid="model-fit"]')).toBeVisible();
    });
  });

  test('assumption checking and warnings', async ({ page }) => {
    await test.step('Configure analysis with violations', async () => {
      // Use dataset that violates normality assumption
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-skewed');
      
      await page.click('text=Test Selection');
      await page.click('text=Independent Samples t-test');
      
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', 'skewed_outcome');
      await page.selectOption('[data-testid="grouping-variable"]', 'group');
    });

    await test.step('Execute and check warnings', async () => {
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });
      
      // Verify assumption violation warnings
      await expect(page.locator('[data-testid="analysis-warnings"]')).toBeVisible();
      await expect(page.locator('text=normality assumption')).toBeVisible();
    });

    await test.step('Check assumption details', async () => {
      await page.click('text=Assumptions');
      await expect(page.locator('[data-testid="normality-test"]')).toContainText('Violated');
      await expect(page.locator('[data-testid="assumption-recommendation"]')).toBeVisible();
    });
  });

  test('data upload and validation', async ({ page }) => {
    await test.step('Upload custom dataset', async () => {
      await page.click('button:has-text("Upload Dataset")');
      
      // Upload CSV file
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles('tests/fixtures/sample-data.csv');
      
      await expect(page.locator('[data-testid="upload-progress"]')).toBeVisible();
      await expect(page.locator('text=Upload complete')).toBeVisible();
    });

    await test.step('Validate data quality', async () => {
      await expect(page.locator('[data-testid="data-quality-score"]')).toBeVisible();
      await expect(page.locator('[data-testid="column-summary"]')).toBeVisible();
      
      // Check for any data quality issues
      const qualityScore = await page.locator('[data-testid="quality-score-value"]').textContent();
      expect(parseInt(qualityScore || '0')).toBeGreaterThan(70); // Minimum quality threshold
    });
  });

  test('export customization', async ({ page }) => {
    // Complete a basic analysis first
    await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
    await page.click('text=Test Selection');
    await page.click('text=Independent Samples t-test');
    await page.click('text=Variables');
    await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
    await page.selectOption('[data-testid="grouping-variable"]', 'treatment_group');
    await page.click('text=Review');
    await page.click('button:has-text("Run Statistical Analysis")');
    await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });

    await test.step('Customize export options', async () => {
      await page.click('text=Export');
      await page.click('button:has-text("Custom Export")');
      
      // Select Word format
      await page.click('[data-testid="format-docx"]');
      
      // Customize sections
      await page.uncheck('[data-testid="include-assumptions"]');
      await page.uncheck('[data-testid="include-visualizations"]');
      await page.check('[data-testid="include-apa-text"]');
      
      // Select template
      await page.selectOption('[data-testid="template-select"]', 'apa');
      
      // Custom filename
      await page.fill('[data-testid="filename-input"]', 'my-analysis-results');
    });

    await test.step('Export with custom settings', async () => {
      const downloadPromise = page.waitForEvent('download');
      await page.click('button:has-text("Export Word Document")');
      const download = await downloadPromise;
      
      expect(download.suggestedFilename()).toMatch(/my-analysis-results.*\.docx/);
    });
  });

  test('error handling and recovery', async ({ page }) => {
    await test.step('Handle configuration errors', async () => {
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
      
      await page.click('text=Test Selection');
      await page.click('text=Independent Samples t-test');
      
      // Try to proceed without selecting variables
      await page.click('text=Review');
      
      // Should show validation errors
      await expect(page.locator('[data-testid="validation-errors"]')).toBeVisible();
      await expect(page.locator('text=Please assign required variables')).toBeVisible();
    });

    await test.step('Handle analysis execution errors', async () => {
      // Mock server error for this test
      await page.route('/api/v1/statistical-analysis/execute', route => {
        route.fulfill({
          status: 500,
          body: JSON.stringify({ success: false, message: 'Server error' })
        });
      });

      // Complete configuration
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
      await page.selectOption('[data-testid="grouping-variable"]', 'treatment_group');
      
      await page.click('text=Review');
      await page.click('button:has-text("Run Statistical Analysis")');
      
      // Should show error message
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('text=Server error')).toBeVisible();
      
      // Retry button should be available
      await expect(page.locator('button:has-text("Retry")')).toBeVisible();
    });
  });

  test('accessibility compliance', async ({ page }) => {
    await test.step('Check keyboard navigation', async () => {
      // Tab through the interface
      await page.keyboard.press('Tab');
      await expect(page.locator(':focus')).toBeVisible();
      
      // Should be able to navigate with keyboard
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
    });

    await test.step('Check ARIA labels', async () => {
      // Verify important elements have proper ARIA labels
      await expect(page.locator('[aria-label]')).toHaveCount({ min: 5 });
      await expect(page.locator('[role="tab"]')).toHaveCount({ min: 4 });
    });
  });

  test('performance benchmarks', async ({ page }) => {
    await test.step('Measure page load time', async () => {
      const startTime = Date.now();
      await page.goto('/statistical-analysis');
      await expect(page.locator('h1')).toBeVisible();
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(3000); // Page should load within 3 seconds
    });

    await test.step('Measure analysis execution time', async () => {
      await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
      await page.click('text=Test Selection');
      await page.click('text=Independent Samples t-test');
      await page.click('text=Variables');
      await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
      await page.selectOption('[data-testid="grouping-variable"]', 'treatment_group');
      await page.click('text=Review');
      
      const startTime = Date.now();
      await page.click('button:has-text("Run Statistical Analysis")');
      await expect(page.locator('text=Analysis completed')).toBeVisible();
      const analysisTime = Date.now() - startTime;
      
      expect(analysisTime).toBeLessThan(10000); // Analysis should complete within 10 seconds
    });
  });
});

test.describe('Statistical Analysis API Integration', () => {
  test('validates API responses', async ({ page }) => {
    // Intercept API calls to validate request/response format
    await page.route('/api/v1/statistical-analysis/**', async (route) => {
      const response = await route.fetch();
      const data = await response.json();
      
      // Validate response structure
      expect(data).toHaveProperty('success');
      if (data.success) {
        expect(data).toHaveProperty('result');
      } else {
        expect(data).toHaveProperty('message');
      }
      
      await route.fulfill({ response });
    });

    // Execute a complete analysis workflow
    await page.goto('/statistical-analysis');
    await page.selectOption('select[data-testid="dataset-select"]', 'demo-clinical');
    await page.click('text=Test Selection');
    await page.click('text=Independent Samples t-test');
    await page.click('text=Variables');
    await page.selectOption('[data-testid="dependent-variable"]', 'outcome_score');
    await page.selectOption('[data-testid="grouping-variable"]', 'treatment_group');
    await page.click('text=Review');
    await page.click('button:has-text("Run Statistical Analysis")');
    
    await expect(page.locator('text=Analysis completed')).toBeVisible({ timeout: 30000 });
  });
});