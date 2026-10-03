"use client";

import { FlaskConical, Lock, Sparkles } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useEditPlan, useLockPlan, useRevisePlan } from "@/lib/api/queries";
import { DOMAIN_LABEL, type Domain, type PlanCatalogue, type Run } from "@/lib/api/types";
import {
  domainState,
  draftFromPlan,
  draftProblems,
  isEmptyPatch,
  patchFromDraft,
  setDomain,
  toggleKpi,
  type PlanDraft,
} from "@/lib/plan-draft";
import { formatClock } from "@/lib/when";

import { Conversation } from "./clarify-panel";

const OPTIONS_FOR: { value: PlanDraft["options_for"]; label: string; hint: string }[] = [
  { value: "off_target", label: "Off-target KPIs only", hint: "Options for every KPI that is missed or at risk" },
  { value: "all", label: "Every KPI", hint: "Options for every KPI in the plan, met ones included" },
];

export function PlanEditor({ run, catalogue }: { run: Run; catalogue: PlanCatalogue }) {
  const plan = run.plan;
  const edit = useEditPlan(run.id);
  const revise = useRevisePlan(run.id);
  const lock = useLockPlan(run.id);

  const [draft, setDraft] = useState<PlanDraft | null>(() => (plan ? draftFromPlan(plan) : null));
  const [shownRevision, setShownRevision] = useState(plan?.revision ?? 0);
  const [feedback, setFeedback] = useState("");
  const [faults, setFaults] = useState<string[]>([]);

  // A saved edit or a revision from the planner replaces the draft with what the server now holds
  if (plan && plan.revision !== shownRevision) {
    setShownRevision(plan.revision);
    setDraft(draftFromPlan(plan));
  }
  if (!plan || !draft) return null;

  const patch = patchFromDraft(plan, draft);
  const dirty = !isEmptyPatch(patch);
  const problems = draftProblems(draft);
  const kpis = catalogue.kpis;
  const update = (next: Partial<PlanDraft>) => setDraft({ ...draft, ...next });
  const busy = edit.isPending || revise.isPending || lock.isPending;
  const audiences = catalogue.audiences.includes(draft.audience)
    ? catalogue.audiences
    : [draft.audience, ...catalogue.audiences];

  return (
    <div className="flex flex-col gap-6">
      <details className="group rounded-xl border bg-card px-4 py-3">
        <summary className="cursor-pointer text-base font-medium text-muted-foreground">
          The conversation so far
        </summary>
        <div className="mt-4">
          <Conversation run={run} />
        </div>
      </details>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Scope</CardTitle>
              <CardDescription className="text-base">
                Revision {plan.revision}. Change anything here, then save. Nothing runs until you lock the plan.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 sm:grid-cols-2">
              <div className="flex flex-col gap-2">
                <Label htmlFor="plan-period" className="text-base">
                  Period
                </Label>
                <Select value={draft.period_year} onValueChange={(value) => update({ period_year: value })}>
                  <SelectTrigger id="plan-period" className="h-11 w-full text-base">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[...catalogue.periods].reverse().map((p) => (
                      <SelectItem key={p} value={p} className="text-base">
                        {p}
                        {p === catalogue.current_period ? " (current)" : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="plan-audience" className="text-base">
                  Who will read it
                </Label>
                <Select value={draft.audience} onValueChange={(value) => update({ audience: value })}>
                  <SelectTrigger id="plan-audience" className="h-11 w-full text-base">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {audiences.map((a) => (
                      <SelectItem key={a} value={a} className="text-base">
                        {a}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <fieldset className="flex flex-col gap-2 sm:col-span-2">
                <legend className="mb-2 text-base font-medium">Draft options for</legend>
                <div className="flex flex-wrap gap-3">
                  {OPTIONS_FOR.map((option) => (
                    <label
                      key={option.value}
                      className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border bg-background px-3 py-2 has-[:checked]:border-primary has-[:checked]:bg-primary/5 has-[:focus-visible]:ring-3 has-[:focus-visible]:ring-ring/50"
                    >
                      <input
                        type="radio"
                        name="options_for"
                        value={option.value}
                        checked={draft.options_for === option.value}
                        onChange={() => update({ options_for: option.value })}
                        className="mt-1 size-4 accent-[var(--primary)]"
                      />
                      <span className="flex flex-col">
                        <span className="text-base font-medium">{option.label}</span>
                        <span className="text-sm text-muted-foreground">{option.hint}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xl">KPIs</CardTitle>
              <CardDescription className="text-base">
                {draft.kpi_keys.length} of {kpis.length} chosen. An area is included when any of its KPIs is.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2">
              {catalogue.domains.map((domain) => (
                <DomainGroup
                  key={domain}
                  domain={domain}
                  draft={draft}
                  catalogue={catalogue}
                  onArea={(on) => setDraft(setDomain(draft, domain, on, kpis))}
                  onKpi={(key) => setDraft(toggleKpi(draft, key, kpis))}
                />
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Outline</CardTitle>
              <CardDescription className="text-base">
                The steps the agents will follow. You can reword them, the work itself is fixed by the graph. Changing
                the scope above does not reword them, the planner does when you ask for changes in words.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ol className="flex flex-col gap-4">
                {plan.steps.map((step, index) => {
                  const value = draft.steps[step.id] ?? { title: step.title, detail: step.detail };
                  return (
                    <li key={step.id} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-3">
                      <span
                        aria-hidden
                        className="mt-2 grid size-7 place-items-center rounded-full bg-muted text-sm font-semibold"
                      >
                        {index + 1}
                      </span>
                      <div className="flex flex-col gap-2">
                        <Input
                          value={value.title}
                          aria-label={`Step ${index + 1} title`}
                          onChange={(event) =>
                            update({ steps: { ...draft.steps, [step.id]: { ...value, title: event.target.value } } })
                          }
                          className="h-10 text-base font-medium"
                        />
                        <Textarea
                          value={value.detail}
                          aria-label={`Step ${index + 1} detail`}
                          onChange={(event) =>
                            update({ steps: { ...draft.steps, [step.id]: { ...value, detail: event.target.value } } })
                          }
                          rows={2}
                          className="min-h-0 text-base text-muted-foreground"
                        />
                      </div>
                    </li>
                  );
                })}
              </ol>
            </CardContent>
          </Card>

          {(dirty || edit.isError) && (
            <div
              role="region"
              aria-label="Unsaved changes"
              className="sticky bottom-4 z-10 flex flex-wrap items-center gap-3 rounded-xl border bg-card p-4 shadow-lg"
            >
              <span className="text-base font-medium">You have unsaved changes.</span>
              {problems.length > 0 && <span className="text-base text-critical-ink">{problems.join(" ")}</span>}
              {edit.isError && <span className="text-base text-critical-ink">{edit.error.message}</span>}
              <span className="ml-auto flex gap-2">
                <Button variant="outline" disabled={busy} onClick={() => setDraft(draftFromPlan(plan))}>
                  Discard
                </Button>
                <Button disabled={busy || problems.length > 0} onClick={() => edit.mutate(patch)}>
                  {edit.isPending ? "Saving" : "Save changes"}
                </Button>
              </span>
            </div>
          )}
        </div>

        <aside className="flex flex-col gap-6 xl:sticky xl:top-20">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Sparkles aria-hidden className="size-5 text-primary" />
                Ask for changes
              </CardTitle>
              <CardDescription className="text-base">
                Say it in words, for example &quot;drop finance&quot; or &quot;options for every KPI&quot;.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form
                className="flex flex-col gap-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!feedback.trim() || busy || dirty) return;
                  revise.mutate(feedback, { onSuccess: () => setFeedback("") });
                }}
              >
                <Label htmlFor="plan-feedback" className="sr-only">
                  What should change
                </Label>
                <Textarea
                  id="plan-feedback"
                  value={feedback}
                  onChange={(event) => setFeedback(event.target.value)}
                  rows={3}
                  className="text-base"
                  placeholder="What should change?"
                />
                {dirty && (
                  <p className="text-sm text-muted-foreground">Save or discard your own edits first.</p>
                )}
                <Button type="submit" variant="outline" disabled={!feedback.trim() || busy || dirty}>
                  {revise.isPending ? "Revising" : "Revise the plan"}
                </Button>
              </form>
              {revise.isError && (
                <Alert variant="destructive" className="mt-3">
                  <AlertDescription className="text-base">{revise.error.message}</AlertDescription>
                </Alert>
              )}
              {revise.data && (
                <Alert className="mt-3" aria-live="polite">
                  <AlertTitle className="text-base">What changed</AlertTitle>
                  <AlertDescription>
                    {revise.data.changes.length === 0 ? (
                      <p className="text-base">Nothing. The planner did not find a change it could make from that.</p>
                    ) : (
                      <ul className="list-disc pl-5 text-base">
                        {revise.data.changes.map((change) => (
                          <li key={change}>{change}</li>
                        ))}
                      </ul>
                    )}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          <LockCard
            run={run}
            catalogue={catalogue}
            faults={faults}
            onFaults={setFaults}
            disabledReason={
              dirty ? "Save or discard your edits first." : problems.length > 0 ? problems.join(" ") : null
            }
            busy={busy}
            error={lock.error?.message ?? null}
            onLock={() => lock.mutate(faults)}
            locking={lock.isPending}
          />

          <details className="rounded-xl border bg-card px-4 py-3">
            <summary className="cursor-pointer text-base font-medium">
              Revision history ({run.plan_history.length})
            </summary>
            <ol className="mt-3 flex flex-col gap-3">
              {[...run.plan_history].reverse().map((entry) => (
                <li key={`${entry.revision}-${entry.at}`} className="flex flex-col gap-1">
                  <span className="text-sm text-muted-foreground">
                    Revision {entry.revision} · {formatClock(entry.at)}
                  </span>
                  <ul className="list-disc pl-5 text-base">
                    {entry.changes.map((change) => (
                      <li key={change}>{change}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </details>
        </aside>
      </div>
    </div>
  );
}

function DomainGroup({
  domain,
  draft,
  catalogue,
  onArea,
  onKpi,
}: {
  domain: Domain;
  draft: PlanDraft;
  catalogue: PlanCatalogue;
  onArea: (on: boolean) => void;
  onKpi: (key: string) => void;
}) {
  const inDomain = catalogue.kpis.filter((k) => k.domain === domain);
  const state = domainState(draft, domain, catalogue.kpis);
  const chosen = inDomain.filter((k) => draft.kpi_keys.includes(k.key)).length;
  const areaId = `area-${domain}`;
  return (
    <fieldset className="flex flex-col gap-2 rounded-lg border p-3">
      <legend className="sr-only">{DOMAIN_LABEL[domain]} KPIs</legend>
      <div className="flex items-center gap-3 border-b pb-2">
        <Checkbox
          id={areaId}
          checked={state}
          onCheckedChange={() => onArea(state !== true)}
          className="size-5"
        />
        <Label htmlFor={areaId} className="text-base font-semibold">
          {DOMAIN_LABEL[domain]}
        </Label>
        <span className="ml-auto text-sm text-muted-foreground">
          {chosen} of {inDomain.length}
        </span>
      </div>
      <ul className="flex flex-col gap-1">
        {inDomain.map((kpi) => {
          const id = `kpi-${kpi.key}`;
          return (
            <li key={kpi.key} className="flex min-h-10 items-center gap-3">
              <Checkbox
                id={id}
                checked={draft.kpi_keys.includes(kpi.key)}
                onCheckedChange={() => onKpi(kpi.key)}
                className="size-5"
              />
              <Label htmlFor={id} className="flex flex-1 flex-wrap items-baseline gap-x-2 text-base font-normal">
                {kpi.name}
                <span className="font-mono text-xs text-muted-foreground">{kpi.key}</span>
              </Label>
            </li>
          );
        })}
      </ul>
    </fieldset>
  );
}

function LockCard({
  run,
  catalogue,
  faults,
  onFaults,
  disabledReason,
  busy,
  error,
  onLock,
  locking,
}: {
  run: Run;
  catalogue: PlanCatalogue;
  faults: string[];
  onFaults: (next: string[]) => void;
  disabledReason: string | null;
  busy: boolean;
  error: string | null;
  onLock: () => void;
  locking: boolean;
}) {
  const plan = run.plan;
  if (!plan) return null;
  const toggle = (id: string) => onFaults(faults.includes(id) ? faults.filter((f) => f !== id) : [...faults, id]);
  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-xl">
          <Lock aria-hidden className="size-5 text-primary" />
          Lock and run
        </CardTitle>
        <CardDescription className="text-base">
          Locking freezes revision {plan.revision}. The agents then work on {plan.kpi_keys.length} KPI
          {plan.kpi_keys.length === 1 ? "" : "s"} across {plan.domains.length} area{plan.domains.length === 1 ? "" : "s"} for{" "}
          {plan.period_year}, and the plan cannot change afterwards.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {catalogue.faults.length > 0 && (
          <details className="rounded-lg border border-dashed px-3 py-2">
            <summary className="flex cursor-pointer items-center gap-2 text-base font-medium">
              <FlaskConical aria-hidden className="size-4" />
              Demo: inject a failure{faults.length > 0 ? ` (${faults.length} on)` : ""}
            </summary>
            <p className="mt-2 text-sm text-muted-foreground">
              Breaks the draft on purpose so you can watch the validation gate catch it and repair it. Synthetic data
              only.
            </p>
            <ul className="mt-2 flex flex-col gap-2">
              {catalogue.faults.map((fault) => {
                const id = `fault-${fault.id}`;
                return (
                  <li key={fault.id} className="flex items-start gap-3">
                    <Checkbox
                      id={id}
                      checked={faults.includes(fault.id)}
                      onCheckedChange={() => toggle(fault.id)}
                      className="mt-0.5 size-5"
                    />
                    <Label htmlFor={id} className="flex flex-col items-start gap-0.5 text-base font-normal">
                      <span className="font-medium">{fault.label}</span>
                      <span className="text-sm text-muted-foreground">{fault.description}</span>
                    </Label>
                  </li>
                );
              })}
            </ul>
          </details>
        )}
        {disabledReason && <p className="text-sm text-muted-foreground">{disabledReason}</p>}
        {error && (
          <Alert variant="destructive">
            <AlertDescription className="text-base">{error}</AlertDescription>
          </Alert>
        )}
        <Button size="lg" disabled={busy || disabledReason !== null} onClick={onLock}>
          <Lock aria-hidden data-icon="inline-start" />
          {locking ? "Locking" : "Lock plan and start"}
        </Button>
      </CardContent>
    </Card>
  );
}
