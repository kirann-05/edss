"use client";

import { ArrowRight, FileText, Printer, Undo2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ReasonDialog } from "@/components/brief/decision-dialogs";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { VersionStateBadge } from "@/components/status/status-badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMe, useRollback, useVersions } from "@/lib/api/queries";
import type { Version } from "@/lib/api/types";
import { formatWhen } from "@/lib/when";

import { DiffView } from "./diff-view";

export function ReportsView() {
  const me = useMe();
  const versions = useVersions();
  const rollback = useRollback();
  const [target, setTarget] = useState<Version | null>(null);
  const [compare, setCompare] = useState<{ from: number; to: number } | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const mayRollback = me.data?.permissions.includes("rollback") ?? false;

  if (versions.isPending) return <Skeleton className="h-96 w-full" />;
  if (versions.isError) {
    return (
      <>
        <PageHeader title="Reports" />
        <ErrorPanel error={versions.error} onRetry={() => versions.refetch()} what="the reports" />
      </>
    );
  }

  const list = versions.data; // newest first
  const current = list.find((v) => v.state === "current") ?? null;
  const pair = compare ?? (list.length >= 2 ? { from: list[1].version, to: list[0].version } : null);

  return (
    <>
      <PageHeader
        title="Reports"
        description="Every approved brief is kept as an immutable version. One is current. A rollback moves the pointer back and deletes nothing."
      />

      {done && (
        <Alert className="border-good-mark/50 bg-good-tint" aria-live="polite">
          <AlertDescription className="text-base">{done}</AlertDescription>
        </Alert>
      )}

      {current ? (
        <Card className="border-primary/40">
          <CardHeader>
            <CardDescription className="text-base">Current report</CardDescription>
            <CardTitle className="flex flex-wrap items-center gap-3 text-2xl">
              {current.title}
              <span className="text-lg font-normal text-muted-foreground">version {current.version}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-center gap-4">
            <p className="text-base text-muted-foreground">
              Approved by {current.approved_by} on {formatWhen(current.approved_at)} · {current.kpi_count} KPIs
              {current.edit_count > 0 ? ` · ${current.edit_count} edit${current.edit_count === 1 ? "" : "s"} on approval` : ""}
            </p>
            <span className="ml-auto flex gap-2">
              <Button asChild variant="outline">
                <Link href={`/reports/${current.version}?print=1`}>
                  <Printer aria-hidden data-icon="inline-start" />
                  Print or save as PDF
                </Link>
              </Button>
              <Button asChild>
                <Link href={`/reports/${current.version}`}>
                  Open
                  <ArrowRight aria-hidden data-icon="inline-end" />
                </Link>
              </Button>
            </span>
          </CardContent>
        </Card>
      ) : (
        <p className="rounded-xl border border-dashed p-8 text-center text-base text-muted-foreground">
          No report has been approved yet. A brief becomes a report when a Registrar or Principal approves it.
        </p>
      )}

      {list.length > 0 && (
        <section aria-labelledby="versions-heading" className="flex flex-col gap-3">
          <h2 id="versions-heading" className="text-xl font-semibold">
            All versions
          </h2>
          <div className="rounded-xl border bg-card px-2">
            <Table className="text-base">
              <TableHeader>
                <TableRow>
                  <TableHead className="text-base">Version</TableHead>
                  <TableHead className="text-base">Brief</TableHead>
                  <TableHead className="text-base">Approved</TableHead>
                  <TableHead className="text-base">State</TableHead>
                  <TableHead className="text-right text-base">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {list.map((version) => (
                  <TableRow key={version.version} className="align-top">
                    <TableCell className="py-3 font-semibold tabular-nums">v{version.version}</TableCell>
                    <TableCell className="py-3 whitespace-normal">
                      <Link
                        href={`/reports/${version.version}`}
                        className="font-medium underline-offset-4 outline-none hover:underline focus-visible:underline focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {version.title}
                      </Link>
                      <span className="block text-sm text-muted-foreground">
                        {version.kpi_count} KPIs
                        {version.edit_count > 0 ? ` · ${version.edit_count} edit${version.edit_count === 1 ? "" : "s"} on approval` : ""}
                        {version.escalation_acknowledged ? " · escalation acknowledged" : ""}
                      </span>
                    </TableCell>
                    <TableCell className="py-3 whitespace-normal">
                      {version.approved_by}
                      <span className="block text-sm text-muted-foreground">{formatWhen(version.approved_at)}</span>
                    </TableCell>
                    <TableCell className="py-3">
                      <VersionStateBadge state={version.state} />
                    </TableCell>
                    <TableCell className="py-3 text-right">
                      {mayRollback && version.state !== "current" && (
                        <Button variant="outline" size="sm" onClick={() => setTarget(version)}>
                          <Undo2 aria-hidden data-icon="inline-start" />
                          Make current
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </section>
      )}

      {pair && (
        <section aria-labelledby="compare-heading" className="flex flex-col gap-3">
          <h2 id="compare-heading" className="flex items-center gap-2 text-xl font-semibold">
            <FileText aria-hidden className="size-5" />
            Compare versions
          </h2>
          <div className="flex flex-wrap items-end gap-4">
            <VersionPick
              id="compare-from"
              label="From"
              value={pair.from}
              versions={list}
              onChange={(from) => setCompare({ ...pair, from })}
            />
            <VersionPick
              id="compare-to"
              label="To"
              value={pair.to}
              versions={list}
              onChange={(to) => setCompare({ ...pair, to })}
            />
          </div>
          <DiffView from={pair.from} to={pair.to} />
        </section>
      )}

      <ReasonDialog
        open={target !== null}
        onOpenChange={(open) => !open && setTarget(null)}
        title={target ? `Make version ${target.version} current?` : ""}
        description={
          target && current
            ? `Version ${current.version} stops being the report leadership sees, and version ${target.version} takes its place. Every version is kept, and the audit log records who did it and why.`
            : "Every version is kept, and the audit log records who did it and why."
        }
        confirmLabel={target ? `Roll back to version ${target.version}` : "Roll back"}
        destructive
        busy={rollback.isPending}
        error={rollback.error?.message ?? null}
        onConfirm={(reason) => {
          if (!target) return;
          rollback.mutate(
            { to_version: target.version, reason },
            {
              onSuccess: (version) => {
                setDone(`Version ${version.version} is current again. The rollback is in the audit log.`);
                setTarget(null);
              },
            },
          );
        }}
      />
    </>
  );
}

function VersionPick({
  id,
  label,
  value,
  versions,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  versions: Version[];
  onChange: (version: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id} className="text-base">
        {label}
      </Label>
      <Select value={String(value)} onValueChange={(v) => onChange(Number(v))}>
        <SelectTrigger id={id} className="h-10 min-w-48 text-base">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {versions.map((v) => (
            <SelectItem key={v.version} value={String(v.version)} className="text-base">
              Version {v.version}
              {v.state === "current" ? " (current)" : v.state === "rolled_back" ? " (rolled back)" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
