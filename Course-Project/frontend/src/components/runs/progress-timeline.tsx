"use client";

import { cn } from "cn";
import { CircleCheck, CircleX, Hourglass, LoaderCircle, TriangleAlert, type LucideIcon } from "lucide-react";
import { useMemo } from "react";

import type { RunEvent } from "@/lib/api/types";
import { buildProgress, formatElapsed, type Step } from "@/lib/run-progress";
import type { Connection } from "@/lib/use-run-events";
import { useNow } from "@/lib/use-run-events";

interface Look {
  icon: LucideIcon;
  words: string;
  mark: string;
  bar: string;
  spin?: boolean;
}

function lookOf(step: Step): Look {
  if (step.state === "running") {
    return { icon: LoaderCircle, words: "working", mark: "text-primary", bar: "bg-primary/70 motion-safe:animate-pulse", spin: true };
  }
  if (step.state === "failed") return { icon: CircleX, words: "failed", mark: "text-critical-mark", bar: "bg-critical-mark" };
  if (step.state === "waiting") {
    return { icon: Hourglass, words: "waiting for a person", mark: "text-warning-ink", bar: "bg-warning-mark" };
  }
  if (step.ok === false) return { icon: TriangleAlert, words: "check failed", mark: "text-serious-ink", bar: "bg-serious-mark" };
  return { icon: CircleCheck, words: "done", mark: "text-good-mark", bar: "bg-primary/60" };
}

const CONNECTION_WORDS: Record<Connection, string> = {
  connecting: "Connecting",
  live: "Live",
  reconnecting: "Reconnecting",
  ended: "Finished",
};

export function ProgressTimeline({
  events,
  connection,
  live,
  simulatedLatencyMs,
}: {
  events: RunEvent[];
  connection: Connection;
  /** True while the graph is still working, so open steps grow with the clock */
  live: boolean;
  simulatedLatencyMs: number;
}) {
  const now = useNow(live);
  const progress = useMemo(() => buildProgress(events, live ? now : undefined), [events, live, now]);
  const scale = Math.max(progress.totalMs, 1);
  const last = events[events.length - 1];

  return (
    <section aria-labelledby="progress-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h2 id="progress-heading" className="text-xl font-semibold">
          Progress
        </h2>
        <span className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden
            className={cn(
              "size-2 rounded-full",
              connection === "live" ? "bg-good-mark" : connection === "reconnecting" ? "bg-warning-mark" : "bg-neutral-mark",
            )}
          />
          {CONNECTION_WORDS[connection]}
        </span>
        {progress.totalMs > 0 && (
          <span className="text-sm text-muted-foreground">Elapsed {formatElapsed(progress.totalMs)}</span>
        )}
        {progress.parallel >= 2 && (
          <span className="text-sm text-muted-foreground">
            {progress.parallel} domain agents worked at the same time (measured from the events)
          </span>
        )}
      </div>

      {simulatedLatencyMs > 0 && (
        <p className="rounded-lg border border-dashed px-3 py-2 text-sm text-muted-foreground">
          Each domain agent pauses {simulatedLatencyMs} ms to stand in for a slow source system. This latency is
          simulated, so the timings show the shape of parallel work, not real source speed.
        </p>
      )}

      {/* one polite announcement per change, so a screen reader hears progress without the whole list */}
      <p aria-live="polite" className="sr-only">
        {last ? `${last.label}: ${last.state}${last.detail ? `, ${last.detail}` : ""}` : ""}
      </p>

      {progress.groups.length === 0 ? (
        <p className="rounded-xl border border-dashed p-6 text-base text-muted-foreground">
          Waiting for the first step to start.
        </p>
      ) : (
        <ol className="flex flex-col gap-5">
          {progress.groups.map((group) => (
            <li key={group.id} className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">{group.title}</h3>
              <ol className="flex flex-col divide-y rounded-xl border bg-card">
                {group.steps.map((step) => {
                  const look = lookOf(step);
                  const Icon = look.icon;
                  const end = step.endMs ?? progress.totalMs;
                  const left = (step.startMs / scale) * 100;
                  const width = Math.max(((end - step.startMs) / scale) * 100, 0.8);
                  return (
                    <li
                      key={step.key}
                      className="grid grid-cols-[1.5rem_minmax(0,1fr)] items-center gap-x-3 gap-y-1 px-4 py-3 md:grid-cols-[1.5rem_minmax(0,1fr)_minmax(8rem,16rem)_5rem]"
                    >
                      <Icon aria-hidden className={cn("size-5", look.mark, look.spin && "motion-safe:animate-spin")} />
                      <div className="flex min-w-0 flex-col">
                        <span className="text-base font-medium">
                          {step.label}
                          <span className="sr-only">, {look.words}</span>
                        </span>
                        {step.detail && (
                          <span
                            className={cn(
                              "text-sm",
                              step.ok === false || step.state === "failed" ? "text-serious-ink" : "text-muted-foreground",
                            )}
                          >
                            {step.detail}
                          </span>
                        )}
                      </div>
                      <div aria-hidden className="relative col-start-2 h-2 rounded-full bg-muted md:col-start-auto">
                        <span
                          className={cn("absolute inset-y-0 rounded-full", look.bar)}
                          style={{ left: `${Math.min(left, 99.2)}%`, width: `${Math.min(width, 100 - Math.min(left, 99.2))}%` }}
                        />
                      </div>
                      <span className="col-start-2 text-sm text-muted-foreground tabular-nums md:col-start-auto md:text-right">
                        {step.state === "running" ? "running" : step.state === "waiting" ? "" : formatElapsed(step.elapsedMs)}
                      </span>
                    </li>
                  );
                })}
              </ol>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
