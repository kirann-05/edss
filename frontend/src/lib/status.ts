// The status vocabulary. Every status is an icon plus a label plus a tone. Colour is never the
// only carrier of meaning (docs/UI_SPEC.md), because the warning and serious marks are below
// 3:1 on a light surface by design.
import {
  Archive,
  BadgeCheck,
  Ban,
  CircleCheck,
  CircleHelp,
  CircleSlash,
  CircleX,
  ClipboardCheck,
  Clock,
  CornerUpLeft,
  FileText,
  History,
  Hourglass,
  ListChecks,
  LoaderCircle,
  MessageCircleQuestion,
  Scale,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  TriangleAlert,
  Undo2,
  type LucideIcon,
} from "lucide-react";

import type {
  BriefStatus,
  FactStatus,
  HealthState,
  KpiStatus,
  RunStatus,
  Version,
} from "@/lib/api/types";

export type Tone = "good" | "warning" | "serious" | "critical" | "neutral";

// Full class names, written out, so Tailwind can see them.
export const TONE_CLASS: Record<Tone, string> = {
  good: "bg-good-tint text-good-ink border-good-mark/50",
  warning: "bg-warning-tint text-warning-ink border-warning-mark/70",
  serious: "bg-serious-tint text-serious-ink border-serious-mark/60",
  critical: "bg-critical-tint text-critical-ink border-critical-mark/50",
  neutral: "bg-neutral-tint text-neutral-ink border-border",
};

/** The text colour of a tone, for an icon or a word set beside a figure. */
export const TONE_TEXT: Record<Tone, string> = {
  good: "text-good-ink",
  warning: "text-warning-ink",
  serious: "text-serious-ink",
  critical: "text-critical-ink",
  neutral: "text-neutral-ink",
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

export const RUN_STATUS: Record<RunStatus, StatusStyle> = {
  clarifying: {
    label: "Needs your answers",
    tone: "neutral",
    icon: MessageCircleQuestion,
    hint: "The agent has questions before it can plan",
  },
  planning: { label: "Plan to review", tone: "neutral", icon: ListChecks, hint: "A plan exists and can still be edited" },
  running: { label: "Running", tone: "neutral", icon: LoaderCircle, hint: "The plan is locked and the agents are working" },
  awaiting_review: {
    label: "Awaiting review",
    tone: "warning",
    icon: ClipboardCheck,
    hint: "A draft is ready and waits for a named person",
  },
  completed: { label: "Done", tone: "good", icon: CircleCheck, hint: "A person has decided and the run is finished" },
  failed: { label: "Stopped", tone: "critical", icon: CircleX, hint: "The run stopped. It can be resumed from its last checkpoint" },
};

export const BRIEF_STATUS: Record<BriefStatus, StatusStyle> = {
  draft: { label: "Draft", tone: "neutral", icon: FileText, hint: "Validated and waiting for a decision" },
  escalated: {
    label: "Escalated",
    tone: "serious",
    icon: ShieldAlert,
    hint: "Validation could not be satisfied inside the retry budget. A person decides",
  },
  approved: { label: "Approved", tone: "good", icon: CircleCheck, hint: "Approved by a named person" },
  published: { label: "Published", tone: "good", icon: BadgeCheck, hint: "Approved and released as a report version" },
  rolled_back: { label: "Rolled back", tone: "warning", icon: Undo2, hint: "Taken out of service by a rollback" },
  overridden: { label: "Overridden", tone: "neutral", icon: Ban, hint: "A person set the draft aside and gave a reason" },
  returned: { label: "Sent back", tone: "neutral", icon: CornerUpLeft, hint: "A person sent the draft back with a reason" },
};

export const VERSION_STATE: Record<Version["state"], StatusStyle> = {
  current: { label: "Current", tone: "good", icon: BadgeCheck, hint: "The version leadership sees now" },
  previous: { label: "Previous", tone: "neutral", icon: History, hint: "An earlier version, kept in full" },
  rolled_back: { label: "Rolled back", tone: "warning", icon: Undo2, hint: "Taken out of service by a rollback, kept in full" },
};
