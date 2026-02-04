import { test, expect } from '@playwright/test';

test.describe('Docker Smoke Tests', () => {
  test.describe.configure({ mode: 'serial' });

  test('orchestrator health check', async ({ request }) => {
    const response = await request.get('http://localhost:3001/health');
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe('ok');
  });

  test('worker health check', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('web app loads', async ({ page }) => {
    await page.goto('http://localhost:5173');
    await expect(page).toHaveTitle(/ResearchFlow|ResearchOps/);
  });

  test('orchestrator API responds', async ({ request }) => {
    const response = await request.get('http://localhost:3001/api/stages');
    expect(response.ok()).toBeTruthy();
  });

  test('worker API responds', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/agents');
    expect(response.ok()).toBeTruthy();
  });

  test('orchestrator can reach worker', async ({ request }) => {
    const response = await request.get('http://localhost:3001/api/health/worker');
    expect(response.ok()).toBeTruthy();
  });

  test('manuscript generation endpoint exists', async ({ request }) => {
    const response = await request.post('http://localhost:3001/api/manuscript/generate/full', {
      data: { test: true },
    });
    expect(response.status()).not.toBe(404);
  });

  test('notifications endpoint exists', async ({ request }) => {
    const response = await request.get('http://localhost:3001/api/notifications');
    expect(response.status()).not.toBe(500);
  });

  test('governance mode is set', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    const body = await response.json();
    expect(body.governance_mode).toBeDefined();
  });
});
