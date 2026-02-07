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
      'tests/integration/**/*.test.ts',
      'tests/governance/**/*.test.ts',
    ],
    exclude: [
      'node_modules',
      '**/node_modules/**',
      'tests/e2e/**',
      'services/web/**',
      'tests/integration/api-endpoints.test.ts',
      'tests/integration/artifacts.test.ts',
      'tests/integration/standby-mode.test.ts',
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
});
