/**
 * Complete 20-Stage Workflow E2E Tests
 * Tests the full research workflow from hypothesis to publication
 */

import { test, expect } from '@playwright/test';

import { TestUser, TestProject } from './fixtures';

test.describe('Complete 20-Stage Workflow', () => {
  let user: TestUser;
  let project: TestProject;

  test.beforeAll(async ({ request }) => {
    user = await TestUser.create('researcher', request);
    project = await TestProject.create(user.id, {
      name: 'E2E Complete Workflow Test',
      type: 'cohort',
      governanceMode: 'DEMO',
    }, request, user.getAuthHeaders());
  });

  test.afterAll(async () => {
    await project?.cleanup();
    await user?.cleanup();
  });

  test('Stage 1: Hypothesis Formation', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/1`);
    await expect(page.locator('[data-testid="stage-title"]')).toContainText('Hypothesis');

    await page.fill('[data-testid="research-question"]',
      'Does a Mediterranean diet reduce cardiovascular events in high-risk patients?');
    await page.fill('[data-testid="hypothesis"]',
      'Mediterranean diet will reduce major cardiovascular events by 30% compared to control diet');

    await page.click('[data-testid="save-and-continue"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 2: Literature Review', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/2`);
    await expect(page.locator('[data-testid="stage-title"]')).toContainText('Literature');

    await page.fill('[data-testid="search-query"]', 'Mediterranean diet cardiovascular prevention');
    await page.click('[data-testid="search-button"]');

    await page.waitForSelector('[data-testid="search-results"]', { timeout: 30000 });

    // Select first 3 results
    for (let i = 0; i < 3; i++) {
      await page.click(`[data-testid="result-${i}"] [data-testid="select-checkbox"]`);
    }

    await page.click('[data-testid="save-selection"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 3: Protocol Design', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/3`);

    await page.selectOption('[data-testid="study-type"]', 'cohort');
    await page.fill('[data-testid="population"]', 'Adults 50-75 years with high cardiovascular risk');
    await page.fill('[data-testid="intervention"]', 'Mediterranean diet counseling and support');
    await page.fill('[data-testid="comparator"]', 'Standard dietary advice');
    await page.fill('[data-testid="primary-outcome"]', 'Composite of MI, stroke, CV death');
    await page.fill('[data-testid="sample-size"]', '500');

    await page.click('[data-testid="save-and-continue"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 4: Data Collection Setup', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/4`);

    // Upload test dataset
    const fileInput = page.locator('[data-testid="file-upload"]');
    await fileInput.setInputFiles('tests/e2e/fixtures/sample-data.csv');

    await page.waitForSelector('[data-testid="upload-success"]', { timeout: 30000 });
    await page.click('[data-testid="confirm-schema"]');

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 5: Data Preprocessing', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/5`);

    // Check for PHI banner in DEMO mode
    await expect(page.locator('[data-testid="phi-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="phi-banner"]')).toContainText('Demo Mode');

    await page.click('[data-testid="run-preprocessing"]');
    await page.waitForSelector('[data-testid="preprocessing-complete"]', { timeout: 60000 });

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 6: Exploratory Analysis', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/6`);

    await page.click('[data-testid="generate-summary"]');
    await page.waitForSelector('[data-testid="summary-stats"]', { timeout: 30000 });

    await expect(page.locator('[data-testid="summary-stats"]')).toBeVisible();
    await page.click('[data-testid="save-and-continue"]');

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 7: Statistical Modeling', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/7`);

    await page.selectOption('[data-testid="model-type"]', 'cox_regression');
    await page.click('[data-testid="run-analysis"]');

    await page.waitForSelector('[data-testid="analysis-results"]', { timeout: 120000 });
    await expect(page.locator('[data-testid="analysis-results"]')).toBeVisible();

    await page.click('[data-testid="save-and-continue"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 8: Visualization', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/8`);

    await page.click('[data-testid="generate-charts"]');
    await page.waitForSelector('[data-testid="chart-gallery"]', { timeout: 60000 });

    await expect(page.locator('[data-testid="chart-gallery"]')).toBeVisible();
    await page.click('[data-testid="save-and-continue"]');

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 9: Interpretation', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/9`);

    await page.fill('[data-testid="interpretation-notes"]',
      'Results suggest Mediterranean diet is associated with reduced cardiovascular events.');
    await page.click('[data-testid="save-and-continue"]');

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 10: Validation', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/10`);

    await page.click('[data-testid="run-validation"]');
    await page.waitForSelector('[data-testid="validation-results"]', { timeout: 60000 });

    await expect(page.locator('[data-testid="validation-score"]')).toBeVisible();
    await page.click('[data-testid="approve-validation"]');

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 11: Iteration Review', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/11`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 12: Documentation', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/12`);

    // Test manuscript generation panel
    await expect(page.locator('[data-testid="generation-panel"]')).toBeVisible();
    await page.click('[data-testid="mark-complete"]');

    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 13: Internal Review', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/13`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 14: Ethical Review', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/14`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 15: Artifact Bundling', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/15`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 16: Collaboration Handoff', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/16`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 17: Archiving', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/17`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 18: Impact Assessment', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/18`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 19: Dissemination', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/19`);
    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');
  });

  test('Stage 20: Final Export', async ({ page }) => {
    await page.goto(`/projects/${project.id}/workflow/20`);

    // Verify workflow completion
    await expect(page.locator('[data-testid="workflow-progress"]')).toContainText('19/20');

    await page.click('[data-testid="generate-final-export"]');
    await page.waitForSelector('[data-testid="export-ready"]', { timeout: 120000 });

    await page.click('[data-testid="mark-complete"]');
    await expect(page.locator('[data-testid="stage-status"]')).toHaveAttribute('data-status', 'complete');

    // Verify full workflow completion
    await expect(page.locator('[data-testid="workflow-complete-banner"]')).toBeVisible();
  });
});
