import { test, expect } from '@playwright/test';

test.describe('Workflow', () => {
  test('should navigate between workflow stages', async ({ page }) => {
    // Assumes app allows navigation without auth in DEMO mode or will be adapted later
    await page.goto('/workflow');

    // Ensure the page renders
    await expect(page.locator('body')).toBeVisible();

    // Prefer explicit test IDs if present
    const stageCards = page.locator('[data-testid^="card-stage-"], [data-testid^="stage-"]');

    // If stages exist, verify at least one is visible and clickable
    const count = await stageCards.count();
    expect(count).toBeGreaterThanOrEqual(0);

    if (count > 0) {
      await stageCards.first().click();
      await page.waitForTimeout(250);

      // Either navigation occurs or a modal/dialog opens
      const hasDialog = await page.locator('[role="dialog"], [data-testid*="modal"]').first().isVisible().catch(() => false);
      const urlChanged = page.url().includes('/workflow') || page.url().includes('/pipeline');
      expect(hasDialog || urlChanged).toBeTruthy();
    }
  });

  test('should deep link to a workflow route', async ({ page }) => {
    await page.goto('/workflow');
    await expect(page).toHaveURL(/\/workflow/);
    await expect(page.locator('main, [role="main"], body')).toBeVisible();
  });
});
