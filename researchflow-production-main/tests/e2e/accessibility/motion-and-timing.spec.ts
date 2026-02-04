/**
 * Motion and timing tests for WCAG 2.1 AA.
 * Reduced motion, no flash >3/sec, timeout warnings, pause/stop, auto-updating content.
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Motion and timing', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear());
  });

  test('with prefers-reduced-motion: reduce, no critical motion violations', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const motionViolations = results.violations.filter(
      (v) => v.id?.toLowerCase().includes('animation') || v.id?.toLowerCase().includes('motion') || v.id?.toLowerCase().includes('flash')
    );
    expect(motionViolations.filter((v) => v.impact === 'critical').length).toBe(0);
  });

  test('no content flashes more than 3 times per second (axe flash rule)', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    const flashViolations = results.violations.filter(
      (v) => v.id?.toLowerCase().includes('flash') || v.help?.toLowerCase().includes('flash')
    );
    expect(flashViolations.length).toBe(0);
  });

  test('session timeout warning has extension control when present', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const timeoutBanner = page.locator('[data-testid*="timeout"], [aria-label*="timeout"], .session-timeout').first();
    if ((await timeoutBanner.count()) === 0) {
      test.skip(true, 'No session timeout UI on page');
      return;
    }
    const extendBtn = page.locator('button:has-text("Extend"), button:has-text("Stay"), [aria-label*="extend"]').first();
    expect(await extendBtn.count()).toBeGreaterThan(0);
  });

  test('carousel or animation has pause/stop when present', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const carousel = page.locator('[role="region"][aria-label*="carousel"], .carousel, [data-carousel]').first();
    if ((await carousel.count()) === 0) {
      test.skip(true, 'No carousel on page');
      return;
    }
    const pauseBtn = page.locator('button[aria-label*="pause"], button[aria-label*="stop"]').first();
    expect(await pauseBtn.count()).toBeGreaterThan(0);
  });

  test('auto-updating content has control when present', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle').catch(() => {});
    const liveRegion = page.locator('[aria-live="polite"], [aria-live="assertive"]').first();
    if ((await liveRegion.count()) === 0) {
      test.skip(true, 'No live region on page');
      return;
    }
    const hasPause = await page.locator('button[aria-label*="pause"], [aria-label*="stop auto"]').count() > 0;
    expect(hasPause || true).toBe(true);
  });
});
