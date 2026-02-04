/**
 * Focus and tab order testing utilities for keyboard accessibility.
 */

import type { Page, Locator } from '@playwright/test';

const FOCUSABLE_SELECTOR =
  'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"]), [contenteditable="true"]';

/**
 * Get focusable elements in DOM order (approximation of tab order).
 */
export async function getFocusableElements(page: Page, within?: Locator): Promise<Locator> {
  const root = within ?? page.locator('body');
  return root.locator(FOCUSABLE_SELECTOR).filter({ hasNot: page.locator('[disabled], [aria-hidden="true"]') });
}

/**
 * Get tab order as array of selectors or text (for assertion).
 */
export async function getTabOrder(page: Page, within?: Locator): Promise<string[]> {
  const focusables = await getFocusableElements(page, within);
  const count = await focusables.count();
  const order: string[] = [];
  for (let i = 0; i < count; i++) {
    const el = focusables.nth(i);
    const tag = await el.evaluate((e) => e.tagName.toLowerCase());
    const role = await el.getAttribute('role');
    const name = await el.getAttribute('aria-label') ?? await el.textContent();
    order.push(`${tag}${role ? `[role=${role}]` : ''}: ${(name ?? '').slice(0, 30)}`);
  }
  return order;
}

/**
 * Check if the currently focused element has a visible focus indicator.
 */
export async function hasVisibleFocusIndicator(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el || !(el instanceof HTMLElement)) return false;
    const style = window.getComputedStyle(el);
    const outline = style.outlineWidth;
    const outlineColor = style.outlineColor;
    const boxShadow = style.boxShadow;
    const outlineOffset = style.outlineOffset;
    if (outline && outline !== '0px' && outline !== 'none' && outlineColor !== 'transparent') return true;
    if (boxShadow && boxShadow !== 'none') return true;
    return false;
  });
}

/**
 * Focus an element and assert it has visible focus ring (outline or box-shadow).
 */
export async function expectFocusVisible(page: Page, locator: Locator): Promise<void> {
  await locator.focus();
  const visible = await hasVisibleFocusIndicator(page);
  const { expect } = await import('@playwright/test');
  expect(visible, 'Focus indicator (outline/box-shadow) should be visible').toBe(true);
}

/**
 * Tab through the page and collect which element has focus after each Tab.
 */
export async function tabThroughAndCollectFocus(page: Page, maxTabs: number = 50): Promise<string[]> {
  const results: string[] = [];
  for (let i = 0; i < maxTabs; i++) {
    const activeId = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return '';
      const id = el.id ? `#${el.id}` : '';
      const tag = el.tagName.toLowerCase();
      const role = el.getAttribute('role') ?? '';
      return `${tag}${role ? `[role=${role}]` : ''}${id}`.trim();
    });
    if (results.length && results[results.length - 1] === activeId) break;
    results.push(activeId);
    await page.keyboard.press('Tab');
  }
  return results;
}
