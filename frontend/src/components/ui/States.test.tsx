import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorState } from "./States";
import { ApiError } from "@/lib/api";

describe("ErrorState", () => {
  it("renders a distinct unauthorized message for a 401 ApiError", () => {
    render(<ErrorState error={new ApiError(401, "invalid or missing API key")} />);
    expect(screen.getByText(/unauthorized/i)).toBeInTheDocument();
    expect(screen.queryByText(/invalid or missing API key/)).not.toBeInTheDocument();
  });

  it("renders the raw message for a non-401 error", () => {
    render(<ErrorState error={new ApiError(404, "channel not found")} />);
    expect(screen.getByText("channel not found")).toBeInTheDocument();
  });

  it("renders the raw message for a plain (non-ApiError) Error", () => {
    render(<ErrorState error={new Error("network down")} />);
    expect(screen.getByText("network down")).toBeInTheDocument();
  });

  it("shows a retry button only when onRetry is provided, and only for non-401 errors", () => {
    const { rerender } = render(<ErrorState error={new Error("boom")} onRetry={() => {}} />);
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();

    rerender(<ErrorState error={new ApiError(401, "nope")} onRetry={() => {}} />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });
});
