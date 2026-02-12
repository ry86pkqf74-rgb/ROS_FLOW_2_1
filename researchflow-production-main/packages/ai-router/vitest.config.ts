/**
 * Phase 8: Vitest Configuration for AI Router
 *
 * Configuration for Jest/Vitest tests:
 * - Test file discovery
 * - Coverage settings
 * - Timeout configuration
 * - Mock setup
 *
 * Note: Module resolution aliases are handled by the root vitest.config.ts
 * via vite-tsconfig-paths plugin.
 */

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.spec.ts', 'src/__tests__/**/*.ts'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
    globals: true,
    setupFiles: [],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov', 'json-summary'],
      exclude: [
        'node_modules/',
        'src/__tests__/',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
    testTimeout: 30000,
    hookTimeout: 30000,
    bail: 0,
    reporters: ['default', 'html'],
    outputFile: {
      html: './test-report.html',
    },
    mockReset: true,
    restoreMocks: true,
    clearMocks: true,
    snapshotFormat: {
      printBasicPrototype: true,
    },
  },
});
