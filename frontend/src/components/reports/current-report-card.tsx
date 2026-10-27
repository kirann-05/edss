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
    <section aria-label="Current approved report" className="flex flex-col gap-3 rounded-xl border bg-card p-4">
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <FileText aria-hidden className="size-4 text-primary" />
        Current approved report
      </p>
      {current ? (
        <>
          <div className="flex flex-col gap-0.5">
            <span className="text-lg leading-snug font-semibold">
              {current.title}, version {current.version}
            </span>
            <span className="text-sm text-muted-foreground">
              Approved by {current.approved_by} on {formatWhen(current.approved_at)}
            </span>
          </div>
          <Button asChild variant="outline" className="self-start">
            <Link href={`/reports/${current.version}`}>
              Read it
              <ArrowRight aria-hidden data-icon="inline-end" />
            </Link>
          </Button>
        </>
      ) : (
        <p className="text-base text-muted-foreground">
          No report has been approved yet. The figures here are live from the engine, not an approved brief.
        </p>
      )}
    </section>
  );
}
