"use client";

import { TriangleAlert } from "lucide-react";
import { useId } from "react";

import { KpiStatusBadge } from "@/components/status/status-badge";
import { DOMAIN_LABEL, type KpiOut } from "@/lib/api/types";
import { formatNumber, formatVariance, formatWithUnit, roundingHidesMiss } from "@/lib/format";

import { FlagLine } from "./flag-line";
import { Sparkline } from "./sparkline";

/** "%" sits against the figure, any other unit is smaller text beside it. */
export function UnitText({ unit }: { unit: string }) {
  if (!unit) return null;
  return unit === "%" ? (
    <span className="text-2xl font-medium text-muted-foreground">%</span>
  ) : (
    <span className="text-base text-muted-foreground">{unit}</span>
  );
}

const longDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export function KpiCard({ kpi, onOpen }: { kpi: KpiOut; onOpen: (key: string) => void }) {
  const summaryId = useId();
  const hidesMiss =
    kpi.target !== null &&
    roundingHidesMiss({ value: kpi.value, target: kpi.target, precision: kpi.precision, status: kpi.status });
  const variance = formatVariance({ varianceAbs: kpi.variance_abs, precision: kpi.precision, unit: kpi.unit });
  const shown = formatNumber(kpi.value, kpi.precision);

  return (
    // The title is a real button stretched over the whole card, so a click anywhere opens the
    // drill-down and a keyboard user gets one clear control instead of a card full of tab stops.
    <article className="relative flex h-full w-full flex-col gap-3 rounded-xl border bg-card p-5 shadow-xs transition-shadow hover:shadow-md has-[button:focus-visible]:ring-2 has-[button:focus-visible]:ring-ring">
      <div className="flex flex-col gap-0.5">
        <p className="text-sm text-muted-foreground">{DOMAIN_LABEL[kpi.domain]}</p>
        <h3 className="text-lg leading-snug font-semibold">
          <button
            type="button"
            onClick={() => onOpen(kpi.key)}
            aria-describedby={summaryId}
            className="text-left outline-none after:absolute after:inset-0 after:rounded-xl after:content-['']"
          >
            {kpi.name}
          </button>
        </h3>
      </div>

      <p className="flex items-baseline gap-1.5">
        <span className="text-5xl font-semibold tracking-tight">{shown}</span>
        {kpi.value !== null && <UnitText unit={kpi.unit} />}
      </p>

      <p className="text-base text-muted-foreground">
        Target {formatWithUnit(kpi.target, kpi.precision, kpi.unit)}
      </p>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <KpiStatusBadge status={kpi.status} />
        {kpi.variance_abs !== null && <span className="text-base">{variance}</span>}
      </div>

      {hidesMiss && (
        <p className="flex items-start gap-1.5 text-base font-medium text-critical-ink">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          Reads as {shown} but the target is missed.
        </p>
      )}

      <FlagLine flags={kpi.flags} />

      <div className="mt-auto flex items-end justify-between gap-3 border-t pt-3">
        <div className="text-sm text-muted-foreground">
          {kpi.as_of && <p>Oldest input {longDate(kpi.as_of)}</p>}
          {kpi.placeholder && <p>Placeholder definition</p>}
        </div>
        <Sparkline points={kpi.trend} precision={kpi.precision} unit={kpi.unit} />
      </div>

      <p id={summaryId} className="sr-only">
        {`${DOMAIN_LABEL[kpi.domain]}. Value ${formatWithUnit(kpi.value, kpi.precision, kpi.unit)}. Target ${formatWithUnit(kpi.target, kpi.precision, kpi.unit)}. ${kpi.status.replace("_", " ")}, ${variance}. Opens the drill-down.`}
      </p>
    </article>
  );
}
