import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { RichText as RichTextValue } from "@/lib/api/types";

import { RichText } from "./rich-text";

const text = (value: string) => ({ t: "text" as const, text: value, unresolved: false });
const kpi = (key: string, field: string, display: string, status: string) => ({
  t: "ref" as const,
  kind: "kpi" as const,
  key,
  field,
  display,
  status,
  unresolved: false,
});

function rich(...segments: RichTextValue["segments"]): RichTextValue {
  return { text: "", segments };
}

describe("RichText", () => {
  it("shows a figure as a control that opens its KPI", async () => {
    const onKpi = vi.fn();
    render(<RichText value={rich(kpi("PL_PCT", "value", "75.0%", "missed"), text(" placed"))} onKpi={onKpi} />);
    await userEvent.click(screen.getByRole("button", { name: /75\.0%/ }));
    expect(onKpi).toHaveBeenCalledWith("PL_PCT");
  });

  it("says a KPI figure's status in words, not only in colour", () => {
    render(<RichText value={rich(kpi("PL_PCT", "value", "75.0%", "missed"))} onKpi={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent("Missed");
  });

  it("shows a status reference as a status badge", () => {
    render(<RichText value={rich(kpi("PL_PCT", "status", "Missed", "missed"))} onKpi={() => {}} />);
    expect(screen.getByRole("button")).toHaveTextContent("Missed");
  });

  it("keeps the plain text around a figure", () => {
    render(<RichText value={rich(text("Placement is "), kpi("PL_PCT", "value", "75.0%", "missed"), text(" today."))} />);
    expect(screen.getByText(/Placement is/)).toHaveTextContent("Placement is 75.0% (Missed) today.");
  });

  it("is plain text, not a button, when the reader may not open drill-downs", () => {
    render(<RichText value={rich(kpi("PL_PCT", "value", "75.0%", "missed"))} />);
    expect(screen.queryByRole("button")).toBeNull();
    expect(screen.getByText("75.0%")).toBeInTheDocument();
  });

  it("badges a provisional record wherever it appears, and opens its source", async () => {
    const onFact = vi.fn();
    const fact = { t: "ref" as const, kind: "fact" as const, key: "8841", field: "value", display: "412", status: "provisional", unresolved: false };
    render(<RichText value={rich(fact)} onFact={onFact} />);
    expect(screen.getByRole("button")).toHaveTextContent("Provisional");
    await userEvent.click(screen.getByRole("button"));
    expect(onFact).toHaveBeenCalledWith(8841);
  });

  it("does not badge a final record", () => {
    const fact = { t: "ref" as const, kind: "fact" as const, key: "12", field: "value", display: "9,200", status: "final", unresolved: false };
    render(<RichText value={rich(fact)} onFact={() => {}} />);
    expect(screen.getByRole("button")).not.toHaveTextContent("Final");
  });

  it("flags a reference that does not resolve, so it cannot pass for a figure", () => {
    const broken = { t: "ref" as const, kind: "kpi" as const, key: "NOPE", field: "value", display: "{{kpi:NOPE}}", unresolved: true };
    render(<RichText value={rich(broken)} onKpi={() => {}} />);
    expect(screen.getByText("{{kpi:NOPE}}")).toBeInTheDocument();
    expect(screen.getByText(/unresolved reference/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
