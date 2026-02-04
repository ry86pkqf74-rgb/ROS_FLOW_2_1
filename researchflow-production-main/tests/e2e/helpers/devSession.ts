/**
 * Dev Session Helper for E2E Tests
 * 
 * Provides utilities for managing dev authentication sessions in Playwright tests.
 * Works with the /api/dev-auth endpoints and X-Dev-User-Id header authentication.
 */

import { Page, APIRequestContext, expect } from '@playwright/test';

export interface DevUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

export interface DevSession {
  sessionId: string;
  userId: string;
  email: string;
  name: string;
  role: string;
  expiresAt: string;
}

// Default test users
export const TEST_USERS = {
  default: {
    id: 'e2e-user-001',
    email: 'e2e-test@researchflow.local',
    name: 'E2E Test User',
    role: 'user'
  },
  admin: {
    id: 'e2e-user-002',
    email: 'e2e-admin@researchflow.local',
    name: 'E2E Admin User',
    role: 'admin'
  },
  researcher: {
    id: 'e2e-user-003',
    email: 'e2e-researcher@researchflow.local',
    name: 'E2E Researcher',
    role: 'researcher'
  }
} as const;

// Test project IDs
export const TEST_PROJECTS = {
  demo: 'e2e-project-demo',
  live: 'e2e-project-live',
  offline: 'e2e-project-offline'
} as const;

/**
 * Create a dev session via API
 */
export async function createDevSession(
  request: APIRequestContext,
  user: DevUser = TEST_USERS.default
): Promise<DevSession> {
  const response = await request.post('/api/dev-auth/session', {
    data: user
  });

  expect(response.ok()).toBeTruthy();
  return await response.json();
}

/**
 * Delete a dev session via API
 */
export async function deleteDevSession(
  request: APIRequestContext,
  sessionId: string
): Promise<void> {
  const response = await request.delete(`/api/dev-auth/session/${sessionId}`);
  expect(response.ok()).toBeTruthy();
}

/**
 * Validate a dev session via API
 */
export async function validateDevSession(
  request: APIRequestContext,
  sessionId: string
): Promise<boolean> {
  const response = await request.get(`/api/dev-auth/session/${sessionId}`);
  if (!response.ok()) return false;
  
  const data = await response.json();
  return data.valid === true;
}

/**
 * Get dev auth status
 */
export async function getDevAuthStatus(
  request: APIRequestContext
): Promise<{ enabled: boolean; environment: string; governanceMode: string }> {
  const response = await request.get('/api/dev-auth/status');
  expect(response.ok()).toBeTruthy();
  return await response.json();
}

/**
 * Setup page with dev user authentication
 * Sets the X-Dev-User-Id header for all subsequent requests
 */
export async function setupDevAuth(
  page: Page,
  userId: string = TEST_USERS.default.id
): Promise<void> {
  await page.setExtraHTTPHeaders({
    'X-Dev-User-Id': userId
  });
}

/**
 * Clear dev auth from page
 */
export async function clearDevAuth(page: Page): Promise<void> {
  await page.setExtraHTTPHeaders({});
}

/**
 * Login as dev user and navigate to app
 */
export async function loginAsDevUser(
  page: Page,
  user: DevUser = TEST_USERS.default,
  navigateTo: string = '/'
): Promise<void> {
  await setupDevAuth(page, user.id);
  await page.goto(navigateTo);
  
  // Wait for app to be ready
  await page.waitForLoadState('networkidle');
}

/**
 * Switch governance mode for testing
 */
export async function setGovernanceMode(
  page: Page,
  mode: 'DEMO' | 'LIVE' | 'STANDBY'
): Promise<void> {
  // Store mode in localStorage for the app to pick up
  await page.evaluate((governanceMode) => {
    localStorage.setItem('governanceMode', governanceMode);
  }, mode);
}

/**
 * Get current governance mode
 */
export async function getGovernanceMode(page: Page): Promise<string> {
  return await page.evaluate(() => {
    return localStorage.getItem('governanceMode') || 'DEMO';
  });
}

/**
 * Wait for workflow pipeline to be ready
 * Uses stable selectors from workflow-pipeline.tsx
 */
export async function waitForWorkflowReady(page: Page): Promise<void> {
  await page.waitForSelector('[data-testid="accordion-workflow-groups"]', {
    state: 'visible',
    timeout: 10000
  });
}

/**
 * Upload file to the file input
 */
export async function uploadFile(
  page: Page,
  filePath: string
): Promise<void> {
  const fileInput = page.locator('[data-testid="input-file-upload"]');
  await fileInput.setInputFiles(filePath);
}

/**
 * Execute a workflow stage
 */
export async function executeStage(
  page: Page,
  stageName?: string
): Promise<void> {
  const executeButton = stageName
    ? page.locator(`[data-testid="button-execute-stage"][data-stage="${stageName}"]`)
    : page.locator('[data-testid="button-execute-stage"]').first();
  
  await executeButton.click();
}

/**
 * Wait for stage execution results
 */
export async function waitForStageResults(
  page: Page,
  timeout: number = 30000
): Promise<void> {
  await page.waitForSelector('[data-testid="section-execution-results"]', {
    state: 'visible',
    timeout
  });
}

/**
 * Get stage outputs
 */
export async function getStageOutputs(page: Page): Promise<string[]> {
  const outputs = await page.locator('[data-testid="list-stage-outputs"] li').allTextContents();
  return outputs;
}

/**
 * Get research overview text
 */
export async function getResearchOverview(page: Page): Promise<string> {
  const textarea = page.locator('[data-testid="textarea-research-overview"]');
  return await textarea.inputValue();
}

/**
 * Assert dev auth is enabled in test environment
 */
export async function assertDevAuthEnabled(
  request: APIRequestContext
): Promise<void> {
  const status = await getDevAuthStatus(request);
  expect(status.enabled).toBeTruthy();
  expect(status.environment).not.toBe('production');
}

/**
 * Fixture-style helper for managing dev session lifecycle
 */
export class DevSessionManager {
  private sessions: Map<string, DevSession> = new Map();
  private request: APIRequestContext;

  constructor(request: APIRequestContext) {
    this.request = request;
  }

  async create(user: DevUser = TEST_USERS.default): Promise<DevSession> {
    const session = await createDevSession(this.request, user);
    this.sessions.set(session.sessionId, session);
    return session;
  }

  async cleanup(): Promise<void> {
    for (const [sessionId] of this.sessions) {
      try {
        await deleteDevSession(this.request, sessionId);
      } catch (e) {
        // Ignore cleanup errors
      }
    }
    this.sessions.clear();
  }

  getSession(sessionId: string): DevSession | undefined {
    return this.sessions.get(sessionId);
  }
}
