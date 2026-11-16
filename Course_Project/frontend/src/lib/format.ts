// Display formatting for numbers that come from the KPI engine.
//
// The API sends every figure as a plain decimal string (never a float), already computed
// from unrounded values. The UI only decides how many places to show. Rounding is done on
// the string with BigInt so it is exact: 1.005 rounds to 1.01, not the 1.00 that
// Number.prototype.toFixed gives. Rule 5: a missed target is never hidden by rounding.

const PLAIN_DECIMAL = /^-?\d+(\.\d+)?$/;

/** Round a plain decimal string half away from zero to a fixed number of places. */
export function roundDecimal(input: string, places: number): string {
  if (!PLAIN_DECIMAL.test(input)) {
    throw new Error(`Not a plain decimal string: ${JSON.stringify(input)}`);
  }
  const negative = input.startsWith("-");
  const [intPart, fracPart = ""] = (negative ? input.slice(1) : input).split(".");

  // one extra digit is needed to decide the rounding
  const padded = fracPart.padEnd(places + 1, "0");
  const kept = BigInt(intPart + padded.slice(0, places));
  const scaled = Number(padded[places]) >= 5 ? kept + 1n : kept;

  const digits = scaled.toString().padStart(places + 1, "0");
  const whole = digits.slice(0, digits.length - places);
  const fraction = places > 0 ? `.${digits.slice(-places)}` : "";
  // a value that rounds to zero is just zero, never "-0.0"
  return `${negative && scaled !== 0n ? "-" : ""}${whole}${fraction}`;
}

function group(whole: string): string {
  return whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** Fixed places with thousands grouping. An undefined value is shown as n/a, never as zero. */
export function formatNumber(value: string | null | undefined, places: number): string {
  if (value === null || value === undefined) return "n/a";
  const rounded = roundDecimal(value, places);
  const negative = rounded.startsWith("-");
  const [whole, fraction] = (negative ? rounded.slice(1) : rounded).split(".");
  return `${negative ? "-" : ""}${group(whole)}${fraction === undefined ? "" : `.${fraction}`}`;
}

export type KpiStatus = "met" | "at_risk" | "missed" | "undefined";

/**
 * True when a missed KPI would read as equal to its target at the display precision,
 * for example 74.96 against 75 shown to one place. The UI must then say so out loud.
 */
export function roundingHidesMiss(input: {
  value: string | null | undefined;
  target: string;
  precision: number;
  status: KpiStatus;
}): boolean {
  if (input.status !== "missed" || input.value === null || input.value === undefined) return false;
  return roundDecimal(input.value, input.precision) === roundDecimal(input.target, input.precision);
}

const MAX_VARIANCE_PLACES = 4;

function isZero(decimal: string): boolean {
  return /^-?0+(\.0+)?$/.test(decimal);
}

/**
 * Words for the gap to target, for example "3.4 pts below target". Starts at the KPI's
 * display precision and adds places until the gap is visible, so a real shortfall is
 * never printed as "0.0 below target".
 */
export function formatVariance(input: {
  varianceAbs: string | null | undefined;
  precision: number;
  unit: string;
}): string {
  if (input.varianceAbs === null || input.varianceAbs === undefined) return "no target gap";
  if (isZero(input.varianceAbs)) return "on target";

  const direction = input.varianceAbs.startsWith("-") ? "below target" : "above target";
  const magnitude = input.varianceAbs.replace(/^-/, "");
  const unit = input.unit === "%" ? "pts" : input.unit;
  const withUnit = (amount: string) => [amount, unit, direction].filter(Boolean).join(" ");

  for (let places = input.precision; places <= MAX_VARIANCE_PLACES; places += 1) {
    const rounded = roundDecimal(magnitude, places);
    if (!isZero(rounded)) return withUnit(rounded);
  }
  return withUnit(`under ${roundDecimal("0.0001", MAX_VARIANCE_PLACES)}`);
}

/** A figure with its unit: "75.0%", "6.24 LPA", "2.65 level". Undefined is n/a, never zero. */
export function formatWithUnit(
  value: string | null | undefined,
  places: number,
  unit: string,
): string {
  const figure = formatNumber(value, places);
  if (value === null || value === undefined || unit === "") return figure;
  return unit === "%" ? `${figure}%` : `${figure} ${unit}`;
}

/** A raw input or record: whole numbers stay whole, anything else to two places. */
export function formatFigure(value: string): string {
  return formatNumber(value, value.includes(".") ? 2 : 0);
}

/** The exact figure without a long tail: up to four places, trailing zeros removed. */
export function formatExact(value: string): string {
  const rounded = roundDecimal(value, 4);
  return rounded.includes(".") ? rounded.replace(/0+$/, "").replace(/\.$/, "") : rounded;
}
