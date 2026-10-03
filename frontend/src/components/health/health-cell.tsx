import { Lock } from "lucide-react";

import { FactStatusBadge, HealthBadge, StatusChip } from "@/components/status/status-badge";
import type { HealthCell } from "@/lib/api/types";
import { FACT_STATUS } from "@/lib/status";

const plural = (count: number, word: string) => `${count} ${word}`;

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

  return (
    <div className="flex flex-col items-start gap-1.5">
      <HealthBadge state={cell.state} label={label} />
      {cell.as_of && (
        <p className="text-sm text-muted-foreground">
          <span className="tabular">Oldest {cell.as_of}</span>
          {" · "}
          {plural(cell.fact_count, "records")}
        </p>
      )}
      {nonFinal.provisional > 0 && (
        <StatusChip style={FACT_STATUS.provisional} label={`${nonFinal.provisional} provisional`} />
      )}
      {nonFinal.forecast > 0 && <StatusChip style={FACT_STATUS.forecast} label={`${nonFinal.forecast} forecast`} />}
      {nonFinal.pending_reconciliation > 0 && (
        <StatusChip
          style={FACT_STATUS.pending_reconciliation}
          label={`${nonFinal.pending_reconciliation} pending reconciliation`}
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
