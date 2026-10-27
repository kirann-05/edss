"use client";

import { Info, TriangleAlert } from "lucide-react";

import { KpiStatusBadge } from "@/components/status/status-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DOMAIN_LABEL, DOMAIN_TABS, type Figure } from "@/lib/api/types";
import { flagSummaries } from "@/lib/flags";
import { formatNumber, formatVariance, formatWithUnit, roundingHidesMiss } from "@/lib/format";

/** Every KPI in the brief at a glance, grouped by area. The name opens its drill-down. */
export function FigureTable({ figures, onKpi }: { figures: Figure[]; onKpi?: (key: string) => void }) {
  const groups = DOMAIN_TABS.map((domain) => ({ domain, rows: figures.filter((f) => f.domain === domain) })).filter(
    (g) => g.rows.length > 0,
  );
  return (
    <Table className="text-base">
      <TableHeader>
        <TableRow>
          <TableHead className="text-base">KPI</TableHead>
          <TableHead className="text-right text-base">Value and target</TableHead>
          <TableHead className="text-base">Status and gap</TableHead>
        </TableRow>
      </TableHeader>
      {groups.map(({ domain, rows }) => (
        <TableBody key={domain}>
          <TableRow className="hover:bg-transparent">
            <TableHead
              scope="colgroup"
              colSpan={3}
              className="h-auto bg-muted/50 py-1.5 text-xs font-semibold tracking-wider text-muted-foreground uppercase"
            >
              {DOMAIN_LABEL[domain]}
            </TableHead>
          </TableRow>
          {rows.map((figure) => (
            <FigureRow key={figure.key} figure={figure} onKpi={onKpi} />
          ))}
        </TableBody>
      ))}
    </Table>
  );
}

function FigureRow({ figure, onKpi }: { figure: Figure; onKpi?: (key: string) => void }) {
  const hidesMiss =
    figure.target !== null &&
    roundingHidesMiss({ value: figure.value, target: figure.target, precision: figure.precision, status: figure.status });
  const notes = flagSummaries(figure.flags);
  return (
    <TableRow className="align-top">
      <TableCell className="py-2.5 whitespace-normal">
        <div className="flex flex-col gap-0.5">
          {onKpi ? (
            <button
              type="button"
              onClick={() => onKpi(figure.key)}
              className="w-fit text-left font-medium underline-offset-4 outline-none hover:underline focus-visible:underline focus-visible:ring-2 focus-visible:ring-ring"
            >
              {figure.name}
            </button>
          ) : (
            <span className="font-medium">{figure.name}</span>
          )}
          {notes.length > 0 && (
            <span className="flex items-start gap-1 text-sm text-muted-foreground">
              <Info aria-hidden className="mt-0.5 size-3.5 shrink-0" />
              {notes.map((n) => n.text).join(" · ")}
            </span>
          )}
        </div>
      </TableCell>
      <TableCell className="py-2.5 text-right whitespace-normal">
        <span className="block font-semibold tabular-nums">
          {formatWithUnit(figure.value, figure.precision, figure.unit)}
        </span>
        <span className="block text-sm text-muted-foreground tabular-nums">
          target {formatWithUnit(figure.target, figure.precision, figure.unit)}
        </span>
        {hidesMiss && (
          <span className="mt-1 flex items-center justify-end gap-1 text-sm font-medium text-critical-ink">
            <TriangleAlert aria-hidden className="size-4 shrink-0" />
            reads as {formatNumber(figure.value, figure.precision)}, still missed
          </span>
        )}
      </TableCell>
      <TableCell className="py-2.5 whitespace-normal">
        <KpiStatusBadge status={figure.status} />
        <span className="mt-1 block text-sm text-muted-foreground">
          {formatVariance({ varianceAbs: figure.variance_abs, precision: figure.precision, unit: figure.unit })}
        </span>
      </TableCell>
    </TableRow>
  );
}
