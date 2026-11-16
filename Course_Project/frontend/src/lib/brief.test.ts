import { describe, expect, it } from "vitest";

import type { Brief, BriefOption, RichText } from "@/lib/api/types";

import {
  allEdits,
  decisionState,
  draftFromOption,
  editsForOption,
  lines,
  segmentsText,
  strayNumbers,
} from "./brief";

const rich = (text: string): RichText => ({ text, segments: [{ t: "text", text, unresolved: false }] });

const OPTION: BriefOption = {
  id: "PL_PCT-1",
  title: "Intensify pre-placement training",
  description: rich("{{kpi:PL_PCT}} is {{kpi:PL_PCT.gap}}. Focus training where conversion is lowest."),
  assumptions: [rich("Students attend the sessions."), rich("Recruiters keep visiting.")],
  risks: [rich("Training load on faculty.")],
  trade_offs: [rich("Depth in a few departments against even coverage.")],
};

function brief(overrides: Partial<Brief> = {}): Brief {
  return {
    id: "brief-1",
    run_id: "run-1",
    status: "draft",
    escalated: false,
    diagnosis: null,
    attempts: 1,
    created_at: "2026-10-03T10:00:00Z",
    created_by: "registrar@edss.test",
    request: "Prepare the leadership brief",
    period_year: "2025-26",
    document: {
      title: "Decision brief, 2025-26",
      period_year: "2025-26",
      kpis: [],
      summary: [],
      option_sets: [
        { kpi_key: "PL_PCT", kpi_name: "Placement percentage", status: "missed", attempt: 1, guided_by: "Strategic plan", options: [OPTION] },
      ],
      assumptions: [],
      data_health: [],
    },
    validation: { attempt: 1, passed: true, checks: [] },
    history: [],
    repair_log: [],
    approval: null,
    edits: [],
    version: null,
    decision_reason: null,
    approval_state: { can_approve: true, blocked_reason: null, needs_acknowledgement: false, failing_checks: [] },
    can_decide: true,
    ...overrides,
  };
}

describe("editsForOption", () => {
  it("finds no edits in an untouched draft", () => {
    expect(editsForOption(OPTION, draftFromOption(OPTION))).toEqual([]);
  });

  it("reports only the fields that changed", () => {
    const draft = { ...draftFromOption(OPTION), title: "Targeted pre-placement training" };
    expect(editsForOption(OPTION, draft)).toEqual([
      { option_id: "PL_PCT-1", field: "title", value: "Targeted pre-placement training" },
    ]);
  });

  it("keeps reference tokens in the description exactly as written", () => {
    const description = "{{kpi:PL_PCT}} is {{kpi:PL_PCT.gap}}. Start with the two weakest departments.";
    const [edit] = editsForOption(OPTION, { ...draftFromOption(OPTION), description });
    expect(edit).toEqual({ option_id: "PL_PCT-1", field: "description", value: description });
  });

  it("sends a list as its items, one per line, blank lines dropped", () => {
    const draft = { ...draftFromOption(OPTION), risks: "Training load on faculty.\n\n  Students may skip optional sessions. \n" };
    expect(editsForOption(OPTION, draft)).toEqual([
      {
        option_id: "PL_PCT-1",
        field: "risks",
        value: ["Training load on faculty.", "Students may skip optional sessions."],
      },
    ]);
  });

  it("treats a reordered list as an edit, because order is what the reader sees", () => {
    const draft = { ...draftFromOption(OPTION), assumptions: "Recruiters keep visiting.\nStudents attend the sessions." };
    expect(editsForOption(OPTION, draft).map((e) => e.field)).toEqual(["assumptions"]);
  });

  it("collects the edits of every drafted option in the brief", () => {
    const drafts = { "PL_PCT-1": { ...draftFromOption(OPTION), title: "New title" } };
    expect(allEdits(brief(), drafts)).toHaveLength(1);
    expect(allEdits(brief(), {})).toEqual([]);
  });
});

describe("strayNumbers", () => {
  it("allows numbers inside reference tokens", () => {
    expect(strayNumbers("{{kpi:PL_PCT}} against {{fact:8841}}")).toEqual([]);
  });

  it("allows the same labels the server allows: dates, years, quarters and semesters", () => {
    expect(strayNumbers("By 2026-03-31, for 2025-26, in Q4 and S2")).toEqual([]);
  });

  it("flags a number typed by hand", () => {
    expect(strayNumbers("Raise it by 12% in two years, to 80.5")).toEqual(["12%", "80.5"]);
  });
});

describe("lines and segmentsText", () => {
  it("splits on lines and trims", () => {
    expect(lines(" a \n\nb")).toEqual(["a", "b"]);
  });

  it("reads rendered segments as plain text", () => {
    expect(
      segmentsText([
        { t: "ref", kind: "kpi", key: "PL_PCT", field: "value", display: "75.0%", status: "missed", unresolved: false },
        { t: "text", text: " placed", unresolved: false },
      ]),
    ).toBe("75.0% placed");
  });
});

describe("decisionState", () => {
  it("lets an approver approve a validated draft", () => {
    expect(decisionState(brief(), false)).toEqual({
      kind: "open",
      approve: { enabled: true, reason: null },
      needsAcknowledgement: false,
    });
  });

  it("follows the server when it blocks approval, and shows its reason", () => {
    const blocked = brief({
      status: "escalated",
      approval_state: {
        can_approve: false,
        blocked_reason: "Integrity checks failed (V1). Send it back or override it.",
        needs_acknowledgement: false,
        failing_checks: ["V1"],
      },
    });
    const state = decisionState(blocked, true);
    expect(state.kind === "open" && state.approve).toEqual({
      enabled: false,
      reason: "Integrity checks failed (V1). Send it back or override it.",
    });
  });

  it("needs the acknowledgement ticked for an escalated draft that may be approved", () => {
    const escalated = brief({
      status: "escalated",
      approval_state: { can_approve: true, blocked_reason: null, needs_acknowledgement: true, failing_checks: ["V2"] },
    });
    const before = decisionState(escalated, false);
    const after = decisionState(escalated, true);
    expect(before.kind === "open" && before.approve.enabled).toBe(false);
    expect(after.kind === "open" && after.approve.enabled).toBe(true);
  });

  it("offers nothing to decide once a decision exists", () => {
    expect(decisionState(brief({ status: "published" }), false)).toEqual({ kind: "decided" });
  });

  it("explains when the role may read but not decide", () => {
    expect(decisionState(brief({ can_decide: false }), false).kind).toBe("cannot_decide");
  });
});
