"use client";

import Link from "next/link";

import { ErrorPanel } from "@/components/error-panel";
import { RunStatusBadge } from "@/components/status/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRuns } from "@/lib/api/queries";
import { formatWhen } from "@/lib/when";

export function RunsList() {
  const runs = useRuns();

  if (runs.isPending) return <Skeleton className="h-24 w-full" />;
  if (runs.isError) return <ErrorPanel error={runs.error} onRetry={() => runs.refetch()} what="your runs" />;
  if (runs.data.length === 0) {
    return <p className="text-base text-muted-foreground">No runs yet. The first one you start will appear here.</p>;
  }

  return (
    <ul className="flex flex-col divide-y rounded-xl border bg-card">
      {runs.data.map((run) => (
        <li key={run.id}>
          <Link
            href={`/runs/${run.id}`}
            className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3 outline-none hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-base font-medium">{run.request}</span>
              <span className="text-sm text-muted-foreground">
                {run.created_by_name} · {formatWhen(run.created_at)}
              </span>
            </span>
            <RunStatusBadge status={run.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
