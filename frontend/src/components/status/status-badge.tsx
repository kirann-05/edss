import { cn } from "cn";

import type { FactStatus, HealthState, KpiStatus } from "@/lib/api/types";
import { FACT_STATUS, HEALTH_STATE, KPI_STATUS, TONE_CLASS, type StatusStyle } from "@/lib/status";

export function StatusChip({
  style,
  label,
  className,
}: {
  style: StatusStyle;
  label?: string;
  className?: string;
}) {
  const Icon = style.icon;
  return (
    <span
      title={style.hint}
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-md border px-2 py-0.5 text-sm font-medium whitespace-nowrap",
        TONE_CLASS[style.tone],
        style.dashed && "border-dashed",
        className,
      )}
    >
      <Icon aria-hidden className="size-4 shrink-0" />
      {label ?? style.label}
    </span>
  );
}

export function KpiStatusBadge({ status, className }: { status: KpiStatus; className?: string }) {
  return <StatusChip style={KPI_STATUS[status]} className={className} />;
}

export function FactStatusBadge({ status, className }: { status: FactStatus; className?: string }) {
  return <StatusChip style={FACT_STATUS[status]} className={className} />;
}

export function HealthBadge({
  state,
  label,
  className,
}: {
  state: HealthState;
  label?: string;
  className?: string;
}) {
  return <StatusChip style={HEALTH_STATE[state]} label={label} className={className} />;
}
