import { render, screen, fireEvent } from "@testing-library/react";
import { ConfirmationPrompt } from "@/components/ConfirmationPrompt";

test("renders the proposed action and resolves accept/decline distinctly", () => {
  const onResolve = vi.fn();
  render(<ConfirmationPrompt stepId="step-1" text="Call Example Pharmacy to confirm your refill?" onResolve={onResolve} />);

  expect(screen.getByText("Call Example Pharmacy to confirm your refill?")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: /accept/i }));
  expect(onResolve).toHaveBeenCalledWith(true);

  fireEvent.click(screen.getByRole("button", { name: /decline/i }));
  expect(onResolve).toHaveBeenCalledWith(false);
});

test("the accept button is never styled destructive, regardless of stakes", () => {
  render(<ConfirmationPrompt stepId="step-1" text="Any proposed action" onResolve={vi.fn()} />);

  const accept = screen.getByRole("button", { name: /accept/i });
  expect(accept.className).not.toMatch(/destructive/);
});
