import { expect, test } from "@playwright/test";

import { signInAs } from "./helpers";

// Demo step 6: break the draft on purpose and watch the gate catch it, repair only the failing
// part inside the retry budget, and say so.
test("an injected fault is caught, repaired and shown to the reviewer", async ({ page }) => {
  await signInAs(page, "Registrar");
  await page.goto("/runs");
  await page.getByRole("button", { name: "Placement and research brief for the Governing Council for 2025-26" }).click();
  await page.getByRole("button", { name: /^Start/ }).click();

  await page.getByText("Demo: inject a failure").click();
  await page.getByRole("checkbox", { name: /A figure written by hand/ }).check();
  await page.getByRole("button", { name: "Lock plan and start" }).click();

  // the timeline names the failing check, then the repair, then the passing check
  await expect(page.getByText("Failing: V1 Every figure cites its source")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Repair, attempt 2")).toBeVisible();
  await expect(page.getByText("All nine checks passed")).toBeVisible();

  // the reviewer can follow the same story in the validation report
  await page.getByRole("link", { name: /Open the draft/ }).click();
  await expect(page.getByText("Attempt 1: failing V1")).toBeVisible();
  await expect(page.getByText("Attempt 2: all nine checks passed")).toBeVisible();
});
