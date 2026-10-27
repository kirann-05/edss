"use client";

import { CircleCheck, CircleX, PencilLine, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { DrilldownSheet } from "@/components/drilldown/drilldown-sheet";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { BriefStatusBadge } from "@/components/status/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { useBrief, useCheckEdits, useDecide } from "@/lib/api/queries";
import type { Brief, Decision, EditRequest, Role, ValidationReport } from "@/lib/api/types";
import { FIELD_LABEL, allEdits, decisionState, draftFromOption, type OptionDraft } from "@/lib/brief";
import { useDrilldownParam } from "@/lib/use-drilldown-param";
import { ROLE_LABEL } from "@/lib/roles";
import { formatWhen } from "@/lib/when";

import { BriefDocument } from "./brief-document";
import { BriefTabs } from "./brief-tabs";
import { ConfirmDialog, ReasonDialog } from "./decision-dialogs";
import { FactDialog } from "./fact-dialog";

type Dialog = "approve" | "approve_edits" | "override" | "send_back" | null;

/** The report a refused edit came back with (422), so the approver sees what to fix. */
function rejectedReport(error: unknown): ValidationReport | null {
  if (!(error instanceof ApiError) || error.status !== 422) return null;
  const body = error.detail as { detail?: { report?: ValidationReport } } | undefined;
  return body?.detail?.report ?? null;
}

export function BriefReview({ id }: { id: string }) {
  const brief = useBrief(id);
  const decide = useDecide(id);
  const check = useCheckEdits(id);
  const { open } = useDrilldownParam();

  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, OptionDraft>>({});
  const [checkedFor, setCheckedFor] = useState<string | null>(null);
  const [ack, setAck] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [factId, setFactId] = useState<number | null>(null);

  const edits = useMemo(() => (brief.data && editing ? allEdits(brief.data, drafts) : []), [brief.data, drafts, editing]);
  const editsKey = JSON.stringify(edits);
  const checkCurrent = checkedFor === editsKey && check.data !== undefined;
  const checkPassed = checkCurrent && check.data?.report.passed === true;

  if (brief.isPending) {
    return (
      <div className="flex flex-col gap-6" aria-busy="true">
        <Skeleton className="h-10 w-96" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }
  if (brief.isError) {
    return (
      <>
        <PageHeader title="Draft brief" />
        <ErrorPanel error={brief.error} onRetry={() => brief.refetch()} what="this brief" />
      </>
    );
  }

  const data = brief.data;
  const state = decisionState(data, ack);
  const handlers = { onKpi: (key: string) => open(key), onFact: (factIdValue: number) => setFactId(factIdValue) };
  const editedOptions = new Set(data.edits.map((e) => e.option_id));
  const decideError = decide.error ? decide.error.message : null;
  const rejected = rejectedReport(decide.error);

  const startEditing = () => {
    setDrafts(
      Object.fromEntries(data.document.option_sets.flatMap((set) => set.options.map((o) => [o.id, draftFromOption(o)]))),
    );
    setCheckedFor(null);
    check.reset();
    decide.reset();
    setEditing(true);
  };
  const stopEditing = () => {
    setEditing(false);
    setDrafts({});
    setCheckedFor(null);
    check.reset();
  };
  const runCheck = () => {
    const key = editsKey;
    check.mutate(edits, { onSuccess: () => setCheckedFor(key) });
  };
  const send = (decision: Partial<Decision> & Pick<Decision, "kind">) =>
    decide.mutate(
      { ...decision, ack_escalation: ack },
      {
        onSuccess: () => {
          setDialog(null);
          setEditing(false);
          setDrafts({});
          // the outcome is shown at the top, and the reviewer is usually far down among the options
          const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" });
        },
      },
    );

  return (
    <div className="flex flex-col gap-6 pb-28">
      <PageHeader
        title={data.document.title}
        description={
          <>
            {data.request ? `"${data.request}"` : data.run_id} · drafted {formatWhen(data.created_at)} ·{" "}
            {data.attempts} attempt{data.attempts === 1 ? "" : "s"}
          </>
        }
        actions={
          <>
            <BriefStatusBadge status={data.status} className="text-base" />
            <ValidationChip passed={data.validation.passed} failing={data.approval_state.failing_checks} />
          </>
        }
      />

      {state.kind === "decided" ? (
        <DecisionSummary brief={data} />
      ) : (
        data.status === "escalated" && <EscalationNotice brief={data} />
      )}

      <div className="grid grid-cols-1 items-start gap-8 2xl:grid-cols-[minmax(0,1fr)_24rem]">
        <BriefDocument
          document={data.document}
          decided={state.kind === "decided"}
          handlers={handlers}
          editedOptions={editedOptions}
          editing={editing}
          drafts={drafts}
          onDraft={(optionId, draft) => setDrafts((previous) => ({ ...previous, [optionId]: draft }))}
        />
        <aside className="flex min-w-0 flex-col gap-4 2xl:sticky 2xl:top-20 2xl:max-h-[calc(100dvh-6rem)] 2xl:overflow-y-auto">
          <BriefTabs brief={data} onKpi={handlers.onKpi} />
        </aside>
      </div>

      {state.kind !== "decided" && (
        <div
          role="region"
          aria-label="Decision"
          className="sticky bottom-0 z-20 -mx-4 flex flex-col gap-3 border-t bg-background/95 px-4 py-4 shadow-[0_-4px_12px_rgb(0_0_0/0.04)] backdrop-blur lg:-mx-8 lg:px-8"
        >
          {state.kind === "cannot_decide" ? (
            <p className="text-base text-muted-foreground">{state.reason}</p>
          ) : editing ? (
            <EditingBar
              edits={edits}
              checking={check.isPending}
              checkCurrent={checkCurrent}
              checkPassed={checkPassed}
              checkReport={check.data?.report ?? null}
              checkError={check.error?.message ?? null}
              onCheck={runCheck}
              onApprove={() => setDialog("approve_edits")}
              onCancel={stopEditing}
              busy={decide.isPending}
            />
          ) : (
            <>
              {state.needsAcknowledgement && (
                <div className="flex items-start gap-3">
                  <Checkbox id="ack" checked={ack} onCheckedChange={(v) => setAck(v === true)} className="mt-0.5 size-5" />
                  <Label htmlFor="ack" className="text-base font-normal">
                    I acknowledge that checks {data.approval_state.failing_checks.join(", ")} did not pass, and I am
                    approving with that known.
                  </Label>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <Button size="lg" disabled={!state.approve.enabled || decide.isPending} onClick={() => setDialog("approve")}>
                  <CircleCheck aria-hidden data-icon="inline-start" />
                  Approve
                </Button>
                <Button size="lg" variant="outline" disabled={decide.isPending} onClick={startEditing}>
                  <PencilLine aria-hidden data-icon="inline-start" />
                  Edit options
                </Button>
                <Button size="lg" variant="outline" disabled={decide.isPending} onClick={() => setDialog("send_back")}>
                  Send back
                </Button>
                <Button size="lg" variant="destructive" disabled={decide.isPending} onClick={() => setDialog("override")}>
                  Override
                </Button>
                {state.approve.reason && <p className="text-base text-muted-foreground">{state.approve.reason}</p>}
              </div>
            </>
          )}
          {decideError && dialog === null && (
            <p role="alert" className="text-base text-critical-ink">
              {decideError}
              {rejected && ` Failing: ${rejected.checks.filter((c) => !c.passed).map((c) => c.id).join(", ")}.`}
            </p>
          )}
        </div>
      )}

      <ConfirmDialog
        open={dialog === "approve"}
        onOpenChange={(o) => setDialog(o ? "approve" : null)}
        title="Approve and publish?"
        description="The brief is published as the next report version, under your name and role, and the audit log records it. A Registrar or Principal can roll it back later, nothing is ever deleted."
        confirmLabel="Approve and publish"
        busy={decide.isPending}
        busyLabel="Publishing"
        error={dialog === "approve" ? decideError : null}
        onConfirm={() => send({ kind: "approve" })}
      />
      <ConfirmDialog
        open={dialog === "approve_edits"}
        onOpenChange={(o) => setDialog(o ? "approve_edits" : null)}
        title="Approve with your edits?"
        description="Your edits are checked again on the server. If they pass, the edited brief is published and the draft's text is kept beside it, so anyone can see what changed."
        confirmLabel="Approve with edits"
        busy={decide.isPending}
        busyLabel="Publishing"
        error={dialog === "approve_edits" ? decideError : null}
        onConfirm={() => send({ kind: "edit", edits })}
      >
        <EditList edits={edits} />
      </ConfirmDialog>
      <ReasonDialog
        open={dialog === "send_back"}
        onOpenChange={(o) => setDialog(o ? "send_back" : null)}
        title="Send the draft back"
        description="Nothing is published. The run ends and the reason is recorded, so whoever starts the next run knows what to change."
        confirmLabel="Send back"
        busy={decide.isPending}
        error={dialog === "send_back" ? decideError : null}
        onConfirm={(reason) => send({ kind: "send_back", reason })}
      />
      <ReasonDialog
        open={dialog === "override"}
        onOpenChange={(o) => setDialog(o ? "override" : null)}
        title="Override the draft"
        description="You set the agents' draft aside. Nothing is published, and your reason is kept in the audit log beside your name."
        confirmLabel="Override"
        destructive
        busy={decide.isPending}
        error={dialog === "override" ? decideError : null}
        onConfirm={(reason) => send({ kind: "override", reason })}
      />

      <DrilldownSheet period={data.period_year} />
      <FactDialog id={factId} onClose={() => setFactId(null)} />
    </div>
  );
}

function ValidationChip({ passed, failing }: { passed: boolean; failing: string[] }) {
  return passed ? (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-good-mark/50 bg-good-tint px-2 py-0.5 text-base font-medium text-good-ink">
      <CircleCheck aria-hidden className="size-4" />
      Validation passed
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-critical-mark/50 bg-critical-tint px-2 py-0.5 text-base font-medium text-critical-ink">
      <CircleX aria-hidden className="size-4" />
      Failing {failing.join(", ")}
    </span>
  );
}

function EscalationNotice({ brief }: { brief: Brief }) {
  const state = brief.approval_state;
  return (
    <Alert className="border-serious-mark/60 bg-serious-tint">
      <ShieldAlert aria-hidden className="text-serious-ink" />
      <AlertTitle className="text-base text-serious-ink">
        Escalated after {brief.attempts} attempts: validation could not be satisfied inside the retry budget
      </AlertTitle>
      <AlertDescription className="flex flex-col gap-2 text-base text-foreground">
        {brief.diagnosis && <p>Diagnosis: {brief.diagnosis}</p>}
        <p>
          {state.can_approve
            ? `Only completeness checks failed (${state.failing_checks.join(", ")}). You may approve after acknowledging that, or edit the options until they pass.`
            : `${state.blocked_reason ?? "Approval is blocked."} You can also edit the failing options until the checks pass, then approve with your edits.`}
        </p>
      </AlertDescription>
    </Alert>
  );
}

function DecisionSummary({ brief }: { brief: Brief }) {
  if (brief.status === "published" || brief.status === "approved" || brief.status === "rolled_back") {
    const approval = brief.approval;
    return (
      <Alert className={brief.status === "rolled_back" ? "border-warning-mark/70 bg-warning-tint" : "border-good-mark/50 bg-good-tint"}>
        <CircleCheck aria-hidden />
        <AlertTitle className="text-base">
          {brief.status === "rolled_back"
            ? `Version ${brief.version} was taken out of service by a rollback`
            : `Published as version ${brief.version}`}
        </AlertTitle>
        <AlertDescription className="flex flex-col gap-2 text-base text-foreground">
          {approval && (
            <p>
              Approved by {approval.actor_name} ({ROLE_LABEL[approval.role as Role] ?? approval.role}) on{" "}
              {formatWhen(approval.at)}
              {approval.ack_escalation ? ", acknowledging that it was escalated" : ""}.
            </p>
          )}
          {brief.edits.length > 0 && (
            <details>
              <summary className="cursor-pointer font-medium">
                {brief.edits.length} edit{brief.edits.length === 1 ? "" : "s"} made on approval
              </summary>
              <EditList
                edits={brief.edits.map((e) => ({ option_id: e.option_id, field: e.field as EditRequest["field"], value: e.after }))}
                before={Object.fromEntries(brief.edits.map((e) => [`${e.option_id}:${e.field}`, e.before]))}
              />
            </details>
          )}
          {brief.version !== null && (
            <Link href={`/reports/${brief.version}`} className="w-fit font-medium underline underline-offset-4">
              Open version {brief.version} in Reports
            </Link>
          )}
        </AlertDescription>
      </Alert>
    );
  }
  return (
    <Alert>
      <ShieldAlert aria-hidden />
      <AlertTitle className="text-base">{brief.status === "overridden" ? "Overridden" : "Sent back"}, nothing was published</AlertTitle>
      <AlertDescription className="text-base text-foreground">Reason: {brief.decision_reason}</AlertDescription>
    </Alert>
  );
}

function EditList({
  edits,
  before = {},
}: {
  edits: EditRequest[];
  before?: Record<string, string | string[]>;
}) {
  if (edits.length === 0) return null;
  const text = (value: string | string[]) => (Array.isArray(value) ? value.join("\n") : value);
  return (
    <ul className="mt-2 flex max-h-72 flex-col gap-2 overflow-y-auto">
      {edits.map((edit) => {
        const key = `${edit.option_id}:${edit.field}`;
        return (
          <li key={key} className="flex flex-col gap-1 rounded-lg border bg-background p-2 text-sm">
            <span className="font-semibold">
              {edit.option_id}, {FIELD_LABEL[edit.field]}
            </span>
            {before[key] !== undefined && (
              <span className="whitespace-pre-wrap text-critical-ink">
                <span className="sr-only">Before: </span>
                <del>{text(before[key])}</del>
              </span>
            )}
            <span className="whitespace-pre-wrap text-good-ink">
              <span className="sr-only">After: </span>
              {text(edit.value)}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function EditingBar({
  edits,
  checking,
  checkCurrent,
  checkPassed,
  checkReport,
  checkError,
  onCheck,
  onApprove,
  onCancel,
  busy,
}: {
  edits: EditRequest[];
  checking: boolean;
  checkCurrent: boolean;
  checkPassed: boolean;
  checkReport: ValidationReport | null;
  checkError: string | null;
  onCheck: () => void;
  onApprove: () => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const failing = checkReport?.checks.filter((c) => !c.passed) ?? [];
  // the server's own words for what is wrong, so the approver knows what to change
  const problems = failing.flatMap((c) => c.violations.map((v) => `${c.id}: ${v.message}`)).slice(0, 3);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-base font-medium">
          {edits.length === 0 ? "No changes yet" : `${edits.length} change${edits.length === 1 ? "" : "s"}`}
        </span>
        <Button size="lg" variant="outline" disabled={edits.length === 0 || checking || busy} onClick={onCheck}>
          {checking ? "Checking" : "Check my edits"}
        </Button>
        <Button size="lg" disabled={!checkPassed || busy} onClick={onApprove}>
          <CircleCheck aria-hidden data-icon="inline-start" />
          Approve with edits
        </Button>
        <Button size="lg" variant="ghost" disabled={busy} onClick={onCancel}>
          Cancel editing
        </Button>
      </div>
      <p role="status" className="text-base">
        {checkError ? (
          <span className="text-critical-ink">{checkError}</span>
        ) : !checkCurrent ? (
          <span className="text-muted-foreground">
            {edits.length === 0 ? "Change an option above." : "Check your edits against all nine checks before approving."}
          </span>
        ) : checkPassed ? (
          <span className="text-good-ink">Your edits pass all nine checks. Nothing is saved until you approve.</span>
        ) : (
          <span className="flex flex-col gap-1 text-critical-ink">
            <span>
              Your edits fail {failing.map((c) => c.id).join(", ")}. Fix them and check again.
            </span>
            {problems.map((problem) => (
              <span key={problem} className="text-sm">
                {problem}
              </span>
            ))}
          </span>
        )}
      </p>
    </div>
  );
}
