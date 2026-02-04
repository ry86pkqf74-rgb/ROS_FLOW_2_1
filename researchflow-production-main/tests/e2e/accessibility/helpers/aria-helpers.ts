/**
 * ARIA and semantics testing utilities for WCAG 2.1 AA.
 * Used by screen-reader.spec and forms.spec.
 */

import type { Page, Locator } from '@playwright/test';

const INTERACTIVE_SELECTOR =
  'button, [role="button"], a[href], input, select, textarea, [role="checkbox"], [role="radio"], [role="menuitem"], [role="tab"], [contenteditable="true"]';

/**
 * Get all interactive elements in a container or the whole page.
 */
export async function getInteractiveElements(page: Page, within?: Locator): Promise<Locator> {
  const root = within ?? page.locator('body');
  return root.locator(INTERACTIVE_SELECTOR);
}

/**
 * Check that an element has an accessible name: aria-label, aria-labelledby, or visible text.
 */
export async function hasAccessibleName(el: Locator): Promise<boolean> {
  const ariaLabel = await el.getAttribute('aria-label');
  if (ariaLabel?.trim()) return true;
  const ariaLabelledby = await el.getAttribute('aria-labelledby');
  if (ariaLabelledby?.trim()) return true;
  const tagName = await el.evaluate((e) => e.tagName.toLowerCase());
  if (tagName === 'input' || tagName === 'select' || tagName === 'textarea') {
    const id = await el.getAttribute('id');
    if (id) {
      const label = await el.page().locator(`label[for="${id}"]`).first();
      if (await label.count()) return true;
    }
  }
  const text = await el.textContent();
  if (text?.trim()) return true;
  const alt = await el.getAttribute('alt');
  if (alt !== null) return true;
  return false;
}

/**
 * Get heading levels (h1–h6) in document order.
 */
export async function getHeadingLevels(page: Page, within?: Locator): Promise<number[]> {
  const root = within ?? page.locator('body');
  const headings = await root.locator('h1, h2, h3, h4, h5, h6').all();
  const levels: number[] = [];
  for (const h of headings) {
    const tag = await h.evaluate((e) => e.tagName);
    const level = parseInt(tag.replace('H', ''), 10);
    levels.push(level);
  }
  return levels;
}

/**
 * Validate heading hierarchy: no skipped levels; optionally single h1.
 */
export function validateHeadingHierarchy(levels: number[], options?: { singleH1?: boolean }): { valid: boolean; message: string } {
  const singleH1 = options?.singleH1 ?? true;
  const h1Count = levels.filter((l) => l === 1).length;
  if (singleH1 && h1Count !== 1 && levels.length > 0) {
    return { valid: false, message: `Expected single h1, found ${h1Count}` };
  }
  let prev = 0;
  for (const l of levels) {
    if (l > prev + 1) {
      return { valid: false, message: `Heading level skip: ${prev} to ${l}` };
    }
    prev = l;
  }
  return { valid: true, message: 'OK' };
}

/**
 * Check for landmark roles: main, nav, aside (or role="main", etc.).
 */
export async function getLandmarks(page: Page, within?: Locator): Promise<{ role: string; count: number }[]> {
  const root = within ?? page.locator('body');
  const mainCount = await root.locator('main').count();
  const navCount = await root.locator('nav').count();
  const asideCount = await root.locator('aside').count();
  const found: { role: string; count: number }[] = [];
  if (mainCount) found.push({ role: 'main', count: mainCount });
  if (navCount) found.push({ role: 'nav', count: navCount });
  if (asideCount) found.push({ role: 'aside', count: asideCount });
  const roleMain = await root.locator('[role="main"]').count();
  if (roleMain) found.push({ role: 'main (role)', count: roleMain });
  return found;
}

/**
 * Check if element has aria-live or is inside a live region.
 */
export async function isLiveRegion(el: Locator): Promise<boolean> {
  const live = await el.getAttribute('aria-live');
  if (live) return true;
  const parent = el.locator('xpath=ancestor::*[@aria-live]').first();
  return (await parent.count()) > 0;
}

/**
 * Get images that have no alt attribute (missing alt).
 * Empty alt or role="presentation" is valid for decorative images.
 */
export async function getImagesWithoutAlt(page: Page, within?: Locator): Promise<Locator[]> {
  const root = within ?? page.locator('body');
  const imgs = await root.locator('img').all();
  const missing: Locator[] = [];
  for (const img of imgs) {
    const alt = await img.getAttribute('alt');
    const role = await img.getAttribute('role');
    if (role === 'presentation') continue;
    if (alt === null) missing.push(img);
  }
  return missing;
}
