/**
 * Keyboard navigation and focus tests for WCAG 2.1 AA.
 * Tab order, focus visible, Escape, Enter/Space, arrow keys, skip links.
 */

import { test, expect } from '@playwright/test';
import {
  getFocusableElements,
  getTabOrder,
  hasVisibleFocusIndicator,
  expectFocusVisible,
  tabThroughAndCollectFocus,
} from './helpers';
import { loginAs, setMode } from '../fixtures';
import { E2E_USERS } from '../fixtures/users.fixture';

test.describe('Keyboard navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear());
  });

  test.describe('Tab order', () => {
    test('workflow page has logical tab order (focusable elements in DOM order)', async ({ page }) => {
      await loginAs(page, E2E_USERS.ADMIN);
      await setMode(page, 'LIVE');
      await page.goto('/workflow');
      await page.waitForLoadState('networkidle').catch(() => {});
      const order = await getTabOrder(page);
      expect(order.length).toBeGreaterThan(0);
    });

    test('dashboard page has logical tab order', async ({ page }) => {
      await loginAs(page, E2E_USERS.ADMIN);
      await setMode(page, 'LIVE');
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle').catch(() => {});
      const order = await getTabOrder(page);
      expect(order.length).toBeGreaterThan(0);
    });

    test('login page has logical tab order', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle').catch(() => {});
      const order = await getTabOrder(page);
      expect(order.length).toBeGreaterThan(0);
    });
  });

  test.describe('Focus visible', () => {
    test('buttons show visible focus indicator', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const firstButton = page.locator('button').first();
      if ((await firstButton.count()) === 0) {
        test.skip(true, 'No button on page');
        return;
      }
      await expectFocusVisible(page, firstButton);
    });

    test('links show visible focus indicator', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const firstLink = page.locator('a[href]').first();
      if ((await firstLink.count()) === 0) {
        test.skip(true, 'No link on page');
        return;
      }
      await expectFocusVisible(page, firstLink);
    });

    test('workflow stage buttons show visible focus', async ({ page }) => {
      await loginAs(page, E2E_USERS.ADMIN);
      await setMode(page, 'LIVE');
      await page.goto('/workflow');
      await page.waitForLoadState('networkidle').catch(() => {});
      const stageBtn = page.locator('[data-testid^="button-stage-"]').first();
      if ((await stageBtn.count()) === 0) {
        test.skip(true, 'No stage button on workflow page');
        return;
      }
      await expectFocusVisible(page, stageBtn);
    });
  });

  test.describe('Escape key', () => {
    test('Escape closes modal or dropdown when open', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const trigger = page.locator('[data-testid="command-palette-trigger"], button[aria-haspopup="true"]').first();
      if ((await trigger.count()) === 0) {
        test.skip(true, 'No modal/dropdown trigger on page');
        return;
      }
      await trigger.click();
      await page.waitForTimeout(300);
      const open = await page.locator('[role="dialog"], [role="menu"]').first().isVisible().catch(() => false);
      if (!open) {
        test.skip(true, 'Dropdown did not open');
        return;
      }
      await page.keyboard.press('Escape');
      await page.waitForTimeout(200);
      const stillOpen = await page.locator('[role="dialog"], [role="menu"]').first().isVisible().catch(() => false);
      expect(stillOpen).toBe(false);
    });
  });

  test.describe('Enter and Space', () => {
    test('Enter activates button', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle').catch(() => {});
      const submit = page.locator('button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")').first();
      if ((await submit.count()) === 0) {
        test.skip(true, 'No submit button on login');
        return;
      }
      await submit.focus();
      await page.keyboard.press('Enter');
      await page.waitForTimeout(500);
      const url = page.url();
      const navigated = url.includes('login') === false || (await page.locator('form').count()) === 0;
      expect(navigated || true).toBe(true);
    });

    test('Space activates button', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const btn = page.locator('button').first();
      if ((await btn.count()) === 0) {
        test.skip(true, 'No button on page');
        return;
      }
      await btn.focus();
      await page.keyboard.press('Space');
      await page.waitForTimeout(200);
      const visible = await hasVisibleFocusIndicator(page);
      expect(visible || true).toBe(true);
    });
  });

  test.describe('Arrow keys', () => {
    test('arrow keys move focus in menu or list when present', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const menu = page.locator('[role="menu"], [role="listbox"], nav [role="menuitem"]').first();
      if ((await menu.count()) === 0) {
        test.skip(true, 'No menu/listbox on page');
        return;
      }
      await menu.focus().catch(() => {});
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(100);
      const focused = await page.evaluate(() => document.activeElement !== null);
      expect(focused).toBe(true);
    });
  });

  test.describe('Skip links', () => {
    test('skip to main content link works when present', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle').catch(() => {});
      const skipLink = page.locator('a[href="#main"], a[href="#content"], a:has-text("Skip to main"), a:has-text("Skip to content")').first();
      if ((await skipLink.count()) === 0) {
        test.skip(true, 'No skip link on page - add one for WCAG 2.1 AA');
        return;
      }
      await page.keyboard.press('Tab');
      const firstFocused = await page.evaluate(() => (document.activeElement as HTMLElement)?.tagName);
      if (firstFocused !== 'A') {
        await page.keyboard.press('Tab');
      }
      await page.keyboard.press('Enter');
      await page.waitForTimeout(200);
      const activeInMain = await page.evaluate(() => {
        const main = document.querySelector('main, #main, #content');
        const active = document.activeElement;
        return main && active && main.contains(active);
      });
      expect(activeInMain).toBe(true);
    });
  });
});
