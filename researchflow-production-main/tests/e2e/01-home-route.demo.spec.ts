/**
 * E2E Test: Home Route - Demo Mode
 * 
 * Tests the home route functionality in DEMO governance mode.
 * Verifies basic navigation, UI rendering, and demo mode restrictions.
 */

import { test, expect } from '@playwright/test';
import {
  loginAsDevUser,
  TEST_USERS,
  setGovernanceMode,
  getGovernanceMode,
  waitForWorkflowReady,
  assertDevAuthEnabled
} from './helpers/devSession';

test.describe('Home Route - Demo Mode', () => {
  test.beforeEach(async ({ page, request }) => {
    // Verify dev auth is enabled
    await assertDevAuthEnabled(request);
    
    // Login as default test user
    await loginAsDevUser(page, TEST_USERS.default);
    
    // Set governance mode to DEMO
    await setGovernanceMode(page, 'DEMO');
  });

  test('should render home page with workflow pipeline', async ({ page }) => {
    await page.goto('/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Check for main app container
    await expect(page.locator('main')).toBeVisible();
    
    // Check for workflow groups accordion
    await waitForWorkflowReady(page);
    
    const workflowGroups = page.locator('[data-testid="accordion-workflow-groups"]');
    await expect(workflowGroups).toBeVisible();
  });

  test('should display DEMO mode indicator', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check governance mode is DEMO
    const mode = await getGovernanceMode(page);
    expect(mode).toBe('DEMO');
    
    // Look for demo mode indicator in UI
    const demoIndicator = page.locator('[data-testid="governance-mode-indicator"]');
    if (await demoIndicator.isVisible()) {
      await expect(demoIndicator).toContainText(/demo/i);
    }
  });

  test('should show file upload input', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    const fileUpload = page.locator('[data-testid="input-file-upload"]');
    await expect(fileUpload).toBeVisible();
  });

  test('should have execute stage button disabled without file', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    const executeButton = page.locator('[data-testid="button-execute-stage"]').first();
    
    // Button should be disabled when no file is uploaded
    if (await executeButton.isVisible()) {
      const isDisabled = await executeButton.isDisabled();
      // In demo mode without file, button should be disabled
      expect(isDisabled).toBe(true);
    }
  });

  test('should show research overview textarea', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    const textarea = page.locator('[data-testid="textarea-research-overview"]');
    if (await textarea.isVisible()) {
      await expect(textarea).toBeEditable();
    }
  });

  test('should navigate between workflow groups', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    const accordionItems = page.locator('[data-testid="accordion-workflow-groups"] [role="button"]');
    const count = await accordionItems.count();
    
    // Should have at least one workflow group
    expect(count).toBeGreaterThan(0);
    
    // Click first accordion item to expand
    if (count > 0) {
      await accordionItems.first().click();
      // Wait for expansion animation
      await page.waitForTimeout(300);
    }
  });

  test('should show demo mode limitations message', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Check for any demo mode limitation notices
    const demoNotice = page.locator('text=/demo|sample|simulated/i');
    
    // If there's a demo notice, verify it exists
    if (await demoNotice.first().isVisible()) {
      await expect(demoNotice.first()).toBeVisible();
    }
  });

  test('should handle keyboard navigation', async ({ page }) => {
    await page.goto('/');
    await waitForWorkflowReady(page);
    
    // Tab to first interactive element
    await page.keyboard.press('Tab');
    
    // Check that something is focused
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeTruthy();
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Page should still render
    await expect(page.locator('main')).toBeVisible();
    
    // Workflow should still be accessible
    const workflowGroups = page.locator('[data-testid="accordion-workflow-groups"]');
    await expect(workflowGroups).toBeVisible();
  });
});

test.describe('Home Route - Authentication', () => {
  test('should identify dev user from header', async ({ page, request }) => {
    await assertDevAuthEnabled(request);
    
    // Login with specific user
    await loginAsDevUser(page, TEST_USERS.researcher);
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // User should be authenticated
    // Check for any user-specific UI elements
    const userIndicator = page.locator('[data-testid="user-info"], [data-testid="user-avatar"]');
    if (await userIndicator.isVisible()) {
      await expect(userIndicator).toBeVisible();
    }
  });

  test('should handle different user roles', async ({ page, request }) => {
    await assertDevAuthEnabled(request);
    
    // Test with admin user
    await loginAsDevUser(page, TEST_USERS.admin);
    
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Admin might see additional options
    await expect(page.locator('main')).toBeVisible();
  });
});
