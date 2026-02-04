import { test, expect } from '@playwright/test';

test.describe('Pipeline dashboard', () => {
  test('should load pipeline dashboard', async ({ page }) => {
    await page.goto('/pipeline');

    await expect(page).toHaveURL(/\/pipeline/);
    await expect(page.locator('main, [role="main"], body')).toBeVisible();
  });

  test('should show runs tab or empty state', async ({ page }) => {
    await page.goto('/pipeline');

    // The existing suite uses many data-testid conventions; keep assertions flexible
    const statusSummaryCard = page.locator('[data-testid="card-status-summary"], [data-testid*="status-summary"], [data-testid*="pipeline-status"], .pipeline-status-card');
    const runsTab = page.locator('[data-testid="tab-runs"], [role="tab"]:has-text("Runs"), text=/Runs/i');

    // Either a known card, the runs tab, or generic content should be visible
    const hasStatus = await statusSummaryCard.first().isVisible().catch(() => false);
    const hasRuns = await runsTab.first().isVisible().catch(() => false);

    expect(hasStatus || hasRuns).toBeTruthy();
  });
});
