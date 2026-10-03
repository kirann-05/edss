"use client";

import { cn } from "cn";
import {
  CalendarClock,
  CircleSlash,
  Clock,
  Divide,
  FileQuestion,
  Hourglass,
  Scale,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";

import { KpiStatusBadge } from "@/components/status/status-badge";
import type { BriefDocument as BriefDocumentValue } from "@/lib/api/types";
import type { OptionDraft } from "@/lib/brief";
import { TONE_CLASS, type Tone } from "@/lib/status";

import { FigureTable } from "./figure-table";
import { OptionCard } from "./option-card";
import { RichText, type FigureHandlers } from "./rich-text";

const ASSUMPTION_KIND: Record<string, { label: string; tone: Tone; icon: LucideIcon }> = {
  as_of: { label: "As of", tone: "neutral", icon: CalendarClock },
  placeholder: { label: "Placeholder", tone: "neutral", icon: FileQuestion },
  stale: { label: "Stale", tone: "warning", icon: Clock },
  missing: { label: "No record", tone: "serious", icon: CircleSlash },
  excluded: { label: "Excluded", tone: "serious", icon: Scale },
  undefined: { label: "Undefined", tone: "neutral", icon: Divide },
  provisional: { label: "Provisional", tone: "warning", icon: Hourglass },
  forecast: { label: "Forecast", tone: "neutral", icon: TrendingUp },
};

function Section({ title, id, children }: { title: string; id: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <h2 id={id} className="text-xl font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

/**
 * The brief as leadership reads it. The same component shows a draft under review and a published
 * version, so what was approved is exactly what is shown later.
 */
export function BriefDocument({
  document,
  handlers,
  editedOptions = new Set<string>(),
  editing = false,
  drafts = {},
  onDraft,
}: {
  document: BriefDocumentValue;
  handlers: FigureHandlers;
  editedOptions?: Set<string>;
  editing?: boolean;
  drafts?: Record<string, OptionDraft>;
  onDraft?: (optionId: string, draft: OptionDraft) => void;
}) {
  const headline = new Map(document.summary.map((s) => [s.kpi_key, s.text]));

  return (
    <div className="flex flex-col gap-10">
      <Section title="KPIs at a glance" id="brief-glance">
        <div className="rounded-xl border bg-card px-2">
          <FigureTable figures={document.kpis} onKpi={handlers.onKpi} />
        </div>
      </Section>

      <Section title="Options for decision" id="brief-options">
        {document.option_sets.length === 0 ? (
          <p className="rounded-xl border border-dashed p-6 text-base text-muted-foreground">
            No KPI in this brief is off target, so there is nothing to decide.
          </p>
        ) : (
          document.option_sets.map((set) => {
            const line = headline.get(set.kpi_key);
            return (
              <article key={set.kpi_key} className="flex flex-col gap-3 rounded-2xl border bg-card p-5">
                <header className="flex flex-wrap items-center gap-3">
                  <h3 className="text-lg font-semibold">
                    {handlers.onKpi ? (
                      <button
                        type="button"
                        onClick={() => handlers.onKpi?.(set.kpi_key)}
                        className="text-left underline-offset-4 outline-none hover:underline focus-visible:underline focus-visible:ring-2 focus-visible:ring-ring"
                      >
                        {set.kpi_name}
                      </button>
                    ) : (
                      set.kpi_name
                    )}
                  </h3>
                  <KpiStatusBadge status={set.status} />
                  {set.attempt > 1 && (
                    <span className="text-sm text-muted-foreground">Redrafted on attempt {set.attempt}</span>
                  )}
                </header>
                {line && (
                  <p className="text-base text-muted-foreground">
                    <RichText value={line} {...handlers} />
                  </p>
                )}
                <div className="flex flex-col gap-3">
                  {set.options.map((option, index) => (
                    <OptionCard
                      key={option.id}
                      option={option}
                      index={index}
                      handlers={handlers}
                      edited={editedOptions.has(option.id)}
                      editing={editing}
                      draft={drafts[option.id]}
                      onDraft={onDraft ? (draft) => onDraft(option.id, draft) : undefined}
                    />
                  ))}
                </div>
              </article>
            );
          })
        )}
      </Section>

      <Section title="Assumptions and caveats" id="brief-assumptions">
        <ul className="flex flex-col divide-y rounded-xl border bg-card">
          {document.assumptions.map((assumption, index) => {
            const kind = ASSUMPTION_KIND[assumption.kind] ?? { label: assumption.kind, tone: "neutral" as Tone, icon: FileQuestion };
            const Icon = kind.icon;
            return (
              <li key={index} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-start sm:gap-4">
                <span
                  className={cn(
                    "inline-flex w-fit shrink-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-sm font-medium sm:w-32",
                    TONE_CLASS[kind.tone],
                  )}
                >
                  <Icon aria-hidden className="size-4 shrink-0" />
                  {kind.label}
                </span>
                <p className="text-base">
                  <RichText value={assumption.text} {...handlers} />
                </p>
              </li>
            );
          })}
        </ul>
      </Section>
    </div>
  );
}
