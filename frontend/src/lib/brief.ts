// Rules for the review screen that are worth testing on their own: what counts as an edit, when the
// Approve button may be pressed, and a quick hint about typed numbers. The server decides all of
// these again. The UI only shows the same answer early and says why.
import type { Brief, BriefOption, EditRequest, Segment } from "@/lib/api/types";

export const LIST_FIELDS = ["assumptions", "risks", "trade_offs"] as const;
export type ListField = (typeof LIST_FIELDS)[number];

export const FIELD_LABEL: Record<EditRequest["field"], string> = {
  title: "Title",
  description: "Description",
  assumptions: "Assumptions",
  risks: "Risks",
  trade_offs: "Trade-offs",
};

/** An option as the approver edits it. Lists are one item per line. */
export interface OptionDraft {
  title: string;
  description: string;
  assumptions: string;
  risks: string;
  trade_offs: string;
}

export function draftFromOption(option: BriefOption): OptionDraft {
  return {
    title: option.title,
    description: option.description.text,
    assumptions: option.assumptions.map((a) => a.text).join("\n"),
    risks: option.risks.map((r) => r.text).join("\n"),
    trade_offs: option.trade_offs.map((t) => t.text).join("\n"),
  };
}

export function lines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

const sameList = (a: readonly string[], b: readonly string[]) =>
  a.length === b.length && a.every((x, i) => x === b[i]);

/** The edits one option's draft makes, field by field, and nothing for a field left alone. */
export function editsForOption(option: BriefOption, draft: OptionDraft): EditRequest[] {
  const edits: EditRequest[] = [];
  if (draft.title.trim() !== option.title) {
    edits.push({ option_id: option.id, field: "title", value: draft.title.trim() });
  }
  if (draft.description.trim() !== option.description.text) {
    edits.push({ option_id: option.id, field: "description", value: draft.description.trim() });
  }
  for (const field of LIST_FIELDS) {
    const before = option[field].map((item) => item.text);
    const after = lines(draft[field]);
    if (!sameList(before, after)) edits.push({ option_id: option.id, field, value: after });
  }
  return edits;
}

export function allEdits(brief: Brief, drafts: Readonly<Record<string, OptionDraft>>): EditRequest[] {
  return brief.document.option_sets.flatMap((set) =>
    set.options.flatMap((option) => (drafts[option.id] ? editsForOption(option, drafts[option.id]) : [])),
  );
}

// The server's number lint allows dates, financial year labels and quarter or semester labels
// (backend/app/agents/tokens.py). Anything else with a digit outside a reference token is rejected.
const ALLOWED = [/\b\d{4}-\d{2}-\d{2}\b/g, /\b\d{4}-\d{2}\b/g, /\bQ[1-4]\b/g, /\bS[12]\b/g];

/** Numbers typed by hand, which check V1 will reject. A hint only, the server's check decides. */
export function strayNumbers(text: string): string[] {
  let rest = text.replace(/\{\{[^}]*\}\}/g, " ");
  for (const pattern of ALLOWED) rest = rest.replace(pattern, " ");
  return rest.match(/\d+(?:[.,]\d+)*%?/g) ?? [];
}

export function segmentsText(segments: readonly Segment[]): string {
  return segments.map((s) => (s.t === "text" ? (s.text ?? "") : (s.display ?? ""))).join("");
}

export type DecisionState =
  | { kind: "cannot_decide"; reason: string }
  | { kind: "decided" }
  | {
      kind: "open";
      approve: { enabled: boolean; reason: string | null };
      needsAcknowledgement: boolean;
    };

const OPEN = new Set<Brief["status"]>(["draft", "escalated"]);

/**
 * What the person in front of the screen may do now. Approve follows the server's own approval
 * state, and an escalated draft that may be approved also needs the acknowledgement ticked.
 */
export function decisionState(brief: Brief, acknowledged: boolean): DecisionState {
  if (!OPEN.has(brief.status)) return { kind: "decided" };
  if (!brief.can_decide) {
    return { kind: "cannot_decide", reason: "Your role may read drafts but not decide on them." };
  }
  const state = brief.approval_state;
  if (!state.can_approve) {
    return {
      kind: "open",
      approve: { enabled: false, reason: state.blocked_reason ?? "This draft cannot be approved." },
      needsAcknowledgement: false,
    };
  }
  if (state.needs_acknowledgement && !acknowledged) {
    return {
      kind: "open",
      approve: { enabled: false, reason: "Tick the acknowledgement before approving." },
      needsAcknowledgement: true,
    };
  }
  return { kind: "open", approve: { enabled: true, reason: null }, needsAcknowledgement: state.needs_acknowledgement };
}
