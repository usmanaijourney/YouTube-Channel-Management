import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("renders green styling for a healthy-family status", () => {
    render(<StatusBadge status="healthy" />);
    expect(screen.getByText("healthy")).toHaveClass("text-emerald-400");
  });

  it("renders red styling for a failed-family status", () => {
    render(<StatusBadge status="failed" />);
    expect(screen.getByText("failed")).toHaveClass("text-red-400");
  });

  it("renders amber styling for a mocked status", () => {
    render(<StatusBadge status="mocked" />);
    expect(screen.getByText("mocked")).toHaveClass("text-amber-400");
  });

  it("is case-insensitive when mapping status to color", () => {
    render(<StatusBadge status="HEALTHY" />);
    expect(screen.getByText("HEALTHY")).toHaveClass("text-emerald-400");
  });

  it("falls back to gray for an unrecognized status", () => {
    render(<StatusBadge status="some_weird_state" />);
    expect(screen.getByText("some_weird_state")).toHaveClass("text-slate-400");
  });

  it("falls back to gray and shows 'unknown' for null/undefined", () => {
    render(<StatusBadge status={null} />);
    expect(screen.getByText("unknown")).toHaveClass("text-slate-400");
  });
});
