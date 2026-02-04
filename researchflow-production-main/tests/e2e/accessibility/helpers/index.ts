/**
 * Accessibility test helpers for WCAG 2.1 AA.
 */

export {
  assertNoCriticalOrSeriousViolations,
  toHaveNoCriticalA11yViolations,
  getViolationSummary,
  A11Y_THRESHOLDS,
  type AxeResults,
  type AxeViolation,
  type AxeImpact,
} from './a11y-matchers';

export {
  getInteractiveElements,
  hasAccessibleName,
  getHeadingLevels,
  validateHeadingHierarchy,
  getLandmarks,
  isLiveRegion,
  getImagesWithoutAlt,
} from './aria-helpers';

export {
  getFocusableElements,
  getTabOrder,
  hasVisibleFocusIndicator,
  expectFocusVisible,
  tabThroughAndCollectFocus,
} from './focus-helpers';

export {
  CONTRAST_RATIOS,
  contrastRatio,
  getElementContrastRatio,
  expectMinContrast,
} from './contrast-helpers';
