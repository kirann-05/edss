"use client";

import { ErrorPanel } from "@/components/error-panel";
import { FactStatusBadge } from "@/components/status/status-badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useFact } from "@/lib/api/queries";
import { DOMAIN_LABEL } from "@/lib/api/types";
import { formatFigure } from "@/lib/format";
import { formatDay } from "@/lib/when";

/** One source record: what it is, its status, and exactly where it came from (rule 3). */
export function FactDialog({ id, onClose }: { id: number | null; onClose: () => void }) {
  const fact = useFact(id);
  return (
    <Dialog open={id !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Source record {id}</DialogTitle>
          <DialogDescription>
            {fact.data
              ? `${fact.data.metric_label}, ${fact.data.dept_code}, ${fact.data.period_year} ${fact.data.period_sub}`.trim()
              : "The record behind this figure."}
          </DialogDescription>
        </DialogHeader>
        {fact.isPending && <Skeleton className="h-48 w-full" />}
        {fact.isError && <ErrorPanel error={fact.error} what="this record" />}
        {fact.data && (
          <dl className="grid grid-cols-[9rem_minmax(0,1fr)] gap-x-4 gap-y-3 text-base">
            <dt className="text-muted-foreground">Value</dt>
            <dd className="font-semibold tabular-nums">
              {formatFigure(fact.data.value)} {fact.data.unit}
            </dd>
            <dt className="text-muted-foreground">Status</dt>
            <dd className="flex flex-col gap-1">
              <FactStatusBadge status={fact.data.status} />
              <span className="text-sm text-muted-foreground">
                {fact.data.used
                  ? "Final or audited, so it counts as an actual."
                  : "Not final, so it is kept out of actuals and shown with its badge."}
              </span>
            </dd>
            <dt className="text-muted-foreground">Area</dt>
            <dd>{DOMAIN_LABEL[fact.data.domain]}</dd>
            <dt className="text-muted-foreground">As of</dt>
            <dd>{formatDay(fact.data.as_of)}</dd>
            <dt className="text-muted-foreground">Source</dt>
            <dd>
              {fact.data.source_system}
              <span className="block text-sm text-muted-foreground">Owner: {fact.data.source_owner}</span>
            </dd>
            <dt className="text-muted-foreground">Reference</dt>
            <dd className="font-mono text-sm break-all">{fact.data.source_ref}</dd>
            <dt className="text-muted-foreground">Ingest batch</dt>
            <dd className="tabular-nums">{fact.data.batch_id}</dd>
          </dl>
        )}
      </DialogContent>
    </Dialog>
  );
}
