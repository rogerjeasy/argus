import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import HistoryPage from "@/app/app/history/page";

test("shows a real empty state, not fabricated history", () => {
  render(<HistoryPage />);
  expect(screen.getByText(/no sessions logged yet/i)).toBeInTheDocument();
  expect(screen.getByText(/once you start a session/i)).toBeInTheDocument();
});
