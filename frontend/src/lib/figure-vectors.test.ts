import { describe, expect, it } from "vitest";

import vectors from "../../../shared/figure-vectors.json";
import {
  formatExact,
  formatNumber,
  formatVariance,
  formatWithUnit,
  roundDecimal,
  roundingHidesMiss,
} from "./format";
import type { KpiStatus } from "./format";

// The same vectors run in backend/tests/agents/test_figures.py. If the two ever disagree about
// rounding, one of the suites fails, instead of a brief and the dashboard quietly differing.
describe("shared figure vectors", () => {
  it.each(vectors.round_decimal)("roundDecimal $value to $places is $expected", (v) => {
    expect(roundDecimal(v.value, v.places)).toBe(v.expected);
  });
  it.each(vectors.format_number)("formatNumber $value to $places is $expected", (v) => {
    expect(formatNumber(v.value, v.places)).toBe(v.expected);
  });
  it.each(vectors.format_with_unit)("formatWithUnit $value $unit is $expected", (v) => {
    expect(formatWithUnit(v.value, v.places, v.unit)).toBe(v.expected);
  });
  it.each(vectors.format_variance)("formatVariance $variance_abs is $expected", (v) => {
    expect(formatVariance({ varianceAbs: v.variance_abs, precision: v.precision, unit: v.unit })).toBe(
      v.expected,
    );
  });
  it.each(vectors.rounding_hides_miss)("roundingHidesMiss $value vs $target is $expected", (v) => {
    expect(
      roundingHidesMiss({
        value: v.value,
        target: v.target,
        precision: v.precision,
        status: v.status as KpiStatus,
      }),
    ).toBe(v.expected);
  });
  it.each(vectors.format_exact)("formatExact $value is $expected", (v) => {
    expect(formatExact(v.value)).toBe(v.expected);
  });
});
