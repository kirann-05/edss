import { describe, expect, it } from "vitest";

import type { DepartmentRow } from "@/lib/api/types";

import { buildBarOption, chartSummary, rowLabel, type BarChartInput } from "./bar-option";

const visible = (code: string, over: Partial<DepartmentRow> = {}): DepartmentRow => ({
  dept_code: code,
  dept_name: code,
  school: "School",
  access: "visible",
  state: "ok",
  value: "80",
  inputs: [],
  stale: false,
  as_of: "2026-09-01",
  reason: null,
  fact_ids: [],
  ...over,
});

const input = (rows: DepartmentRow[], over: Partial<BarChartInput> = {}): BarChartInput => ({
  name: "Placement percentage",
  unit: "%",
  precision: 1,
  target: "75",
  rows,
  highlight: null,
  animate: false,
  ...over,
});

// the option shape is ECharts-internal, so read it through loose accessors in the tests
/* eslint-disable @typescript-eslint/no-explicit-any */
const series = (option: any) => option.series[0];

describe("rowLabel says why a department has no bar", () => {
  it.each([
    [visible("CSE"), "CSE"],
    [visible("CIVIL", { stale: true }), "CIVIL (stale)"],
    [visible("MECH", { state: "missing", value: null }), "MECH (no record)"],
    [visible("BIOTECH", { state: "excluded", value: null }), "BIOTECH (excluded)"],
    [visible("AIML", { state: "undefined", value: null }), "AIML (undefined)"],
    [{ ...visible("ECE"), access: "restricted", state: null, value: null } as DepartmentRow, "ECE (restricted)"],
  ])("labels %#", (row, expected) => {
    expect(rowLabel(row)).toBe(expected);
  });
});

describe("buildBarOption", () => {
  it("draws a bar only where there is a value, never a zero bar for a gap", () => {
    const option = buildBarOption(
      input([
        visible("CSE", { value: "80" }),
        visible("MECH", { state: "missing", value: null }),
        visible("AIML", { state: "undefined", value: null }),
      ]),
    );
    expect(series(option).data.map((d: any) => d?.value ?? null)).toEqual([80, null, null]);
  });

  it("starts every bar at zero, because a bar's length is its value", () => {
    const option = buildBarOption(input([visible("CSE")])) as any;
    expect(option.xAxis.min).toBe(0);
  });

  it("marks the institution target with a solid line and a direct label", () => {
    const option = buildBarOption(input([visible("CSE")], { target: "74.96", precision: 1 })) as any;
    const line = series(option).markLine;
    expect(line.data[0].xAxis).toBe(74.96);
    expect(line.lineStyle.type).toBe("solid");
    expect(line.label.formatter).toBe("Target 75.0");
  });

  it("keeps the axis long enough to show the target even when every bar is shorter", () => {
    const option = buildBarOption(input([visible("CSE", { value: "10" })], { target: "75" })) as any;
    expect(option.xAxis.max).toBeGreaterThanOrEqual(75);
  });

  it.each([
    ["84.6", "75", "%", 100],
    ["2.65", "2.5", "level", 3],
    ["2199", "2000", "INR lakh", 2500],
    ["6.24", "6", "LPA", 8],
  ])("ends the axis at a tidy number: %s against %s %s gives %i", (value, target, unit, expected) => {
    const option = buildBarOption(input([visible("CSE", { value })], { target, unit })) as any;
    expect(option.xAxis.max).toBe(expected);
  });

  it("ends a percentage axis at 100 rather than a tidy number beyond it", () => {
    const option = buildBarOption(input([visible("CSE", { value: "94.6" })], { target: "85" })) as any;
    expect(option.xAxis.max).toBe(100);
  });

  it("lets a percentage axis run past 100 when a value really is above it", () => {
    const option = buildBarOption(input([visible("CSE", { value: "104" })], { target: "85" })) as any;
    expect(option.xAxis.max).toBeGreaterThan(104);
  });

  it("puts the target label at the top, clear of the axis numbers", () => {
    const option = buildBarOption(input([visible("CSE")]));
    expect(series(option).markLine.label.position).toBe("start");
  });

  it("labels each bar tip with the exact rounded figure", () => {
    const option = buildBarOption(input([visible("CSE", { value: "74.96" })]));
    const formatter = series(option).label.formatter;
    expect(formatter({ dataIndex: 0 })).toBe("75.0");
  });

  it("uses one colour for every bar, lightening a stale one and lifting a highlighted one", () => {
    const option = buildBarOption(
      input([visible("CSE"), visible("CIVIL", { stale: true }), visible("ECE")], { highlight: "ECE" }),
    );
    const [plain, stale, picked] = series(option).data;
    expect(stale.itemStyle.opacity).toBeLessThan(1);
    expect(plain.itemStyle.color).not.toBe(picked.itemStyle.color);
    expect(plain.itemStyle.color).toBe(stale.itemStyle.color);
  });

  it("rounds only the data end of a bar", () => {
    const option = buildBarOption(input([visible("CSE")]));
    expect(series(option).itemStyle.borderRadius).toEqual([0, 4, 4, 0]);
  });

  it("switches animation off when asked, for people who prefer reduced motion", () => {
    expect((buildBarOption(input([visible("CSE")], { animate: false })) as any).animation).toBe(false);
    expect((buildBarOption(input([visible("CSE")], { animate: true })) as any).animation).toBe(true);
  });

  it("draws no target line when the KPI has no target", () => {
    const option = buildBarOption(input([visible("CSE")], { target: null }));
    expect(series(option).markLine).toBeUndefined();
  });
});

describe("chartSummary (the screen-reader text)", () => {
  it("lists each department, says what is missing, and gives the target", () => {
    const text = chartSummary(
      input([
        visible("CSE", { value: "80" }),
        visible("MECH", { state: "missing", value: null }),
        { ...visible("ECE"), access: "restricted", state: null, value: null } as DepartmentRow,
      ]),
    );
    expect(text).toContain("Placement percentage by department");
    expect(text).toContain("CSE 80.0%");
    expect(text).toContain("MECH no record");
    expect(text).toContain("ECE restricted");
    expect(text).toContain("Target 75.0%");
  });
});
