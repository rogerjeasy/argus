import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { SessionStage } from "@/components/SessionStage";

const BASE = { status: "idle" as const, guardrailDecision: null, usingCachedGuidance: false, micLevel: 0, playbackLevel: 0 };

test("shows a ready-to-start label when idle", () => {
  render(<SessionStage {...BASE} />);
  expect(screen.getByText(/ready to start/i)).toBeInTheDocument();
});

test("shows a listening label with a Mic icon once connected", () => {
  render(<SessionStage {...BASE} status="connected" />);
  const status = screen.getByRole("status");
  expect(status).toHaveTextContent(/listening/i);
  expect(status.querySelector("svg")).not.toBeNull();
});

test("shows a speaking label once playback is nonzero", () => {
  render(<SessionStage {...BASE} status="connected" playbackLevel={0.5} />);
  expect(screen.getByRole("status")).toHaveTextContent(/argus is speaking/i);
});

test("shows a guardrail-pending label when a confirmation is required", () => {
  render(<SessionStage {...BASE} status="connected" guardrailDecision="requires_confirmation" />);
  expect(screen.getByRole("status")).toHaveTextContent(/needs your input/i);
});

test("shows a degraded label while using cached guidance", () => {
  render(<SessionStage {...BASE} status="connected" usingCachedGuidance />);
  expect(screen.getByRole("status")).toHaveTextContent(/reduced connectivity/i);
});

test("shows an error label on session error", () => {
  render(<SessionStage {...BASE} status="error" />);
  expect(screen.getByRole("status")).toHaveTextContent(/something went wrong/i);
});

test("scales up with a higher mic level while listening", () => {
  render(<SessionStage {...BASE} status="connected" micLevel={0.8} />);
  // The transform lives on the inner circle, not the outer role="status"
  // wrapper (which also contains the caption paragraph beneath it).
  const orb = screen.getByRole("status").firstElementChild as HTMLElement;
  expect(orb.style.transform).toBe("scale(1.12)");
});
