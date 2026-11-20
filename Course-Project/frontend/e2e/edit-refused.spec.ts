import { expect, test } from "@playwright/test";

import { draftViaApi, signInAs } from "./helpers";

// Rule 1 holds for people too: an approver who types a figure into an option is stopped by the
// same check V1 that stops the model, and nothing can be published until the figure is removed.
test("a figure typed into an edit is refused, and nothing is published", async ({ page }) => {
  await signInAs(page, "Principal / Director");
  const { briefId } = await draftViaApi(page.request);
  const before = await (await page.request.get("/api/reports/versions")).json();

  await page.goto(`/review/${briefId}`);
  await page.getByRole("button", { name: "Edit options" }).click();
  const description = page.getByRole("textbox", { name: "Description" }).first();
  await description.fill(`${await description.inputValue()} This lifts it to 1.2 papers per faculty.`);

  // said while typing, before anything is sent
  await expect(page.getByText("Typed number 1.2 will fail check V1")).toBeVisible();

  await page.getByRole("button", { name: "Check my edits" }).click();
  await expect(page.getByText("Your edits fail V1. Fix them and check again.")).toBeVisible();
  await expect(page.getByText("V1: Figure written by hand: '1.2'")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve with edits" })).toBeDisabled();

  await page.getByRole("button", { name: "Cancel editing" }).click();
  const after = await (await page.request.get("/api/reports/versions")).json();
  expect(after).toHaveLength(before.length);
  const brief = await (await page.request.get(`/api/briefs/${briefId}`)).json();
  expect(brief.status).toBe("draft");
});
