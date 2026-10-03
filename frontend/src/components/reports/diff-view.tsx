"use client";

import { cn } from "cn";

import { ErrorPanel } from "@/components/error-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { useDiff } from "@/lib/api/queries";
import type { Change } from "@/lib/api/types";
import { TONE_CLASS } from "@/lib/status";

const SECTION_TITLE: Record<Change["section"], string> = {
  figures: "Figures",
  options: "Options",
  assumptions: "Assumptions",
};

const KIND = {
  added: { label: "Added", tone: "good" as const },
  removed: { label: "Removed", tone: "critical" as const },
  changed: { label: "Changed", tone: "warning" as const },
};

function where(change: Change): string {
  if (change.option_id) return `${change.option_id}${change.field ? `, ${change.field.replaceAll("_", " ")}` : ""}`;
  return change.kpi_key ?? change.field ?? "";
}

/** What differs between two published versions, section by section, decided by the server. */
export function DiffView({ from, to }: { from: number; to: number }) {
  const diff = useDiff(from, to);
  if (from === to) return <p className="text-base text-muted-foreground">Choose two different versions.</p>;
  if (diff.isPending) return <Skeleton className="h-32 w-full" />;
  if (diff.isError) return <ErrorPanel error={diff.error} onRetry={() => diff.refetch()} what="the comparison" />;
  if (diff.data.changes.length === 0) {
    return <p className="text-base text-muted-foreground">Versions {from} and {to} say the same thing.</p>;
  }
  const sections = (["figures", "options", "assumptions"] as const)
    .map((section) => ({ section, changes: diff.data.changes.filter((c) => c.section === section) }))
    .filter((group) => group.changes.length > 0);

  return (
    <div className="flex flex-col gap-5">
      {sections.map(({ section, changes }) => (
        <section key={section} className="flex flex-col gap-2">
          <h3 className="text-base font-semibold">
            {SECTION_TITLE[section]} ({changes.length})
          </h3>
          <ul className="flex flex-col gap-2">
            {changes.map((change, index) => {
              const kind = KIND[change.kind];
              return (
                <li key={index} className="flex flex-col gap-2 rounded-lg border bg-background p-3">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className={cn("rounded-md border px-2 py-0.5 text-sm font-medium", TONE_CLASS[kind.tone])}>
                      {kind.label}
                    </span>
                    <span className="font-mono text-sm">{where(change)}</span>
                  </span>
                  {(change.before || change.after) && (
                    <div className="grid gap-2 md:grid-cols-2">
                      {change.before !== null && (
                        <p className="rounded-md border border-critical-mark/40 bg-critical-tint px-2 py-1 text-sm whitespace-pre-wrap">
                          <span className="font-medium">Version {from}: </span>
                          {change.before}
                        </p>
                      )}
                      {change.after !== null && (
                        <p className="rounded-md border border-good-mark/40 bg-good-tint px-2 py-1 text-sm whitespace-pre-wrap">
                          <span className="font-medium">Version {to}: </span>
                          {change.after}
                        </p>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
