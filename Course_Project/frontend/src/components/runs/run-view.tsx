"use client";

import { ArrowRight, ClipboardCheck, FlaskConical, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { RunStatusBadge } from "@/components/status/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe, usePlanCatalogue, useResumeRun, useRun, useSystemStatus } from "@/lib/api/queries";
import { DOMAIN_LABEL, type PlanCatalogue, type Run } from "@/lib/api/types";
import { buildProgress, stageOf } from "@/lib/run-progress";
import { useRunEvents } from "@/lib/use-run-events";
import { formatWhen } from "@/lib/when";

import { ClarifyPanel } from "./clarify-panel";
import { PlanEditor } from "./plan-editor";
import { ProgressTimeline } from "./progress-timeline";
import { StageStepper } from "./stage-stepper";

const AFTER_LOCK = new Set(["running", "awaiting_review", "completed", "failed"]);

export function RunView({ id }: { id: string }) {
  const run = useRun(id);
  const catalogue = usePlanCatalogue();
  const status = run.data?.status ?? "";
  const { events, connection } = useRunEvents(id, AFTER_LOCK.has(status), status);

  if (run.isPending) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-8 w-96" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (run.isError) {
    return (
      <>
        <PageHeader title="Brief request" />
        <ErrorPanel error={run.error} onRetry={() => run.refetch()} what="this run" />
      </>
    );
  }

  const data = run.data;
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Brief request"
        description={
          <>
            {data.id} · started by {data.created_by_name} · {formatWhen(data.created_at)}
          </>
        }
        actions={<RunStatusBadge status={data.status} className="text-base" />}
      />
      <StageStepper current={stageOf(data.status)} stopped={data.status === "failed"} />

      {data.status === "clarifying" && <ClarifyPanel run={data} />}
      {data.status === "planning" &&
        (catalogue.data ? (
          <PlanEditor run={data} catalogue={catalogue.data} />
        ) : catalogue.isError ? (
          <ErrorPanel error={catalogue.error} onRetry={() => catalogue.refetch()} what="the plan choices" />
        ) : (
          <Skeleton className="h-96 w-full" />
        ))}
      {AFTER_LOCK.has(data.status) && (
        <AfterLock run={data} events={events} connection={connection} catalogue={catalogue.data} />
      )}
    </div>
  );
}

function AfterLock({
  run,
  events,
  connection,
  catalogue,
}: {
  run: Run;
  events: ReturnType<typeof useRunEvents>["events"];
  connection: ReturnType<typeof useRunEvents>["connection"];
  catalogue: PlanCatalogue | undefined;
}) {
  const system = useSystemStatus();
  const resume = useResumeRun(run.id);
  const progress = useMemo(() => buildProgress(events), [events]);
  const validations = progress.steps.filter((s) => s.node === "validate" && s.state === "done");
  const escalated = validations.length > 0 && validations[validations.length - 1].ok === false;

  return (
    <div className="flex flex-col gap-6">
      {run.status === "failed" && (
        <Alert variant="destructive">
          <ShieldAlert aria-hidden />
          <AlertTitle className="text-base">The run stopped</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-3">
            <p className="text-base">{run.error ?? "A step failed."} Finished steps are kept, a resume starts from the last checkpoint.</p>
            {resume.isError && <p className="text-base">{resume.error.message}</p>}
            <Button variant="outline" disabled={resume.isPending} onClick={() => resume.mutate()}>
              {resume.isPending ? "Resuming" : "Resume from the last checkpoint"}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {(run.status === "awaiting_review" || run.status === "completed") && run.brief_id && (
        <DraftReady run={run} escalated={escalated} />
      )}

      <LockedPlan run={run} catalogue={catalogue} />

      <ProgressTimeline
        events={events}
        connection={connection}
        live={run.status === "running"}
        simulatedLatencyMs={system.data?.simulated_source_latency_ms ?? 0}
      />
    </div>
  );
}

function DraftReady({ run, escalated }: { run: Run; escalated: boolean }) {
  const me = useMe();
  const mayReview = me.data?.permissions.includes("review") ?? false;
  const mayRead = me.data?.permissions.includes("view_reports") ?? false;
  const decided = run.status === "completed";
  return (
    <Card className={escalated && !decided ? "border-serious-mark/60" : "border-primary/40"}>
      <CardContent className="flex flex-wrap items-center gap-4 pt-6">
        <ClipboardCheck aria-hidden className="size-6 text-primary" />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-lg font-semibold">
            {decided
              ? "A decision has been recorded"
              : escalated
                ? "The draft is waiting for a person, escalated"
                : "The draft passed all nine checks and is waiting for a person"}
          </p>
          <p className="text-base text-muted-foreground">
            {decided
              ? "The run is finished. The brief shows who decided and what was published."
              : escalated
                ? "Validation could not be satisfied inside the retry budget. The reviewer sees the diagnosis, and a failed integrity check can never be approved."
                : mayReview
                  ? "Nothing is published until a named approver decides."
                  : "A Registrar or Principal will review it. Nothing is published until they decide."}
          </p>
        </div>
        {mayReview && (
          <Button asChild size="lg">
            <Link href={`/review/${run.brief_id}`}>
              {decided ? "Open the brief" : "Open the draft"}
              <ArrowRight aria-hidden data-icon="inline-end" />
            </Link>
          </Button>
        )}
        {decided && !mayReview && mayRead && (
          <Button asChild variant="outline" size="lg">
            <Link href="/reports">Go to reports</Link>
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

function LockedPlan({ run, catalogue }: { run: Run; catalogue: PlanCatalogue | undefined }) {
  const plan = run.plan;
  if (!plan) return null;
  const names = new Map(catalogue?.kpis.map((k) => [k.key, k.name]) ?? []);
  const faultNames = new Map(catalogue?.faults.map((f) => [f.id, f.label]) ?? []);
  return (
    <details className="rounded-xl border bg-card px-4 py-3">
      <summary className="cursor-pointer text-base font-medium">
        Locked plan, revision {plan.revision}: {plan.period_year}, {plan.domains.map((d) => DOMAIN_LABEL[d]).join(", ")},{" "}
        {plan.kpi_keys.length} KPI{plan.kpi_keys.length === 1 ? "" : "s"}
      </summary>
      <div className="mt-3 flex flex-col gap-3 text-base">
        <p>
          <span className="text-muted-foreground">Request: </span>
          {plan.request}
        </p>
        <p>
          <span className="text-muted-foreground">For: </span>
          {plan.audience}.{" "}
          {plan.options_for === "all" ? "Options for every KPI." : "Options for KPIs that are off target."}
        </p>
        <ul className="flex flex-wrap gap-2">
          {plan.kpi_keys.map((key) => (
            <li key={key} className="rounded-md border bg-background px-2 py-0.5 text-sm">
              {names.get(key) ?? key}
            </li>
          ))}
        </ul>
        <ol className="list-decimal pl-5">
          {plan.steps.map((step) => (
            <li key={step.id}>
              <span className="font-medium">{step.title}.</span> <span className="text-muted-foreground">{step.detail}</span>
            </li>
          ))}
        </ol>
        {run.faults.length > 0 && (
          <p className="flex items-center gap-2 text-serious-ink">
            <FlaskConical aria-hidden className="size-4" />
            Failure injected for the demo: {run.faults.map((f) => faultNames.get(f) ?? f).join(", ")}
          </p>
        )}
      </div>
    </details>
  );
}
