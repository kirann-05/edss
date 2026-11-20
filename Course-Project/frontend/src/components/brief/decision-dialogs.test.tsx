import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ReasonDialog } from "./decision-dialogs";

function open(onConfirm = vi.fn()) {
  render(
    <ReasonDialog
      open
      onOpenChange={() => {}}
      title="Override the draft"
      description="Nothing is published."
      confirmLabel="Override"
      busy={false}
      error={null}
      onConfirm={onConfirm}
    />,
  );
  return onConfirm;
}

describe("ReasonDialog", () => {
  it("will not confirm without a reason", () => {
    open();
    expect(screen.getByRole("button", { name: "Override" })).toBeDisabled();
  });

  it("will not accept a reason too short to mean anything", async () => {
    open();
    await userEvent.type(screen.getByLabelText(/Reason/), "ok");
    expect(screen.getByRole("button", { name: "Override" })).toBeDisabled();
    expect(screen.getByText(/At least 10 characters/)).toBeInTheDocument();
  });

  it("confirms with the reason, trimmed", async () => {
    const onConfirm = open();
    await userEvent.type(screen.getByLabelText(/Reason/), "  The figures do not match the registrar's report.  ");
    await userEvent.click(screen.getByRole("button", { name: "Override" }));
    expect(onConfirm).toHaveBeenCalledWith("The figures do not match the registrar's report.");
  });

  it("shows the server's refusal", () => {
    render(
      <ReasonDialog open onOpenChange={() => {}} title="t" description="d" confirmLabel="Go" busy={false} error="a reason is required" onConfirm={() => {}} />,
    );
    expect(screen.getByText("a reason is required")).toBeInTheDocument();
  });
});
