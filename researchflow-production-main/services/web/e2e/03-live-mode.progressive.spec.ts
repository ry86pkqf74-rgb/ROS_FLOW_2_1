import { test, expect } from "@playwright/test";
import { devLoginAndGetToken, modeStore } from "./helpers/devSession";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";

const PAPER_TITLE =
  "Characteristics of hospitalized adult patients with laboratory documented Influenza A, B and Respiratory Syncytial Virus – A single center retrospective observational study";

const DATASET_URL =
  "https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0214517pone.0214517.s003.xlsx";

async function downloadToTemp(request: any, url: string, filename: string) {
  const res = await request.get(url);
  if (!res.ok()) {
    throw new Error(
      `Failed to download dataset: ${res.status()} ${res.statusText()}`
    );
  }
  const buf = await res.body();
  const filePath = path.join(os.tmpdir(), filename);
  fs.writeFileSync(filePath, buf);
  return filePath;
}

test("LIVE mode: upload real XLSX + execute stages sequentially (2)", async ({
  page,
  request,
}, testInfo) => {
  const baseURL = testInfo.project.use.baseURL as string;
  const token = await devLoginAndGetToken(baseURL);

  await page.addInitScript(
    ({ t, m }) => {
      localStorage.setItem("access_token", t);
      localStorage.setItem("ros-mode-storage", JSON.stringify(m));
    },
    { t: token, m: modeStore(true) }
  );

  const datasetPath = await downloadToTemp(
    request,
    DATASET_URL,
    "plosone_s003.xlsx"
  );

  await page.goto("/workflow");
  await expect(page.getByTestId("section-workflow")).toBeVisible();

  // Seed topic/title (lets AI fill the rest)
  const overview = page.getByTestId("textarea-research-overview");
  if (await overview.count()) {
    await overview.fill(
      `${PAPER_TITLE}\n\nUse this title as the topic. Generate all remaining fields and propose an analysis plan.`
    );
  }

  // Upload dataset
  await expect(page.getByTestId("section-data-upload")).toBeVisible({
    timeout: 60_000,
  });
  await page.getByTestId("input-file-upload").setInputFiles(datasetPath);

  await expect(page.getByTestId("section-uploaded-file")).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.getByTestId("text-file-name")).toContainText(".xlsx");

  // Select a stage if none is selected (selectedStage starts null)
  await expect(page.getByTestId("accordion-workflow-groups")).toBeVisible();
  await page
    .getByTestId("accordion-workflow-groups")
    .click({ position: { x: 50, y: 50 } });

  // Execute 2 stages sequentially (CI)
  for (let i = 0; i < 2; i++) {
    const execute = page.getByTestId("button-execute-stage");
    await expect(execute).toBeVisible();

    await expect(execute).toBeEnabled({ timeout: 120_000 });
    await execute.click();

    await Promise.race([
      page
        .getByTestId("section-execution-results")
        .waitFor({ state: "visible", timeout: 180_000 }),
      expect(execute).toContainText("Completed", { timeout: 180_000 }),
    ]);

    await expect(page.getByTestId("list-stage-outputs")).toBeVisible({
      timeout: 180_000,
    });

    // attempt to progress to next stage by clicking further down the list
    await page
      .getByTestId("accordion-workflow-groups")
      .click({ position: { x: 50, y: 140 } });
  }
});
