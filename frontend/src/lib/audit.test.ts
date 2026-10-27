import { describe, expect, it } from "vitest";

import type { AuditRow } from "@/lib/api/types";

import { actionWords, auditQuery, filtersFrom, filtersToParams, rowSummary, shortHash } from "./audit";

const row = (outputs: Record<string, unknown>): AuditRow => ({
  id: 1,
  ts: "2026-10-03T10:00:00Z",
  run_id: "run-1",
  actor_type: "agent",
  actor_id: "domain:finance",
  action: "node.done",
  inputs: {},
  outputs,
  prev_hash: "0".repeat(64),
  hash: "a".repeat(64),
});

describe("rowSummary", () => {
  it("says what happened and leaves out hashes and payload summaries", () => {
    expect(rowSummary(row({ digest: "abc", summary: { x: 1 }, elapsed_ms: 704 }))).toBe("elapsed ms: 704");
  });

  it("shortens long values and lists", () => {
    expect(rowSummary(row({ rolled_back: [2, 3], reason: "x".repeat(80) }))).toBe(
      `rolled back: 2, 3 · reason: ${"x".repeat(57)}...`,
    );
  });

  it("counts a list of records rather than describing the first one", () => {
    expect(rowSummary(row({ edits: [{ option: "PL_PCT-2", field: "title" }] }))).toBe("edits: 1 item");
  });

  it("is empty when there is nothing to say", () => {
    expect(rowSummary(row({}))).toBe("");
  });
});

describe("actionWords", () => {
  it("names known actions in words and keeps unknown ones as they are", () => {
    expect(actionWords("report.rollback")).toBe("Rolled back");
    expect(actionWords("something.new")).toBe("something.new");
  });
});

describe("filters", () => {
  it("round-trips through the address bar, leaving out empty filters", () => {
    const params = new URLSearchParams("run=run-2&action=plan.lock&page=3");
    const filters = filtersFrom(params);
    expect(filters).toEqual({ run: "run-2", actor: "", action: "plan.lock", since: "", until: "", who: "everyone", page: 3 });
    expect(filtersToParams(filters)).toBe("run=run-2&action=plan.lock&page=3");
  });

  it("turns a page number into an offset for the API", () => {
    const query = new URLSearchParams(auditQuery({ ...filtersFrom(new URLSearchParams()), page: 3 }));
    expect(query.get("offset")).toBe("100");
    expect(query.get("limit")).toBe("50");
  });

  it("sends whole local days as exact instants", () => {
    const query = new URLSearchParams(
      auditQuery({ run: "", actor: "", action: "", since: "2026-10-03", until: "2026-10-03", who: "everyone", page: 1 }),
    );
    const since = new Date(query.get("since") as string);
    const until = new Date(query.get("until") as string);
    expect(since.getHours()).toBe(0);
    expect(until.getTime() - since.getTime()).toBe(24 * 3600 * 1000 - 1);
  });

  it("treats a nonsense page as the first", () => {
    expect(filtersFrom(new URLSearchParams("page=banana")).page).toBe(1);
  });
});

describe("shortHash", () => {
  it("keeps the ends of a hash so two can be compared by eye", () => {
    expect(shortHash("0123456789abcdef0123")).toBe("012345…ef0123");
    expect(shortHash("short")).toBe("short");
  });
});

describe("who did it", () => {
  it("asks the API for people's actions only, and keeps the choice in the address", () => {
    const filters = { ...filtersFrom(new URLSearchParams("who=people")), page: 1 };
    expect(filters.who).toBe("people");
    expect(new URLSearchParams(auditQuery(filters)).get("actor_type")).toBe("user");
    expect(filtersToParams(filters)).toBe("who=people");
    expect(new URLSearchParams(auditQuery(filtersFrom(new URLSearchParams()))).has("actor_type")).toBe(false);
  });
});
