import { test, expect } from "@playwright/test";
import { devLoginAndGetToken, modeStore } from "./helpers/devSession";

test("OFFLINE mode: workflow loads (AI disabled)", async ({ page }, testInfo) => {
  const baseURL = testInfo.project.use.baseURL as string;
  const token = await devLoginAndGetToken(baseURL);

  await page.addInitScript(
    ({ t, m }) => {
      localStorage.setItem("access_token", t);
      localStorage.setItem("ros-mode-storage", JSON.stringify(m));
    },
    { t: token, m: modeStore(false) }
  );

  await page.goto("/workflow");

  await expect(page.getByTestId("section-workflow")).toBeVisible();
  await expect(page.getByTestId("card-stage-details")).toBeVisible();
});
