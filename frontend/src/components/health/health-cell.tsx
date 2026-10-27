import { Archive, CircleCheck, Lock } from "lucide-react";

import { FactStatusBadge, HealthBadge, StatusChip } from "@/components/status/status-badge";
import type { HealthCell } from "@/lib/api/types";
import { FACT_STATUS } from "@/lib/status";

const plural = (count: number, word: string) => `${count} ${word}`;
// badges may wrap here, so the whole matrix fits a projector at 125 percent zoom without scrolling
const WRAP = "whitespace-normal";

/** One department in one domain: how fresh it is, and which of its figures are not final. */
export function HealthCellView({ cell }: { cell: HealthCell }) {
  if (cell.restricted || !cell.state) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
        <Lock aria-hidden className="size-4" /> Restricted
      </span>
    );
  }

  const nonFinal = cell.non_final;
  const label =
    cell.state === "stale" && cell.age_days !== null && cell.age_days !== undefined
      ? `Stale, ${cell.age_days} days`
      : undefined;

  // a healthy cell stays quiet, so the few that are not stand out across the grid
  const quiet = cell.state === "fresh" || cell.state === "closed";
  const Provisional = FACT_STATUS.provisional.icon;
  const Forecast = FACT_STATUS.forecast.icon;

  return (
    <div className="flex flex-col items-start gap-1.5">
      {quiet ? (
        <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
          {cell.state === "fresh" ? (
            <CircleCheck aria-hidden className="size-3.5 text-good-mark" />
          ) : (
            <Archive aria-hidden className="size-3.5" />
          )}
          {cell.state === "fresh" ? "Fresh" : "Closed year"}
        </span>
      ) : (
        <HealthBadge state={cell.state} label={label} className={WRAP} />
      )}
      {cell.as_of && (
        <p className="text-sm text-muted-foreground">
          <span className="sr-only">Oldest record </span>
          <span className="tabular block whitespace-nowrap">{cell.as_of}</span>
          <span className="block">{plural(cell.fact_count, "records")}</span>
        </p>
      )}
      {nonFinal.provisional > 0 && (
        <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
          <Provisional aria-hidden className="size-3.5" />
          {nonFinal.provisional} provisional
        </span>
      )}
      {nonFinal.forecast > 0 && (
        <span className="inline-flex items-center gap-1 text-sm text-muted-foreground">
          <Forecast aria-hidden className="size-3.5" />
          {nonFinal.forecast} forecast
        </span>
      )}
      {nonFinal.pending_reconciliation > 0 && (
        <StatusChip
          style={FACT_STATUS.pending_reconciliation}
          label={`${nonFinal.pending_reconciliation} pending reconciliation`}
          className={WRAP}
        />
      )}
    </div>
  );
}

/** What each badge means, for people reading the matrix for the first time. */
export function HealthLegend({ staleAfterDays }: { staleAfterDays: number }) {
  return (
    <dl className="grid gap-x-8 gap-y-3 text-base sm:grid-cols-2">
      <div className="flex items-start gap-3">
        <dt className="shrink-0">
          <HealthBadge state="fresh" />
        </dt>
        <dd className="text-muted-foreground">Updated within the last {staleAfterDays} days.</dd>
      </div>
      <div className="flex items-start gap-3">
        <dt className="shrink-0">
          <HealthBadge state="stale" label="Stale" />
        </dt>
        <dd className="text-muted-foreground">
          Older than {staleAfterDays} days. Still used in figures, and flagged wherever it is.
        </dd>
      </div>
      <div className="flex items-start gap-3">
        <dt className="shrink-0">
          <HealthBadge state="missing" />
        </dt>
        <dd className="text-muted-foreground">No data at all. Left out of figures, never counted as zero.</dd>
      </div>
      <div className="flex items-start gap-3">
        <dt className="shrink-0">
          <FactStatusBadge status="pending_reconciliation" />
        </dt>
        <dd className="text-muted-foreground">
          Provisional, forecast and unreconciled figures are counted here but kept out of actuals.
        </dd>
      </div>
    </dl>
  );
}
