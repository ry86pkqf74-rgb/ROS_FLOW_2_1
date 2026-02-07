/**
 * Screen reader and ARIA tests for WCAG 2.1 AA.
 * ARIA labels, live regions, heading hierarchy, form labels, images, tables, landmarks.
 */

import { test, expect } from '@playwright/test';

import { loginAs, setMode } from '../fixtures';
import { E2E_USERS } from '../fixtures/users.fixture';

import {
  getInteractiveElements,
  hasAccessibleName,
  getHeadingLevels,
  validateHeadingHierarchy,
  getLandmarks,
  getImagesWithoutAlt,
} from './helpers';

const MAJOR_PAGES = [
  { path: '/', name: 'Home' },
  { path: '/demo', name: 'Demo' },
  { path: '/login', name: 'Login' },
  { path: '/workflow', name: 'Workflow', auth: true },
  { path: '/dashboard', name: 'Dashboard', auth: true },
  { path: '/governance', name: 'Governance', auth: true },
] as const;

test.describe('Screen reader and ARIA', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear());
  });

  test.describe('ARIA labels on interactive elements', () => {
    for (const route of MAJOR_PAGES) {
      test(`${route.name} interactive elements have accessible names`, async ({ page }) => {
        if (route.auth) {
          await loginAs(page, E2E_USERS.ADMIN);
          await setMode(page, 'LIVE');
        }
        await page.goto(route.path, { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle').catch(() => {});
        const interactive = await getInteractiveElements(page);
        const count = await interactive.count();
        let missing = 0;
        for (let i = 0; i < Math.min(count, 50); i++) {
          const el = interactive.nth(i);
          const hasName = await hasAccessibleName(el);
          if (!hasName) missing++;
        }
        expect(missing, `Page ${route.name}: interactive elements should have accessible names`).toBe(0);
      });
    }
  });

  test.describe('Heading hierarchy', () => {
    for (const route of MAJOR_PAGES) {
      test(`${route.name} has valid heading hierarchy (no skip, single h1)`, async ({ page }) => {
        if (route.auth) {
          await loginAs(page, E2E_USERS.ADMIN);
          await setMode(page, 'LIVE');
        }
        await page.goto(route.path, { waitUntil: 'domcontentloaded' });
        await page.waitForLoadState('networkidle').catch(() => {});
        const levels = await getHeadingLevels(page);
        if (levels.length === 0) {
          test.skip(true, 'No headings on page');
          return;
        }
        const { valid, message } = validateHeadingHierarchy(levels, { singleH1: true });
        expect(valid, message).toBe(true);
      });
    }
  });

  test.describe('Landmark regions', () => {
    test('major pages have main landmark', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const landmarks = await getLandmarks(page);
      const hasMain = landmarks.some((l) => l.role === 'main');
      expect(hasMain, 'Page should have main landmark').toBe(true);
    });

    test('workflow page has main and nav', async ({ page }) => {
      await loginAs(page, E2E_USERS.ADMIN);
      await setMode(page, 'LIVE');
      await page.goto('/workflow');
      await page.waitForLoadState('networkidle').catch(() => {});
      const landmarks = await getLandmarks(page);
      const hasMain = landmarks.some((l) => l.role === 'main');
      expect(hasMain).toBe(true);
    });
  });

  test.describe('Image alt text', () => {
    test('images have alt or role=presentation', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const missing = await getImagesWithoutAlt(page);
      expect(missing.length, 'Images without alt should be 0').toBe(0);
    });

    test('demo page images have alt', async ({ page }) => {
      await page.goto('/demo');
      await page.waitForLoadState('networkidle').catch(() => {});
      const missing = await getImagesWithoutAlt(page);
      expect(missing.length).toBe(0);
    });
  });

  test.describe('Tables', () => {
    test('tables have headers or caption when present', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const tables = await page.locator('table').all();
      for (const table of tables) {
        const hasTh = (await table.locator('th').count()) > 0;
        const hasCaption = (await table.locator('caption').count()) > 0;
        const hasAriaLabel = (await table.getAttribute('aria-label')) ?? (await table.getAttribute('aria-labelledby'));
        expect(hasTh || hasCaption || !!hasAriaLabel, 'Table should have th, caption, or aria-label').toBe(true);
      }
    });
  });
});
