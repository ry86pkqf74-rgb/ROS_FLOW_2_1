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
});
