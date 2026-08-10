import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChannelsPage from "./page";
import { useChannels } from "@/lib/hooks";
import type { ChannelSummary } from "@/lib/types";

vi.mock("@/lib/hooks", () => ({
  useChannels: vi.fn(),
}));

const mockedUseChannels = vi.mocked(useChannels);

const SAMPLE_CHANNEL: ChannelSummary = {
  channel_id: "channel-001",
  name: "TechExplained Daily",
  niche: "consumer tech explainers",
  status: "active",
  created_at: "2026-08-09T21:00:00Z",
  schedule: { videos_per_day: 2 },
  current_task_count: 0,
  tasks_completed: 1,
  tasks_failed: 0,
  videos_produced: 1,
  videos_uploaded: 1,
  cost_total: 0.02,
};

const OTHER_CHANNEL: ChannelSummary = {
  ...SAMPLE_CHANNEL,
  channel_id: "channel-002",
  name: "Cooking Corner",
  niche: "home cooking",
  status: "paused",
};

describe("ChannelsPage", () => {
  it("shows skeleton loading state while data is loading", () => {
    mockedUseChannels.mockReturnValue({ data: undefined, error: undefined, isLoading: true } as never);
    const { container } = render(<ChannelsPage />);
    expect(container.querySelectorAll(".animate-pulse").length).toBeGreaterThan(0);
  });

  it("shows an error state when the request fails", () => {
    mockedUseChannels.mockReturnValue({
      data: undefined,
      error: new Error("Network error — could not reach the dashboard server"),
      isLoading: false,
    } as never);
    render(<ChannelsPage />);
    expect(screen.getByText(/could not reach the dashboard server/i)).toBeInTheDocument();
  });

  it("shows an empty state when there are no channels", () => {
    mockedUseChannels.mockReturnValue({ data: [], error: undefined, isLoading: false } as never);
    render(<ChannelsPage />);
    expect(screen.getByText(/no channels match your filters/i)).toBeInTheDocument();
  });

  it("renders real channel data in the table", () => {
    mockedUseChannels.mockReturnValue({ data: [SAMPLE_CHANNEL], error: undefined, isLoading: false } as never);
    render(<ChannelsPage />);
    expect(screen.getByText("TechExplained Daily")).toBeInTheDocument();
    // "active" also appears as a filter-dropdown option, so there's more than one match.
    expect(screen.getAllByText("active").length).toBeGreaterThan(0);
    expect(screen.getByText("$0.0200")).toBeInTheDocument();
  });

  it("filters the table as the user types in the search box", async () => {
    mockedUseChannels.mockReturnValue({
      data: [SAMPLE_CHANNEL, OTHER_CHANNEL],
      error: undefined,
      isLoading: false,
    } as never);
    const user = userEvent.setup();
    render(<ChannelsPage />);

    expect(screen.getByText("TechExplained Daily")).toBeInTheDocument();
    expect(screen.getByText("Cooking Corner")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText(/search channels/i), "Cooking");

    expect(screen.queryByText("TechExplained Daily")).not.toBeInTheDocument();
    expect(screen.getByText("Cooking Corner")).toBeInTheDocument();
  });

  it("filters the table by status via the status dropdown", async () => {
    mockedUseChannels.mockReturnValue({
      data: [SAMPLE_CHANNEL, OTHER_CHANNEL],
      error: undefined,
      isLoading: false,
    } as never);
    const user = userEvent.setup();
    render(<ChannelsPage />);

    await user.selectOptions(screen.getByLabelText("Filter by status"), "paused");

    expect(screen.queryByText("TechExplained Daily")).not.toBeInTheDocument();
    expect(screen.getByText("Cooking Corner")).toBeInTheDocument();
  });
});
