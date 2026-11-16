import { describe, expect, it } from "vitest";

import { safeNext } from "./navigation";

describe("safeNext (no open redirect after sign-in)", () => {
  it.each([
    ["/", "/"],
    ["/data-health", "/data-health"],
    ["/?kpi=PL_PCT&period=2025-26", "/?kpi=PL_PCT&period=2025-26"],
  ])("keeps the same-site path %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });

  it.each([
    ["https://evil.example/phish"],
    ["//evil.example/phish"],
    ["/\\evil.example"],
    ["javascript:alert(1)"],
    ["evil"],
    [""],
    [null],
    [undefined],
  ])("sends %s to the dashboard instead", (input) => {
    expect(safeNext(input as string | null | undefined)).toBe("/");
  });

  it("never loops back to the login page", () => {
    expect(safeNext("/login")).toBe("/");
    expect(safeNext("/login?next=/x")).toBe("/");
  });
});
