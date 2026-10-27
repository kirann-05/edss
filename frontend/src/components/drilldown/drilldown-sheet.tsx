"use client";

import { Info, Lock, TriangleAlert } from "lucide-react";
import Link from "next/link";

import { DeptComparison } from "@/components/charts/dept-comparison";
import { FlagLine } from "@/components/kpi/flag-line";
import { UnitText } from "@/components/kpi/unit-text";
import { FactStatusBadge, KpiStatusBadge } from "@/components/status/status-badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useKpiDrilldown } from "@/lib/api/queries";
import { DOMAIN_LABEL, type KpiDrilldown } from "@/lib/api/types";
import {
  formatExact,
  formatFigure,
  formatNumber,
  formatVariance,
  formatWithUnit,
  roundingHidesMiss,
} from "@/lib/format";
import { restoreDrilldownFocus, useDrilldownParam } from "@/lib/use-drilldown-param";

import { ErrorPanel } from "../error-panel";

/**
 * KPI to source in one place (FR-6): the figure, how it is built, each department's part in it,
 * and every record behind it with its status and where it came from.
 */
export function DrilldownSheet({ period }: { period?: string }) {
  const { kpi, dept, close } = useDrilldownParam();
  const query = useKpiDrilldown(kpi, period);

  return (
    <Sheet open={kpi !== null} onOpenChange={(open) => !open && close()}>
      <SheetContent
        onCloseAutoFocus={restoreDrilldownFocus}
        className="w-full gap-0 overflow-y-auto data-[side=right]:sm:max-w-[780px]"
      >
        {query.data ? (
          <Body data={query.data} highlight={dept} period={period} />
        ) : (
          <>
            <SheetHeader className="p-6 pb-2">
              <SheetTitle className="text-2xl">KPI drill-down</SheetTitle>
              <SheetDescription className="text-base">
                {query.isError ? "This drill-down could not be loaded." : "Loading the figure and its sources."}
              </SheetDescription>
            </SheetHeader>
            <div className="p-6 pt-2">
              {query.isError ? (
                <ErrorPanel error={query.error} onRetry={() => query.refetch()} what="this drill-down" />
              ) : (
                <div className="flex flex-col gap-4">
                  <Skeleton className="h-16 w-48" />
                  <Skeleton className="h-40 w-full" />
                  <Skeleton className="h-64 w-full" />
                </div>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function Body({ data, highlight, period }: { data: KpiDrilldown; highlight: string | null; period?: string }) {
  const { kpi } = data;
  const shown = formatNumber(kpi.value, kpi.precision);
  const hidesMiss =
    kpi.target !== null &&
    roundingHidesMiss({ value: kpi.value, target: kpi.target, precision: kpi.precision, status: kpi.status });

  return (
    <>
      <SheetHeader className="p-6 pb-2">
        <SheetTitle className="pr-10 text-2xl">{kpi.name}</SheetTitle>
        <SheetDescription className="text-base">
          {DOMAIN_LABEL[kpi.domain]} · {kpi.key} · definition version {kpi.version} · {kpi.period_year}
        </SheetDescription>
      </SheetHeader>

      <div className="flex flex-col gap-8 p-6 pt-4">
        <Section title="The figure">
          <p className="flex items-baseline gap-2">
            <span className="text-6xl font-semibold tracking-tight">{shown}</span>
            {kpi.value !== null && <UnitText unit={kpi.unit} />}
          </p>
          <p className="text-base text-muted-foreground">
            Target {formatWithUnit(kpi.target, kpi.precision, kpi.unit)}
          </p>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <KpiStatusBadge status={kpi.status} />
            {kpi.variance_abs !== null && (
              <span className="text-base">
                {formatVariance({ varianceAbs: kpi.variance_abs, precision: kpi.precision, unit: kpi.unit })}
              </span>
            )}
          </div>
          {hidesMiss && (
            <p className="flex items-start gap-2 text-base font-medium text-critical-ink">
              <TriangleAlert aria-hidden className="mt-0.5 size-5 shrink-0" />
              Shown to {kpi.precision} {kpi.precision === 1 ? "place" : "places"} this reads as {shown}, the same as the
              target. It is missed: the exact figure is {kpi.value ? formatExact(kpi.value) : "not available"}.
            </p>
          )}
          <FlagLine flags={kpi.flags} />
        </Section>

        <Section title="How it is calculated">
          <p className="text-base">{kpi.formula_text}</p>
          <p className="text-sm text-muted-foreground">
            As written in the definition: <code className="font-mono text-foreground">{kpi.formula}</code>
          </p>
          {data.inputs.length > 0 && (
            <dl className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-1 rounded-lg border bg-card p-4 text-base">
              {data.inputs.map((input) => (
                <div key={input.label} className="contents">
                  <dt className="text-muted-foreground">{input.description}</dt>
                  <dd className="tabular text-right font-medium">{formatFigure(input.value)}</dd>
                </div>
              ))}
            </dl>
          )}
          {kpi.placeholder && (
            <p className="flex items-start gap-2 text-sm text-muted-foreground">
              <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
              {kpi.note ?? "Placeholder definition pending IQAC."}
            </p>
          )}
        </Section>

        <Section title="By department">
          {data.access === "restricted" && (
            <p className="flex items-start gap-2 text-sm text-muted-foreground">
              <Lock aria-hidden className="mt-0.5 size-4 shrink-0" />
              You can see the institution figure and your own department. Other departments are shown as
              restricted.
            </p>
          )}
          <DeptComparison kpi={kpi} rows={data.departments} highlight={highlight} showInputs />
          {data.spread && kpi.unit === "%" && (
            <p className="rounded-lg border bg-card p-4 text-base">
              The institution figure of <strong>{formatWithUnit(kpi.value, kpi.precision, kpi.unit)}</strong> is built from
              totals, not by averaging departments. A simple average of the {data.spread.count} department values would
              give <strong>{formatWithUnit(data.spread.simple_mean, kpi.precision, kpi.unit)}</strong>, which weights a
              small department the same as a large one.
            </p>
          )}
        </Section>

        <Section title="Source records">
          <p className="text-sm text-muted-foreground">
            {data.facts.length} record{data.facts.length === 1 ? "" : "s"} behind this figure.
            {data.facts_hidden > 0 &&
              ` ${data.facts_hidden} more belong to departments you cannot see.`}
          </p>
          <div className="overflow-x-auto rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Department</TableHead>
                  <TableHead>Record</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Source</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.facts.map((fact) => (
                  <TableRow key={fact.id} className={fact.used ? undefined : "bg-neutral-tint/60"}>
                    <TableCell className="font-medium">{fact.dept_code}</TableCell>
                    <TableCell>
                      {fact.metric_label}
                      <span className="text-muted-foreground"> · {fact.period_sub}</span>
                    </TableCell>
                    <TableCell className="tabular text-right">
                      {formatFigure(fact.value)}
                      <span className="text-muted-foreground"> {fact.unit}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col items-start gap-1">
                        <FactStatusBadge status={fact.status} />
                        {!fact.used && <span className="text-sm font-medium">Kept out of the figure</span>}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">
                      <p>{fact.source_system}</p>
                      <p className="font-mono text-xs text-muted-foreground">{fact.source_ref}</p>
                      <p className="tabular text-xs text-muted-foreground">As of {fact.as_of}</p>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Section>

        <Link
          href={period ? `/data-health?period=${period}` : "/data-health"}
          className="text-base font-medium text-primary underline-offset-4 hover:underline"
        >
          Open data health
        </Link>
      </div>
    </>
  );
}
