import { expect, test, type Page } from "@playwright/test";

import { draftViaApi, signInAs } from "./helpers";

/** Press Tab until the focused control's name matches, so a test cannot reach anything a person could not. */
async function tabTo(page: Page, name: RegExp, max = 150): Promise<string> {
  for (let press = 0; press < max; press++) {
    await page.keyboard.press("Tab");
    const label = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return "";
      return (el.getAttribute("aria-label") || el.innerText || el.getAttribute("title") || "").trim().split("\n")[0];
    });
    if (name.test(label)) return label;
  }
  throw new Error(`Tab never reached a control named ${name}`);
}

test("the skip link is the first stop and moves focus to the page content", async ({ page }) => {
  await signInAs(page, "Registrar");
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Audit" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to main content" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
});

test("a KPI opens its drill-down from the keyboard and focus returns when it closes", async ({ page }) => {
  await signInAs(page, "Registrar");
  await expect(page.getByRole("heading", { name: "Institution KPIs" })).toBeVisible();
  await expect(page.getByText("Overall pass percentage").first()).toBeVisible();

  await tabTo(page, /^Overall pass percentage$/);
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Overall pass percentage" }).first()).toBeVisible();
  await expect(page).toHaveURL(/kpi=AC_PASS_PCT/);

  await page.keyboard.press("Escape");
  await expect(page).not.toHaveURL(/kpi=/);
  await expect(page.getByRole("button", { name: "Overall pass percentage" })).toBeFocused();
});

test("a brief can be approved with the keyboard alone, and a dialog traps focus", async ({ page }) => {
  await signInAs(page, "Principal / Director");
  const { briefId } = await draftViaApi(page.request);
  await page.goto(`/review/${briefId}`);
  await expect(page.getByRole("button", { name: "Approve", exact: true })).toBeVisible();

  await tabTo(page, /^Approve$/);
  await page.keyboard.press("Enter");
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();

  // tabbing round the dialog never leaves it
  for (let press = 0; press < 8; press++) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => !!document.activeElement?.closest('[role="dialog"]'))).toBe(true);
  }

  await tabTo(page, /^Approve and publish$/, 12);
  await page.keyboard.press("Enter");
  await expect(page.getByText(/Published as version \d+/)).toBeVisible();
});

test("Escape closes a dialog without deciding anything", async ({ page }) => {
  await signInAs(page, "Registrar");
  const { briefId } = await draftViaApi(page.request);
  await page.goto(`/review/${briefId}`);
  await page.getByRole("button", { name: "Override" }).click();
  await expect(page.getByRole("heading", { name: "Override the draft" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  const brief = await (await page.request.get(`/api/briefs/${briefId}`)).json();
  expect(brief.status).toBe("draft");
});
