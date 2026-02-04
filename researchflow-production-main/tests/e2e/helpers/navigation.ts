/**
 * E2E Navigation Helpers
 *
 * Reusable helpers for stage traversal and workflow navigation.
 * Selectors define the contract; the app may need to add data-testid for full coverage.
 */

import type { Page } from '@playwright/test';

export async function navigateToStage(
  page: Page,
  projectId: string,
  stageNumber: number
): Promise<void> {
  await page.goto(`/projects/${projectId}/workflow/${stageNumber}`);
  await page.waitForSelector(`[data-testid="stage-${stageNumber}"]`, { state: 'visible' });
}

export async function waitForStageComplete(page: Page): Promise<void> {
  await page.waitForSelector('[data-testid="stage-status"][data-status="complete"]', {
    timeout: 30000,
  });
}

export async function navigateToNextStage(page: Page): Promise<void> {
  await page.click('[data-testid="next-stage-button"]');
  await page.waitForLoadState('networkidle');
}
