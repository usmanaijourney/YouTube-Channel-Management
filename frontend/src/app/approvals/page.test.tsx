import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ApprovalsPage from "./page";
import { useApprovals } from "@/lib/hooks";
import { api, ApiError } from "@/lib/api";
import type { Approval } from "@/lib/types";

vi.mock("@/lib/hooks", () => ({ useApprovals: vi.fn() }));
vi.mock("swr", () => ({ mutate: vi.fn() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ApiError: actual.ApiError, api: { decideApproval: vi.fn() } };
});

const mockedUseApprovals = vi.mocked(useApprovals);
const mockedDecide = vi.mocked(api.decideApproval);

const PENDING: Approval = {
  id: 1,
  task_id: "task_abc",
  channel_id: "channel-001",
  stage: "topic",
  status: "pending",
  payload: { title: "Why USB-C won" },
  requested_at: "2026-08-11 02:00:00",
  decided_at: null,
  decided_by: null,
  note: null,
};

/** The page calls useApprovals twice: once for "pending", once for everything. */
function mockLists(pending: Approval[], all: Approval[] = pending) {
  mockedUseApprovals.mockImplementation(((status?: string) => ({
    data: status === "pending" ? pending : all,
    error: undefined,
    isLoading: false,
  })) as never);
}

describe("ApprovalsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a pending gate with the payload the operator must judge", () => {
    mockLists([PENDING]);
    render(<ApprovalsPage />);

    expect(screen.getByText("Topic")).toBeInTheDocument();
    expect(screen.getByText(/Why USB-C won/)).toBeInTheDocument();
    expect(screen.getByText(/task_abc/)).toBeInTheDocument();
  });

  it("says nothing is blocked when there are no pending gates", () => {
    mockLists([]);
    render(<ApprovalsPage />);
    expect(screen.getByText(/No run is blocked/)).toBeInTheDocument();
  });

  it("submits an approval with the typed note", async () => {
    mockLists([PENDING]);
    mockedDecide.mockResolvedValue({ ...PENDING, status: "approved" });
    render(<ApprovalsPage />);

    await userEvent.type(screen.getByPlaceholderText(/Optional note/), "good angle");
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(mockedDecide).toHaveBeenCalledWith("task_abc", "topic", "approved", "good angle");
  });

  it("submits a rejection", async () => {
    mockLists([PENDING]);
    mockedDecide.mockResolvedValue({ ...PENDING, status: "rejected" });
    render(<ApprovalsPage />);

    await userEvent.click(screen.getByRole("button", { name: "Reject" }));
    expect(mockedDecide).toHaveBeenCalledWith("task_abc", "topic", "rejected", "");
  });

  it("surfaces a conflict when the gate was already decided elsewhere", async () => {
    mockLists([PENDING]);
    mockedDecide.mockRejectedValue(new ApiError(409, "the 'topic' gate for 'task_abc' is already approved"));
    render(<ApprovalsPage />);

    await userEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(await screen.findByText(/already approved/)).toBeInTheDocument();
  });

  it("lists decided gates separately from pending ones", () => {
    const decided: Approval = {
      ...PENDING,
      id: 2,
      task_id: "task_old",
      status: "rejected",
      decided_at: "2026-08-11 01:00:00",
      note: "off-brand",
    };
    mockLists([], [decided]);
    render(<ApprovalsPage />);

    expect(screen.getByText("task_old")).toBeInTheDocument();
    expect(screen.getByText("off-brand")).toBeInTheDocument();
  });
});
