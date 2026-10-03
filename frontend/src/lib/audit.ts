// Reading the audit log as a person. Rows keep the full inputs and outputs (or a summary and a
// hash of them), so a row is described in one line here and shown in full when opened.
import type { AuditRow } from "@/lib/api/types";

const ACTION_WORDS: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.demo_login": "Signed in with the demo button",
  "auth.login_failed": "Sign-in failed",
  "auth.locked": "Sign-in refused, too many failures",
  "auth.logout": "Signed out",
  "run.create": "Started a run",
  "run.answer": "Answered the planner",
  "run.skip_questions": "Skipped the planner's questions",
  "plan.edit": "Edited the plan",
  "plan.revise": "Asked for plan changes",
  "plan.lock": "Locked the plan",
  "run.resume": "Resumed a stopped run",
  "run.failed": "Run stopped",
  "node.done": "Step finished",
  "node.failed": "Step failed",
  "gate.waiting": "Waiting at the human gate",
  "brief.draft": "Draft created",
  "brief.approve": "Approved",
  "brief.edit": "Approved with edits",
  "brief.override": "Overrode the draft",
  "brief.send_back": "Sent the draft back",
  "brief.refused": "Refused",
  "report.publish": "Published a version",
  "report.rollback": "Rolled back",
};

export function actionWords(action: string): string {
  return ACTION_WORDS[action] ?? action;
}

const HIDDEN = new Set(["digest", "keys", "summary"]);

function short(value: unknown): string {
  if (value === null || value === undefined) return "none";
  if (Array.isArray(value)) {
    if (value.length === 0) return "none";
    // a list of records is counted, a list of plain values is shown
    if (value.some((item) => item !== null && typeof item === "object")) {
      return `${value.length} item${value.length === 1 ? "" : "s"}`;
    }
    return value.map(short).join(", ");
  }
  if (typeof value === "object") return `${Object.keys(value as object).length} fields`;
  const text = String(value);
  return text.length > 60 ? `${text.slice(0, 57)}...` : text;
}

/** One line for a row: the outputs that say what happened, without hashes or long payloads. */
export function rowSummary(row: AuditRow): string {
  const parts = Object.entries(row.outputs)
    .filter(([key]) => !HIDDEN.has(key))
    .slice(0, 3)
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${short(value)}`);
  return parts.join(" · ");
}

export interface AuditFilters {
  run: string;
  actor: string;
  action: string;
  since: string; // YYYY-MM-DD, the viewer's local day
  until: string;
  page: number;
}

export const PAGE_SIZE = 50;

/** The API query for these filters. Dates are whole local days, sent as exact instants. */
export function auditQuery(filters: AuditFilters): string {
  const query = new URLSearchParams();
  if (filters.run.trim()) query.set("run_id", filters.run.trim());
  if (filters.actor.trim()) query.set("actor", filters.actor.trim());
  if (filters.action.trim()) query.set("action", filters.action.trim());
  if (filters.since) query.set("since", new Date(`${filters.since}T00:00:00`).toISOString());
  if (filters.until) query.set("until", new Date(`${filters.until}T23:59:59.999`).toISOString());
  query.set("offset", String(Math.max(0, filters.page - 1) * PAGE_SIZE));
  query.set("limit", String(PAGE_SIZE));
  return query.toString();
}

export function filtersFrom(params: URLSearchParams): AuditFilters {
  return {
    run: params.get("run") ?? "",
    actor: params.get("actor") ?? "",
    action: params.get("action") ?? "",
    since: params.get("since") ?? "",
    until: params.get("until") ?? "",
    page: Math.max(1, Number(params.get("page") ?? "1") || 1),
  };
}

/** The address bar form of the filters, leaving out what is empty so links stay short. */
export function filtersToParams(filters: AuditFilters): string {
  const query = new URLSearchParams();
  for (const key of ["run", "actor", "action", "since", "until"] as const) {
    if (filters[key].trim()) query.set(key, filters[key].trim());
  }
  if (filters.page > 1) query.set("page", String(filters.page));
  return query.toString();
}

export const shortHash = (hash: string) => (hash.length > 12 ? `${hash.slice(0, 6)}…${hash.slice(-6)}` : hash);
