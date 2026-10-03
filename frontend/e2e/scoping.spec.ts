import { expect, test } from "@playwright/test";

import { signInAs } from "./helpers";

// Demo step 9, and the guarantee in docs/SPEC.md section 2: a HOD never receives another
// department's record-level detail. The check is on what the server sends, not on what the page draws.
test("a HOD sees institution KPIs but only their own department's detail", async ({ page }) => {
  await signInAs(page, "Head of Department (CSE)");

  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link")).toHaveText(["Dashboard", "Reports", "Data health"]);

  // the server refuses what the menu hides
  await page.goto("/review");
  await expect(page.getByText("Your role does not include this.")).toBeVisible();
  for (const path of ["/api/briefs", "/api/audit", "/api/runs", "/api/admin/users"]) {
    expect((await page.request.get(path)).status(), path).toBe(403);
  }

  // other departments are named, and carry nothing else
  const body = await (await page.request.get("/api/kpis/PL_PCT")).json();
  const others = body.departments.filter((d: { dept_code: string }) => d.dept_code !== "CSE");
  expect(others.length).toBeGreaterThan(3);
  for (const row of others) {
    expect(row.access).toBe("restricted");
    expect(row.value).toBeNull();
    expect(row.inputs).toEqual([]);
    expect(row.fact_ids).toEqual([]);
  }
  const own = body.departments.find((d: { dept_code: string }) => d.dept_code === "CSE");
  expect(own.access).toBe("visible");
  expect(own.fact_ids.length).toBeGreaterThan(0);

  // data health is the same: other departments' cells say nothing about their freshness or records
  const health = await (await page.request.get("/api/data-health")).json();
  const cells = health.cells as { dept_code: string; restricted: boolean; state: string | null; as_of: string | null; fact_count: number; batch_ids: number[] }[];
  const otherCells = cells.filter((c) => c.dept_code !== "CSE");
  expect(otherCells.length).toBeGreaterThan(20);
  for (const cell of otherCells) {
    expect(cell.restricted).toBe(true);
    expect(cell.state).toBeNull();
    expect(cell.as_of).toBeNull();
    expect(cell.fact_count).toBe(0);
    expect(cell.batch_ids).toEqual([]);
  }
  // the positive control: the check above can see detail when there is some to see
  expect(cells.filter((c) => c.dept_code === "CSE").some((c) => c.state !== null && c.fact_count > 0)).toBe(true);

  // a record of another department looks exactly like a record that does not exist
  const registrar = await (await page.context().browser()!.newContext({ baseURL: "http://127.0.0.1:3100" })).request;
  await registrar.post("/api/auth/demo-login", { data: { email: "registrar@edss.test" } });
  const civilFact = (await (await registrar.get("/api/kpis/PL_PCT")).json()).departments.find(
    (d: { dept_code: string }) => d.dept_code === "CIVIL",
  ).fact_ids[0];
  expect(civilFact).toBeGreaterThan(0);
  expect((await registrar.get(`/api/facts/${civilFact}`)).status()).toBe(200);
  const hidden = await page.request.get(`/api/facts/${civilFact}`);
  const missing = await page.request.get("/api/facts/999999999");
  expect(hidden.status()).toBe(404);
  expect(await hidden.text()).toBe((await missing.text()).replace("999999999", String(civilFact)));

  // and the page says so in words
  await page.goto("/?kpi=PL_PCT");
  await expect(page.getByText("restricted").first()).toBeVisible();
});
