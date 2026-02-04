/**
 * Automated accessibility scans using @axe-core/playwright.
 * WCAG 2.1 AA: 0 critical, 0 serious violations.
 */

import * as fs from 'fs';
import * as path from 'path';
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { assertNoCriticalOrSeriousViolations, getViolationSummary, A11Y_THRESHOLDS } from './helpers';
import { loginAs, setMode } from '../fixtures';
import { E2E_USERS } from '../fixtures/users.fixture';

const REPORTS_DIR = path.join(process.cwd(), 'tests', 'e2e', 'accessibility', 'reports');

const MAJOR_PAGES = [
  { path: '/', name: 'Home' },
  { path: '/demo', name: 'Demo landing' },
  { path: '/login', name: 'Login' },
  { path: '/dashboard', name: 'Dashboard', auth: true },
  { path: '/workflow', name: 'Workflow', auth: true },
  { path: '/pipeline', name: 'Pipeline', auth: true },
  { path: '/governance', name: 'Governance', auth: true },
  { path: '/manuscripts/new', name: 'Manuscript new', auth: true },
  { path: '/project/demo-project/compliance', name: 'Compliance', auth: true },
] as const;

const VIEWPORTS = [
  { width: 1280, height: 720, name: 'desktop' },
  { width: 768, height: 1024, name: 'tablet' },
  { width: 375, height: 667, name: 'mobile' },
] as const;

test.describe('Axe-core accessibility scans', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear());
  });

  for (const viewport of VIEWPORTS) {
    test.describe(`Viewport: ${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.setViewportSize(viewport);
      });

      for (const route of MAJOR_PAGES) {
        test(`${route.name} (${route.path}) has no critical/serious violations`, async ({ page }) => {
          if (route.auth) {
            await loginAs(page, E2E_USERS.ADMIN);
            await setMode(page, 'LIVE');
          }
          const response = await page.goto(route.path, { waitUntil: 'domcontentloaded' });
          if (response && !response.ok() && response.status() === 404) {
            test.skip(true, `Page ${route.path} not found`);
            return;
          }
          await page.waitForLoadState('networkidle').catch(() => {});
          const results = await new AxeBuilder({ page })
            .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
            .analyze();
          assertNoCriticalOrSeriousViolations(results, A11Y_THRESHOLDS);
        });
      }
    });
  }

  test.describe('Workflow stages', () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript(() => localStorage.clear());
      await loginAs(page, E2E_USERS.ADMIN);
      await setMode(page, 'LIVE');
      await page.goto('/workflow');
      await page.waitForLoadState('networkidle').catch(() => {});
    });

    test('workflow page has no critical/serious violations', async ({ page }) => {
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      assertNoCriticalOrSeriousViolations(results, A11Y_THRESHOLDS);
    });

    test('each stage panel (1–20) has no critical/serious violations', async ({ page }) => {
      for (let stageId = 1; stageId <= 20; stageId++) {
        const btn = page.locator(`[data-testid="button-stage-${stageId}"]`).first();
        if ((await btn.count()) === 0) continue;
        await btn.click();
        await page.waitForTimeout(300);
        const results = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
          .analyze();
        const summary = getViolationSummary(results);
        expect(
          summary.critical,
          `Stage ${stageId}: expected 0 critical violations`
        ).toBe(0);
        expect(
          summary.serious,
          `Stage ${stageId}: expected 0 serious violations`
        ).toBe(0);
      }
    });
  });

  test('generate accessibility report data', async ({ page }) => {
    const reportEntries: Array<{
      page: string;
      path: string;
      violations: number;
      critical: number;
      serious: number;
      timestamp: string;
    }> = [];
    await loginAs(page, E2E_USERS.ADMIN);
    await setMode(page, 'LIVE');
    for (const route of MAJOR_PAGES.filter((r) => r.auth)) {
      await page.goto(route.path, { waitUntil: 'domcontentloaded' });
      await page.waitForLoadState('networkidle').catch(() => {});
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      const summary = getViolationSummary(results);
      reportEntries.push({
        page: route.name,
        path: route.path,
        violations: results.violations.length,
        critical: summary.critical,
        serious: summary.serious,
        timestamp: new Date().toISOString(),
      });
    }
    expect(reportEntries.length).toBeGreaterThan(0);
    if (!fs.existsSync(REPORTS_DIR)) {
      fs.mkdirSync(REPORTS_DIR, { recursive: true });
    }
    const jsonPath = path.join(REPORTS_DIR, 'a11y-results.json');
    fs.writeFileSync(
      jsonPath,
      JSON.stringify(
        { run: new Date().toISOString(), pages: reportEntries },
        null,
        2
      ),
      'utf-8'
    );
  });
});
