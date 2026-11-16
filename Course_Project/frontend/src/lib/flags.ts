import type { LucideIcon } from "lucide-react";
import { CircleSlash, Clock, Divide, Scale, Target } from "lucide-react";

import type { DeptFlagList, KpiOut } from "@/lib/api/types";
import type { Tone } from "@/lib/status";

export type FlagKind = "missing" | "excluded" | "stale" | "undefined" | "no_target";

export interface FlagSummary {
  kind: FlagKind;
  tone: Tone;
  icon: LucideIcon;
  text: string;
  /** What it means, for a tooltip */
  hint: string;
}

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? "" : "s"}`;

/** "CIVIL", "CSE and 2 others", or "1 department" when the viewer may not see the names. */
function who(list: DeptFlagList): string {
  const hidden = list.total - list.departments.length;
  if (list.departments.length === 0) return plural(list.total, "department");
  const names = list.departments.join(", ");
  return hidden > 0 ? `${names} and ${plural(hidden, "other")}` : names;
}

/**
 * The data-quality problems behind a KPI, in a fixed order with the most serious first.
 * A department that is missing, excluded or stale is always said out loud, never left out.
 */
export function flagSummaries(flags: KpiOut["flags"]): FlagSummary[] {
  const out: FlagSummary[] = [];
  if (flags.missing.total > 0)
    out.push({
      kind: "missing",
      tone: "serious",
      icon: CircleSlash,
      text: `No record: ${who(flags.missing)}`,
      hint: "No data for this period. Left out of the figure, never counted as zero",
    });
  if (flags.excluded.total > 0)
    out.push({
      kind: "excluded",
      tone: "serious",
      icon: Scale,
      text: `Excluded: ${who(flags.excluded)}`,
      hint: "An input is provisional, forecast or pending reconciliation, so it is kept out of actuals",
    });
  if (flags.stale.total > 0)
    out.push({
      kind: "stale",
      tone: "warning",
      icon: Clock,
      text: `Stale: ${who(flags.stale)}`,
      hint: "Data older than the freshness window. Used in the figure, but flagged",
    });
  if (flags.undefined.total > 0)
    out.push({
      kind: "undefined",
      tone: "neutral",
      icon: Divide,
      text: `Undefined: ${who(flags.undefined)}`,
      hint: "Nothing to divide by for these departments, so no value (not zero, not 100)",
    });
  if (flags.no_target)
    out.push({
      kind: "no_target",
      tone: "neutral",
      icon: Target,
      text: "No target set",
      hint: "There is no target for this period, so no status can be decided",
    });
  return out;
}

function mergeList(lists: DeptFlagList[]): DeptFlagList {
  const named = new Set(lists.flatMap((l) => l.departments));
  // A department the viewer cannot see is counted once, however many KPIs it affects, by taking
  // the largest hidden count of any single KPI. That never over-counts, though it can under-count.
  const hidden = Math.max(0, ...lists.map((l) => l.total - l.departments.length));
  return { departments: [...named].sort(), total: named.size + hidden };
}

/** One set of flags for the whole dashboard: every department with a problem, counted once. */
export function mergeFlags(all: KpiOut["flags"][]): KpiOut["flags"] {
  return {
    stale: mergeList(all.map((f) => f.stale)),
    missing: mergeList(all.map((f) => f.missing)),
    excluded: mergeList(all.map((f) => f.excluded)),
    undefined: mergeList(all.map((f) => f.undefined)),
    excluded_fact_count: Math.max(0, ...all.map((f) => f.excluded_fact_count)),
    no_target: all.some((f) => f.no_target),
  };
}
