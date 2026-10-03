import { expect, test } from "@playwright/test";

import { draftViaApi, signInAs } from "./helpers";

// The flow the whole system exists for (docs/ARCHITECTURE.md section 10): a person asks, the
// agents draft and validate, a named approver publishes, and the publish can be rolled back with
// the audit chain still intact.
test("the Principal asks for a brief, approves it, and rolls the report back", async ({ page }) => {
  await signInAs(page, "Principal / Director");

  // ask, and lock the plan the planner proposes
  await page.goto("/runs");
  await page.getByRole("button", { name: "Placement and research brief for the Governing Council for 2025-26" }).click();
  await page.getByRole("button", { name: /^Start/ }).click();
  await expect(page).toHaveURL(/\/runs\/run-\d+/);
  await page.getByRole("button", { name: "Lock plan and start" }).click();

  // the agents work, validation passes, and the draft waits for a person
  await expect(page.getByText("The draft passed all nine checks and is waiting for a person")).toBeVisible({
    timeout: 30_000,
  });
  await page.getByRole("link", { name: /Open the draft/ }).click();
  await expect(page.getByRole("heading", { name: "Decision brief, 2025-26" })).toBeVisible();

  // nothing is published until the approver confirms
  await page.getByRole("button", { name: "Approve", exact: true }).click();
  await page.getByRole("button", { name: "Approve and publish" }).click();
  const published = page.getByText(/Published as version \d+/);
  await expect(published).toBeVisible();
  // other tests share this backend, so read the number instead of assuming it is 1
  const first = Number((await published.textContent())?.match(/version (\d+)/)?.[1]);
  expect(first).toBeGreaterThan(0);

  // a second report, so there is something to roll back from
  const second = await draftViaApi(page.request);
  const approved = await page.request.post(`/api/briefs/${second.briefId}/decision`, { data: { kind: "approve" } });
  expect(approved.ok()).toBeTruthy();
  const secondVersion: number = (await approved.json()).version;
  expect(secondVersion).toBe(first + 1);

  await page.goto("/reports");
  await expect(page.getByText(`version ${secondVersion}`, { exact: true }).first()).toBeVisible();
  await page.getByRole("row", { name: new RegExp(`^v${first}\\b`) }).getByRole("button", { name: "Make current" }).click();
  const roll = page.getByRole("button", { name: `Roll back to version ${first}` });
  await expect(roll).toBeDisabled(); // a reason is required first
  await page.getByLabel(/Reason/).fill("The second report was approved by mistake, restoring the first.");
  await roll.click();
  await expect(page.getByText(`Version ${first} is current again`)).toBeVisible();
  await expect(page.getByRole("row", { name: new RegExp(`^v${secondVersion}\\b`) })).toContainText("Rolled back");

  // every step is in the audit log, and the chain still verifies
  await page.goto("/audit");
  await expect(page.getByText("The audit chain verifies")).toBeVisible();
  await expect(page.getByText("report.rollback").first()).toBeVisible();
});
