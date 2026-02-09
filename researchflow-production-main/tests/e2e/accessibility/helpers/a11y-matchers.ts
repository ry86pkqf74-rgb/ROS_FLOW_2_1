/**
 * Custom accessibility assertions for Playwright.
 * Wraps axe results and DOM checks for WCAG 2.1 AA compliance.
 */

import type { Result as AxeResult } from 'axe-core';
import { expect } from '@playwright/test';

export type AxeImpact = 'critical' | 'serious' | 'moderate' | 'minor';

export interface AxeViolation {
  id: string;
  impact?: AxeImpact;
  description: string;
  help: string;
  helpUrl: string;
  nodes: Array<{ html: string; target: string[] }>;
}

export interface AxeResults {
  violations: AxeViolation[];
  passes: AxeResult[];
  incomplete: AxeResult[];
  inapplicable: AxeResult[];
}

/** Thresholds: 0 critical, 0 serious per WCAG 2.1 AA */
export const A11Y_THRESHOLDS = {
  critical: 0,
  serious: 0,
} as const;

/**
 * Assert no critical or serious axe violations.
 * Use after axe.run() or AxeBuilder.analyze().
 */
export function assertNoCriticalOrSeriousViolations(
  results: AxeResults,
  thresholds: { critical: number; serious: number } = A11Y_THRESHOLDS
): void {
  const critical = results.violations.filter((v) => v.impact === 'critical');
  const serious = results.violations.filter((v) => v.impact === 'serious');
  if (critical.length > thresholds.critical) {
    const msg = critical.map((v) => `${v.id}: ${v.help}`).join('; ');
    expect(critical.length, `Critical violations: ${msg}`).toBeLessThanOrEqual(thresholds.critical);
  }
  if (serious.length > thresholds.serious) {
    const msg = serious.map((v) => `${v.id}: ${v.help}`).join('; ');
    expect(serious.length, `Serious violations: ${msg}`).toBeLessThanOrEqual(thresholds.serious);
  }
}

/**
 * Custom matcher: expect(results).toHaveNoCriticalA11yViolations()
 * Extend expect in spec or global setup if needed.
 */
export function toHaveNoCriticalA11yViolations(results: AxeResults): { pass: boolean; message: () => string } {
  const critical = results.violations.filter((v) => v.impact === 'critical');
  const serious = results.violations.filter((v) => v.impact === 'serious');
  const pass = critical.length <= A11Y_THRESHOLDS.critical && serious.length <= A11Y_THRESHOLDS.serious;
  const message = () =>
    pass
      ? 'Expected critical/serious violations'
      : `Found ${critical.length} critical, ${serious.length} serious: ${[...critical, ...serious].map((v) => v.help).join('; ')}`;
  return { pass, message };
}

/**
 * Get violation summary for reporting.
 */
export function getViolationSummary(results: AxeResults): { critical: number; serious: number; violations: AxeViolation[] } {
  const critical = results.violations.filter((v) => v.impact === 'critical');
  const serious = results.violations.filter((v) => v.impact === 'serious');
  return {
    critical: critical.length,
    serious: serious.length,
    violations: results.violations,
  };
}
