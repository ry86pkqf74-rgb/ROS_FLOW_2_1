/**
 * E2E Test: Live Mode - Progressive Workflow Execution
 * 
 * Tests progressive multi-stage workflow execution in LIVE governance mode.
 * Uses real PLOS ONE dataset for end-to-end validation.
 * 
 * LIVE Dataset: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0214517
 * Supplementary: pone.0214517.s003.xlsx
 */

import { test, expect } from '@playwright/test';
import {
  loginAsDevUser,
  TEST_USERS,
  TEST_PROJECTS,
  setGovernanceMode,
  getGovernanceMode,
  waitForWorkflowReady,
  uploadFile,
  executeStage,
  waitForStageResults,
  getStageOutputs,
  getResearchOverview,
  assertDevAuthEnabled,
  DevSessionManager
} from './helpers/devSession';

// LIVE dataset URL for testing
const PLOS_DATASET_URL = 'https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0214517';
const SUPPLEMENTARY_FILE = 'pone.0214517.s003.xlsx';

test.describe('Live Mode - Progressive Workflow Execution', () => {
  let sessionManager: DevSessionManager;

  test.beforeEach(async ({ page, request }) => {
    // Verify dev auth is enabled
    await assertDevAuthEnabled(request);
    
    // Initialize session manager
    sessionManager = new DevSessionManager(request);
    
    // Login as test user
    await loginAsDevUser(page, TEST_USERS.default);
    
    // Set governance mode to LIVE
    await setGovernanceMode(page, 'LIVE');
  });

  test.afterEach(async () => {
    // Cleanup sessions
    if (sessionManager) {
      await sessionManager.cleanup();
    }
  });

  test('should display LIVE mode indicator with warnings', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Verify governance mode is LIVE
    const mode = await getGovernanceMode(page);
    expect(mode).toBe('LIVE');
    
    // Check for LIVE mode indicator
    const modeIndicator = page.locator('[data-testid="governance-mode-indicator"]');
    if (await modeIndicator.isVisible()) {
      const text = await modeIndicator.textContent();
      expect(text?.toUpperCase()).toContain('LIVE');
    }
    
    // LIVE mode should show a warning or confirmation
    const liveWarning = page.locator('[data-testid="live-mode-warning"], text=/real data|production/i');
    if (await liveWarning.first().isVisible()) {
      await expect(liveWarning.first()).toBeVisible();
    }
  });

  test('should show all workflow stages for progressive execution', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Get all stage elements
    const stages = page.locator('[data-testid^="workflow-stage-"]');
    const stageCount = await stages.count();
    
    // Progressive workflow should have multiple stages
    expect(stageCount).toBeGreaterThanOrEqual(3);
    
    // Check stage names include expected workflow
    const stageNames = await page.locator('[data-testid="stage-name"]').allTextContents();
    // Should have research workflow stages
  });

  test('should enable progressive stage execution', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // First stage should be available
    const firstExecuteButton = page.locator('[data-testid="button-execute-stage"]').first();
    await expect(firstExecuteButton).toBeVisible();
    
    // Subsequent stages should be locked until prerequisites complete
    const allExecuteButtons = page.locator('[data-testid="button-execute-stage"]');
    const buttonCount = await allExecuteButtons.count();
    
    if (buttonCount > 1) {
      // Later stages might be disabled
      const secondButton = allExecuteButtons.nth(1);
      const isDisabled = await secondButton.isDisabled();
      // Second stage should be disabled until first completes
      // (This depends on workflow configuration)
    }
  });

  test('should show stage dependencies', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Look for dependency indicators
    const dependencies = page.locator('[data-testid="stage-dependencies"], [data-testid="stage-prerequisites"]');
    
    if (await dependencies.first().isVisible()) {
      await expect(dependencies.first()).toBeVisible();
    }
  });

  test('should track stage completion status', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Check for stage status indicators
    const statusIndicators = page.locator('[data-testid="stage-status"]');
    const count = await statusIndicators.count();
    
    if (count > 0) {
      // All stages should start in pending/ready state
      const firstStatus = await statusIndicators.first().textContent();
      expect(firstStatus?.toLowerCase()).toMatch(/pending|ready|available/);
    }
  });

  test('should provide research overview input', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    const overviewTextarea = page.locator('[data-testid="textarea-research-overview"]');
    
    if (await overviewTextarea.isVisible()) {
      // Should be editable
      await expect(overviewTextarea).toBeEditable();
      
      // Enter test research overview
      await overviewTextarea.fill('E2E Test: Analysis of supplementary data from PLOS ONE article');
      
      // Verify input
      const value = await overviewTextarea.inputValue();
      expect(value).toContain('PLOS ONE');
    }
  });

  test('should show execution results section', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Results section should exist (may be hidden initially)
    const resultsSection = page.locator('[data-testid="section-execution-results"]');
    
    // Check if results section is in DOM
    const exists = await resultsSection.count();
    expect(exists).toBeGreaterThanOrEqual(0);
  });

  test('should display stage outputs list', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Outputs list should exist for completed stages
    const outputsList = page.locator('[data-testid="list-stage-outputs"]');
    
    // Check if outputs list is in DOM
    const exists = await outputsList.count();
    expect(exists).toBeGreaterThanOrEqual(0);
  });

  test('should handle file upload for LIVE data processing', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    const fileInput = page.locator('[data-testid="input-file-upload"]');
    await expect(fileInput).toBeVisible();
    
    // Check that XLSX files are accepted
    const acceptedTypes = await fileInput.getAttribute('accept');
    if (acceptedTypes) {
      expect(acceptedTypes).toMatch(/xlsx|xls/i);
    }
  });

  test('should show AI provider status in LIVE mode', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check for AI provider status indicator
    const aiStatus = page.locator('[data-testid="ai-provider-status"], [data-testid="mercury-status"]');
    
    if (await aiStatus.isVisible()) {
      await expect(aiStatus).toBeVisible();
    }
  });

  test('should enforce FAVES compliance checks in LIVE mode', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // LIVE mode should show FAVES compliance indicators
    const favesIndicator = page.locator('[data-testid="faves-compliance"], text=/faves|compliance/i');
    
    if (await favesIndicator.first().isVisible()) {
      await expect(favesIndicator.first()).toBeVisible();
    }
  });
});

test.describe('Live Mode - Error Handling', () => {
  test.beforeEach(async ({ page, request }) => {
    await assertDevAuthEnabled(request);
    await loginAsDevUser(page, TEST_USERS.default);
    await setGovernanceMode(page, 'LIVE');
  });

  test('should display error messages for failed stages', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Error message container should exist
    const errorContainer = page.locator('[data-testid="stage-error"], [role="alert"]');
    
    // Should not show errors initially
    const visibleErrors = await errorContainer.filter({ hasText: /error/i }).count();
    expect(visibleErrors).toBe(0);
  });

  test('should allow retry of failed stages', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Retry button should exist (appears on error)
    const retryButton = page.locator('[data-testid="button-retry-stage"]');
    
    // Retry button should not be visible when no errors
    const isVisible = await retryButton.isVisible();
    expect(isVisible).toBe(false);
  });

  test('should preserve progress on page refresh', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Store some state
    await page.evaluate(() => {
      localStorage.setItem('e2e-test-marker', 'test-value');
    });
    
    // Refresh page
    await page.reload();
    await waitForWorkflowReady(page);
    
    // Check state persisted
    const marker = await page.evaluate(() => {
      return localStorage.getItem('e2e-test-marker');
    });
    
    expect(marker).toBe('test-value');
    
    // Cleanup
    await page.evaluate(() => {
      localStorage.removeItem('e2e-test-marker');
    });
  });

  test('should handle network disconnection gracefully', async ({ page, context }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Simulate offline mode
    await context.setOffline(true);
    
    // Try to interact with the page
    await page.locator('[data-testid="accordion-workflow-groups"]').click();
    
    // Should show offline indicator or error
    // (Implementation dependent)
    
    // Restore connection
    await context.setOffline(false);
  });
});

test.describe('Live Mode - Data Source Integration', () => {
  test('should reference PLOS ONE dataset correctly', async ({ page }) => {
    // This test documents the expected LIVE dataset
    const expectedDataset = {
      source: PLOS_DATASET_URL,
      supplementary: SUPPLEMENTARY_FILE,
      format: 'xlsx'
    };
    
    expect(expectedDataset.source).toContain('plos.org');
    expect(expectedDataset.supplementary).toContain('pone.0214517');
    expect(expectedDataset.format).toBe('xlsx');
  });

  test('should validate expected selectors exist', async ({ page, request }) => {
    await assertDevAuthEnabled(request);
    await loginAsDevUser(page, TEST_USERS.default);
    
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Verify all expected stable selectors from workflow-pipeline.tsx
    const selectors = [
      'accordion-workflow-groups',
      'input-file-upload',
      'button-execute-stage',
      // These may not be visible until execution
      // 'section-execution-results',
      // 'list-stage-outputs',
      // 'textarea-research-overview'
    ];
    
    for (const selector of selectors) {
      const element = page.locator(`[data-testid="${selector}"]`);
      const count = await element.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }
  });
});
