"use client";

import { PageHeader } from "@/components/page-header";
import { NewRunForm } from "@/components/runs/new-run-form";
import { RunsList } from "@/components/runs/runs-list";
import { Card, CardContent } from "@/components/ui/card";

export default function RunsPage() {
  return (
    <>
      <PageHeader
        title="New brief"
        description="Ask for a decision brief. The planner asks what it needs and proposes a plan you can edit. Nothing runs until you lock it."
      />
      <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <Card>
          <CardContent className="pt-6">
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
