"use client";

import { PageHeader } from "@/components/page-header";
import { NewRunForm } from "@/components/runs/new-run-form";
import { RunsList } from "@/components/runs/runs-list";
import { Card, CardContent } from "@/components/ui/card";

// what happens after Start, so a first-time user knows nothing runs or publishes on its own
const STEPS = [
  ["Ask", "Say what the brief should cover, in plain words."],
  ["Answer", "The planner asks what it needs, such as the year."],
  ["Check the plan", "Edit the areas and KPIs, then lock it."],
  ["Review", "Agents draft and check it; a named person approves."],
] as const;

export default function RunsPage() {
  return (
    <>
      <PageHeader
        title="New brief"
        description="Ask for a decision brief. The planner asks what it needs and proposes a plan you can edit. Nothing runs until you lock it."
      />
      <ol aria-label="How a brief is made" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {STEPS.map(([title, text], index) => (
          <li key={title} className="flex gap-3 rounded-xl border bg-card p-3">
            <span className="grid size-7 shrink-0 place-items-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
              {index + 1}
            </span>
            <span className="flex flex-col">
              <span className="font-medium">{title}</span>
              <span className="text-sm text-muted-foreground">{text}</span>
            </span>
          </li>
        ))}
      </ol>
      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <Card>
          <CardContent>
            <NewRunForm />
          </CardContent>
        </Card>
        <section aria-labelledby="recent-runs" className="flex flex-col gap-3">
          <h2 id="recent-runs" className="text-xl font-semibold">
            Recent runs
          </h2>
          <RunsList />
        </section>
      </div>
    </>
  );
}
