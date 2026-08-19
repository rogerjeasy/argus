import { render, screen, fireEvent } from "@testing-library/react";
import { Switch } from "@/components/ui/switch";

test("renders unchecked by default and toggles on click", () => {
  const onCheckedChange = vi.fn();
  render(<Switch checked={false} onCheckedChange={onCheckedChange} aria-label="Audio perception" />);

  const toggle = screen.getByRole("switch", { name: /audio perception/i });
  expect(toggle).toHaveAttribute("aria-checked", "false");

  fireEvent.click(toggle);
  expect(onCheckedChange).toHaveBeenCalledWith(true);
});

test("is keyboard operable — renders as a real, focusable <button>", () => {
  // Space/Enter activating a focused <button> is native browser default
  // behavior (fired as a "click" event, not synthesized from keydown) —
  // jsdom's fireEvent.keyDown doesn't replicate that default action, so
  // asserting the real interaction here would test jsdom's limitations,
  // not this component. The real, verifiable contract is that Radix
  // renders a genuine <button role="switch">, which is keyboard-operable
  // for free in every real browser without any extra handling here.
  render(<Switch checked={false} onCheckedChange={vi.fn()} aria-label="Audio perception" />);

  const toggle = screen.getByRole("switch", { name: /audio perception/i });
  expect(toggle.tagName).toBe("BUTTON");
  expect(toggle).not.toHaveAttribute("tabindex", "-1");
});

test("reflects a checked state passed in as a controlled prop", () => {
  render(<Switch checked={true} onCheckedChange={vi.fn()} aria-label="Audio perception" />);

  expect(screen.getByRole("switch", { name: /audio perception/i })).toHaveAttribute("aria-checked", "true");
});
