import { test, expect } from "@playwright/test";

test("HomeRoute renders marketing sections (DEMO)", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#workflow")).toBeVisible();
  await expect(page.locator("#ai-insights")).toBeVisible();
});
