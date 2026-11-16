import { describe, expect, it } from "vitest";

import { formatAge, formatClock, formatDay, formatWhen } from "./when";

describe("dates as a person reads them", () => {
  it("shows a date-only as-of date on its own day, whatever the viewer's time zone", () => {
    // read as local midnight, so a viewer west of UTC never sees the day before
    expect(formatDay("2026-10-03")).toBe("3 Oct 2026");
  });

  it("shows a full timestamp with its date and time", () => {
    expect(formatWhen("2026-10-03T11:12:00Z")).toMatch(/^\d{1,2} Oct 2026, \d{2}:\d{2}$/);
    expect(formatClock("2026-10-03T11:12:07Z")).toMatch(/^\d{2}:\d{2}:07$/);
  });

  it("leaves text that is not a date as it was, rather than showing Invalid Date", () => {
    for (const format of [formatWhen, formatClock, formatDay]) expect(format("not a date")).toBe("not a date");
    expect(formatAge("not a date")).toBe("not a date");
  });

  it("gives a coarse age", () => {
    const now = Date.parse("2026-10-03T12:00:00Z");
    const ago = (minutes: number) => formatAge(new Date(now - minutes * 60_000).toISOString(), now);
    expect(ago(0)).toBe("just now");
    expect(ago(5)).toBe("5 min ago");
    expect(ago(150)).toBe("3 h ago");
    expect(ago(60 * 24)).toBe("1 day ago");
    expect(ago(60 * 24 * 3)).toBe("3 days ago");
    expect(formatAge(new Date(now + 60_000).toISOString(), now)).toBe("just now"); // a clock a little ahead
  });
});
