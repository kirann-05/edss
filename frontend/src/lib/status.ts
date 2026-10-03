// The status vocabulary. Every status is an icon plus a label plus a tone. Colour is never the
// only carrier of meaning (docs/UI_SPEC.md), because the warning and serious marks are below
// 3:1 on a light surface by design.
import {
  Archive,
  CircleCheck,
  CircleHelp,
  CircleSlash,
  CircleX,
  Clock,
  Hourglass,
  Scale,
  ShieldCheck,
  TrendingUp,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react";

import type { FactStatus, HealthState, KpiStatus } from "@/lib/api/types";

export type Tone = "good" | "warning" | "serious" | "critical" | "neutral";

// Full class names, written out, so Tailwind can see them.
export const TONE_CLASS: Record<Tone, string> = {
  good: "bg-good-tint text-good-ink border-good-mark/50",
  warning: "bg-warning-tint text-warning-ink border-warning-mark/70",
  serious: "bg-serious-tint text-serious-ink border-serious-mark/60",
  critical: "bg-critical-tint text-critical-ink border-critical-mark/50",
  neutral: "bg-neutral-tint text-neutral-ink border-border",
};

export interface StatusStyle {
  label: string;
  tone: Tone;
  icon: LucideIcon;
  /** A dashed outline marks a projection, a second cue beyond the icon and label */
  dashed?: boolean;
  /** One sentence for a tooltip */
  hint: string;
}

export const KPI_STATUS: Record<KpiStatus, StatusStyle> = {
  met: { label: "Met", tone: "good", icon: CircleCheck, hint: "At or beyond target with a safe margin" },
  at_risk: {
    label: "At risk",
    tone: "warning",
    icon: TriangleAlert,
    hint: "Target reached, but by less than the safety margin",
  },
  missed: { label: "Missed", tone: "critical", icon: CircleX, hint: "Target not reached" },
  undefined: {
    label: "Undefined",
    tone: "neutral",
    icon: CircleHelp,
    hint: "Cannot be computed: nothing to divide by, or no target set",
  },
};

export const FACT_STATUS: Record<FactStatus, StatusStyle> = {
  final: { label: "Final", tone: "neutral", icon: ShieldCheck, hint: "Approved and final" },
  audited: { label: "Audited", tone: "neutral", icon: ShieldCheck, hint: "Audited figure" },
  provisional: {
    label: "Provisional",
    tone: "warning",
    icon: Hourglass,
    hint: "Not yet confirmed. Never counted as final",
  },
  forecast: {
    label: "Forecast",
    tone: "neutral",
    icon: TrendingUp,
    dashed: true,
    hint: "A projection. Never counted as an actual",
  },
  pending_reconciliation: {
    label: "Pending reconciliation",
    tone: "serious",
    icon: Scale,
    hint: "Not reconciled yet. Kept out of actuals until it is",
  },
};

export const HEALTH_STATE: Record<HealthState, StatusStyle> = {
  fresh: { label: "Fresh", tone: "good", icon: CircleCheck, hint: "Updated within the freshness window" },
  stale: { label: "Stale", tone: "warning", icon: Clock, hint: "Older than the freshness window. Used, but flagged" },
  missing: { label: "No record", tone: "serious", icon: CircleSlash, hint: "No data for this period. Never treated as zero" },
  closed: { label: "Closed year", tone: "neutral", icon: Archive, hint: "A finished period. Freshness no longer applies" },
};
