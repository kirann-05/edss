import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { ErrorPanel } from "./error-panel";

describe("ErrorPanel", () => {
  it("gives the server's reason for something that is not there", () => {
    render(<ErrorPanel error={new ApiError(404, "There is no run 'abc'")} what="this run" />);
    expect(screen.getByText("We could not load this run")).toBeInTheDocument();
    expect(screen.getByText("There is no run 'abc'.")).toBeInTheDocument();
  });

  it("falls back to a plain sentence when the server only said Not Found", () => {
    render(<ErrorPanel error={new ApiError(404, "Not Found")} />);
    expect(screen.getByText("That period or item does not exist.")).toBeInTheDocument();
  });

  it("offers to try again only when trying again could help", () => {
    const { rerender } = render(<ErrorPanel error={new TypeError("Failed to fetch")} onRetry={() => {}} />);
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    rerender(<ErrorPanel error={new ApiError(403, "no")} onRetry={() => {}} />);
    expect(screen.getByText("Your role does not include this.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Try again" })).not.toBeInTheDocument();
  });
});
