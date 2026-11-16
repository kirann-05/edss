import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RunEvent } from "@/lib/api/types";

import { ProgressTimeline } from "./progress-timeline";

let id = 0;
const T0 = Date.parse("2026-10-03T10:00:00.000Z");
const event = (node: string, label: string, state: RunEvent["state"], at: number, extra: Partial<RunEvent> = {}): RunEvent => ({
  id: ++id,
  ts: new Date(T0 + at).toISOString(),
  node,
  label,
  state,
  elapsed_ms: null,
  attempt: null,
  detail: null,
  ok: null,
  ...extra,
});

const props = { connection: "ended" as const, live: false, simulatedLatencyMs: 0 };

describe("ProgressTimeline", () => {
  it("waits quietly before the first step", () => {
    render(<ProgressTimeline events={[]} {...props} />);
    expect(screen.getByText("Waiting for the first step to start.")).toBeInTheDocument();
  });

  it("groups steps as the graph runs and says each step's state in words", () => {
    render(
      <ProgressTimeline
        {...props}
        events={[
          event("plan_lock", "Plan locked", "running", 0),
          event("plan_lock", "Plan locked", "done", 2, { elapsed_ms: 2 }),
          event("domain:finance", "Finance agent", "running", 3),
        ]}
      />,
    );
    const preparation = screen.getByRole("heading", { name: "Preparation" }).closest("li") as HTMLElement;
    expect(within(preparation).getByText(/Plan locked/)).toHaveTextContent("done");
    const agents = screen.getByRole("heading", { name: "Domain agents" }).closest("li") as HTMLElement;
    expect(within(agents).getByText(/Finance agent/)).toHaveTextContent("working");
  });

  it("names the failing check and the repair, so the story can be followed", () => {
    render(
      <ProgressTimeline
        {...props}
        events={[
          event("validate", "Validation, attempt 1", "running", 10),
          event("validate", "Validation, attempt 1", "done", 14, { elapsed_ms: 4, ok: false, detail: "Failing: V1 Every figure cites its source" }),
          event("regenerate", "Repair, attempt 2", "running", 15),
          event("regenerate", "Repair, attempt 2", "done", 16, { elapsed_ms: 1 }),
          event("validate", "Validation, attempt 2", "running", 17),
          event("validate", "Validation, attempt 2", "done", 20, { elapsed_ms: 3, ok: true, detail: "All nine checks passed" }),
        ]}
      />,
    );
    expect(screen.getByText("Failing: V1 Every figure cites its source")).toBeInTheDocument();
    expect(screen.getByText(/Validation, attempt 1/)).toHaveTextContent("check failed");
    expect(screen.getByText("Repair, attempt 2")).toBeInTheDocument();
    expect(screen.getByText("All nine checks passed")).toBeInTheDocument();
  });

  it("claims parallel work only when the events show agents overlapping", () => {
    const together = [
      event("domain:academic", "Academic agent", "running", 0),
      event("domain:research", "Research agent", "running", 1),
      event("domain:academic", "Academic agent", "done", 700, { elapsed_ms: 700 }),
      event("domain:research", "Research agent", "done", 701, { elapsed_ms: 700 }),
    ];
    const { unmount } = render(<ProgressTimeline {...props} events={together} />);
    expect(screen.getByText(/2 domain agents worked at the same time/)).toBeInTheDocument();
    unmount();

    const apart = [
      event("domain:academic", "Academic agent", "running", 0),
      event("domain:academic", "Academic agent", "done", 100, { elapsed_ms: 100 }),
      event("domain:research", "Research agent", "running", 200),
      event("domain:research", "Research agent", "done", 300, { elapsed_ms: 100 }),
    ];
    render(<ProgressTimeline {...props} events={apart} />);
    expect(screen.queryByText(/worked at the same time/)).toBeNull();
  });

  it("says plainly when the source delay is simulated, and says nothing when there is none", () => {
    const events = [event("plan_lock", "Plan locked", "done", 0, { elapsed_ms: 0 })];
    const { unmount } = render(<ProgressTimeline {...props} events={events} simulatedLatencyMs={700} />);
    expect(screen.getByText(/pauses 700 ms .* simulated/)).toBeInTheDocument();
    unmount();
    render(<ProgressTimeline {...props} events={events} simulatedLatencyMs={0} />);
    expect(screen.queryByText(/simulated/)).toBeNull();
  });

  it("shows a step waiting for a person without a timing", () => {
    render(<ProgressTimeline {...props} events={[event("human_gate", "Waiting for a person to review", "waiting", 5)]} />);
    const review = screen.getByRole("heading", { name: "Human review" }).closest("li") as HTMLElement;
    expect(within(review).getByText(/Waiting for a person to review/)).toHaveTextContent("waiting for a person");
    expect(review).not.toHaveTextContent(/\d+ ms/); // no timing for a step that has not finished
  });
});
