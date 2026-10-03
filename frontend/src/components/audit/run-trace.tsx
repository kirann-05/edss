"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { ProgressTimeline } from "@/components/runs/progress-timeline";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRunTrace, useSystemStatus } from "@/lib/api/queries";

import { AuditRows } from "./audit-view";

/** One run from start to finish: the live timeline it showed, and every audit row it left. */
export function RunTrace({ id }: { id: string }) {
  const trace = useRunTrace(id);
  const system = useSystemStatus();
  if (trace.isPending) return <Skeleton className="h-96 w-full" />;
  if (trace.isError) {
    return (
      <>
        <PageHeader title={`Run trace, ${id}`} />
        <ErrorPanel error={trace.error} onRetry={() => trace.refetch()} what="this trace" />
      </>
    );
  }
  const rows = [...trace.data.audit].reverse();
  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button asChild variant="ghost">
          <Link href="/audit">
            <ArrowLeft aria-hidden data-icon="inline-start" />
            Audit
          </Link>
        </Button>
        <Button asChild variant="ghost">
          <Link href={`/runs/${id}`}>Open the run</Link>
        </Button>
      </div>
      <PageHeader
        title={`Run trace, ${id}`}
        description={`${trace.data.events.length} progress events and ${trace.data.audit.length} audit rows, newest first.`}
      />
      <ProgressTimeline
        events={trace.data.events}
        connection="ended"
        live={false}
        simulatedLatencyMs={system.data?.simulated_source_latency_ms ?? 0}
      />
      <section aria-labelledby="trace-rows" className="flex flex-col gap-3">
        <h2 id="trace-rows" className="text-xl font-semibold">
          Audit rows for this run
        </h2>
        <AuditRows rows={rows} showRun={false} />
      </section>
    </>
  );
}
