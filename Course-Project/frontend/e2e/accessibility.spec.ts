import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { draftViaApi, signInAs } from "./helpers";

// Automated checks catch a share of accessibility problems, not all of them (roughly a third by
// common estimates), so this does not replace the keyboard walk-through in docs/UI_SPEC.md. It
// does stop the mechanical ones from coming back: contrast, names, labels, landmarks, ARIA use.
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function scan(page: Page, name: string) {
  await page.waitForTimeout(600); // let dialogs and sheets finish animating, or contrast is measured mid-fade
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  const report = violations.map((v) => ({
    rule: v.id,
    impact: v.impact,
    help: v.help,
    where: v.nodes.slice(0, 4).map((n) => `${n.target.join(" ")}: ${n.failureSummary?.split("\n")[1]?.trim() ?? ""}`),
    count: v.nodes.length,
  }));
  expect(report, `${name} has accessibility violations:\n${JSON.stringify(report, null, 2)}`).toEqual([]);
}

test("the sign-in page", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await scan(page, "sign-in");
});

test("every page the Registrar can open, and its main states", async ({ page }) => {
  await signInAs(page, "Registrar");

  // data to look at: a run waiting for answers, one with a plan, and one published
  const vague = await (await page.request.post("/api/runs", { data: { request: "Prepare the leadership brief" } })).json();
  const planned = await (
    await page.request.post("/api/runs", { data: { request: "Placement and research brief for the Governing Council for 2025-26" } })
  ).json();
  const { runId, briefId } = await draftViaApi(page.request);
  expect((await page.request.post(`/api/briefs/${briefId}/decision`, { data: { kind: "approve" } })).ok()).toBeTruthy();
  const second = await draftViaApi(page.request, "Placement brief for the Governing Council for 2025-26", ["fake_number"]);

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Institution KPIs" })).toBeVisible();
  await expect(page.getByText("Overall pass percentage").first()).toBeVisible();
  await scan(page, "dashboard");

  await page.goto("/?kpi=PL_PCT");
  await expect(page.getByRole("heading", { name: "Placement percentage" }).first()).toBeVisible();
  await scan(page, "KPI drill-down");

  await page.goto("/data-health");
  await expect(page.getByRole("heading", { name: "Data health" })).toBeVisible();
  await scan(page, "data health");

  await page.goto("/runs");
  await expect(page.getByRole("heading", { name: "New brief" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Prepare the leadership brief/ })).toBeVisible();
  await scan(page, "new brief");

  await page.goto(`/runs/${vague.id}`);
  await expect(page.getByText("Before I plan this")).toBeVisible();
  await scan(page, "planner questions");

  await page.goto(`/runs/${planned.id}`);
  await expect(page.getByRole("button", { name: "Lock plan and start" })).toBeVisible();
  await scan(page, "plan editor");

  await page.goto(`/runs/${runId}`);
  await expect(page.getByText("The draft passed all nine checks and is waiting for a person").or(page.getByText("A decision has been recorded"))).toBeVisible();
  await scan(page, "finished run with progress");

  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Placement brief/ }).first()).toBeVisible();
  await scan(page, "review queue");

  await page.goto(`/review/${second.briefId}`);
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toBeVisible();
  await scan(page, "brief under review");

  await page.getByRole("button", { name: "Edit options" }).click();
  await expect(page.getByRole("button", { name: "Check my edits" })).toBeVisible();
  await scan(page, "brief while editing");
  await page.getByRole("button", { name: "Cancel editing" }).click();

  await page.getByRole("button", { name: "Override" }).click();
  await expect(page.getByRole("heading", { name: "Override the draft" })).toBeVisible();
  await scan(page, "override dialog");
  await page.keyboard.press("Escape");

  await page.goto(`/review/${briefId}?kpi=PL_PCT`);
  await expect(page.getByRole("heading", { name: "Placement percentage" }).first()).toBeVisible();
  await scan(page, "published brief with a drill-down open");

  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "All versions" })).toBeVisible();
  await scan(page, "reports");

  await page.goto("/reports/1");
  await expect(page.getByRole("heading", { name: "KPIs at a glance" })).toBeVisible();
  await scan(page, "a published version");

  await page.goto("/audit");
  await expect(page.getByText("The audit chain verifies")).toBeVisible();
  await page.getByRole("button", { name: /^#\d+/ }).first().click();
  await scan(page, "audit with a row open");

  await page.goto(`/audit/runs/${runId}`);
  await expect(page.getByRole("heading", { name: `Run trace, ${runId}` })).toBeVisible();
  await scan(page, "run trace");

  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Data access" })).toBeVisible();
  await scan(page, "data access");
});

test("the Administrator's people page and its dialogs", async ({ page }) => {
  await signInAs(page, "Administrator");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "People and roles" })).toBeVisible();
  await scan(page, "people and roles");

  await page.getByRole("button", { name: "Add a person" }).click();
  await expect(page.getByRole("heading", { name: "Add a person" })).toBeVisible();
  await scan(page, "add a person dialog");
});

test("the Governing Council reads published reports", async ({ page }) => {
  await signInAs(page, "Governing Council");
  await expect(page).toHaveURL(/\/reports/);
  await expect(page.getByRole("heading", { name: "Reports" })).toBeVisible();
  await scan(page, "reports for the Governing Council");
});
