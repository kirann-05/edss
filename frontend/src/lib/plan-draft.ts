// The plan as a person edits it, before it is saved. Only what changed is sent, and the KPI
// selection is the one source of truth for areas: the API works out the areas from the KPIs, so the
// two can never disagree.
import type { Domain, Plan, PlanCatalogue, PlanPatch } from "@/lib/api/types";

export type KpiChoice = PlanCatalogue["kpis"][number];

export interface PlanDraft {
  period_year: string;
  audience: string;
  options_for: Plan["options_for"];
  kpi_keys: string[];
  steps: Record<string, { title: string; detail: string }>;
}

export function draftFromPlan(plan: Plan): PlanDraft {
  return {
    period_year: plan.period_year,
    audience: plan.audience,
    options_for: plan.options_for,
    kpi_keys: [...plan.kpi_keys],
    steps: Object.fromEntries(plan.steps.map((s) => [s.id, { title: s.title, detail: s.detail }])),
  };
}

const sameSet = (a: readonly string[], b: readonly string[]) =>
  a.length === b.length && a.every((x) => b.includes(x));

/** Only the fields that differ from the saved plan. An empty object means nothing to save. */
export function patchFromDraft(plan: Plan, draft: PlanDraft): PlanPatch {
  const patch: PlanPatch = {};
  if (draft.period_year !== plan.period_year) patch.period_year = draft.period_year;
  if (draft.audience.trim() !== plan.audience) patch.audience = draft.audience.trim();
  if (draft.options_for !== plan.options_for) patch.options_for = draft.options_for;
  if (!sameSet(draft.kpi_keys, plan.kpi_keys)) patch.kpi_keys = [...draft.kpi_keys];

  const steps: NonNullable<PlanPatch["steps"]> = {};
  for (const step of plan.steps) {
    const edited = draft.steps[step.id];
    if (!edited) continue;
    const change: { title?: string; detail?: string } = {};
    if (edited.title.trim() !== step.title) change.title = edited.title.trim();
    if (edited.detail.trim() !== step.detail) change.detail = edited.detail.trim();
    if (Object.keys(change).length > 0) steps[step.id] = change;
  }
  if (Object.keys(steps).length > 0) patch.steps = steps;
  return patch;
}

export const isEmptyPatch = (patch: PlanPatch) => Object.keys(patch).length === 0;

export function sortByCatalogue(keys: readonly string[], kpis: readonly KpiChoice[]): string[] {
  const order = new Map(kpis.map((k, i) => [k.key, i]));
  return [...keys].sort((a, b) => (order.get(a) ?? Number.MAX_SAFE_INTEGER) - (order.get(b) ?? Number.MAX_SAFE_INTEGER));
}

export function toggleKpi(draft: PlanDraft, key: string, kpis: readonly KpiChoice[]): PlanDraft {
  const keys = draft.kpi_keys.includes(key)
    ? draft.kpi_keys.filter((k) => k !== key)
    : [...draft.kpi_keys, key];
  return { ...draft, kpi_keys: sortByCatalogue(keys, kpis) };
}

/** Turning an area on selects all its KPIs, turning it off removes them. */
export function setDomain(
  draft: PlanDraft,
  domain: Domain,
  on: boolean,
  kpis: readonly KpiChoice[],
): PlanDraft {
  const inDomain = kpis.filter((k) => k.domain === domain).map((k) => k.key);
  const others = draft.kpi_keys.filter((k) => !inDomain.includes(k));
  return { ...draft, kpi_keys: sortByCatalogue(on ? [...others, ...inDomain] : others, kpis) };
}

/** An area is on when all its KPIs are chosen, partly on when some are. */
export function domainState(
  draft: PlanDraft,
  domain: Domain,
  kpis: readonly KpiChoice[],
): boolean | "indeterminate" {
  const inDomain = kpis.filter((k) => k.domain === domain);
  const chosen = inDomain.filter((k) => draft.kpi_keys.includes(k.key)).length;
  if (chosen === 0) return false;
  return chosen === inDomain.length ? true : "indeterminate";
}

/** What stops the draft being saved, in words. The API checks the same things again. */
export function draftProblems(draft: PlanDraft): string[] {
  const problems: string[] = [];
  if (draft.kpi_keys.length === 0) problems.push("Choose at least one KPI.");
  if (!draft.audience.trim()) problems.push("Say who the brief is for.");
  if (Object.values(draft.steps).some((s) => !s.title.trim())) problems.push("Every step needs a title.");
  return problems;
}
