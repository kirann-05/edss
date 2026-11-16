"use client";

import { ArrowRight, FileText } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useCurrentReport } from "@/lib/api/queries";
import { formatWhen } from "@/lib/when";

/** The dashboard's fourth panel (FR-10): the executive report leadership has approved. */
export function CurrentReportCard() {
  const report = useCurrentReport();
  if (report.isPending || report.isError) return null;
  const current = report.data.current;
  return (
    <section
      aria-label="Current approved report"
      className="flex flex-wrap items-center gap-4 rounded-xl border bg-card px-5 py-4"
    >
      <FileText aria-hidden className="size-6 text-primary" />
      {current ? (
        <>
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="text-sm text-muted-foreground">Current approved report</span>
            <span className="text-lg font-semibold">
              {current.title}, version {current.version}
            </span>
            <span className="text-sm text-muted-foreground">
              Approved by {current.approved_by} on {formatWhen(current.approved_at)}
            </span>
          </div>
          <Button asChild variant="outline">
            <Link href={`/reports/${current.version}`}>
              Read it
              <ArrowRight aria-hidden data-icon="inline-end" />
            </Link>
          </Button>
        </>
      ) : (
        <p className="text-base text-muted-foreground">
          No report has been approved yet. The figures below are live from the engine, not an approved brief.
        </p>
      )}
    </section>
  );
}
