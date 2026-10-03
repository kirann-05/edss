// Builds the ECharts option for a department comparison. Kept free of React and the DOM
// (apart from the tooltip, which only runs on hover) so the rules below are unit-tested.
//
//   * one series, so one colour for every bar: emphasis, not a rainbow
//   * bars start at zero and are thin, with a rounded tip and a square baseline
//   * a department with no figure gets no bar and says why, it is never drawn as zero
//   * the value sits at the bar tip in ink (text never wears the data colour)
//   * the institution target is a solid line with a direct label
//   * tooltips are built with textContent, because names are untrusted data
import type { EChartsCoreOption } from "echarts/core";

import type { DepartmentRow } from "@/lib/api/types";
import { BAR_THICKNESS, CHART } from "@/lib/chart-theme";
import { formatNumber, formatWithUnit } from "@/lib/format";

export interface BarChartInput {
  name: string;
  unit: string;
  precision: number;
  target: string | null;
  rows: DepartmentRow[];
  highlight?: string | null;
  animate: boolean;
}

const NO_BAR_WORDS: Record<string, string> = {
  missing: "no record",
  excluded: "excluded",
  undefined: "undefined",
};

const hasBar = (row: DepartmentRow) =>
  row.access === "visible" && row.state === "ok" && row.value !== null;

/** The category label, which also explains a missing bar. */
export function rowLabel(row: DepartmentRow): string {
  if (row.access === "restricted") return `${row.dept_code} (restricted)`;
  if (row.state === "ok") return row.stale ? `${row.dept_code} (stale)` : row.dept_code;
  return `${row.dept_code} (${NO_BAR_WORDS[row.state ?? ""] ?? "no figure"})`;
}

/** Text for a screen reader. The chart is a picture, so this says what it shows. */
export function chartSummary(input: BarChartInput): string {
  const parts = input.rows.map((row) => {
    if (row.access === "restricted") return `${row.dept_code} restricted`;
    if (hasBar(row)) {
      const stale = row.stale ? " (stale)" : "";
      return `${row.dept_code} ${formatWithUnit(row.value, input.precision, input.unit)}${stale}`;
    }
    return `${row.dept_code} ${NO_BAR_WORDS[row.state ?? ""] ?? "no figure"}`;
  });
  const target =
    input.target === null
      ? ""
      : ` Target ${formatWithUnit(input.target, input.precision, input.unit)}.`;
  return `${input.name} by department. ${parts.join(", ")}.${target}`;
}

const NICE_STEPS = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10];

/** A tidy axis end with room for the labels: 84.6 gives 100, 2.65 gives 3, 2199 gives 2500. */
function niceMax(value: number): number {
  if (value <= 0) return 1;
  const padded = value * 1.1;
  const magnitude = 10 ** Math.floor(Math.log10(padded));
  const step = NICE_STEPS.find((s) => s * magnitude >= padded) ?? 10;
  return step * magnitude;
}

function tooltipElement(row: DepartmentRow, input: BarChartInput): HTMLElement {
  const root = document.createElement("div");
  root.style.cssText = "font-size:13px;line-height:1.4;min-width:140px";

  const value = document.createElement("div");
  value.style.cssText = "font-size:15px;font-weight:600";
  value.textContent = formatWithUnit(row.value, input.precision, input.unit);

  const name = document.createElement("div");
  name.style.color = CHART.inkSecondary;
  name.textContent = row.dept_name;

  root.append(value, name);
  const note = row.stale
    ? `Stale. Oldest input ${row.as_of ?? "unknown"}`
    : row.as_of
      ? `Oldest input ${row.as_of}`
      : null;
  if (note) {
    const line = document.createElement("div");
    line.style.color = CHART.inkSecondary;
    line.textContent = note;
    root.append(line);
  }
  return root;
}

export function buildBarOption(input: BarChartInput): EChartsCoreOption {
  const target = input.target === null ? null : Number(input.target);
  const numbers = input.rows.map((row) => (hasBar(row) ? Number(row.value) : null));
  const longest = Math.max(0, target ?? 0, ...numbers.filter((n): n is number => n !== null));

  const data = input.rows.map((row, index) =>
    numbers[index] === null
      ? null
      : {
          value: numbers[index],
          itemStyle: {
            color: row.dept_code === input.highlight ? CHART.seriesLift : CHART.series,
            opacity: row.stale ? 0.55 : 1,
          },
        },
  );

  return {
    animation: input.animate,
    grid: { left: 150, right: 56, top: target === null ? 8 : 28, bottom: 24 },
    tooltip: {
      trigger: "item",
      confine: true,
      backgroundColor: CHART.surface,
      borderColor: CHART.axis,
      borderWidth: 1,
      textStyle: { color: CHART.ink },
      formatter: (params: { dataIndex: number }) =>
        tooltipElement(input.rows[params.dataIndex], input),
    },
    xAxis: {
      type: "value",
      min: 0,
      max: input.unit === "%" && longest <= 100 ? 100 : niceMax(longest),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: CHART.inkSecondary, fontSize: 13 },
      splitLine: { lineStyle: { color: CHART.grid, width: 1, type: "solid" } },
    },
    yAxis: {
      type: "category",
      inverse: true,
      data: input.rows.map(rowLabel),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: CHART.axis, width: 1 } },
      axisLabel: { color: CHART.ink, fontSize: 13, width: 140, overflow: "break" },
    },
    series: [
      {
        type: "bar",
        data,
        barWidth: BAR_THICKNESS,
        itemStyle: { borderRadius: [0, 4, 4, 0] },
        emphasis: { itemStyle: { color: CHART.seriesLift } },
        label: {
          show: true,
          position: "right",
          color: CHART.ink,
          fontSize: 13,
          formatter: (params: { dataIndex: number }) =>
            formatNumber(input.rows[params.dataIndex].value, input.precision),
        },
        ...(target === null
          ? {}
          : {
              markLine: {
                silent: true,
                symbol: "none",
                lineStyle: { color: CHART.ink, width: 2, type: "solid" },
                label: {
                  formatter: `Target ${formatNumber(input.target, input.precision)}`,
                  position: "start", // the top, because the department axis runs downward
                  color: CHART.ink,
                  fontSize: 13,
                },
                data: [{ xAxis: target }],
              },
            }),
      },
    ],
  };
}
