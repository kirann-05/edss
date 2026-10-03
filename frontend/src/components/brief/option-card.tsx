"use client";

import { PencilLine, TriangleAlert } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { BriefOption, RichText as RichTextValue } from "@/lib/api/types";
import { FIELD_LABEL, LIST_FIELDS, editsForOption, strayNumbers, type OptionDraft } from "@/lib/brief";

import { RichText, type FigureHandlers } from "./rich-text";

function ListBlock({ label, items, handlers }: { label: string; items: RichTextValue[]; handlers: FigureHandlers }) {
  return (
    <div className="grid gap-x-4 gap-y-1 sm:grid-cols-[7rem_minmax(0,1fr)]">
      <dt className="text-sm font-semibold tracking-wide text-muted-foreground uppercase">{label}</dt>
      <dd>
        {items.length === 0 ? (
          <p className="text-base text-critical-ink">None listed</p>
        ) : (
          <ul className="flex list-disc flex-col gap-1 pl-5 text-base">
            {items.map((item, index) => (
              <li key={index}>
                <RichText value={item} {...handlers} />
              </li>
            ))}
          </ul>
        )}
      </dd>
    </div>
  );
}

export function OptionCard({
  option,
  index,
  handlers,
  edited = false,
  editing = false,
  draft,
  onDraft,
}: {
  option: BriefOption;
  index: number;
  handlers: FigureHandlers;
  /** The approver changed this option when they approved it */
  edited?: boolean;
  editing?: boolean;
  draft?: OptionDraft;
  onDraft?: (draft: OptionDraft) => void;
}) {
  if (editing && draft && onDraft) {
    return <OptionEditor option={option} index={index} draft={draft} onDraft={onDraft} />;
  }
  return (
    <article className="flex flex-col gap-3 rounded-xl border bg-background p-4">
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-sm font-medium text-muted-foreground">Option {index + 1}</span>
        <h4 className="text-lg leading-snug font-semibold">{option.title}</h4>
        {edited && (
          <span className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-sm text-muted-foreground">
            <PencilLine aria-hidden className="size-3.5" />
            Edited by the approver
          </span>
        )}
      </header>
      <p className="text-base leading-relaxed">
        <RichText value={option.description} {...handlers} />
      </p>
      <dl className="flex flex-col gap-3 border-t pt-3">
        <ListBlock label="Assumptions" items={option.assumptions} handlers={handlers} />
        <ListBlock label="Risks" items={option.risks} handlers={handlers} />
        <ListBlock label="Trade-offs" items={option.trade_offs} handlers={handlers} />
      </dl>
    </article>
  );
}

function OptionEditor({
  option,
  index,
  draft,
  onDraft,
}: {
  option: BriefOption;
  index: number;
  draft: OptionDraft;
  onDraft: (draft: OptionDraft) => void;
}) {
  const id = (field: string) => `${option.id}-${field}`;
  const changes = editsForOption(option, draft);
  const typed = [draft.title, draft.description, draft.assumptions, draft.risks, draft.trade_offs].flatMap(strayNumbers);

  return (
    <article className="flex flex-col gap-4 rounded-xl border-2 border-primary/40 bg-background p-4">
      <header className="flex items-baseline gap-3">
        <span className="text-sm font-medium text-muted-foreground">Option {index + 1}</span>
        <span className="text-sm text-muted-foreground">
          {changes.length === 0 ? "No changes yet" : `${changes.length} field${changes.length === 1 ? "" : "s"} changed`}
        </span>
      </header>
      <div className="flex flex-col gap-2">
        <Label htmlFor={id("title")} className="text-base">
          Title
        </Label>
        <Input
          id={id("title")}
          value={draft.title}
          onChange={(event) => onDraft({ ...draft, title: event.target.value })}
          className="h-11 text-base font-medium"
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={id("description")} className="text-base">
          Description
        </Label>
        <Textarea
          id={id("description")}
          value={draft.description}
          onChange={(event) => onDraft({ ...draft, description: event.target.value })}
          rows={4}
          className="font-mono text-sm leading-relaxed"
          aria-describedby={id("tokens")}
        />
        <p id={id("tokens")} className="text-sm text-muted-foreground">
          Figures appear as references such as <code className="font-mono">{"{{kpi:PL_PCT}}"}</code>. Keep a
          reference where a figure belongs, numbers cannot be typed by hand (check V1).
        </p>
      </div>
      {LIST_FIELDS.map((field) => (
        <div key={field} className="flex flex-col gap-2">
          <Label htmlFor={id(field)} className="text-base">
            {FIELD_LABEL[field]} <span className="font-normal text-muted-foreground">(one per line)</span>
          </Label>
          <Textarea
            id={id(field)}
            value={draft[field]}
            onChange={(event) => onDraft({ ...draft, [field]: event.target.value })}
            rows={3}
            className="text-base"
          />
        </div>
      ))}
      {typed.length > 0 && (
        <p role="status" className="flex items-start gap-2 text-base text-critical-ink">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          Typed {typed.length === 1 ? "number" : "numbers"} {typed.join(", ")} will fail check V1. Use a figure
          reference instead.
        </p>
      )}
      {changes.length > 0 && (
        <details className="rounded-lg bg-muted/50 px-3 py-2" open>
          <summary className="cursor-pointer text-base font-medium">Changes from the draft</summary>
          <dl className="mt-2 flex flex-col gap-3">
            {changes.map((change) => {
              const before =
                change.field === "title"
                  ? option.title
                  : change.field === "description"
                    ? option.description.text
                    : option[change.field].map((x) => x.text).join("\n");
              const after = Array.isArray(change.value) ? change.value.join("\n") : change.value;
              return (
                <div key={change.field} className="flex flex-col gap-1">
                  <dt className="text-sm font-semibold">{FIELD_LABEL[change.field]}</dt>
                  <dd className="grid gap-2 md:grid-cols-2">
                    <p className="rounded-md border border-critical-mark/40 bg-critical-tint px-2 py-1 text-sm whitespace-pre-wrap">
                      <span className="sr-only">Before: </span>
                      <del className="no-underline">{before}</del>
                    </p>
                    <p className="rounded-md border border-good-mark/40 bg-good-tint px-2 py-1 text-sm whitespace-pre-wrap">
                      <span className="sr-only">After: </span>
                      <ins className="no-underline">{after}</ins>
                    </p>
                  </dd>
                </div>
              );
            })}
          </dl>
        </details>
      )}
    </article>
  );
}
