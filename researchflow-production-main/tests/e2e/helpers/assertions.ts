/**
 * E2E Custom Assertions
 *
 * Reusable assertions for stage status, validation, and PHI gate.
 * The app may need these data-testids for full coverage: validation-error, phi-gate-banner, stage-{n}-status.
 */

import type { Page } from '@playwright/test';
import { expect } from '@playwright/test';

export async function expectStageComplete(page: Page, stageNumber: number): Promise<void> {
  const status = page.locator(`[data-testid="stage-${stageNumber}-status"]`);
  await expect(status).toHaveText('Complete');
}

export async function expectNoValidationErrors(page: Page): Promise<void> {
  const errors = page.locator('[data-testid="validation-error"]');
  await expect(errors).toHaveCount(0);
}

export async function expectPHIGateVisible(page: Page): Promise<void> {
  await expect(page.locator('[data-testid="phi-gate-banner"]')).toBeVisible();
}
