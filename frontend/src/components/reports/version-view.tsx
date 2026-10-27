"use client";

import { ArrowLeft, Printer, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { BriefDocument } from "@/components/brief/brief-document";
import { FactDialog } from "@/components/brief/fact-dialog";
import { DrilldownSheet } from "@/components/drilldown/drilldown-sheet";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { VersionStateBadge } from "@/components/status/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe, useSystemStatus, useVersion } from "@/lib/api/queries";
import { FIELD_LABEL } from "@/lib/brief";
import type { EditRequest } from "@/lib/api/types";
import { useDrilldownParam } from "@/lib/use-drilldown-param";
import { formatWhen } from "@/lib/when";

/** A published version as leadership reads it, and as it prints. Nothing here can change it. */
export function VersionView({ number }: { number: number }) {
  const version = useVersion(number);
  const me = useMe();
  const system = useSystemStatus();
  const params = useSearchParams();
  const { open } = useDrilldownParam();
  const [factId, setFactId] = useState<number | null>(null);
  const printed = useRef(false);
  const [openedAt] = useState(() => new Date().toISOString());

  // the drill-down is for people who may read the data behind the dashboard. The Governing
  // Council reads published reports only, so figures stay plain text for them.
  const mayDrill = me.data?.permissions.includes("view_dashboard") ?? false;

  useEffect(() => {
    if (params.get("print") === "1" && version.data && !printed.current) {
      printed.current = true;
      window.setTimeout(() => window.print(), 300);
    }
  }, [params, version.data]);

  if (version.isPending) return <Skeleton className="h-96 w-full" />;
  if (version.isError) {
    return (
      <>
        <PageHeader title={`Version ${number}`} />
        <ErrorPanel error={version.error} onRetry={() => version.refetch()} what="this version" />
      </>
    );
  }

  const data = version.data;
  const handlers = mayDrill ? { onKpi: (key: string) => open(key), onFact: (id: number) => setFactId(id) } : {};

  return (
    <article className="flex flex-col gap-6">
      {/* only on paper: what this is and when it was printed, since the page chrome is hidden */}
      <p className="hidden text-sm print:block">
        EDSS executive report, version {data.version} ({data.state.replace("_", " ")}). Printed{" "}
        {formatWhen(openedAt)}. Data mode: {system.data?.data_mode ?? "unknown"}.
      </p>

      <div className="flex flex-wrap gap-2 print:hidden">
        <Button asChild variant="ghost">
          <Link href="/reports">
            <ArrowLeft aria-hidden data-icon="inline-start" />
            All reports
          </Link>
        </Button>
      </div>

      <PageHeader
        title={data.title}
        description={
          <>
            Version {data.version} · approved by {data.approved_by} on {formatWhen(data.approved_at)}
          </>
        }
        actions={
          <>
            <VersionStateBadge state={data.state} className="text-base" />
            <Button variant="outline" onClick={() => window.print()} className="print:hidden">
              <Printer aria-hidden data-icon="inline-start" />
              Print or save as PDF
            </Button>
          </>
        }
      />

      {data.state === "rolled_back" && (
        <Alert className="border-warning-mark/70 bg-warning-tint">
          <TriangleAlert aria-hidden />
          <AlertTitle className="text-base">This version was rolled back</AlertTitle>
          <AlertDescription className="text-base text-foreground">
            It is kept for the record, but it is not the report leadership sees now.
          </AlertDescription>
        </Alert>
      )}
      {data.escalation_acknowledged && (
        <Alert className="border-serious-mark/60 bg-serious-tint">
          <TriangleAlert aria-hidden />
          <AlertTitle className="text-base">Approved with a known gap</AlertTitle>
          <AlertDescription className="text-base text-foreground">
            The draft was escalated, and the approver acknowledged that some completeness checks had not passed.
          </AlertDescription>
        </Alert>
      )}

      <BriefDocument
        document={data.document}
        handlers={handlers}
        editedOptions={new Set(data.edits.map((e) => e.option_id))}
        decided
      />

      {data.edits.length > 0 && (
        <section aria-labelledby="edits-heading" className="flex flex-col gap-3 break-inside-avoid">
          <h2 id="edits-heading" className="text-xl font-semibold">
            Edits made on approval
          </h2>
          <ul className="flex flex-col gap-2">
            {data.edits.map((edit, index) => (
              <li key={index} className="flex flex-col gap-1 rounded-lg border bg-card p-3 text-base">
                <span className="font-semibold">
                  {edit.option_id}, {FIELD_LABEL[edit.field as EditRequest["field"]] ?? edit.field}
                  <span className="font-normal text-muted-foreground">
                    {" "}
                    by {edit.by}, {formatWhen(edit.at)}
                  </span>
                </span>
                <span className="text-sm whitespace-pre-wrap text-critical-ink">
                  Before: {Array.isArray(edit.before) ? edit.before.join("; ") : edit.before}
                </span>
                <span className="text-sm whitespace-pre-wrap text-good-ink">
                  After: {Array.isArray(edit.after) ? edit.after.join("; ") : edit.after}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {mayDrill && <DrilldownSheet period={data.period_year} />}
      <FactDialog id={factId} onClose={() => setFactId(null)} />
    </article>
  );
}
