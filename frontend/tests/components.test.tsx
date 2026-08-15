import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Circle } from "lucide-react";
import { Button } from "../components/ui/button";
import { StatusBadge } from "../components/ui/status-badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Alert } from "../components/ui/alert";

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

describe("Input", () => {
  it("renders as a text input", () => {
    render(<Input aria-label="Email" defaultValue="" />);
    expect(screen.getByRole("textbox", { name: "Email" })).toBeInTheDocument();
  });

  it("carries aria-invalid through for destructive-border styling", () => {
    render(<Input aria-label="Email" aria-invalid="true" />);
    expect(screen.getByRole("textbox", { name: "Email" })).toHaveAttribute("aria-invalid", "true");
  });
});

describe("Label", () => {
  it("associates with its control via htmlFor", () => {
    render(
      <>
        <Label htmlFor="email-field">Email</Label>
        <input id="email-field" />
      </>
    );
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
  });
});

describe("Alert", () => {
  it("renders as an alert role with destructive styling", () => {
    render(<Alert variant="destructive">Something went wrong</Alert>);
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toBe("Something went wrong");
    expect(alert.className).toContain("text-destructive");
  });
});
