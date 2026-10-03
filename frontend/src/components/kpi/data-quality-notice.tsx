import { Info } from "lucide-react";
import Link from "next/link";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { KpiOut } from "@/lib/api/types";
import { flagSummaries, mergeFlags } from "@/lib/flags";

import { FlagLine } from "./flag-line";

/**
 * Says up front, above the figures, that some of them rest on incomplete data. A leader should
 * never have to open a card to find out.
 */
export function DataQualityNotice({ kpis, period }: { kpis: KpiOut[]; period?: string }) {
  const merged = mergeFlags(kpis.map((k) => k.flags));
  // no_target is a per-KPI matter, the others are about whole departments
  const problems = flagSummaries({ ...merged, no_target: false });
  if (problems.length === 0) return null;
  return (
    <Alert>
      <Info aria-hidden />
      <AlertTitle className="text-base">Some figures rest on incomplete data</AlertTitle>
      <AlertDescription className="flex flex-col gap-2">
        <FlagLine flags={{ ...merged, no_target: false }} />
        <Link
          href={period ? `/data-health?period=${period}` : "/data-health"}
          className="text-base font-medium text-primary underline-offset-4 hover:underline"
        >
          Open data health
        </Link>
      </AlertDescription>
    </Alert>
  );
}
