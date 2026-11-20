import { describe, expect, it } from "vitest";

import type { Permission } from "@/lib/api/types";

import { isActive, landingFor, navFor } from "./nav";

const as = (...permissions: Permission[]) => ({ permissions });

// the permission sets below are copied from backend/app/core/rbac.py, one per role
const REGISTRAR = as(
  "view_dashboard", "view_data_health", "start_run", "view_reports",
  "review", "approve", "rollback", "view_audit", "manage_scope", "refresh_data",
);
const PRINCIPAL = as(
  "view_dashboard", "view_data_health", "start_run", "view_reports", "review", "approve", "rollback", "view_audit",
);
const DEAN = as("view_dashboard", "view_data_health", "start_run", "view_reports");
const HOD = as("view_dashboard", "view_data_health", "view_reports");
const VIEWER = as("view_reports");
const ADMIN = as("view_data_health", "manage_users", "refresh_data");

const hrefs = (me: { permissions: Permission[] }) => navFor(me).map((i) => i.href);

describe("navigation follows permissions", () => {
  it("gives the Registrar every page, including scope grants under Admin", () => {
    expect(hrefs(REGISTRAR)).toEqual(["/", "/runs", "/review", "/reports", "/data-health", "/audit", "/admin"]);
  });

  it("gives the Principal everything except Admin", () => {
    expect(hrefs(PRINCIPAL)).toEqual(["/", "/runs", "/review", "/reports", "/data-health", "/audit"]);
  });

  it("lets a Dean start briefs but not review them", () => {
    expect(hrefs(DEAN)).toEqual(["/", "/runs", "/reports", "/data-health"]);
  });

  it("shows a HOD no page that starts, reviews or audits anything", () => {
    expect(hrefs(HOD)).toEqual(["/", "/reports", "/data-health"]);
  });

  it("lands the Governing Council on published reports, the only thing they may read", () => {
    expect(hrefs(VIEWER)).toEqual(["/reports"]);
    expect(landingFor(VIEWER)).toBe("/reports");
  });

  it("lands an administrator on data health and shows Admin", () => {
    expect(hrefs(ADMIN)).toEqual(["/data-health", "/admin"]);
    expect(landingFor(ADMIN)).toBe("/data-health");
  });

  it("has no landing page for someone with no permissions", () => {
    expect(landingFor(as())).toBeNull();
  });
});

describe("isActive", () => {
  it("matches the dashboard only on the exact path", () => {
    expect(isActive("/", "/")).toBe(true);
    expect(isActive("/", "/data-health")).toBe(false);
  });

  it("matches a section and anything beneath it", () => {
    expect(isActive("/data-health", "/data-health")).toBe(true);
    expect(isActive("/runs", "/runs/run-3")).toBe(true);
    expect(isActive("/data-health", "/data-healthy")).toBe(false);
  });
});
