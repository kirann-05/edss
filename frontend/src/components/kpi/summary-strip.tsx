"use client";

import { cn } from "cn";

import type { KpiList, KpiStatus } from "@/lib/api/types";
import { KPI_STATUS, TONE_CLASS } from "@/lib/status";

const ORDER: KpiStatus[] = ["missed", "at_risk", "met", "undefined"];

/** Counts by status. Each tile also filters the grid below, so the strip is both summary and filter. */
export function SummaryStrip({
  summary,
  active,
  onChange,
}: {
  summary: KpiList["summary"];
  active: KpiStatus | null;
  onChange: (status: KpiStatus | null) => void;
}) {
  return (
    <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="KPIs by status">
      {ORDER.map((status) => {
        const style = KPI_STATUS[status];
        const Icon = style.icon;
        const pressed = active === status;
        return (
          <li key={status}>
            <button
              type="button"
              aria-pressed={pressed}
              onClick={() => onChange(pressed ? null : status)}
              className={cn(
                "flex w-full items-center gap-3 rounded-xl border bg-card px-4 py-3 text-left transition-colors hover:bg-accent",
                pressed && "ring-2 ring-ring",
              )}
            >
              <span className={cn("grid size-10 shrink-0 place-items-center rounded-lg border", TONE_CLASS[style.tone])}>
                <Icon aria-hidden className="size-5" />
              </span>
              <span className="flex flex-col">
                <span className="text-3xl leading-none font-semibold">{summary[status]}</span>
                <span className="mt-1 text-base text-muted-foreground">{style.label}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
