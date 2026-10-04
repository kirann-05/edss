"use client";

import { cn } from "cn";
import { useRouter } from "next/navigation";
import { Suspense, useEffect } from "react";

import { landingFor } from "@/components/app-shell/nav";
import { ErrorPanel } from "@/components/error-panel";
import { HealthCellView, HealthLegend } from "@/components/health/health-cell";
import { RefreshButton, RefreshOutcome } from "@/components/health/refresh-button";
import { PageHeader } from "@/components/page-header";
import { PeriodSelect } from "@/components/period-select";
import { HealthBadge } from "@/components/status/status-badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useDataHealth, useMe, useRefreshData } from "@/lib/api/queries";
import { DOMAIN_LABEL, type HealthState } from "@/lib/api/types";
import { usePeriod } from "@/lib/use-period";

export default function DataHealthPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <DataHealth />
    </Suspense>
  );
}

const STATES: HealthState[] = ["fresh", "stale", "missing", "closed"];

function DataHealth() {
  const router = useRouter();
  const me = useMe();
  const { period } = usePeriod();

  const mayView = me.data?.permissions.includes("view_data_health") ?? false;
  const landing = me.data ? landingFor(me.data) : null;
  useEffect(() => {
    if (me.data && !mayView && landing) router.replace(landing);
  }, [me.data, mayView, landing, router]);

  const health = useDataHealth(period, mayView);
  const refresh = useRefreshData();
  const mayRefresh = me.data?.permissions.includes("refresh_data") ?? false;

  if (me.data && !mayView) return null;
  if (health.isPending) return <Skeleton className="h-96 w-full" aria-busy="true" />;
  if (health.isError) {
    return (
      <>
        <PageHeader title="Data health" actions={<PeriodSelect />} />
        <ErrorPanel error={health.error} onRetry={() => health.refetch()} what="data health" />
      </>
    );
  }

  const data = health.data;
  const cellOf = (dept: string, domain: string) => data.cells.find((c) => c.dept_code === dept && c.domain === domain);

  return (
    <>
      <PageHeader
        title="Data health"
        description={
          data.is_current
            ? `How fresh each department's data is for ${data.period_year}, judged against ${data.stale_after_days} days. Each cell shows its oldest record's date and how many records it has.`
            : `${data.period_year} is a closed year, so freshness no longer applies. Gaps are still shown.`
        }
        actions={
          <>
            {mayRefresh && <RefreshButton refresh={refresh} />}
            <PeriodSelect />
          </>
        }
      />

      {mayRefresh && <RefreshOutcome refresh={refresh} />}

      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="Cells by state">
        {STATES.map((state) => (
          <li key={state} className="flex flex-col items-start gap-2 rounded-xl border bg-card p-4">
            <HealthBadge state={state} />
            <span className="text-4xl font-semibold">{data.summary[state]}</span>
          </li>
        ))}
      </ul>

      <Card className={cn(health.isFetching && "opacity-60 transition-opacity")}>
        <CardContent className="overflow-x-auto p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead scope="col" className="min-w-24 whitespace-normal">
                  Department
                </TableHead>
                {data.domains.map((domain) => (
                  <TableHead key={domain} scope="col" className="min-w-24 whitespace-normal">
                    {DOMAIN_LABEL[domain]}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.departments.map((dept) => (
                <TableRow key={dept.code}>
                  <TableHead scope="row" className="align-top whitespace-normal">
                    <span className="text-base font-semibold">{dept.code}</span>
                    <span className="block text-sm font-normal text-muted-foreground">{dept.name}</span>
                  </TableHead>
                  {data.domains.map((domain) => {
                    const cell = cellOf(dept.code, domain);
                    return (
                      <TableCell key={domain} className="align-top whitespace-normal">
                        {cell && <HealthCellView cell={cell} />}
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">What the states mean</h2>
        </CardHeader>
        <CardContent>
          <HealthLegend staleAfterDays={data.stale_after_days} />
        </CardContent>
      </Card>

      <section aria-labelledby="batches" className="flex flex-col gap-3">
        <h2 id="batches" className="text-2xl font-semibold">
          Ingest batches
        </h2>
        <div className="overflow-x-auto rounded-xl border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Batch</TableHead>
                <TableHead>Domain</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>File or view</TableHead>
                <TableHead className="text-right">Rows</TableHead>
                <TableHead className="text-right">Rejected</TableHead>
                <TableHead>Finished</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.batches.map((batch) => (
                <TableRow key={batch.id}>
                  <TableCell className="tabular">{batch.id}</TableCell>
                  <TableCell>{DOMAIN_LABEL[batch.domain]}</TableCell>
                  <TableCell>
                    {batch.source}
                    <span className="block text-sm text-muted-foreground">{batch.owner_office}</span>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{batch.file_ref}</TableCell>
                  <TableCell className="tabular text-right">{batch.row_count}</TableCell>
                  <TableCell className="tabular text-right">{batch.rejected_count}</TableCell>
                  <TableCell className="tabular text-muted-foreground">{batch.finished_at}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>
    </>
  );
}
