import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";

// docs/DEMO.md, clicked through with the same labels it tells Kiran to click. The headings must
// match the steps below one for one, so a step dropped from either side fails this test.
const STEPS = [
  "Step 1. Data health first (Registrar)",
  "Step 2. A vague request, questions, and an edited plan (Registrar)",
  "Step 3. Four agents at the same time (Registrar)",
  "Step 4. The miss that rounds to the target (Registrar)",
  "Step 5. The brief (Registrar)",
  "Step 6. Break it on purpose (Registrar)",
  "Step 7. The Principal edits and approves",
  "Step 8. Roll back, and the audit chain (Principal)",
  "Step 9. What a HOD can see (HOD, CSE)",
];

const LEADERSHIP = "Prepare the leadership brief";
const COUNCIL = "Placement and research brief for the Governing Council for 2025-26";

function menu(page: Page, name: string) {
  return page.getByRole("navigation", { name: "Main" }).getByRole("link", { name, exact: true });
}

async function signIn(page: Page, role: string) {
  const escaped = role.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await page.getByRole("button", { name: new RegExp(`^${escaped}`) }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

// the radio itself is visually hidden, a person clicks its label
function choice(page: Page, name: string) {
  return page.locator("label", { has: page.getByRole("radio", { name, exact: true }) });
}

async function signOut(page: Page) {
  await page.getByRole("button", { name: /Account menu for/ }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
}

// What the room sees at the moment each step makes its point: no sideways scroll on the page, and
// with REHEARSE_SCREENS=1 a picture of it in docs/demo-screens, the backup if the laptop fails.
async function projector(page: Page, step: number) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, `step ${step} scrolls sideways`).toBeLessThanOrEqual(0);
  // nor a table on screen that has to be scrolled sideways to be read
  const clipped = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>("*")]
      .filter((el) => ["auto", "scroll"].includes(getComputedStyle(el).overflowX))
      .filter((el) => {
        const box = el.getBoundingClientRect();
        return box.bottom > 0 && box.top < window.innerHeight && box.width > 0;
      })
      .filter((el) => el.scrollWidth > el.clientWidth + 1)
      .map((el) => el.getAttribute("aria-label") ?? el.textContent?.slice(0, 40)),
  );
  expect(clipped, `step ${step} has a region to scroll sideways`).toEqual([]);
  // the picture is of the settled screen, not a sheet or dialog halfway through its animation
  await page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((a) => a.effect?.getTiming().iterations !== Infinity)
        .map((a) => a.finished.catch(() => undefined)),
    ),
  );
  // and not halfway through a smooth scroll
  await page.waitForFunction(
    () => new Promise((settled) => { const y = window.scrollY; setTimeout(() => settled(window.scrollY === y), 150); }),
  );
  if (process.env.REHEARSE_VIDEO === "1") {
    await page.waitForTimeout(6_000); // time to say the step's "Say" line over the recording
  }
  if (process.env.REHEARSE_SCREENS) {
    await page.screenshot({ path: join(__dirname, "..", "..", "docs", "demo-screens", `step-${step}.png`) });
  }
}

test("DEMO.md has exactly the steps this rehearsal walks", () => {
  const doc = readFileSync(join(__dirname, "..", "..", "docs", "DEMO.md"), "utf8");
  const headings = [...doc.matchAll(/^### (Step \d+\. .+)$/gm)].map((m) => m[1].trim());
  expect(headings).toEqual(STEPS);
});

test("the demo, steps 1 to 9", async ({ page }) => {
  await page.goto("/login");

  await test.step(STEPS[0], async () => {
    await signIn(page, "Registrar");
    await expect(page.getByText("Current approved report")).toBeVisible();
    await expect(page.getByText("Decision brief, 2025-26, version 1")).toBeVisible();
    await expect(page.getByText(/13 of 13 KPI definitions and targets are placeholders pending IQAC approval/)).toBeVisible();
    await expect(page.getByText("Some figures rest on incomplete data")).toBeVisible();
    await page.getByRole("link", { name: "Open data health" }).click();
    await expect(page.getByText(/^Stale, \d+ days$/)).toBeVisible();
    await expect(page.getByText("No record", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("1 pending reconciliation")).toBeVisible();
    await projector(page, 1);
  });

  await test.step(STEPS[1], async () => {
    await menu(page, "New brief").click();
    await page.getByRole("button", { name: LEADERSHIP, exact: true }).click();
    await page.getByRole("button", { name: "Start", exact: true }).click();
    await expect(page.getByText("Questions from the planner")).toBeVisible();
    await expect(page.getByText("Which period should the brief cover?").first()).toBeVisible();
    await choice(page, "2025-26").click();
    await choice(page, "All four areas").click();
    await choice(page, "Governing Council review").click();
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByText(/^Revision 1\./)).toBeVisible();
    await page.getByRole("checkbox", { name: "Curriculum compliance" }).click();
    await page.getByRole("button", { name: "Save changes" }).click();
    await expect(page.getByText(/^Revision 2\./)).toBeVisible();
    await expect(page.getByText(/^12 of 13 chosen/)).toBeVisible();
    await projector(page, 2);
  });

  await test.step(STEPS[2], async () => {
    await page.getByRole("button", { name: "Lock plan and start" }).click();
    for (const agent of ["Academic agent", "Research agent", "Placement agent", "Finance agent"]) {
      await expect(page.getByRole("listitem").filter({ hasText: new RegExp(`^${agent}`) })).toContainText("done", { timeout: 30_000 });
    }
    await expect(page.getByText("The draft passed all nine checks and is waiting for a person")).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText("4 domain agents worked at the same time")).toBeVisible();
    await projector(page, 3);
  });

  await test.step(STEPS[3], async () => {
    await menu(page, "Dashboard").click();
    await expect(page.getByText("Reads as 75.0 but the target is missed.")).toBeVisible();
    await page.getByRole("button", { name: "Placement percentage", exact: true }).first().click();
    const sheet = page.getByRole("dialog");
    await expect(sheet.getByText(/It is missed: the exact figure is 74\.96/)).toBeVisible();
    await expect(sheet.getByText("75.7%")).toBeVisible();
    await expect(sheet.getByText(/^\d+ records behind this figure\.$/)).toBeVisible();
    await projector(page, 4);
    await page.keyboard.press("Escape");
  });

  await test.step(STEPS[4], async () => {
    await menu(page, "Review queue").click();
    await page.getByRole("link", { name: LEADERSHIP }).click();
    await expect(page.getByRole("heading", { name: "Decision brief, 2025-26" })).toBeVisible();
    await expect(page.getByText("Validation passed")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Options for decision" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Confirm provisional offers quickly" })).toBeVisible();
    await expect(page.getByText("Strategic plan pack").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Assumptions and caveats" })).toBeVisible();
    await expect(page.getByText("Forecast figures are shown apart and are never added to actuals.")).toBeVisible();
    await expect(page.getByText("All nine checks passed on attempt 1 of the drafting loop.")).toBeVisible();
    await projector(page, 5);
  });

  await test.step(STEPS[5], async () => {
    await menu(page, "New brief").click();
    await page.getByRole("button", { name: COUNCIL, exact: true }).click();
    await page.getByRole("button", { name: "Start", exact: true }).click();
    await page.getByText("Demo: inject a failure").click();
    await page.getByRole("checkbox", { name: /A figure written by hand/ }).check();
    await page.getByRole("button", { name: "Lock plan and start" }).click();
    await expect(page.getByText("Failing: V1 Every figure cites its source")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText("Repair, attempt 2")).toBeVisible();
    await expect(page.getByText("All nine checks passed")).toBeVisible();
    await page.getByRole("link", { name: /Open the draft/ }).click();
    await expect(page.getByText("Attempt 1: failing V1")).toBeVisible();
    await expect(page.getByText("Attempt 2: all nine checks passed")).toBeVisible();
    await page.getByText("Attempt 1: failing V1").scrollIntoViewIfNeeded();
    await projector(page, 6);
  });

  await test.step(STEPS[6], async () => {
    await signOut(page);
    await signIn(page, "Principal / Director");
    await menu(page, "Review queue").click();
    await page.getByRole("link", { name: LEADERSHIP }).click();
    await page.getByRole("button", { name: "Edit options" }).click();
    await page.getByRole("textbox", { name: "Title" }).first().fill("Targeted academic support, reviewed by the Dean each semester");
    await page.getByRole("button", { name: "Check my edits" }).click();
    await expect(page.getByText("Your edits pass all nine checks. Nothing is saved until you approve.")).toBeVisible();
    await page.getByRole("button", { name: "Approve with edits" }).click();
    const confirm = page.getByRole("dialog");
    await expect(confirm.getByText("Approve with your edits?")).toBeVisible();
    await confirm.getByRole("button", { name: "Approve with edits" }).click();
    await expect(page.getByText("Published as version 2")).toBeVisible();
    await expect(page.getByText("1 edit made on approval")).toBeVisible();
    await expect(page.getByText("Published as version 2")).toBeInViewport();
    await projector(page, 7);
  });

  await test.step(STEPS[7], async () => {
    await menu(page, "Reports").click();
    await expect(page.getByText("Compare versions")).toBeVisible();
    await page.getByRole("row", { name: /^v1\b/ }).getByRole("button", { name: "Make current" }).click();
    const roll = page.getByRole("button", { name: "Roll back to version 1" });
    await expect(roll).toBeDisabled();
    await page.getByLabel(/Reason/).fill("Restoring the version the Council already saw");
    await roll.click();
    await expect(page.getByText("Version 1 is current again")).toBeVisible();
    await expect(page.getByRole("row", { name: /^v2\b/ })).toContainText("Rolled back");
    await menu(page, "Audit").click();
    await expect(page.getByText("The audit chain verifies")).toBeVisible();
    await projector(page, 8);
  });

  await test.step(STEPS[8], async () => {
    await signOut(page);
    await signIn(page, "Head of Department (CSE)");
    await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link")).toHaveText([
      "Dashboard",
      "Reports",
      "Data health",
    ]);
    await page.getByRole("button", { name: "Placement percentage", exact: true }).first().click();
    await expect(page.getByRole("dialog").getByText("restricted").first()).toBeVisible();
    await projector(page, 9);
    await page.keyboard.press("Escape");
    await menu(page, "Data health").click();
    await expect(page.getByText("Restricted").first()).toBeVisible();
  });
});
