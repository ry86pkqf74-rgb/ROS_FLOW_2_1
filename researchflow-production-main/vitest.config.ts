import { fileURLToPath, URL } from 'node:url';

import { defineConfig } from 'vitest/config';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [
    tsconfigPaths({
      root: '.',
      projects: ['./tsconfig.json'],
    }),
  ],
  resolve: {
    alias: {
      '@apps/api-node/src': fileURLToPath(
        new URL('./services/orchestrator/src', import.meta.url)
      ),
      '@apps/api-node': fileURLToPath(
        new URL('./services/orchestrator', import.meta.url)
      ),
    },
  },
  test: {
    globals: true,
    environment: 'node',
    include: [
      'packages/**/*.test.ts',
      'tests/unit/**/*.test.ts',
      'services/orchestrator/src/**/*.test.ts',
      'services/orchestrator/src/**/*.test.tsx',
    ],
    exclude: [
      'node_modules',
      '**/node_modules/**',
      'tests/e2e/**',
      'services/web/**',
      'tests/integration/**',
      'tests/governance/**',
      'packages/**/tests/integration/**',
      'packages/**/__tests__/integration/**',
      'services/**/tests/integration/**',
      'services/**/__tests__/integration/**',
    ],
    testTimeout: 10000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
});
