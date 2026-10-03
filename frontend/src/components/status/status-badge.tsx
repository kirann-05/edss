import { cn } from "cn";

import type { BriefStatus, FactStatus, HealthState, KpiStatus, RunStatus, Version } from "@/lib/api/types";
import {
  BRIEF_STATUS,
  FACT_STATUS,
  HEALTH_STATE,
  KPI_STATUS,
  RUN_STATUS,
  TONE_CLASS,
  VERSION_STATE,
  type StatusStyle,
} from "@/lib/status";

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

export function RunStatusBadge({ status, className }: { status: RunStatus; className?: string }) {
  const style = RUN_STATUS[status];
  const Icon = style.icon;
  return (
    <span
      title={style.hint}
      className={cn(
        "inline-flex w-fit items-center gap-1.5 rounded-md border px-2 py-0.5 text-sm font-medium whitespace-nowrap",
        TONE_CLASS[style.tone],
        className,
      )}
    >
      <Icon aria-hidden className={cn("size-4 shrink-0", status === "running" && "motion-safe:animate-spin")} />
      {style.label}
    </span>
  );
}

export function BriefStatusBadge({ status, className }: { status: BriefStatus; className?: string }) {
  return <StatusChip style={BRIEF_STATUS[status]} className={className} />;
}

export function VersionStateBadge({ state, className }: { state: Version["state"]; className?: string }) {
  return <StatusChip style={VERSION_STATE[state]} className={className} />;
}
