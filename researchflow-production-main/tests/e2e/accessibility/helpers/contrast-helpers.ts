/**
 * Color contrast utilities for WCAG 2.1 AA.
 * Primary contrast checks are done by axe; these helpers support custom assertions.
 */

import type { Page, Locator } from '@playwright/test';

/** WCAG 2.1 AA: 4.5:1 normal text, 3:1 large text and UI components */
export const CONTRAST_RATIOS = {
  normalText: 4.5,
  largeText: 3,
  uiComponent: 3,
} as const;

/**
 * Parse hex or rgb color to luminance components (0–1).
 * Simplified for sRGB.
 */
function parseColor(cssColor: string): { r: number; g: number; b: number } | null {
  if (cssColor.startsWith('rgb')) {
    const m = cssColor.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (m) return { r: parseInt(m[1], 10) / 255, g: parseInt(m[2], 10) / 255, b: parseInt(m[3], 10) / 255 };
  }
  if (cssColor.startsWith('#')) {
    const hex = cssColor.slice(1).replace(/^(.)(.)(.)$/, '$1$1$2$2$3$3');
    if (hex.length === 6) {
      return {
        r: parseInt(hex.slice(0, 2), 16) / 255,
        g: parseInt(hex.slice(2, 4), 16) / 255,
        b: parseInt(hex.slice(4, 6), 16) / 255,
      };
    }
  }
  return null;
}

/**
 * Relative luminance per WCAG formula.
 */
function luminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)));
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Contrast ratio between two luminances.
 */
export function contrastRatio(L1: number, L2: number): number {
  const [lighter, darker] = L1 >= L2 ? [L1, L2] : [L2, L1];
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Get computed background and color for an element and compute contrast ratio.
 * Returns null if colors cannot be resolved.
 */
export async function getElementContrastRatio(el: Locator): Promise<number | null> {
  const colors = await el.evaluate((node) => {
    const style = window.getComputedStyle(node);
    let bg = style.backgroundColor;
    let fg = style.color;
    if (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent') {
      let parent: Element | null = node.parentElement;
      while (parent && (bg === 'rgba(0, 0, 0, 0)' || bg === 'transparent')) {
        bg = window.getComputedStyle(parent).backgroundColor;
        parent = parent.parentElement;
      }
    }
    return { bg, fg };
  });
  const bgParsed = parseColor(colors.bg);
  const fgParsed = parseColor(colors.fg);
  if (!bgParsed || !fgParsed) return null;
  const L1 = luminance(bgParsed.r, bgParsed.g, bgParsed.b);
  const L2 = luminance(fgParsed.r, fgParsed.g, fgParsed.b);
  return contrastRatio(L1, L2);
}

/**
 * Assert contrast ratio meets minimum (e.g. 4.5 for normal text).
 */
export async function expectMinContrast(
  el: Locator,
  minRatio: number = CONTRAST_RATIOS.normalText
): Promise<void> {
  const ratio = await getElementContrastRatio(el);
  const { expect } = await import('@playwright/test');
  expect(ratio, `Contrast ratio should be >= ${minRatio}`).toBeGreaterThanOrEqual(minRatio);
}
