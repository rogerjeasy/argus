import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Circle } from "lucide-react";
import { Button } from "../components/ui/button";
import { StatusBadge } from "../components/ui/status-badge";

describe("Button", () => {
  it("renders as a button with the default variant classes", () => {
    render(<Button>Start</Button>);
    const button = screen.getByRole("button", { name: "Start" });
    expect(button.className).toContain("bg-primary");
  });

  it("applies the requested variant and size", () => {
    render(
      <Button variant="destructive" size="sm">
        Stop
      </Button>
    );
    const button = screen.getByRole("button", { name: "Stop" });
    expect(button.className).toContain("bg-destructive");
    expect(button.className).toContain("h-10");
  });
});

describe("StatusBadge", () => {
  it("always renders an icon alongside the text label — never color alone", () => {
    render(
      <StatusBadge icon={Circle} tone="success">
        Connected
      </StatusBadge>
    );
    const badge = screen.getByRole("status");
    expect(badge.textContent).toContain("Connected");
    expect(badge.querySelector("svg")).not.toBeNull();
  });
});
