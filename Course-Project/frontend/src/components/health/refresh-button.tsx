"use client";

import { CircleCheck, RefreshCw, TriangleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useRefreshData } from "@/lib/api/queries";
import { formatWhen } from "@/lib/when";

type Refresh = ReturnType<typeof useRefreshData>;

export function RefreshButton({ refresh }: { refresh: Refresh }) {
  return (
    <Button variant="outline" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
      <RefreshCw aria-hidden data-icon="inline-start" className={refresh.isPending ? "motion-safe:animate-spin" : undefined} />
      {refresh.isPending ? "Reading the sources" : "Refresh data"}
    </Button>
  );
}

/** What the refresh did, in words. A refusal says why and that the data in use did not change. */
export function RefreshOutcome({ refresh }: { refresh: Refresh }) {
  if (refresh.isError) {
    return (
      <Alert variant="destructive" aria-live="polite">
        <TriangleAlert aria-hidden />
        <AlertTitle className="text-base">The data was not refreshed</AlertTitle>
        <AlertDescription className="text-base">
          {refresh.error.message} The figures on screen are still the ones from the last successful read.
        </AlertDescription>
      </Alert>
    );
  }
  if (!refresh.isSuccess) return null;
  const result = refresh.data;
  const synthetic = result.source === "synthetic";
  return (
    <Alert className="border-good-mark/50 bg-good-tint" aria-live="polite">
      <CircleCheck aria-hidden className="text-good-ink" />
      <AlertTitle className="text-base text-good-ink">
        {synthetic ? "The synthetic data was generated again" : "The sources were read again"}
      </AlertTitle>
      <AlertDescription className="flex flex-col gap-2 text-base text-foreground">
        <p>
          {synthetic
            ? `${result.accepted} records, dated from today.`
            : `${result.accepted} new records accepted, ${result.rejected} refused, ${result.unchanged_files} file${result.unchanged_files === 1 ? "" : "s"} unchanged and left as they were.`}{" "}
          Read at {formatWhen(result.refreshed_at)}.
        </p>
        {result.rejects.length > 0 && (
          <div>
            <p className="font-medium">Refused rows (the first {result.rejects.length}):</p>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {result.rejects.map((reject) => (
                <li key={reject.where}>
                  <span className="font-mono">{reject.where}</span>: {reject.why.join("; ")}
                </li>
              ))}
            </ul>
            <p className="mt-1 text-sm">
              The data owner fixes these at the source. Nothing was corrected or filled in here.
            </p>
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}
