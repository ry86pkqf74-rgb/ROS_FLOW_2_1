/**
 * Phase 8: Playwright E2E Test Configuration
 *
 * Configuration for ResearchFlow E2E tests:
 * - Base URL and API URL setup
 * - Browser launch options
 * - Test timeout and retry settings
 * - Screenshot and video capture
 * - Trace collection for debugging
 */

import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:5173';
const apiURL = process.env.API_URL || 'http://localhost:3001';

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.ts',
  
  // Test configuration
  timeout: 60000, // 60s per test
  retries: 1,
  workers: process.env.CI ? 1 : 4,

  // Output configuration
  outputDir: './test-results',
  snapshotDir: './screenshots',

  // Reporting
  reporter: [
    ['html', { outputFolder: './html-report' }],
    ['json', { outputFile: './test-results.json' }],
    ['junit', { outputFile: './junit.xml' }],
    ['list'],
  ],

  // Shared settings
  use: {
    // Base URL for navigation
    baseURL,
    
    // Network
    httpCredentials: undefined,
    
    // Recordings
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',

    // Action timeout
    actionTimeout: 10000,
    navigationTimeout: 30000,

    // Extra HTTP headers
    extraHTTPHeaders: {
      'X-Test-Environment': 'playwright',
      // Dev auth header for E2E tests (requires ENABLE_DEV_AUTH=true)
      'X-Dev-User-Id': process.env.E2E_USER_ID || 'e2e-user-001',
    },
  },

  // WebServer configuration
  webServer: {
    command: 'npm run dev',
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },

  // Projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile testing
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // Global setup/teardown
  globalSetup: undefined,
  globalTeardown: undefined,

  // Forbid only
  forbidOnly: !!process.env.CI,

  // Expect configuration
  expect: {
    timeout: 5000,
  },
});
