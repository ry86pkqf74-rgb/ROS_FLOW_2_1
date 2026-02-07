/**
 * Color contrast tests for WCAG 2.1 AA.
 * Text 4.5:1 / large 3:1, UI 3:1, focus indicator, color-only info, dark mode.
 */

import AxeBuilder from '@axe-core/playwright';
import { test, expect } from '@playwright/test';

import { loginAs, setMode } from '../fixtures';
import { E2E_USERS } from '../fixtures/users.fixture';

test.describe('Color contrast', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear());
  });

  test('axe color-contrast rule passes on home page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const contrastViolations = results.violations.filter((v) => v.id === 'color-contrast');
    expect(contrastViolations.length, 'No color-contrast violations').toBe(0);
  });

  test('axe color-contrast rule passes on login page', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle').catch(() => {});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const contrastViolations = results.violations.filter((v) => v.id === 'color-contrast');
    expect(contrastViolations.length).toBe(0);
  });

  test('workflow page passes color-contrast', async ({ page }) => {
    await loginAs(page, E2E_USERS.ADMIN);
    await setMode(page, 'LIVE');
    await page.goto('/workflow');
    await page.waitForLoadState('networkidle').catch(() => {});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const contrastViolations = results.violations.filter((v) => v.id === 'color-contrast');
    expect(contrastViolations.length).toBe(0);
  });

  test('focused element has visible focus indicator (contrast)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const btn = page.locator('button').first();
    if ((await btn.count()) === 0) {
      test.skip(true, 'No button on page');
      return;
    }
    await btn.focus();
    const hasOutline = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      if (!el) return false;
      const s = window.getComputedStyle(el);
      return (
        (s.outlineWidth && s.outlineWidth !== '0px') ||
        (s.boxShadow && s.boxShadow !== 'none')
      );
    });
    expect(hasOutline).toBe(true);
  });

  test('color is not the only means of conveying information (axe)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const colorOnly = results.violations.filter((v) => v.id === 'color-contrast' || v.id.includes('color'));
    const infoConveyed = results.violations.filter((v) => v.help?.toLowerCase().includes('color') && v.help?.toLowerCase().includes('only'));
    expect(infoConveyed.length).toBe(0);
  });

  test('dark mode contrast when theme is dark', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const darkToggle = page.locator('[data-testid="theme-toggle"], button:has-text("Dark"), [aria-label*="dark"]').first();
    if ((await darkToggle.count()) === 0) {
      test.skip(true, 'No dark mode toggle on page');
      return;
    }
    await darkToggle.click();
    await page.waitForTimeout(500);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const contrastViolations = results.violations.filter((v) => v.id === 'color-contrast');
    expect(contrastViolations.length).toBe(0);
  });
});
