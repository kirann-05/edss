// Turns the run's event log into rows a person can follow. The server sends one event when a node
// starts and one when it ends, so the same node appears twice. Here they become one row with a
// start, an end and a state, grouped the way the graph is built (docs/ARCHITECTURE.md section 5).
import type { RunEvent } from "@/lib/api/types";

export type StepState = "running" | "done" | "failed" | "waiting";
export type GroupId =
  | "setup"
  | "domains"
  | "synthesis"
  | "options"
  | "compose"
  | "validation"
  | "gate";

export const GROUP_ORDER: GroupId[] = [
  "setup",
  "domains",
  "synthesis",
  "options",
  "compose",
  "validation",
  "gate",
];

export const GROUP_TITLE: Record<GroupId, string> = {
  setup: "Preparation",
  domains: "Domain agents",
  synthesis: "KPI synthesis",
  options: "Options and risks",
  compose: "Brief",
  validation: "Validation and repair",
  gate: "Human review",
};

export function groupOf(node: string): GroupId {
  if (node === "plan_lock" || node === "access_check") return "setup";
  if (node.startsWith("domain:")) return "domains";
  if (node === "kpi_synthesis") return "synthesis";
  if (node.startsWith("options:")) return "options";
  if (node === "report_compose") return "compose";
  if (node === "validate" || node === "regenerate") return "validation";
  return "gate";
}

export interface Step {
  key: string;
  node: string;
  label: string;
  group: GroupId;
  state: StepState;
  /** Milliseconds after the first event of the run */
  startMs: number;
  /** null while the step is still running */
  endMs: number | null;
  elapsedMs: number | null;
  attempt: number | null;
  detail: string | null;
  /** For a check: did it come out right. null for steps that have no outcome */
  ok: boolean | null;
}

export interface StepGroup {
  id: GroupId;
  title: string;
  steps: Step[];
}

export interface Progress {
  steps: Step[];
  groups: StepGroup[];
  /** From the first event to the last, or to `nowMs` while something is still running */
  totalMs: number;
  /** The run as a whole stopped. null when it is working, finished, or was resumed */
  failure: RunEvent | null;
  /** Stopped at the human gate, waiting for a person */
  waiting: boolean;
  running: boolean;
  /** The most agents that were working at the same moment in the parallel group */
  parallel: number;
}

const LIFECYCLE = "run";

export function buildProgress(events: readonly RunEvent[], nowMs?: number): Progress {
  if (events.length === 0) {
    return { steps: [], groups: [], totalMs: 0, failure: null, waiting: false, running: false, parallel: 0 };
  }
  const origin = Date.parse(events[0].ts);
  const at = (event: RunEvent) => Date.parse(event.ts) - origin;

  const byKey = new Map<string, Step>();
  let lifecycle: RunEvent | null = null;

  for (const event of events) {
    // "run" events mark the lifecycle (started, resumed, stopped), they are not a step of the graph
    if (event.node === LIFECYCLE) {
      lifecycle = event;
      continue;
    }
    const key = `${event.node}|${event.label}`;
    const existing = byKey.get(key);

    if (event.state === "running") {
      // a node that runs again after a resume starts a fresh row, so its bar shows the real work
      byKey.set(key, {
        key,
        node: event.node,
        label: event.label,
        group: groupOf(event.node),
        state: "running",
        startMs: at(event),
        endMs: null,
        elapsedMs: null,
        attempt: event.attempt,
        detail: null,
        ok: null,
      });
      continue;
    }

    const base: Step = existing ?? {
      key,
      node: event.node,
      label: event.label,
      group: groupOf(event.node),
      state: event.state,
      startMs: at(event),
      endMs: null,
      elapsedMs: null,
      attempt: event.attempt,
      detail: null,
      ok: null,
    };
    byKey.set(key, {
      ...base,
      state: event.state,
      endMs: at(event),
      elapsedMs: event.elapsed_ms,
      attempt: event.attempt ?? base.attempt,
      detail: event.detail ?? base.detail,
      ok: event.ok ?? base.ok,
    });
  }

  const steps = [...byKey.values()];
  const groups = GROUP_ORDER.map((id) => ({
    id,
    title: GROUP_TITLE[id],
    steps: steps.filter((s) => s.group === id),
  })).filter((g) => g.steps.length > 0);

  const last = at(events[events.length - 1]);
  const running = steps.some((s) => s.state === "running");
  const waiting = steps.some((s) => s.state === "waiting");
  const failure = lifecycle && lifecycle.state === "failed" ? lifecycle : null;

  return {
    steps,
    groups,
    totalMs: running && nowMs !== undefined ? Math.max(last, nowMs - origin) : last,
    failure,
    waiting: waiting && !failure,
    running: running && !failure,
    parallel: peakOverlap(steps.filter((s) => s.group === "domains"), nowMs === undefined ? last : nowMs - origin),
  };
}

/** The most steps whose time spans overlap at one instant. Measured from the events, never assumed. */
export function peakOverlap(steps: readonly Step[], openEnd: number): number {
  const marks: [number, number][] = [];
  for (const s of steps) {
    marks.push([s.startMs, 1], [s.endMs ?? openEnd, -1]);
  }
  // at the same instant an end sorts before a start, so back-to-back steps do not count as overlapping
  marks.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  let now = 0;
  let peak = 0;
  for (const [, delta] of marks) {
    now += delta;
    peak = Math.max(peak, now);
  }
  return peak;
}

export function formatElapsed(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 10_000) return `${(ms / 1000).toFixed(1)} s`;
  if (ms < 60_000) return `${Math.round(ms / 1000)} s`;
  const minutes = Math.floor(ms / 60_000);
  return `${minutes} min ${Math.round((ms % 60_000) / 1000)} s`;
}

export type Stage = "clarify" | "plan" | "run" | "review";
export const STAGES: { id: Stage; label: string }[] = [
  { id: "clarify", label: "Clarify" },
  { id: "plan", label: "Plan" },
  { id: "run", label: "Run" },
  { id: "review", label: "Review" },
];

export function stageOf(status: string): Stage {
  switch (status) {
    case "clarifying":
      return "clarify";
    case "planning":
      return "plan";
    case "running":
    case "failed":
      return "run";
    default:
      return "review";
  }
}
