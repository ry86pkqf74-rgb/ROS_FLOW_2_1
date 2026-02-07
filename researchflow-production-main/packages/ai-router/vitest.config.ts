/**
 * Phase 8: Vitest Configuration for AI Router
 *
 * Configuration for Jest/Vitest tests:
 * - Test file discovery
 * - Module resolution
 * - Coverage settings
 * - Timeout configuration
 * - Mock setup
 */

import path from 'path';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Environment
    environment: 'node',
    
    // Test file patterns
    include: ['src/**/*.test.ts', 'src/**/*.spec.ts', 'src/__tests__/**/*.ts'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],

    // Globals
    globals: true,

    // Setup files
    setupFiles: [],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov', 'json-summary'],
      exclude: [
        'node_modules/',
        'src/__tests__/',
      ],
      lines: 80,
      functions: 80,
      branches: 75,
      statements: 80,
    },

    // Test timeout (30 seconds)
    testTimeout: 30000,
    hookTimeout: 30000,

    // Bail on first failure
    bail: 0,

    // Include source maps
    sourcemap: true,

    // Reporter
    reporter: ['default', 'html'],
    outputFile: {
      html: './test-report.html',
    },

    // Mock configuration
    mockReset: true,
    restoreMocks: true,
    clearMocks: true,

    // Snapshot settings
    snapshotFormat: {
      printBasicPrototype: true,
    },
  },

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
