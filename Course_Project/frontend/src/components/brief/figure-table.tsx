"use client";

import { TriangleAlert } from "lucide-react";

import { FlagLine } from "@/components/kpi/flag-line";
import { KpiStatusBadge } from "@/components/status/status-badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DOMAIN_LABEL, type Figure } from "@/lib/api/types";
import { formatNumber, formatVariance, formatWithUnit, roundingHidesMiss } from "@/lib/format";

/** Every KPI in the brief at a glance. The name opens its drill-down. */
export function FigureTable({ figures, onKpi }: { figures: Figure[]; onKpi?: (key: string) => void }) {
  return (
    <Table className="text-base">
      <TableHeader>
        <TableRow>
          <TableHead className="text-base">KPI</TableHead>
          <TableHead className="text-right text-base">Value and target</TableHead>
          <TableHead className="text-base">Status and gap</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {figures.map((figure) => {
          const hidesMiss =
            figure.target !== null &&
            roundingHidesMiss({
              value: figure.value,
              target: figure.target,
              precision: figure.precision,
              status: figure.status,
            });
          return (
            <TableRow key={figure.key} className="align-top">
              <TableCell className="py-3 whitespace-normal">
                <div className="flex flex-col gap-1">
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
                  <span className="text-sm text-muted-foreground">
                    {DOMAIN_LABEL[figure.domain]}
                    {figure.placeholder ? " · placeholder definition" : ""}
                  </span>
                  <FlagLine flags={figure.flags} className="mt-1" />
                </div>
              </TableCell>
              <TableCell className="py-3 text-right whitespace-normal">
                <span className="block text-lg font-semibold tabular-nums">
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
              <TableCell className="py-3 whitespace-normal">
                <KpiStatusBadge status={figure.status} />
                <span className="mt-1 block text-sm text-muted-foreground">
                  {formatVariance({ varianceAbs: figure.variance_abs, precision: figure.precision, unit: figure.unit })}
                </span>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
