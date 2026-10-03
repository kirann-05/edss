"use client";

import { CircleCheck, CircleX } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorPanel } from "@/components/error-panel";
import { BriefStatusBadge } from "@/components/status/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useBriefs } from "@/lib/api/queries";
import type { BriefSummary } from "@/lib/api/types";
import { formatAge } from "@/lib/when";

const WAITING = new Set(["draft", "escalated"]);

export function ReviewQueue() {
  const briefs = useBriefs();
  const [show, setShow] = useState<"waiting" | "all">("waiting");

  if (briefs.isPending) return <Skeleton className="h-64 w-full" />;
  if (briefs.isError) return <ErrorPanel error={briefs.error} onRetry={() => briefs.refetch()} what="the review queue" />;

  const waiting = briefs.data.filter((b) => WAITING.has(b.status));
  const rows = show === "waiting" ? waiting : briefs.data;

  return (
    <div className="flex flex-col gap-4">
      <Tabs value={show} onValueChange={(v) => setShow(v as "waiting" | "all")}>
        <TabsList>
          <TabsTrigger value="waiting" className="text-base">
            Waiting for a decision ({waiting.length})
          </TabsTrigger>
          <TabsTrigger value="all" className="text-base">
            All ({briefs.data.length})
          </TabsTrigger>
        </TabsList>
      </Tabs>
      {rows.length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-base text-muted-foreground">
          {show === "waiting"
            ? "Nothing is waiting for a decision. A draft appears here when a run reaches the human gate."
            : "No drafts yet. Start one from New brief."}
        </p>
      ) : (
        <div className="rounded-xl border bg-card px-2">
          <Table className="text-base">
            <TableHeader>
              <TableRow>
                <TableHead className="text-base">Request</TableHead>
                <TableHead className="text-base">Period</TableHead>
                <TableHead className="text-base">Status</TableHead>
                <TableHead className="text-base">Validation</TableHead>
                <TableHead className="text-right text-base">Off target</TableHead>
                <TableHead className="text-base">Waiting</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((brief) => (
                <QueueRow key={brief.id} brief={brief} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function QueueRow({ brief }: { brief: BriefSummary }) {
  return (
    <TableRow className="align-top">
      <TableCell className="py-3 whitespace-normal">
        <Link
          href={`/review/${brief.id}`}
          className="font-medium underline-offset-4 outline-none hover:underline focus-visible:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          {brief.request ?? brief.id}
        </Link>
        <span className="block text-sm text-muted-foreground">
          {brief.id} · {brief.attempts} attempt{brief.attempts === 1 ? "" : "s"}
        </span>
      </TableCell>
      <TableCell className="py-3">{brief.period_year}</TableCell>
      <TableCell className="py-3">
        <BriefStatusBadge status={brief.status} />
      </TableCell>
      <TableCell className="py-3 whitespace-normal">
        {brief.validation_passed ? (
          <span className="inline-flex items-center gap-1.5 text-good-ink">
            <CircleCheck aria-hidden className="size-4" />
            Passed
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-critical-ink">
            <CircleX aria-hidden className="size-4" />
            Failing {brief.failing_checks.join(", ")}
          </span>
        )}
      </TableCell>
      <TableCell className="py-3 text-right tabular-nums">{brief.off_target_count}</TableCell>
      <TableCell className="py-3 text-muted-foreground">{formatAge(brief.created_at)}</TableCell>
    </TableRow>
  );
}
