import { render, screen, fireEvent } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { SessionControl } from "@/components/SessionControl";
import { useIdToken } from "@/lib/auth/useIdToken";
import { useSession } from "@/lib/session/useSession";

vi.mock("@/lib/auth/useIdToken", () => ({ useIdToken: vi.fn() }));
vi.mock("@/lib/session/useSession", () => ({ useSession: vi.fn() }));

const start = vi.fn();
const stop = vi.fn();
const resolveConfirmation = vi.fn();
const resolveFieldInput = vi.fn();

function baseSession(overrides: Partial<ReturnType<typeof useSession>> = {}) {
  return {
    status: "idle", errorMessage: null, captionText: null, captionLanguage: "en", guardrailDecision: null,
    framingText: null, confidenceLow: false, usingCachedGuidance: false, micLevel: 0, playbackLevel: 0,
    transcriptHistory: [], pendingConfirmation: null, resolveConfirmation, pendingFieldRequest: null,
    resolveFieldInput, start, stop,
    ...overrides,
  } as ReturnType<typeof useSession>;
}

beforeEach(() => {
  vi.mocked(useIdToken).mockReturnValue("fake-token");
  vi.mocked(useSession).mockReturnValue(baseSession());
  start.mockReset();
  stop.mockReset();
});

test("renders the Session Stage, status rail, and transcript feed", () => {
  render(<SessionControl />);
  expect(screen.getByText(/ready to start/i)).toBeInTheDocument();
  expect(screen.getByText(/not connected/i)).toBeInTheDocument();
  expect(screen.getByText(/will appear here/i)).toBeInTheDocument();
});

test("Start becomes Stop once connected, and calls stop()", () => {
  vi.mocked(useSession).mockReturnValue(baseSession({ status: "connected" }));
  render(<SessionControl />);

  const button = screen.getByRole("button", { name: /stop session/i });
  fireEvent.click(button);

  expect(stop).toHaveBeenCalled();
});

test("clicking Start while idle calls start()", () => {
  render(<SessionControl />);
  fireEvent.click(screen.getByRole("button", { name: /start session/i }));
  expect(start).toHaveBeenCalled();
});

test("shows the confirmation prompt when one is pending", () => {
  vi.mocked(useSession).mockReturnValue(
    baseSession({ pendingConfirmation: { stepId: "step-1", text: "Call the pharmacy?" } })
  );
  render(<SessionControl />);
  expect(screen.getByText("Call the pharmacy?")).toBeInTheDocument();
});

test("shows the field prompt when one is pending", () => {
  vi.mocked(useSession).mockReturnValue(
    baseSession({ pendingFieldRequest: { stepId: "step-1", text: "What's your policy number?", label: "Policy number" } })
  );
  render(<SessionControl />);
  expect(screen.getByText("What's your policy number?")).toBeInTheDocument();
});

test("shows the error message region when an error is present", () => {
  vi.mocked(useSession).mockReturnValue(baseSession({ status: "error", errorMessage: "The microphone could not be started." }));
  render(<SessionControl />);
  expect(screen.getByText("The microphone could not be started.")).toBeInTheDocument();
});
