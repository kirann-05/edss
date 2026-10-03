import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StageStepper } from "./stage-stepper";

describe("StageStepper", () => {
  it("marks the current stage and the ones before it, in words as well as marks", () => {
    render(<StageStepper current="run" />);
    const items = screen.getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual([
      expect.stringContaining("Clarify (done)"),
      expect.stringContaining("Plan (done)"),
      expect.stringContaining("Run (current)"),
      expect.stringContaining("Review"),
    ]);
    expect(items[2]).toHaveAttribute("aria-current", "step");
  });

  it("says when the run has stopped", () => {
    render(<StageStepper current="run" stopped />);
    expect(screen.getAllByRole("listitem")[2].textContent).toContain("Run (stopped)");
  });
});
