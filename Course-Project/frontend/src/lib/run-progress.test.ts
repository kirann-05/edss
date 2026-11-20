import { describe, expect, it } from "vitest";

import type { RunEvent } from "@/lib/api/types";

import { buildProgress, formatElapsed, groupOf, peakOverlap, stageOf, type Step } from "./run-progress";

const T0 = Date.parse("2026-10-03T10:00:00.000Z");

let counter = 0;
function event(
  node: string,
  label: string,
  state: RunEvent["state"],
  atMs: number,
  extra: Partial<RunEvent> = {},
): RunEvent {
  counter += 1;
  return {
    id: counter,
    ts: new Date(T0 + atMs).toISOString(),
    node,
    label,
    state,
    elapsed_ms: null,
    attempt: null,
    detail: null,
    ok: null,
    ...extra,
  };
}

const domain = (name: string, label: string, start: number, end: number): RunEvent[] => [
  event(`domain:${name}`, label, "running", start),
  event(`domain:${name}`, label, "done", end, { elapsed_ms: end - start }),
];

describe("groupOf", () => {
  it.each([
    ["plan_lock", "setup"],
    ["access_check", "setup"],
    ["domain:finance", "domains"],
    ["kpi_synthesis", "synthesis"],
    ["options:PL_PCT", "options"],
    ["report_compose", "compose"],
    ["validate", "validation"],
    ["regenerate", "validation"],
    ["prepare_gate", "gate"],
    ["human_gate", "gate"],
    ["finish", "gate"],
  ])("puts %s in %s", (node, group) => {
    expect(groupOf(node)).toBe(group);
  });
});

describe("buildProgress", () => {
  it("is empty when nothing has happened yet", () => {
    const progress = buildProgress([]);
    expect(progress.steps).toEqual([]);
    expect(progress.running).toBe(false);
    expect(progress.totalMs).toBe(0);
  });

  it("merges a node's start and end into one row with its timing", () => {
    const progress = buildProgress([
      event("plan_lock", "Plan locked", "running", 0),
      event("plan_lock", "Plan locked", "done", 12, { elapsed_ms: 12 }),
    ]);
    expect(progress.steps).toHaveLength(1);
    expect(progress.steps[0]).toMatchObject({ state: "done", startMs: 0, endMs: 12, elapsedMs: 12 });
  });

  it("shows a node that has only started as running, with no end", () => {
    const progress = buildProgress([event("domain:academic", "Academic agent", "running", 5)]);
    expect(progress.steps[0]).toMatchObject({ state: "running", endMs: null, elapsedMs: null });
    expect(progress.running).toBe(true);
  });

  it("measures parallelism from the events, so four overlapping agents read as four", () => {
    const progress = buildProgress([
      ...[
        event("domain:academic", "Academic agent", "running", 10),
        event("domain:research", "Research agent", "running", 11),
        event("domain:placement", "Placement agent", "running", 11),
        event("domain:finance", "Finance agent", "running", 12),
      ],
      event("domain:academic", "Academic agent", "done", 410, { elapsed_ms: 400 }),
      event("domain:research", "Research agent", "done", 411, { elapsed_ms: 400 }),
      event("domain:placement", "Placement agent", "done", 412, { elapsed_ms: 401 }),
      event("domain:finance", "Finance agent", "done", 413, { elapsed_ms: 401 }),
    ]);
    expect(progress.parallel).toBe(4);
  });

  it("does not call agents that ran one after another parallel", () => {
    const progress = buildProgress([
      ...domain("academic", "Academic agent", 0, 100),
      ...domain("research", "Research agent", 100, 200),
      ...domain("finance", "Finance agent", 200, 300),
    ]);
    expect(progress.parallel).toBe(1);
  });

  it("follows a failing check, the repair, and the passing check as three rows in order", () => {
    const progress = buildProgress([
      event("validate", "Validation, attempt 1", "running", 100),
      event("validate", "Validation, attempt 1", "done", 110, {
        elapsed_ms: 10,
        ok: false,
        detail: "Failing: V1",
      }),
      event("regenerate", "Repair, attempt 2", "running", 111),
      event("regenerate", "Repair, attempt 2", "done", 120, { elapsed_ms: 9 }),
      event("validate", "Validation, attempt 2", "running", 121),
      event("validate", "Validation, attempt 2", "done", 130, {
        elapsed_ms: 9,
        ok: true,
        detail: "All nine checks passed",
      }),
    ]);
    const group = progress.groups.find((g) => g.id === "validation");
    expect(group?.steps.map((s) => [s.label, s.ok, s.detail])).toEqual([
      ["Validation, attempt 1", false, "Failing: V1"],
      ["Repair, attempt 2", null, null],
      ["Validation, attempt 2", true, "All nine checks passed"],
    ]);
  });

  it("orders groups as the graph runs, whatever order the events arrived in", () => {
    const progress = buildProgress([
      event("kpi_synthesis", "KPI synthesis", "running", 0),
      event("plan_lock", "Plan locked", "running", 1),
      event("human_gate", "Waiting for a person to review", "waiting", 2),
    ]);
    expect(progress.groups.map((g) => g.id)).toEqual(["setup", "synthesis", "gate"]);
  });

  it("marks the run as waiting at the human gate", () => {
    const progress = buildProgress([
      event("prepare_gate", "Draft ready for review", "done", 5, { elapsed_ms: 1 }),
      event("human_gate", "Waiting for a person to review", "waiting", 6),
    ]);
    expect(progress.waiting).toBe(true);
    expect(progress.running).toBe(false);
  });

  it("reports a run-level failure, and clears it once the run is resumed", () => {
    const failed = [
      event("run", "Plan locked, run started", "running", 0),
      event("domain:finance", "Finance agent", "running", 1),
      event("domain:finance", "Finance agent", "failed", 5, { detail: "source timed out" }),
      event("run", "Run stopped", "failed", 6, { detail: "source timed out" }),
    ];
    expect(buildProgress(failed).failure?.detail).toBe("source timed out");
    expect(buildProgress(failed).steps[0]).toMatchObject({ state: "failed", detail: "source timed out" });

    const resumed = [...failed, event("run", "Resuming from the last checkpoint", "running", 20)];
    expect(buildProgress(resumed).failure).toBeNull();
  });

  it("restarts a node's bar when it runs again after a resume", () => {
    const progress = buildProgress([
      event("domain:finance", "Finance agent", "running", 1),
      event("domain:finance", "Finance agent", "failed", 5),
      event("domain:finance", "Finance agent", "running", 30),
      event("domain:finance", "Finance agent", "done", 50, { elapsed_ms: 20 }),
    ]);
    expect(progress.steps).toHaveLength(1);
    expect(progress.steps[0]).toMatchObject({ state: "done", startMs: 29, endMs: 49 });
  });

  it("does not show the lifecycle markers as steps of the graph", () => {
    const progress = buildProgress([
      event("run", "Plan locked, run started", "running", 0),
      event("plan_lock", "Plan locked", "done", 3, { elapsed_ms: 3 }),
    ]);
    expect(progress.steps.map((s) => s.node)).toEqual(["plan_lock"]);
  });

  it("lets an open step grow with the clock", () => {
    const events = [event("domain:academic", "Academic agent", "running", 0)];
    expect(buildProgress(events, T0 + 2500).totalMs).toBe(2500);
    expect(buildProgress(events).totalMs).toBe(0);
  });
});

describe("peakOverlap", () => {
  const step = (startMs: number, endMs: number | null): Step =>
    ({ startMs, endMs, group: "domains" }) as Step;

  it("counts steps that overlap at one instant", () => {
    expect(peakOverlap([step(0, 10), step(5, 15), step(12, 20)], 20)).toBe(2);
  });

  it("does not count steps that only touch end to start", () => {
    expect(peakOverlap([step(0, 10), step(10, 20)], 20)).toBe(1);
  });

  it("treats an open step as lasting until the end given", () => {
    expect(peakOverlap([step(0, null), step(50, 60)], 100)).toBe(2);
  });

  it("is zero with nothing to count", () => {
    expect(peakOverlap([], 0)).toBe(0);
  });
});

describe("formatElapsed", () => {
  it.each([
    [null, ""],
    [0, "0 ms"],
    [312, "312 ms"],
    [1000, "1.0 s"],
    [3249, "3.2 s"],
    [12_400, "12 s"],
    [65_000, "1 min 5 s"],
  ])("writes %s as %j", (ms, text) => {
    expect(formatElapsed(ms)).toBe(text);
  });
});

describe("stageOf", () => {
  it.each([
    ["clarifying", "clarify"],
    ["planning", "plan"],
    ["running", "run"],
    ["failed", "run"],
    ["awaiting_review", "review"],
    ["completed", "review"],
  ])("puts a %s run in the %s stage", (status, stage) => {
    expect(stageOf(status)).toBe(stage);
  });
});
