import { render, screen } from "@testing-library/react";
import { Wifi } from "lucide-react";
import { expect, test } from "vitest";
import { StatusCard } from "@/components/ui/status-card";

test("always renders an icon alongside the text label — never color alone", () => {
  render(<StatusCard icon={Wifi} tone="success" label="Connected" />);
  const card = screen.getByRole("status");
  expect(card.textContent).toContain("Connected");
  expect(card.querySelector("svg")).not.toBeNull();
});

test("renders optional detail text", () => {
  render(<StatusCard icon={Wifi} tone="warning" label="Reconnecting…" detail="Attempt 2 of 5" />);
  expect(screen.getByText("Attempt 2 of 5")).toBeInTheDocument();
});
