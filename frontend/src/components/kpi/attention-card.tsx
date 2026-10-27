"use client";

import { cn } from "cn";
import { ChevronRight, TriangleAlert } from "lucide-react";
import { useId } from "react";

import { KpiStatusBadge } from "@/components/status/status-badge";
import { DOMAIN_LABEL, type KpiOut } from "@/lib/api/types";
import { formatNumber, formatVariance, formatWithUnit, roundingHidesMiss } from "@/lib/format";

import { FlagLine } from "./flag-line";
import { UnitText } from "./unit-text";
import { Sparkline } from "./sparkline";

/**
 * A KPI that is missed or at risk, given room: the figure, the gap in words, what the data
 * cannot support, and the trend. The whole card opens the drill-down.
 */
export function AttentionCard({ kpi, onOpen }: { kpi: KpiOut; onOpen: (key: string) => void }) {
  const summaryId = useId();
  const missed = kpi.status === "missed";
  const hidesMiss =
    kpi.target !== null &&
    roundingHidesMiss({ value: kpi.value, target: kpi.target, precision: kpi.precision, status: kpi.status });
  const variance = formatVariance({ varianceAbs: kpi.variance_abs, precision: kpi.precision, unit: kpi.unit });
  const shown = formatNumber(kpi.value, kpi.precision);

  return (
    <article
      className={cn(
        "relative flex h-full w-full flex-col gap-4 overflow-hidden rounded-xl border bg-card p-5 pl-6 shadow-xs transition-shadow hover:shadow-md",
        "has-[button:focus-visible]:ring-2 has-[button:focus-visible]:ring-ring",
        // a stripe in the status colour, so the kind of problem reads before the words do
        "before:absolute before:inset-y-0 before:left-0 before:w-1.5 before:content-['']",
        missed ? "before:bg-critical-mark" : "before:bg-warning-mark",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          <p className="text-sm text-muted-foreground">{DOMAIN_LABEL[kpi.domain]}</p>
          <h3 className="text-lg leading-snug font-semibold">
            <button
              type="button"
              onClick={() => onOpen(kpi.key)}
              aria-describedby={summaryId}
              className="text-left outline-none after:absolute after:inset-0 after:content-['']"
            >
              {kpi.name}
            </button>
          </h3>
        </div>
        <KpiStatusBadge status={kpi.status} />
      </div>

      <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="flex flex-col gap-1">
          <p className="flex items-baseline gap-1.5">
            <span className="text-5xl font-semibold tracking-tight tabular-nums">{shown}</span>
            {kpi.value !== null && <UnitText unit={kpi.unit} />}
          </p>
          <p className="text-base text-muted-foreground">
            Target {formatWithUnit(kpi.target, kpi.precision, kpi.unit)}
            {kpi.variance_abs !== null && (
              <>
                {" · "}
                <span className={cn("font-medium", missed ? "text-critical-ink" : "text-warning-ink")}>{variance}</span>
              </>
            )}
          </p>
        </div>
        <Sparkline points={kpi.trend} precision={kpi.precision} unit={kpi.unit} />
      </div>

      {hidesMiss && (
        <p className="flex items-start gap-1.5 text-base font-medium text-critical-ink">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          Reads as {shown} but the target is missed.
        </p>
      )}

      <FlagLine flags={kpi.flags} />

      <p className="mt-auto flex items-center gap-1 text-sm font-medium text-primary" aria-hidden>
        See how it is calculated
        <ChevronRight className="size-4" />
      </p>

      <p id={summaryId} className="sr-only">
        {`${DOMAIN_LABEL[kpi.domain]}. Value ${formatWithUnit(kpi.value, kpi.precision, kpi.unit)}. Target ${formatWithUnit(kpi.target, kpi.precision, kpi.unit)}. ${kpi.status.replace("_", " ")}, ${variance}. Opens the drill-down.`}
      </p>
    </article>
  );
}
