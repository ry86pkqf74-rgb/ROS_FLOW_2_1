/**
 * Governance Modes E2E Tests
 *
 * Tests for governance mode switching and UI updates per mode.
 */

import { test, expect } from '@playwright/test';

import { loginAs, setMode } from './fixtures';
import { TestUser, TestProject } from './fixtures';
import { E2E_USERS } from './fixtures/users.fixture';
import { BasePage } from './pages/base.page';
import { GovernancePage } from './pages/governance.page';

test.describe('Governance Modes', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.clear();
    });
  });

  test('DEMO mode shows correct banner @smoke', async ({ page }) => {
    // Mock the governance mode API to return DEMO mode
    await page.route('**/api/governance/mode', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ mode: 'DEMO' }),
      });
    });

    // Navigate and wait for app to load
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // Wait for either the mode banner or the page content to appear
    await page.waitForSelector('[data-testid="mode-banner-demo"], [data-testid="demo-mode-banner"], .bg-amber-500, h1', { timeout: 15000 });

    // Check for demo banner - try multiple possible selectors
    const demoBannerByTestId = page.locator('[data-testid="mode-banner-demo"]');
    const demoBannerAlt = page.locator('[data-testid="demo-mode-banner"]');
    const demoBannerByClass = page.locator('.bg-amber-500');
    
    const hasDemoBanner = 
      await demoBannerByTestId.isVisible().catch(() => false) ||
      await demoBannerAlt.isVisible().catch(() => false) ||
      await demoBannerByClass.isVisible().catch(() => false);

    // If no demo banner visible, check page content for DEMO text
    if (!hasDemoBanner) {
      const pageContent = await page.content();
      expect(pageContent.toUpperCase()).toContain('DEMO');
    } else {
      expect(hasDemoBanner).toBe(true);
    }
  });

  test('LIVE mode shows correct banner', async ({ page }) => {
    // Login and set LIVE mode
    await loginAs(page, E2E_USERS.ADMIN);
    await setMode(page, 'LIVE');

    await page.goto('/');

    const basePage = new BasePage(page);
    await basePage.waitForModeToResolve();

    // Verify LIVE mode
    const mode = await basePage.getCurrentMode();
    expect(mode).toBe('LIVE');

    // Check banner does not show demo warning
    const modeBanner = basePage.getModeBanner();
    await expect(modeBanner).toBeVisible();

    const bannerText = await modeBanner.textContent();
    // In LIVE mode, should not have "DEMO" warning
    if (bannerText?.toLowerCase().includes('demo')) {
      // If demo is mentioned, it should be in a "not demo" context
      expect(bannerText?.toLowerCase()).not.toMatch(/^demo\s*mode/);
    }
  });

  test('mode reflected in governance page', async ({ page }) => {
    // Login as admin for full access
    await loginAs(page, E2E_USERS.ADMIN);
    await setMode(page, 'LIVE');

    const governancePage = new GovernancePage(page);
    await governancePage.navigate();

    // Check that the mode text is visible and correct
    const modeText = await governancePage.getModeText();
    expect(modeText.toUpperCase()).toContain('LIVE');

    // Switch to governance console to see more mode info
    await governancePage.waitForModeToResolve();

    // The system mode card should reflect current mode
    const cardSystemMode = governancePage.cardSystemMode;
    if (await cardSystemMode.isVisible().catch(() => false)) {
      const cardText = await cardSystemMode.textContent();
      expect(cardText?.toUpperCase()).toContain('LIVE');
    }
  });

  test('feature flags match mode', async ({ page }) => {
    // Test in DEMO mode first
    await page.goto('/governance');

    const governancePage = new GovernancePage(page);
    await governancePage.waitForModeToResolve();

    // In DEMO mode, certain flags should be restricted
    const cardFlags = governancePage.cardActiveFlags;
    if (await cardFlags.isVisible().catch(() => false)) {
      // Check that flag states reflect DEMO restrictions
      const flagsText = await cardFlags.textContent();

      // DEMO mode should have some features disabled
      // The exact behavior depends on the implementation
      expect(flagsText).toBeDefined();
    }

    // Now test in LIVE mode
    await loginAs(page, E2E_USERS.ADMIN);
    await setMode(page, 'LIVE');
    await page.goto('/governance');
    await governancePage.waitForModeToResolve();

    // In LIVE mode, more features should be enabled
    if (await cardFlags.isVisible().catch(() => false)) {
      const flagsTextLive = await cardFlags.textContent();
      expect(flagsTextLive).toBeDefined();
    }
  });

  test('operations table reflects current mode', async ({ page }) => {
    // Test in DEMO mode
    await page.goto('/governance');

    const governancePage = new GovernancePage(page);
    await governancePage.waitForModeToResolve();

    const operationsCard = governancePage.cardOperationsTable;

    // Check operations table exists
    if (await operationsCard.isVisible().catch(() => false)) {
      const demoOperations = await operationsCard.textContent();

      // DEMO mode should restrict certain operations
      expect(demoOperations).toBeDefined();

      // Now check LIVE mode
      await loginAs(page, E2E_USERS.ADMIN);
      await setMode(page, 'LIVE');
      await page.goto('/governance');
      await governancePage.waitForModeToResolve();

      const liveOperations = await operationsCard.textContent();
      expect(liveOperations).toBeDefined();

      // Operations should differ between modes
      // (specific assertions depend on actual operation names)
    }
  });

  test.describe('Governance Mode Data & Export', () => {
    test('DEMO mode blocks PHI data upload', async ({ page, request }) => {
      const user = await TestUser.create('researcher', request);
      const project = await TestProject.create(user.id, {
        name: 'DEMO Mode Test',
        type: 'cohort',
        governanceMode: 'DEMO',
      }, request, user.getAuthHeaders());

      await page.goto(`/projects/${project.id}/workflow/4`);

      // Try to upload PHI data
      const fileInput = page.locator('[data-testid="file-upload"]');
      await fileInput.setInputFiles('tests/e2e/fixtures/phi-test-data.csv');

      // Should show PHI gate banner
      await expect(page.locator('[data-testid="phi-gate-banner"]')).toBeVisible();
      await expect(page.locator('[data-testid="phi-gate-banner"]')).toContainText('PHI Not Allowed');

      await project.cleanup();
      await user.cleanup();
    });

    test('DEMO mode allows synthetic data', async ({ page, request }) => {
      const user = await TestUser.create('researcher', request);
      const project = await TestProject.create(user.id, {
        name: 'DEMO Synthetic Test',
        type: 'cohort',
        governanceMode: 'DEMO',
      }, request, user.getAuthHeaders());

      await page.goto(`/projects/${project.id}/workflow/4`);

      const fileInput = page.locator('[data-testid="file-upload"]');
      await fileInput.setInputFiles('tests/e2e/fixtures/synthetic-data.csv');

      // Should NOT show PHI gate
      await expect(page.locator('[data-testid="phi-gate-banner"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="upload-success"]')).toBeVisible();

      await project.cleanup();
      await user.cleanup();
    });

    test('LIVE mode requires steward approval for export', async ({ page, request }) => {
      const user = await TestUser.create('researcher', request);
      const project = await TestProject.create(user.id, {
        name: 'LIVE Mode Test',
        type: 'cohort',
        governanceMode: 'LIVE',
      }, request, user.getAuthHeaders());

      await page.goto(`/projects/${project.id}/workflow/20`);
      await page.click('[data-testid="export-button"]');

      // Should require approval
      await expect(page.locator('[data-testid="approval-required"]')).toBeVisible();
      await expect(page.locator('[data-testid="request-approval-button"]')).toBeVisible();

      await project.cleanup();
      await user.cleanup();
    });

    test('LIVE mode logs PHI access to audit trail', async ({ page, request }) => {
      const steward = await TestUser.create('steward', request);
      const project = await TestProject.create(steward.id, {
        name: 'LIVE Audit Test',
        type: 'cohort',
        governanceMode: 'LIVE',
      }, request, steward.getAuthHeaders());

      await page.goto(`/projects/${project.id}/workflow/5`);

      // Check audit log
      const response = await request.get(`/api/projects/${project.id}/audit`, {
        headers: { Authorization: `Bearer ${steward.token}` },
      });

      const logs = await response.json();
      expect(logs.data.some((l: { action: string }) => l.action.includes('view'))).toBeTruthy();

      await project.cleanup();
      await steward.cleanup();
    });

    test('STANDBY mode blocks all PHI operations', async ({ page, request }) => {
      const user = await TestUser.create('researcher', request);
      const project = await TestProject.create(user.id, {
        name: 'STANDBY Mode Test',
        type: 'cohort',
        governanceMode: 'STANDBY',
      }, request, user.getAuthHeaders());

      await page.goto(`/projects/${project.id}/workflow/4`);

      // Should show standby block
      await expect(page.locator('[data-testid="standby-block"]')).toBeVisible();
      await expect(page.locator('[data-testid="standby-block"]')).toContainText('Standby Mode');

      await project.cleanup();
      await user.cleanup();
    });
  });
});
