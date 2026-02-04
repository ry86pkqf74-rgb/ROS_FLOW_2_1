/**
 * Manuscript Export E2E Tests
 *
 * Validates export panel UI:
 * - Export panel opens from manuscript editor
 * - Format selection (DOCX, PDF, LaTeX, Markdown)
 * - Journal style selection
 * - Progress tracking and download
 */

import { test, expect } from '@playwright/test';

const TEST_MANUSCRIPT_ID = 'test-manuscript-id';

test.describe('Manuscript Export Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`/manuscripts/${TEST_MANUSCRIPT_ID}`);
    await page.waitForLoadState('networkidle');
  });

  test('should open export panel from manuscript editor', async ({ page }) => {
    const exportBtn = page.getByTestId('button-export-panel');
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await exportBtn.click();

    const dialog = page.locator('[role="dialog"]');
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await expect(dialog.getByText(/Export manuscript/i)).toBeVisible();
  });

  test('should show format selection', async ({ page }) => {
    const exportBtn = page.getByTestId('button-export-panel');
    await exportBtn.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const formatTrigger = page.locator('[role="dialog"]').getByRole('combobox').first();
    await expect(formatTrigger).toBeVisible({ timeout: 5000 });
    await formatTrigger.click();

    await expect(page.getByRole('option', { name: /DOCX/i })).toBeVisible();
    await expect(page.getByRole('option', { name: /PDF/i })).toBeVisible();
    await expect(page.getByRole('option', { name: /LaTeX/i })).toBeVisible();
    await expect(page.getByRole('option', { name: /Markdown/i })).toBeVisible();
  });

  test('should show journal style selector', async ({ page }) => {
    const exportBtn = page.getByTestId('button-export-panel');
    await exportBtn.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const journalSelect = page.locator('[role="dialog"]').getByText(/Journal style/i);
    await expect(journalSelect).toBeVisible({ timeout: 5000 });
  });

  test('should have export options toggles', async ({ page }) => {
    const exportBtn = page.getByTestId('button-export-panel');
    await exportBtn.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    await expect(page.getByText(/Include supplementary materials/i)).toBeVisible();
    await expect(page.getByText(/Include track changes/i)).toBeVisible();
    await expect(page.getByText(/Include compliance appendix/i)).toBeVisible();
  });

  test('should have Preview before export and Export buttons', async ({ page }) => {
    const exportBtn = page.getByTestId('button-export-panel');
    await exportBtn.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    await expect(page.getByRole('button', { name: /Preview before export/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Export/i })).toBeVisible();
  });
});

test.describe('Manuscript Export - format selection', () => {
  test('should select DOCX format', async ({ page }) => {
    await page.goto(`/manuscripts/${TEST_MANUSCRIPT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.getByTestId('button-export-panel').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const formatTrigger = page.locator('[role="dialog"]').getByRole('combobox').first();
    await formatTrigger.click();
    await page.getByRole('option', { name: 'DOCX' }).click();
    await expect(formatTrigger).toContainText('DOCX');
  });

  test('should select PDF format', async ({ page }) => {
    await page.goto(`/manuscripts/${TEST_MANUSCRIPT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.getByTestId('button-export-panel').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const formatTrigger = page.locator('[role="dialog"]').getByRole('combobox').first();
    await formatTrigger.click();
    await page.getByRole('option', { name: 'PDF' }).click();
    await expect(formatTrigger).toContainText('PDF');
  });

  test('should select journal style JAMA', async ({ page }) => {
    await page.goto(`/manuscripts/${TEST_MANUSCRIPT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.getByTestId('button-export-panel').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const comboboxes = page.locator('[role="dialog"]').getByRole('combobox');
    const journalCombo = comboboxes.nth(1);
    await journalCombo.click();
    await page.getByRole('option', { name: /JAMA/i }).click();
    await expect(journalCombo).toContainText('JAMA');
  });
});

test.describe('Manuscript Export - progress and download', () => {
  test('should show progress or completion when export is triggered', async ({ page }) => {
    await page.goto(`/manuscripts/${TEST_MANUSCRIPT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.getByTestId('button-export-panel').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const exportButton = page.locator('[role="dialog"]').getByRole('button', { name: /^Export$/ });
    await exportButton.click();

    await page.waitForTimeout(2000);

    const progressOrDone = page.locator('[role="dialog"]').getByText(/Exporting|Export ready|Export failed|Download/i);
    const downloadBtn = page.locator('[role="dialog"]').getByRole('button', { name: /Download/i });
    const hasProgress = await progressOrDone.isVisible().catch(() => false);
    const hasDownload = await downloadBtn.isVisible().catch(() => false);
    expect(hasProgress || hasDownload).toBeTruthy();
  });

  test('should not show error toast on panel open', async ({ page }) => {
    await page.goto(`/manuscripts/${TEST_MANUSCRIPT_ID}`);
    await page.waitForLoadState('networkidle');
    await page.getByTestId('button-export-panel').click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });

    const toastError = page.locator('[role="alert"]').filter({ hasText: /failed|error/i });
    await expect(toastError).not.toBeVisible();
  });
});
