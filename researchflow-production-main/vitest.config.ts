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
      // Exclude integration and governance tests to make test:unit truly unit-only
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
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
    },
  },
});
