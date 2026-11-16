"use client";

import { cn } from "cn";
import { CircleCheck, CircleX, History, Wrench } from "lucide-react";

import { ErrorPanel } from "@/components/error-panel";
import { FactStatusBadge, HealthBadge } from "@/components/status/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useEvidence, usePriorBriefs } from "@/lib/api/queries";
import {
  DOMAIN_LABEL,
  type Brief,
  type CheckResult,
  type HealthNote,
  type HealthState,
  type ValidationReport,
  type Violation,
} from "@/lib/api/types";
import { formatDay } from "@/lib/when";

const FIX_WORDS: Record<NonNullable<Violation["fix"]>, string> = {
  regenerate_options: "Repair: redraft the options for this KPI",
  rebuild_figure: "Repair: rebuild the figure from the KPI engine",
  rebuild_sections: "Repair: rebuild the assumptions and data health sections",
  reset_status: "Repair: put the status back to draft",
};

/** The evidence and the checks beside the brief, as the approver reads it. */
export function BriefTabs({
  brief,
  onKpi,
  showPrior = true,
}: {
  brief: Brief;
  onKpi?: (key: string) => void;
  showPrior?: boolean;
}) {
  const failing = brief.validation.checks.filter((c) => !c.passed).length;
  return (
    <Tabs defaultValue="validation" className="gap-4">
      <TabsList className="h-auto w-full flex-wrap justify-start">
        <TabsTrigger value="validation" className="text-base">
          Validation{failing > 0 ? ` (${failing} failing)` : ""}
        </TabsTrigger>
        <TabsTrigger value="evidence" className="text-base">
          Evidence
        </TabsTrigger>
        <TabsTrigger value="health" className="text-base">
          Data health
        </TabsTrigger>
        {showPrior && (
          <TabsTrigger value="prior" className="text-base">
            Prior briefs
          </TabsTrigger>
        )}
      </TabsList>
      <TabsContent value="validation">
        <ValidationPanel brief={brief} />
      </TabsContent>
      <TabsContent value="evidence">
        <EvidencePanel briefId={brief.id} onKpi={onKpi} />
      </TabsContent>
      <TabsContent value="health">
        <HealthPanel notes={brief.document.data_health} />
      </TabsContent>
      {showPrior && (
        <TabsContent value="prior">
          <PriorPanel briefId={brief.id} />
        </TabsContent>
      )}
    </Tabs>
  );
}

function CheckRow({ check }: { check: CheckResult }) {
  const Icon = check.passed ? CircleCheck : CircleX;
  return (
    <li className="flex flex-col gap-2 py-2.5">
      <div className="flex items-start gap-2">
        <Icon aria-hidden className={cn("mt-0.5 size-5 shrink-0", check.passed ? "text-good-mark" : "text-critical-mark")} />
        <span className="text-base">
          <span className="font-semibold">{check.id}</span> {check.name}
          <span className="sr-only">{check.passed ? ", passed" : ", failed"}</span>
        </span>
      </div>
      {check.violations.length > 0 && (
        <ul className="ml-7 flex flex-col gap-2">
          {check.violations.map((violation, index) => (
            <li key={index} className="rounded-lg border border-critical-mark/40 bg-critical-tint p-3 text-base text-critical-ink">
              <p className="font-medium">{violation.message}</p>
              <p className="mt-1 text-sm">Why: {violation.diagnosis}</p>
              <p className="mt-2 flex flex-wrap gap-1.5 text-sm">
                {violation.locator.section && <Locator label="Section" value={violation.locator.section} />}
                {violation.locator.kpi_key && <Locator label="KPI" value={violation.locator.kpi_key} />}
                {violation.locator.option_id && <Locator label="Option" value={violation.locator.option_id} />}
              </p>
              {violation.fix && <p className="mt-2 text-sm">{FIX_WORDS[violation.fix]}</p>}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function Locator({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded border border-critical-mark/40 bg-background px-1.5 py-0.5">
      {label}: <span className="font-mono">{value}</span>
    </span>
  );
}

function ReportSummary({ report }: { report: ValidationReport }) {
  const failing = report.checks.filter((c) => !c.passed).map((c) => c.id);
  return failing.length === 0 ? (
    <span className="text-good-ink">all nine checks passed</span>
  ) : (
    <span className="text-critical-ink">failing {failing.join(", ")}</span>
  );
}

function ValidationPanel({ brief }: { brief: Brief }) {
  const report = brief.validation;
  return (
    <div className="flex flex-col gap-4">
      <p className="text-base">
        {report.passed ? (
          <span className="font-semibold text-good-ink">All nine checks passed</span>
        ) : (
          <span className="font-semibold text-critical-ink">
            {report.checks.filter((c) => !c.passed).length} of nine checks failed
          </span>
        )}
        <span className="text-muted-foreground">
          {brief.edits.length > 0
            ? " on the brief as the approver edited it."
            : ` on attempt ${report.attempt} of the drafting loop.`}
        </span>
      </p>
      <ul className="flex flex-col divide-y rounded-xl border bg-card px-3">
        {report.checks.map((check) => (
          <CheckRow key={check.id} check={check} />
        ))}
      </ul>
      {brief.history.length > 0 && (
        <section aria-labelledby="attempts-heading" className="flex flex-col gap-2">
          <h3 id="attempts-heading" className="flex items-center gap-2 text-base font-semibold">
            <History aria-hidden className="size-4" />
            Every attempt
          </h3>
          <ol className="flex flex-col gap-1.5 text-base">
            {brief.history.map((attempt) => (
              <li key={attempt.attempt}>
                Attempt {attempt.attempt}: <ReportSummary report={attempt} />
              </li>
            ))}
          </ol>
          {brief.repair_log.length > 0 && (
            <ul className="flex flex-col gap-1.5 text-sm text-muted-foreground">
              {brief.repair_log.map((entry, index) => (
                <li key={index} className="flex items-start gap-2">
                  <Wrench aria-hidden className="mt-0.5 size-4 shrink-0" />
                  {entry}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}

function EvidencePanel({ briefId, onKpi }: { briefId: string; onKpi?: (key: string) => void }) {
  const evidence = useEvidence(briefId);
  if (evidence.isPending) return <Skeleton className="h-64 w-full" />;
  if (evidence.isError) return <ErrorPanel error={evidence.error} onRetry={() => evidence.refetch()} what="the evidence" />;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-base text-muted-foreground">
        Every claim and the records it rests on. Open a KPI to see each record with its status and source reference.
      </p>
      <ul className="flex flex-col divide-y rounded-xl border bg-card">
        {evidence.data.map((row) => (
          <li key={row.kpi_key} className="flex flex-col gap-1.5 px-3 py-3">
            {onKpi ? (
              <button
                type="button"
                onClick={() => onKpi(row.kpi_key)}
                className="w-fit text-left text-base font-medium underline-offset-4 outline-none hover:underline focus-visible:underline focus-visible:ring-2 focus-visible:ring-ring"
              >
                {row.claim}
              </button>
            ) : (
              <span className="text-base font-medium">{row.claim}</span>
            )}
            <span className="text-sm">
              {row.fact_ids.length} record{row.fact_ids.length === 1 ? "" : "s"} from{" "}
              {row.source_systems.length > 0 ? row.source_systems.join(", ") : "no source"}
            </span>
            <span className="text-sm text-muted-foreground">{row.scope}</span>
            <span className="flex flex-wrap gap-1">
              {row.tags.map((tag) => (
                <span key={tag} className="rounded border px-1.5 py-0.5 text-xs text-muted-foreground">
                  {tag.replace("_", " ")}
                </span>
              ))}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const STATE_ORDER: Record<string, number> = { missing: 0, stale: 1, fresh: 2, closed: 3 };

function HealthPanel({ notes }: { notes: HealthNote[] }) {
  const sorted = [...notes].sort(
    (a, b) => (STATE_ORDER[a.state] ?? 9) - (STATE_ORDER[b.state] ?? 9) || a.dept_code.localeCompare(b.dept_code),
  );
  if (sorted.length === 0) {
    return <p className="text-base text-muted-foreground">Every department and area is fresh and final for this period.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="text-base text-muted-foreground">
        Departments and areas the reader should know about: missing or stale data, and records that are not final.
      </p>
      <ul className="flex flex-col divide-y rounded-xl border bg-card">
        {sorted.map((note) => (
          <li key={`${note.dept_code}-${note.domain}`} className="flex flex-col gap-1.5 px-3 py-3">
            <span className="flex flex-wrap items-center gap-2 text-base">
              <span className="font-semibold">{note.dept_code}</span>
              <span className="text-muted-foreground">{DOMAIN_LABEL[note.domain]}</span>
              <HealthBadge state={note.state as HealthState} />
            </span>
            {note.as_of && <span className="text-sm text-muted-foreground">As of {formatDay(note.as_of)}</span>}
            {note.non_final.length > 0 && (
              <span className="flex flex-wrap items-center gap-1.5 text-sm">
                Not final:
                {note.non_final.map((status) => (
                  <FactStatusBadge key={status} status={status} className="text-xs" />
                ))}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function PriorPanel({ briefId }: { briefId: string }) {
  const prior = usePriorBriefs(briefId);
  if (prior.isPending) return <Skeleton className="h-48 w-full" />;
  if (prior.isError) return <ErrorPanel error={prior.error} onRetry={() => prior.refetch()} what="prior briefs" />;
  if (prior.data.length === 0) {
    return <p className="text-base text-muted-foreground">No earlier brief dealt with the same KPIs.</p>;
  }
  return (
    <div className="flex flex-col gap-3">
      <p className="text-base text-muted-foreground">
        Earlier briefs on the same off-target KPIs, and what leadership decided. Context only, never a recommendation.
      </p>
      <ul className="flex flex-col gap-3">
        {prior.data.map((match) => (
          <li key={match.id} className="flex flex-col gap-1.5 rounded-xl border bg-card p-3">
            <span className="text-base font-semibold">{match.title}</span>
            <span className="text-sm text-muted-foreground">
              Decided {formatDay(match.decided_on)} · {match.reason}
            </span>
            <p className="text-base">{match.decision}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
