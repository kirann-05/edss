import { describe, expect, it } from "vitest";

import { formatNumber, formatVariance, roundDecimal, roundingHidesMiss } from "./format";

describe("roundDecimal (exact, half up, no floats)", () => {
  it.each([
    ["74.96", 1, "75.0"],
    ["74.949", 1, "74.9"],
    ["74.95", 1, "75.0"],
    ["1.005", 2, "1.01"], // 1.005.toFixed(2) is "1.00" because of binary floats
    ["0.5", 0, "1"],
    ["12", 2, "12.00"],
    ["-3.449", 1, "-3.4"],
    ["-3.45", 1, "-3.5"],
    ["0", 1, "0.0"],
  ])("rounds %s to %i places as %s", (input, places, expected) => {
    expect(roundDecimal(input, places)).toBe(expected);
  });

  it("never prints negative zero", () => {
    expect(roundDecimal("-0.04", 1)).toBe("0.0");
  });

  it("rejects values that are not plain decimals", () => {
    expect(() => roundDecimal("1e3", 1)).toThrow();
    expect(() => roundDecimal("abc", 1)).toThrow();
  });
});

describe("formatNumber", () => {
  it("formats with grouping and fixed places", () => {
    expect(formatNumber("1234567.891", 1)).toBe("1,234,567.9");
    expect(formatNumber("-1234.5", 0)).toBe("-1,235");
  });

  it("shows an undefined value as an explicit dash, never zero", () => {
    expect(formatNumber(null, 1)).toBe("n/a");
  });
});

describe("roundingHidesMiss (rule 5)", () => {
  it("flags a miss that displays equal to the target (trap T6)", () => {
    expect(
      roundingHidesMiss({ value: "74.96", target: "75", precision: 1, status: "missed" }),
    ).toBe(true);
  });

  it("does not flag a clear miss", () => {
    expect(
      roundingHidesMiss({ value: "71.2", target: "75", precision: 1, status: "missed" }),
    ).toBe(false);
  });

  it("only concerns missed KPIs", () => {
    expect(roundingHidesMiss({ value: "75.04", target: "75", precision: 1, status: "met" })).toBe(
      false,
    );
    expect(roundingHidesMiss({ value: null, target: "75", precision: 1, status: "undefined" })).toBe(
      false,
    );
  });
});

describe("formatVariance", () => {
  it("describes the shortfall in the KPI's own terms", () => {
    expect(formatVariance({ varianceAbs: "-3.4", precision: 1, unit: "%" })).toBe(
      "3.4 pts below target",
    );
    expect(formatVariance({ varianceAbs: "2.1", precision: 1, unit: "%" })).toBe(
      "2.1 pts above target",
    );
  });

  it("uses the unit when it is not a percentage", () => {
    expect(formatVariance({ varianceAbs: "-0.3", precision: 1, unit: "LPA" })).toBe(
      "0.3 LPA below target",
    );
  });

  it("adds precision rather than ever printing a zero gap for a real miss (trap T6)", () => {
    expect(formatVariance({ varianceAbs: "-0.04", precision: 1, unit: "%" })).toBe(
      "0.04 pts below target",
    );
    expect(formatVariance({ varianceAbs: "-0.0004", precision: 1, unit: "%" })).toBe(
      "0.0004 pts below target",
    );
  });

  it("falls back to a bound when the gap is smaller than four places", () => {
    expect(formatVariance({ varianceAbs: "-0.000004", precision: 1, unit: "%" })).toBe(
      "under 0.0001 pts below target",
    );
  });

  it("says on target only for an exact zero", () => {
    expect(formatVariance({ varianceAbs: "0", precision: 1, unit: "%" })).toBe("on target");
    expect(formatVariance({ varianceAbs: "0.000", precision: 1, unit: "%" })).toBe("on target");
  });

  it("has no variance to describe when the KPI is undefined", () => {
    expect(formatVariance({ varianceAbs: null, precision: 1, unit: "%" })).toBe("no target gap");
  });
});
