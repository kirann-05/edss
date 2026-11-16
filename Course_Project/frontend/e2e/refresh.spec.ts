import { expect, test } from "@playwright/test";

import { signInAs } from "./helpers";

test("the Registrar refreshes the data and is told what was read", async ({ page }) => {
  await signInAs(page, "Registrar");
  await page.goto("/data-health");
  await expect(page.getByRole("heading", { name: "Data health" })).toBeVisible();

  await page.getByRole("button", { name: "Refresh data" }).click();
  await expect(page.getByText("The synthetic data was generated again")).toBeVisible();
  await expect(page.getByText(/records, dated from today/)).toBeVisible();

  // the page shows the data that was just read, with the planted gaps still named
  await expect(page.getByText("No record").first()).toBeVisible();
  const audit = await (await page.request.get("/api/audit?action=data.refresh")).json();
  expect(audit.total).toBe(1);
});

test("people who may not refresh do not see the button, and the server refuses them anyway", async ({ page }) => {
  await signInAs(page, "Head of Department (CSE)");
  await page.goto("/data-health");
  await expect(page.getByRole("heading", { name: "Data health" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh data" })).toHaveCount(0);
  expect((await page.request.post("/api/data/refresh")).status()).toBe(403);
});
