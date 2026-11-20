import { describe, expect, it } from "vitest";

import type { Plan } from "@/lib/api/types";

import {
  domainState,
  draftFromPlan,
  draftProblems,
  isEmptyPatch,
  patchFromDraft,
  setDomain,
  sortByCatalogue,
  toggleKpi,
  type KpiChoice,
} from "./plan-draft";

const KPIS: KpiChoice[] = [
  { key: "AC_PASS_PCT", name: "Overall pass percentage", domain: "academic" },
  { key: "AC_CO", name: "Average CO attainment", domain: "academic" },
  { key: "RS_PUB_PF", name: "Publications per faculty", domain: "research" },
  { key: "PL_PCT", name: "Placement percentage", domain: "placement" },
  { key: "PL_AVG", name: "Average package", domain: "placement" },
];

const PLAN: Plan = {
  request: "Prepare the leadership brief",
  period_year: "2025-26",
  domains: ["academic", "placement"],
  kpi_keys: ["AC_PASS_PCT", "AC_CO", "PL_PCT", "PL_AVG"],
  options_for: "off_target",
  audience: "Internal leadership review",
  steps: [
    { id: "access", title: "Confirm access", detail: "Check the scopes." },
    { id: "validate", title: "Validate", detail: "Run the nine checks." },
  ],
  revision: 1,
  locked_at: null,
};

describe("patchFromDraft", () => {
  it("is empty when nothing changed", () => {
    expect(isEmptyPatch(patchFromDraft(PLAN, draftFromPlan(PLAN)))).toBe(true);
  });

  it("sends only the fields that changed", () => {
    const draft = { ...draftFromPlan(PLAN), period_year: "2024-25", options_for: "all" as const };
    expect(patchFromDraft(PLAN, draft)).toEqual({ period_year: "2024-25", options_for: "all" });
  });

  it("does not treat a reordered KPI list as a change", () => {
    const draft = { ...draftFromPlan(PLAN), kpi_keys: ["PL_AVG", "PL_PCT", "AC_CO", "AC_PASS_PCT"] };
    expect(isEmptyPatch(patchFromDraft(PLAN, draft))).toBe(true);
  });

  it("sends the KPI keys alone, so the server works out the areas", () => {
    const draft = toggleKpi(draftFromPlan(PLAN), "RS_PUB_PF", KPIS);
    expect(patchFromDraft(PLAN, draft)).toEqual({ kpi_keys: ["AC_PASS_PCT", "AC_CO", "RS_PUB_PF", "PL_PCT", "PL_AVG"] });
  });

  it("ignores whitespace a person added by accident", () => {
    const draft = { ...draftFromPlan(PLAN), audience: "  Internal leadership review " };
    expect(isEmptyPatch(patchFromDraft(PLAN, draft))).toBe(true);
  });

  it("sends a step change with only the part that changed", () => {
    const draft = draftFromPlan(PLAN);
    draft.steps.validate = { title: "Validate", detail: "Run all nine checks before review." };
    expect(patchFromDraft(PLAN, draft)).toEqual({
      steps: { validate: { detail: "Run all nine checks before review." } },
    });
  });
});

describe("KPI and area selection", () => {
  it("keeps the catalogue order whatever order things were picked in", () => {
    expect(sortByCatalogue(["PL_PCT", "AC_CO", "RS_PUB_PF"], KPIS)).toEqual(["AC_CO", "RS_PUB_PF", "PL_PCT"]);
  });

  it("toggles one KPI off and on again", () => {
    const off = toggleKpi(draftFromPlan(PLAN), "AC_CO", KPIS);
    expect(off.kpi_keys).toEqual(["AC_PASS_PCT", "PL_PCT", "PL_AVG"]);
    expect(toggleKpi(off, "AC_CO", KPIS).kpi_keys).toEqual(PLAN.kpi_keys);
  });

  it("turning an area off removes all of its KPIs", () => {
    expect(setDomain(draftFromPlan(PLAN), "academic", false, KPIS).kpi_keys).toEqual(["PL_PCT", "PL_AVG"]);
  });

  it("turning an area on adds all of its KPIs", () => {
    const draft = setDomain(draftFromPlan(PLAN), "research", true, KPIS);
    expect(draft.kpi_keys).toEqual(["AC_PASS_PCT", "AC_CO", "RS_PUB_PF", "PL_PCT", "PL_AVG"]);
  });

  it("reports an area as on, off or partly on", () => {
    const draft = toggleKpi(draftFromPlan(PLAN), "PL_AVG", KPIS);
    expect(domainState(draft, "academic", KPIS)).toBe(true);
    expect(domainState(draft, "placement", KPIS)).toBe("indeterminate");
    expect(domainState(draft, "research", KPIS)).toBe(false);
  });
});

describe("draftProblems", () => {
  it("has nothing to say about a sound draft", () => {
    expect(draftProblems(draftFromPlan(PLAN))).toEqual([]);
  });

  it("says why an empty selection, a blank audience or a blank step title cannot be saved", () => {
    const draft = { ...draftFromPlan(PLAN), kpi_keys: [], audience: " " };
    draft.steps.access = { title: "", detail: "x" };
    expect(draftProblems(draft)).toEqual([
      "Choose at least one KPI.",
      "Say who the brief is for.",
      "Every step needs a title.",
    ]);
  });
});
