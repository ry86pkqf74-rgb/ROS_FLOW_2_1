import { fileURLToPath, URL } from 'node:url';

import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: [
      'tests/unit/**/*.test.ts',
      'tests/unit/**/*.spec.ts',
      'tests/governance/**/*.test.ts',
      'tests/governance/**/*.spec.ts',
      'packages/**/src/**/__tests__/**/*.test.ts',
      'packages/**/src/**/__tests__/**/*.spec.ts',
    ],
    exclude: [
      'node_modules',
      '**/node_modules/**',
      'tests/e2e/**',
      'tests/integration/**',
      'packages/**/tests/integration/**',
      'services/web/**',
    ],
    testTimeout: 10000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
    },
  },
  resolve: {
    alias: {
      '@researchflow/core': fileURLToPath(new URL('./packages/core', import.meta.url)),
      '@researchflow/ai-router': fileURLToPath(new URL('./packages/ai-router', import.meta.url)),
      '@researchflow/phi-engine': fileURLToPath(new URL('./packages/phi-engine', import.meta.url)),
      '@packages/core': fileURLToPath(new URL('./packages/core', import.meta.url)),
      '@apps/api-node': fileURLToPath(new URL('./services/orchestrator', import.meta.url)),
      '@apps/api-node/src': fileURLToPath(new URL('./services/orchestrator/src', import.meta.url)),
    },
  },
});
