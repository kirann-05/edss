import type { TrendPoint } from "@/lib/api/types";
import { formatWithUnit } from "@/lib/format";

const W = 84;
const H = 28;
const PAD = 5;

/**
 * A 3-period trend. De-emphasis grey line, the current period in the accent colour with a ring
 * in the surface colour. No axes: the card already says the value, this only shows direction.
 * A period with no value leaves a gap, it is never drawn as zero.
 */
export function Sparkline({
  points,
  precision,
  unit,
}: {
  points: TrendPoint[];
  precision: number;
  unit: string;
}) {
  const values = points.map((p) => (p.value === null || p.value === undefined ? null : Number(p.value)));
  const defined = values.filter((v): v is number => v !== null);
  if (defined.length < 2) return null;

  const min = Math.min(...defined);
  const span = Math.max(...defined) - min || 1;
  const x = (i: number) => PAD + (i * (W - 2 * PAD)) / Math.max(points.length - 1, 1);
  const y = (v: number) => H - PAD - ((v - min) / span) * (H - 2 * PAD);

  let path = "";
  let penDown = false;
  values.forEach((v, i) => {
    if (v === null) {
      penDown = false;
      return;
    }
    path += `${penDown ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)} `;
    penDown = true;
  });

  const last = values.length - 1;
  const lastValue = values[last];
  const label = points
    .map((p) => `${p.period_year} ${formatWithUnit(p.value, precision, unit)}`)
    .join(", ");

  return (
    <svg
      role="img"
      aria-label={`Trend: ${label}`}
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      className="shrink-0"
    >
      <path d={path} fill="none" stroke="#898781" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
      {lastValue !== null && (
        <circle cx={x(last)} cy={y(lastValue)} r={4} fill="#2a78d6" stroke="#fcfcfb" strokeWidth={2} />
      )}
    </svg>
  );
}
