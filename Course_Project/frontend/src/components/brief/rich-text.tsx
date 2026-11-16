"use client";

import { cn } from "cn";
import { Fragment } from "react";

import { StatusChip } from "@/components/status/status-badge";
import type { FactStatus, KpiStatus, RichText as RichTextValue, Segment } from "@/lib/api/types";
import { FACT_STATUS, KPI_STATUS, TONE_CLASS, TONE_TEXT } from "@/lib/status";

const NON_FINAL = new Set<string>(["provisional", "forecast", "pending_reconciliation"]);

export interface FigureHandlers {
  /** Open a KPI's drill-down. Missing when the reader may not open drill-downs */
  onKpi?: (key: string) => void;
  /** Open one source record */
  onFact?: (id: number) => void;
}

/**
 * Text written by the drafting step, with every figure resolved by the server. A figure is never
 * plain text: it is a control that opens where it came from, and a figure that is not final
 * always carries its badge (rule 4).
 */
export function RichText({ value, className, ...handlers }: { value: RichTextValue; className?: string } & FigureHandlers) {
  return (
    <span className={className}>
      {value.segments.map((segment, index) =>
        segment.t === "text" ? (
          <Fragment key={index}>{segment.text}</Fragment>
        ) : (
          <FigureRef key={index} segment={segment} {...handlers} />
        ),
      )}
    </span>
  );
}

function FigureRef({ segment, onKpi, onFact }: { segment: Segment } & FigureHandlers) {
  const display = segment.display ?? "";

  if (segment.unresolved) {
    return (
      <code
        title="This reference does not resolve to a figure, so validation will reject the brief"
        className={cn("rounded px-1 font-mono text-sm", TONE_CLASS.critical)}
      >
        {display}
        <span className="sr-only"> (unresolved reference)</span>
      </code>
    );
  }

  if (segment.kind === "fact") {
    const status = segment.status as FactStatus | null;
    const id = Number(segment.key);
    const label = (
      <>
        <span className="font-semibold tabular-nums">{display}</span>
        {status && NON_FINAL.has(status) && <StatusChip style={FACT_STATUS[status]} className="ml-1 px-1.5 py-0 text-xs" />}
      </>
    );
    return onFact ? (
      <button
        type="button"
        onClick={() => onFact(id)}
        title={`Open source record ${segment.key}`}
        className="rounded-sm underline decoration-dotted underline-offset-4 outline-none hover:decoration-solid focus-visible:ring-2 focus-visible:ring-ring"
      >
        {label}
      </button>
    ) : (
      <span>{label}</span>
    );
  }

  // a KPI reference: its value, target, gap or status
  const status = (segment.status ?? "undefined") as KpiStatus;
  const style = KPI_STATUS[status] ?? KPI_STATUS.undefined;
  const open = onKpi && segment.key ? () => onKpi(segment.key as string) : undefined;

  if (segment.field === "status") {
    const chip = <StatusChip style={style} label={display} className="px-1.5 py-0 align-baseline text-sm" />;
    return open ? (
      <button
        type="button"
        onClick={open}
        title={`Open the drill-down for ${segment.key}`}
        className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {chip}
      </button>
    ) : (
      chip
    );
  }

  const Icon = style.icon;
  const inner = (
    <>
      {segment.field === "value" && (
        <Icon aria-hidden className={cn("mr-0.5 inline size-4 -translate-y-px", TONE_TEXT[style.tone])} />
      )}
      <span className="font-semibold tabular-nums">{display}</span>
      {segment.field === "value" && <span className="sr-only"> ({style.label})</span>}
    </>
  );
  return open ? (
    <button
      type="button"
      onClick={open}
      title={`Open the drill-down for ${segment.key}`}
      className="rounded-sm underline decoration-dotted underline-offset-4 outline-none hover:decoration-solid focus-visible:ring-2 focus-visible:ring-ring"
    >
      {inner}
    </button>
  ) : (
    <span>{inner}</span>
  );
}
