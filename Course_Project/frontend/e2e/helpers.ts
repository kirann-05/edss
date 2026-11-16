import { expect, type APIRequestContext, type Page } from "@playwright/test";

/** The demo role buttons on the sign-in page, which is how the demo switches person. */
export async function signInAs(page: Page, roleLabel: string) {
  await page.goto("/login");
  const escaped = roleLabel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await page.getByRole("button", { name: new RegExp(`^${escaped}`) }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

/** A finished draft made through the API with the browser's own session, to save clicks in a test. */
export async function draftViaApi(
  request: APIRequestContext,
  text = "Placement and research brief for the Governing Council for 2025-26",
  faults: string[] = [],
): Promise<{ runId: string; briefId: string }> {
  const created = await request.post("/api/runs", { data: { request: text } });
  expect(created.ok()).toBeTruthy();
  let run = await created.json();
  if (run.status === "clarifying") {
    run = await (await request.post(`/api/runs/${run.id}/skip-questions`)).json();
  }
  const locked = await request.post(`/api/runs/${run.id}/plan/lock`, { data: { faults } });
  expect(locked.ok()).toBeTruthy();
  for (let attempt = 0; attempt < 60; attempt++) {
    run = await (await request.get(`/api/runs/${run.id}`)).json();
    if (run.status !== "running") break;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  expect(run.status).toBe("awaiting_review");
  return { runId: run.id, briefId: run.brief_id };
}
