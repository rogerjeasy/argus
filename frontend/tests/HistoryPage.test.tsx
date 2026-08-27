import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import HistoryPage from "@/app/dashboard/history/page";
import { useIdToken } from "@/lib/auth/useIdToken";
import { getHistory } from "@/lib/api/history";

vi.mock("@/lib/auth/useIdToken", () => ({ useIdToken: vi.fn() }));
vi.mock("@/lib/api/history", () => ({ getHistory: vi.fn() }));

beforeEach(() => {
  vi.mocked(useIdToken).mockReturnValue("fake-token");
});

test("shows a real empty state when there are no sessions, not fabricated history", async () => {
  vi.mocked(getHistory).mockResolvedValue([]);
  render(<HistoryPage />);
  expect(await screen.findByText(/no sessions logged yet/i)).toBeInTheDocument();
});

test("renders one row per past session with its summary", async () => {
  vi.mocked(getHistory).mockResolvedValue([
    { session_id: "s1", summary: "Checked your platform at North Station.", started_at: "2026-08-27T18:00:00Z", ended_at: null, recorded_at: "2026-08-27T18:05:00Z" },
    { session_id: "s2", summary: "Read a sign for you and confirmed a refill by phone.", started_at: "2026-08-26T09:00:00Z", ended_at: null, recorded_at: "2026-08-26T09:10:00Z" },
  ]);

  render(<HistoryPage />);

  expect(await screen.findByText("Checked your platform at North Station.")).toBeInTheDocument();
  expect(screen.getByText("Read a sign for you and confirmed a refill by phone.")).toBeInTheDocument();
  expect(screen.queryByText(/no sessions logged yet/i)).not.toBeInTheDocument();
});

test("shows a retry affordance when history fails to load", async () => {
  vi.mocked(getHistory).mockRejectedValue(new Error("network down"));
  render(<HistoryPage />);
  expect(await screen.findByRole("button", { name: /try again/i })).toBeInTheDocument();
});
