"use client";

import { cn } from "cn";
import { Bot, ChevronRight, Cog, Link2, ShieldCheck, ShieldX, UserRound, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useAudit, useAuditActions, useAuditVerification } from "@/lib/api/queries";
import type { AuditRow } from "@/lib/api/types";
import {
  PAGE_SIZE,
  actionWords,
  auditQuery,
  filtersFrom,
  filtersToParams,
  rowSummary,
  shortHash,
  type AuditFilters,
} from "@/lib/audit";
import { formatClock, formatDay } from "@/lib/when";

const ACTOR_ICON: Record<string, LucideIcon> = { user: UserRound, agent: Bot, system: Cog };

export function VerificationBanner() {
  const verify = useAuditVerification();
  if (verify.isPending) return <Skeleton className="h-20 w-full" />;
  if (verify.isError) return <ErrorPanel error={verify.error} onRetry={() => verify.refetch()} what="the chain check" />;
  const result = verify.data;
  return result.ok ? (
    <Alert className="border-good-mark/50 bg-good-tint">
      <ShieldCheck aria-hidden className="text-good-ink" />
      <AlertTitle className="text-base text-good-ink">The audit chain verifies</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center gap-3 text-base text-foreground">
        All {result.checked} rows were recomputed just now, and each one links to the hash of the row before it.
        <Button variant="outline" size="sm" disabled={verify.isFetching} onClick={() => verify.refetch()}>
          {verify.isFetching ? "Checking" : "Check again"}
        </Button>
      </AlertDescription>
    </Alert>
  ) : (
    <Alert variant="destructive">
      <ShieldX aria-hidden />
      <AlertTitle className="text-base">The audit chain is broken at row {result.broken_at}</AlertTitle>
      <AlertDescription className="text-base">
        Row {result.broken_at} {result.reason}. Every row from there on can no longer be trusted. Checked {result.checked}{" "}
        rows before the break.
      </AlertDescription>
    </Alert>
  );
}

export function AuditView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const applied = filtersFrom(params);
  const [draft, setDraft] = useState<AuditFilters>(applied);
  const page = useAudit(auditQuery(applied));
  const actions = useAuditActions();

  const go = (filters: AuditFilters) => {
    const text = filtersToParams(filters);
    router.replace(text ? `${pathname}?${text}` : pathname, { scroll: false });
  };

  const total = page.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        title="Audit"
        description="Every step, decision and refusal, newest first. Filtering changes what you see, never what the chain check covers."
      />
      <VerificationBanner />

      <form
        className="grid gap-4 rounded-xl border bg-card p-4 md:grid-cols-3 xl:grid-cols-6"
        onSubmit={(event) => {
          event.preventDefault();
          go({ ...draft, page: 1 });
        }}
      >
        <Field id="f-run" label="Run">
          <Input id="f-run" value={draft.run} onChange={(e) => setDraft({ ...draft, run: e.target.value })} placeholder="run-1" className="h-10 text-base" />
        </Field>
        <Field id="f-actor" label="Actor">
          <Input
            id="f-actor"
            value={draft.actor}
            onChange={(e) => setDraft({ ...draft, actor: e.target.value })}
            placeholder="email or agent"
            className="h-10 text-base"
          />
        </Field>
        <Field id="f-action" label="Action">
          <Input
            id="f-action"
            list="audit-actions"
            value={draft.action}
            onChange={(e) => setDraft({ ...draft, action: e.target.value })}
            placeholder="any"
            className="h-10 text-base"
          />
          <datalist id="audit-actions">
            {(actions.data ?? []).map((a) => (
              <option key={a} value={a}>
                {actionWords(a)}
              </option>
            ))}
          </datalist>
        </Field>
        <Field id="f-since" label="From">
          <Input id="f-since" type="date" value={draft.since} onChange={(e) => setDraft({ ...draft, since: e.target.value })} className="h-10 text-base" />
        </Field>
        <Field id="f-until" label="To">
          <Input id="f-until" type="date" value={draft.until} onChange={(e) => setDraft({ ...draft, until: e.target.value })} className="h-10 text-base" />
        </Field>
        <div className="flex items-end gap-2">
          <Button type="submit">Filter</Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              const empty = filtersFrom(new URLSearchParams());
              setDraft(empty);
              go(empty);
            }}
          >
            Clear
          </Button>
        </div>
      </form>

      {page.isPending ? (
        <Skeleton className="h-96 w-full" />
      ) : page.isError ? (
        <ErrorPanel error={page.error} onRetry={() => page.refetch()} what="the audit log" />
      ) : page.data.rows.length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-base text-muted-foreground">
          No rows match these filters.
        </p>
      ) : (
        <section aria-label="Audit rows" className={cn("flex flex-col gap-3", page.isFetching && "opacity-70")}>
          <p className="text-base text-muted-foreground">
            Showing {page.data.offset + 1} to {page.data.offset + page.data.rows.length} of {total}
          </p>
          <AuditRows rows={page.data.rows} />
          <nav aria-label="Pages" className="flex items-center gap-3">
            <Button variant="outline" disabled={applied.page <= 1} onClick={() => go({ ...applied, page: applied.page - 1 })}>
              Newer
            </Button>
            <span className="text-base">
              Page {applied.page} of {pages}
            </span>
            <Button variant="outline" disabled={applied.page >= pages} onClick={() => go({ ...applied, page: applied.page + 1 })}>
              Older
            </Button>
          </nav>
        </section>
      )}
    </>
  );
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id} className="text-base">
        {label}
      </Label>
      {children}
    </div>
  );
}

export function AuditRows({ rows, showRun = true }: { rows: AuditRow[]; showRun?: boolean }) {
  return (
    <ol className="flex flex-col divide-y rounded-xl border bg-card">
      {rows.map((row) => (
        <AuditRowItem key={row.id} row={row} showRun={showRun} />
      ))}
    </ol>
  );
}

function AuditRowItem({ row, showRun }: { row: AuditRow; showRun: boolean }) {
  const [open, setOpen] = useState(false);
  const Icon = ACTOR_ICON[row.actor_type] ?? Cog;
  const summary = rowSummary(row);
  const refused = row.action === "brief.refused" || row.action === "auth.locked" || row.action === "auth.login_failed";
  return (
    <li className="flex flex-col">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="grid grid-cols-[1.25rem_4rem_minmax(0,1fr)] items-start gap-x-3 gap-y-1 px-4 py-3 text-left outline-none hover:bg-muted/50 focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring md:grid-cols-[1.25rem_4rem_9rem_minmax(0,14rem)_minmax(0,1fr)]"
      >
        <ChevronRight aria-hidden className={cn("mt-0.5 size-4 transition-transform motion-reduce:transition-none", open && "rotate-90")} />
        <span className="font-mono text-sm text-muted-foreground tabular-nums">#{row.id}</span>
        <span className="col-start-3 text-sm text-muted-foreground tabular-nums md:col-start-auto">
          {formatDay(row.ts)} {formatClock(row.ts)}
        </span>
        <span className="col-start-3 flex min-w-0 items-center gap-1.5 text-sm md:col-start-auto">
          <Icon aria-hidden className="size-4 shrink-0 text-muted-foreground" />
          <span className="sr-only">{row.actor_type}:</span>
          <span className="truncate">{row.actor_id}</span>
        </span>
        <span className="col-start-3 flex min-w-0 flex-col md:col-start-auto">
          <span className={cn("text-base font-medium", refused && "text-critical-ink")}>
            {actionWords(row.action)} <span className="font-mono text-xs font-normal text-muted-foreground">{row.action}</span>
          </span>
          {summary && <span className="truncate text-sm text-muted-foreground">{summary}</span>}
        </span>
      </button>
      {open && (
        <div className="flex flex-col gap-3 border-t bg-background px-4 py-3 md:pl-28">
          {showRun && row.run_id && (
            <Link
              href={`/audit/runs/${row.run_id}`}
              className="inline-flex w-fit items-center gap-1.5 text-base font-medium underline underline-offset-4"
            >
              <Link2 aria-hidden className="size-4" />
              Run trace for {row.run_id}
            </Link>
          )}
          <div className="grid gap-3 lg:grid-cols-2">
            <Payload title="Inputs" value={row.inputs} />
            <Payload title="Outputs" value={row.outputs} />
          </div>
          <p className="font-mono text-xs break-all text-muted-foreground">
            previous hash {shortHash(row.prev_hash)} → this row {shortHash(row.hash)}
            <span className="sr-only"> (full hash {row.hash})</span>
          </p>
        </div>
      )}
    </li>
  );
}

function Payload({ title, value }: { title: string; value: Record<string, unknown> }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-sm font-semibold">{title}</span>
      <pre className="max-h-64 overflow-auto rounded-lg border bg-muted/40 p-2 text-xs leading-relaxed">
        {Object.keys(value).length === 0 ? "nothing" : JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}
