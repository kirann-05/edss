"use client";

import { cn } from "cn";
import { Info } from "lucide-react";

import { KpiStatusBadge } from "@/components/status/status-badge";
import { DOMAIN_LABEL, DOMAIN_TABS, type KpiOut } from "@/lib/api/types";
import { formatVariance, formatWithUnit } from "@/lib/format";
import { flagSummaries } from "@/lib/flags";

import { Sparkline } from "./sparkline";

/**
 * Every KPI on one screen: grouped by area, one row each, so a leader can scan 13 figures in a
 * few seconds. The name opens the drill-down; data caveats are counted here and spelled out there.
 */
export function KpiTable({ kpis, onOpen }: { kpis: KpiOut[]; onOpen: (key: string) => void }) {
  const groups = DOMAIN_TABS.map((domain) => ({ domain, rows: kpis.filter((k) => k.domain === domain) })).filter(
    (g) => g.rows.length > 0,
  );

  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table className="w-full text-base">
        <caption className="sr-only">Every KPI for the period, grouped by area</caption>
        <thead>
          <tr className="border-b text-left text-sm text-muted-foreground">
            <th scope="col" className="px-4 py-2.5 font-medium">KPI</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Value</th>
            <th scope="col" className="px-4 py-2.5 text-right font-medium">Target</th>
            <th scope="col" className="hidden px-4 py-2.5 font-medium xl:table-cell">Gap</th>
            <th scope="col" className="px-4 py-2.5 font-medium">Status</th>
            <th scope="col" className="hidden px-4 py-2.5 font-medium 2xl:table-cell">
              <span className="sr-only">Trend over three years</span>
              <span aria-hidden>Trend</span>
            </th>
          </tr>
        </thead>
        {groups.map(({ domain, rows }) => (
          <tbody key={domain} className="border-b last:border-b-0">
            <tr>
              <th
                scope="colgroup"
                colSpan={6}
                className="bg-muted/50 px-4 py-1.5 text-left text-xs font-semibold tracking-wider text-muted-foreground uppercase"
              >
                {DOMAIN_LABEL[domain]}
              </th>
            </tr>
            {rows.map((kpi) => (
              <Row key={kpi.key} kpi={kpi} onOpen={onOpen} />
            ))}
          </tbody>
        ))}
      </table>
    </div>
  );
}

function Row({ kpi, onOpen }: { kpi: KpiOut; onOpen: (key: string) => void }) {
  const notes = flagSummaries(kpi.flags);
  const offTarget = kpi.status === "missed" || kpi.status === "at_risk";
  return (
    <tr className="border-t transition-colors first:border-t-0 hover:bg-accent/60">
      <th scope="row" className="min-w-56 px-4 py-2.5 text-left font-normal">
        <button
          type="button"
          onClick={() => onOpen(kpi.key)}
          className="rounded-sm text-left font-medium underline-offset-4 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {kpi.name}
        </button>
        {notes.length > 0 && (
          <span
            className="mt-0.5 flex items-center gap-1 text-sm text-muted-foreground"
            title={notes.map((n) => n.text).join(" · ")}
          >
            <Info aria-hidden className="size-3.5 shrink-0" />
            {notes.length === 1 ? notes[0].text : `${notes.length} data notes`}
            <span className="sr-only">: {notes.map((n) => n.text).join(", ")}</span>
          </span>
        )}
      </th>
      <td className={cn("px-4 py-2.5 text-right font-semibold whitespace-nowrap tabular-nums", offTarget && "text-lg")}>
        {formatWithUnit(kpi.value, kpi.precision, kpi.unit)}
      </td>
      <td className="px-4 py-2.5 text-right whitespace-nowrap text-muted-foreground tabular-nums">
        {formatWithUnit(kpi.target, kpi.precision, kpi.unit)}
      </td>
      <td className="hidden px-4 py-2.5 text-sm whitespace-nowrap text-muted-foreground xl:table-cell">
        {kpi.variance_abs !== null
          ? formatVariance({ varianceAbs: kpi.variance_abs, precision: kpi.precision, unit: kpi.unit })
          : "No value"}
      </td>
      <td className="px-4 py-2.5">
        <KpiStatusBadge status={kpi.status} />
      </td>
      <td className="hidden px-4 py-2.5 2xl:table-cell">
        <Sparkline points={kpi.trend} precision={kpi.precision} unit={kpi.unit} />
      </td>
    </tr>
  );
}
