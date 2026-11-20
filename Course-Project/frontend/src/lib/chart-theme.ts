// Chart colours. ECharts needs concrete values, so these mirror the tokens in globals.css
// (the dataviz reference palette). Keep the two in step. Light theme only for now.
export const CHART = {
  surface: "#fcfcfb",
  ink: "#0b0b0b",
  inkSecondary: "#52514e",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  /** Categorical slot 1. One series, so one colour for every bar (emphasis, not a rainbow) */
  series: "#2a78d6",
  /** The hovered or selected bar lifts one step darker */
  seriesLift: "#1c5cab",
} as const;

/** Bars are thin, never filling the slot (dataviz mark spec: 24px at most) */
export const BAR_THICKNESS = 18;
export const ROW_HEIGHT = 34;
