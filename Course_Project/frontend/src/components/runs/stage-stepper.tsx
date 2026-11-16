import { cn } from "cn";
import { Check } from "lucide-react";

import { STAGES, type Stage } from "@/lib/run-progress";

/** Where this brief is: clarify, plan, run, review. Text and a mark, never colour alone. */
export function StageStepper({ current, stopped = false }: { current: Stage; stopped?: boolean }) {
  const index = STAGES.findIndex((s) => s.id === current);
  return (
    <ol aria-label="Stages of this brief" className="flex flex-wrap items-center gap-x-2 gap-y-2">
      {STAGES.map((stage, i) => {
        const done = i < index;
        const active = i === index;
        return (
          <li key={stage.id} className="flex items-center gap-2" aria-current={active ? "step" : undefined}>
            <span
              className={cn(
                "grid size-7 place-items-center rounded-full border text-sm font-semibold",
                done && "border-primary bg-primary text-primary-foreground",
                active && !stopped && "border-primary bg-primary/10 text-primary",
                active && stopped && "border-critical-mark bg-critical-tint text-critical-ink",
                !done && !active && "border-border bg-background text-muted-foreground",
              )}
            >
              {done ? <Check aria-hidden className="size-4" /> : i + 1}
            </span>
            <span className={cn("text-base", active ? "font-semibold" : done ? "" : "text-muted-foreground")}>
              {stage.label}
              <span className="sr-only">{done ? " (done)" : active ? (stopped ? " (stopped)" : " (current)") : ""}</span>
            </span>
            {i < STAGES.length - 1 && <span aria-hidden className="mx-1 h-px w-8 bg-border" />}
          </li>
        );
      })}
    </ol>
  );
}
