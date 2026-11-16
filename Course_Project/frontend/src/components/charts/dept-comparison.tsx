"use client";

import { BarChart3, Table2 } from "lucide-react";
import { useState } from "react";

import { DeptStateBadge } from "@/components/status/dept-state-badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DepartmentRow, KpiOut } from "@/lib/api/types";
import { formatFigure, formatWithUnit } from "@/lib/format";

import { DeptBarChart } from "./dept-bar-chart";

type Kpi = Pick<KpiOut, "name" | "unit" | "precision" | "target">;

/** Department by department for one KPI: a chart, and its table twin for anyone who needs it. */
export function DeptComparison({
  kpi,
  rows,
  highlight,
  refetching,
  showInputs = false,
}: {
  kpi: Kpi;
  rows: DepartmentRow[];
  highlight?: string | null;
  refetching?: boolean;
  /** Add each department's own inputs (for example students placed and registered) to the table */
  showInputs?: boolean;
}) {
  const [view, setView] = useState<"chart" | "table">("chart");

  return (
    <div className="flex flex-col gap-2">
      <div role="group" aria-label={`View ${kpi.name} by department as`} className="flex gap-1 self-end">
        <Button
          type="button"
          size="sm"
          variant={view === "chart" ? "secondary" : "ghost"}
          aria-pressed={view === "chart"}
          onClick={() => setView("chart")}
        >
          <BarChart3 aria-hidden /> Chart
        </Button>
        <Button
          type="button"
          size="sm"
          variant={view === "table" ? "secondary" : "ghost"}
          aria-pressed={view === "table"}
          onClick={() => setView("table")}
        >
          <Table2 aria-hidden /> Table
        </Button>
      </div>

      {view === "chart" ? (
        <DeptBarChart
          name={kpi.name}
          unit={kpi.unit}
          precision={kpi.precision}
          target={kpi.target}
          rows={rows}
          highlight={highlight}
          refetching={refetching}
        />
      ) : (
        <DeptTable kpi={kpi} rows={rows} highlight={highlight} showInputs={showInputs} />
      )}
    </div>
  );
}

function DeptTable({
  kpi,
  rows,
  highlight,
  showInputs,
}: {
  kpi: Kpi;
  rows: DepartmentRow[];
  highlight?: string | null;
  showInputs: boolean;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Department</TableHead>
          <TableHead className="text-right">{kpi.name}</TableHead>
          {showInputs && <TableHead>Inputs</TableHead>}
          <TableHead>Note</TableHead>
          <TableHead>Oldest input</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.dept_code} data-highlight={row.dept_code === highlight || undefined} className="data-[highlight]:bg-accent">
            <TableCell className="font-medium">
              {row.dept_code}
              <span className="sr-only">, {row.dept_name}</span>
            </TableCell>
            <TableCell className="tabular text-right text-base">
              {row.access === "visible" && row.state === "ok"
                ? formatWithUnit(row.value, kpi.precision, kpi.unit)
                : "n/a"}
            </TableCell>
            {showInputs && (
              <TableCell className="text-sm text-muted-foreground">
                {row.inputs.map((input) => (
                  <p key={input.label}>
                    {input.description}: <span className="tabular text-foreground">{formatFigure(input.value)}</span>
                  </p>
                ))}
              </TableCell>
            )}
            <TableCell>
              <DeptStateBadge row={row} />
            </TableCell>
            <TableCell className="tabular text-muted-foreground">{row.as_of ?? ""}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
