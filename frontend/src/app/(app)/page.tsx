"use client";

import { cn } from "cn";
import { Info } from "lucide-react";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { landingFor } from "@/components/app-shell/nav";
import { DomainTabs } from "@/components/domain/domain-tabs";
import { DrilldownSheet } from "@/components/drilldown/drilldown-sheet";
import { ErrorPanel } from "@/components/error-panel";
import { DataQualityNotice } from "@/components/kpi/data-quality-notice";
import { AttentionCard } from "@/components/kpi/attention-card";
import { KpiTable } from "@/components/kpi/kpi-table";
import { SummaryStrip } from "@/components/kpi/summary-strip";
import { PageHeader } from "@/components/page-header";
import { PeriodSelect } from "@/components/period-select";
import { CurrentReportCard } from "@/components/reports/current-report-card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { useKpis, useMe } from "@/lib/api/queries";
import type { KpiStatus } from "@/lib/api/types";
import { KPI_STATUS } from "@/lib/status";
import { useDrilldownParam } from "@/lib/use-drilldown-param";
import { usePeriod } from "@/lib/use-period";

const longDate = (iso: string) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

export default function DashboardPage() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <Dashboard />
    </Suspense>
  );
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6" aria-busy="true">
      <Skeleton className="h-10 w-72" />
      <Skeleton className="h-20 w-full" />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-72" />
        ))}
      </div>
    </div>
  );
}

function Dashboard() {
  const router = useRouter();
  const me = useMe();
  const { period } = usePeriod();
  const { open } = useDrilldownParam();
  const [filter, setFilter] = useState<KpiStatus | null>(null);

  // A role with no dashboard (the Governing Council, an administrator) goes to its own first page
  const mayView = me.data?.permissions.includes("view_dashboard") ?? false;
  const landing = me.data ? landingFor(me.data) : null;
  useEffect(() => {
    if (me.data && !mayView && landing) router.replace(landing);
  }, [me.data, mayView, landing, router]);

  const kpis = useKpis(period, mayView);

  if (me.data && !mayView) {
    return landing ? null : (
      <div className="flex max-w-xl flex-col gap-2">
        <h1 className="text-3xl font-semibold">Welcome</h1>
        <p className="text-base text-muted-foreground">
          Approved reports will appear here once they are published. Nothing is waiting for you yet.
        </p>
      </div>
    );
  }
  if (kpis.isPending) return <DashboardSkeleton />;
  if (kpis.isError) {
    return (
      <>
        <PageHeader title="Institution KPIs" actions={<PeriodSelect />} />
        <ErrorPanel error={kpis.error} onRetry={() => kpis.refetch()} what="the KPIs" />
      </>
    );
  }

  const data = kpis.data;
  const offTarget = data.kpis.filter((k) => k.status === "missed" || k.status === "at_risk");
  // missed before at risk, then the catalogue's own order
  offTarget.sort((a, b) => (a.status === b.status ? 0 : a.status === "missed" ? -1 : 1));
  const shown = filter ? data.kpis.filter((k) => k.status === filter) : data.kpis;
  const placeholders = data.kpis.filter((k) => k.placeholder).length;
  const refreshing = kpis.isFetching;

  return (
    <>
      <PageHeader
        title="Institution KPIs"
        description={
          <>
            {data.period_year}
            {data.is_current ? " (current)" : ""}
            {data.newest_as_of && <> · newest data {longDate(data.newest_as_of)}</>}
            {data.oldest_as_of && <> · oldest input {longDate(data.oldest_as_of)}</>}
          </>
        }
        actions={<PeriodSelect />}
      />

      <div className="grid grid-cols-1 gap-6 2xl:grid-cols-[minmax(0,1fr)_20rem]">
        {/* context first on a narrow screen, a side column on a wide one */}
        <aside aria-label="About these figures" className="grid content-start gap-4 md:grid-cols-3 2xl:order-last 2xl:grid-cols-1">
          {me.data?.permissions.includes("view_reports") && <CurrentReportCard />}
          <DataQualityNotice kpis={data.kpis} period={period} />
          {placeholders > 0 && (
            <Alert>
              <Info aria-hidden />
              <AlertDescription className="text-sm">
                {placeholders} of {data.kpis.length} KPI definitions and targets are placeholders pending IQAC approval.
                They show how the system works and are not the university&apos;s official figures.
              </AlertDescription>
            </Alert>
          )}
        </aside>

        <div className={cn("flex min-w-0 flex-col gap-8", refreshing && "opacity-60 transition-opacity")}>
          <SummaryStrip summary={data.summary} active={filter} onChange={setFilter} />

          {offTarget.length > 0 && !filter && (
            <section aria-labelledby="attention" className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <h2 id="attention" className="text-xl font-semibold">
                  Needs attention
                </h2>
                <p className="text-base text-muted-foreground">
                  {offTarget.length} of {data.kpis.length} KPIs are off target. Open one to see how it is calculated and
                  where its figures come from.
                </p>
              </div>
              <ul className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                {offTarget.map((kpi) => (
                  <li key={kpi.key} className="flex">
                    <AttentionCard kpi={kpi} onOpen={(key) => open(key)} />
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="kpi-grid" className="flex flex-col gap-3">
            <h2 id="kpi-grid" className="text-xl font-semibold">
              {filter ? `${KPI_STATUS[filter].label} KPIs` : "All KPIs"}
            </h2>
            {shown.length === 0 ? (
              <p className="rounded-xl border border-dashed p-8 text-center text-base text-muted-foreground">
                No KPIs are {filter ? KPI_STATUS[filter].label.toLowerCase() : "available"} for this period.
              </p>
            ) : (
              <KpiTable kpis={shown} onOpen={(key) => open(key)} />
            )}
          </section>

          <DomainTabs period={period} />
        </div>
      </div>
      <DrilldownSheet period={period} />
    </>
  );
}
