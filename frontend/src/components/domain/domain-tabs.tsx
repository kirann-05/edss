"use client";

import { cn } from "cn";
import { useState } from "react";

import { DeptComparison } from "@/components/charts/dept-comparison";
import { ErrorPanel } from "@/components/error-panel";
import { KpiStatusBadge } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDomainView } from "@/lib/api/queries";
import { DOMAIN_LABEL, DOMAIN_TABS, type DomainTab } from "@/lib/api/types";
import { formatWithUnit } from "@/lib/format";
import { useDrilldownParam } from "@/lib/use-drilldown-param";

export function DomainTabs({ period }: { period?: string }) {
  const [tab, setTab] = useState<DomainTab>("academic");
  return (
    <section aria-labelledby="by-department" className="flex flex-col gap-4">
      <h2 id="by-department" className="text-2xl font-semibold">
        By department
      </h2>
      <Tabs value={tab} onValueChange={(value) => setTab(value as DomainTab)}>
        <TabsList className="h-auto flex-wrap">
          {DOMAIN_TABS.map((domain) => (
            <TabsTrigger key={domain} value={domain} className="px-4 py-2 text-base">
              {DOMAIN_LABEL[domain]}
            </TabsTrigger>
          ))}
        </TabsList>
        {DOMAIN_TABS.map((domain) => (
          <TabsContent key={domain} value={domain} className="mt-4">
            <DomainPanel domain={domain} period={period} />
          </TabsContent>
        ))}
      </Tabs>
    </section>
  );
}

function DomainPanel({ domain, period }: { domain: DomainTab; period?: string }) {
  const view = useDomainView(domain, period);
  const { open } = useDrilldownParam();
  const [chosen, setChosen] = useState<string | null>(null);

  if (view.isPending) {
    return (
      <div className="grid gap-4 xl:grid-cols-2">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    );
  }
  if (view.isError) {
    return <ErrorPanel error={view.error} onRetry={() => view.refetch()} what={`${DOMAIN_LABEL[domain]} figures`} />;
  }

  const kpis = view.data.kpis;
  const current = kpis.find(({ kpi }) => kpi.key === chosen) ?? kpis[0];
  if (!current) {
    return <p className="text-base text-muted-foreground">No KPIs in this area for the period.</p>;
  }
  const { kpi, departments } = current;

  // one KPI at a time: the choice of KPI first, then its comparison across departments
  return (
    <div className={cn("flex flex-col gap-4", view.isFetching && "opacity-60 transition-opacity")}>
      <div role="group" aria-label={`${DOMAIN_LABEL[domain]} KPI to compare`} className="flex flex-wrap gap-2">
        {kpis.map(({ kpi: option }) => (
          <Button
            key={option.key}
            variant={option.key === kpi.key ? "default" : "outline"}
            size="sm"
            aria-pressed={option.key === kpi.key}
            onClick={() => setChosen(option.key)}
          >
            {option.name}
          </Button>
        ))}
      </div>
      <Card>
        <CardHeader className="flex flex-col gap-2">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="text-lg font-semibold">{kpi.name}</h3>
            <KpiStatusBadge status={kpi.status} />
          </div>
          <p className="text-base text-muted-foreground">
            Institution {formatWithUnit(kpi.value, kpi.precision, kpi.unit)}
            {" · "}Target {formatWithUnit(kpi.target, kpi.precision, kpi.unit)}
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <DeptComparison kpi={kpi} rows={departments} refetching={view.isFetching} />
          <Button variant="outline" size="sm" className="self-start" onClick={() => open(kpi.key)}>
            Open drill-down
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
