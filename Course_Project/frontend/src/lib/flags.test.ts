import { describe, expect, it } from "vitest";

import type { KpiOut } from "@/lib/api/types";

import { flagSummaries, mergeFlags } from "./flags";

type Flags = KpiOut["flags"];

const none = { departments: [], total: 0 };
const flags = (over: Partial<Flags> = {}): Flags => ({
  stale: none,
  missing: none,
  excluded: none,
  undefined: none,
  excluded_fact_count: 0,
  no_target: false,
  ...over,
});

describe("flagSummaries", () => {
  it("is empty when nothing is wrong", () => {
    expect(flagSummaries(flags())).toEqual([]);
  });

  it("names the departments the viewer may see", () => {
    const [stale] = flagSummaries(flags({ stale: { departments: ["CIVIL"], total: 1 } }));
    expect(stale.text).toBe("Stale: CIVIL");
    expect(stale.kind).toBe("stale");
  });

  it("says how many more there are when the viewer cannot see all of them", () => {
    const [stale] = flagSummaries(flags({ stale: { departments: ["CSE"], total: 3 } }));
    expect(stale.text).toBe("Stale: CSE and 2 others");
  });

  it("gives only a count when the viewer may see none of them", () => {
    const [one] = flagSummaries(flags({ stale: { departments: [], total: 1 } }));
    expect(one.text).toBe("Stale: 1 department");
    const [many] = flagSummaries(flags({ missing: { departments: [], total: 2 } }));
    expect(many.text).toBe("No record: 2 departments");
  });

  it("covers every kind in a fixed order, most serious first", () => {
    const all = flagSummaries(
      flags({
        stale: { departments: ["A"], total: 1 },
        undefined: { departments: ["B"], total: 1 },
        excluded: { departments: ["C"], total: 1 },
        missing: { departments: ["D"], total: 1 },
        no_target: true,
      }),
    );
    expect(all.map((f) => f.kind)).toEqual(["missing", "excluded", "stale", "undefined", "no_target"]);
  });

  it("reports a KPI with no target", () => {
    const [flag] = flagSummaries(flags({ no_target: true }));
    expect(flag.text).toBe("No target set");
  });
});

describe("mergeFlags (the dashboard-wide data quality notice)", () => {
  it("takes the union of departments across KPIs, counting each department once", () => {
    const merged = mergeFlags([
      flags({ stale: { departments: ["CIVIL"], total: 1 } }),
      flags({ stale: { departments: ["CIVIL"], total: 1 } }),
      flags({ stale: { departments: ["ECE"], total: 1 }, missing: { departments: ["MECH"], total: 1 } }),
    ]);
    expect(merged.stale).toEqual({ departments: ["CIVIL", "ECE"], total: 2 });
    expect(merged.missing).toEqual({ departments: ["MECH"], total: 1 });
  });

  it("still counts departments the viewer may not see, without naming them", () => {
    const merged = mergeFlags([flags({ stale: { departments: [], total: 1 } })]);
    expect(merged.stale).toEqual({ departments: [], total: 1 });
    expect(flagSummaries(merged)[0].text).toBe("Stale: 1 department");
  });

  it("does not double count a hidden department that several KPIs share", () => {
    const merged = mergeFlags([
      flags({ stale: { departments: ["CSE"], total: 2 } }),
      flags({ stale: { departments: ["CSE"], total: 2 } }),
    ]);
    expect(merged.stale.total).toBe(2);
  });

  it("is empty when no KPI has a problem", () => {
    expect(flagSummaries(mergeFlags([flags(), flags()]))).toEqual([]);
  });
});
