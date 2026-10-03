import { describe, expect, it } from "vitest";

import type { Permission } from "@/lib/api/types";

import { isActive, landingFor, navFor } from "./nav";

const as = (...permissions: Permission[]) => ({ permissions });

describe("navigation follows permissions", () => {
  it("shows leadership both pages", () => {
    expect(navFor(as("view_dashboard", "view_data_health")).map((i) => i.href)).toEqual([
      "/",
      "/data-health",
    ]);
  });

  it("shows an administrator only data health, and lands them there", () => {
    const admin = as("view_data_health", "manage_users", "refresh_data");
    expect(navFor(admin).map((i) => i.href)).toEqual(["/data-health"]);
    expect(landingFor(admin)).toBe("/data-health");
  });

  it("has no page for someone who may only read published reports yet", () => {
    const viewer = as("view_reports");
    expect(navFor(viewer)).toEqual([]);
    expect(landingFor(viewer)).toBeNull();
  });
});

describe("isActive", () => {
  it("matches the dashboard only on the exact path", () => {
    expect(isActive("/", "/")).toBe(true);
    expect(isActive("/", "/data-health")).toBe(false);
  });

  it("matches a section and anything beneath it", () => {
    expect(isActive("/data-health", "/data-health")).toBe(true);
    expect(isActive("/data-health", "/data-health/batches")).toBe(true);
    expect(isActive("/data-health", "/data-healthy")).toBe(false);
  });
});
