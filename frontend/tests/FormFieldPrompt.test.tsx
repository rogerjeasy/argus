import { render, screen, fireEvent } from "@testing-library/react";
import { FormFieldPrompt } from "@/components/FormFieldPrompt";

test("renders the question and label, and submits the typed value", () => {
  const onResolve = vi.fn();
  render(
    <FormFieldPrompt
      stepId="step-1"
      text="I've filled in what I can, but I need one more thing — what's your policy number?"
      label="Policy number"
      onResolve={onResolve}
    />
  );

  expect(screen.getByText(/what's your policy number/i)).toBeInTheDocument();

  const input = screen.getByLabelText("Policy number");
  fireEvent.change(input, { target: { value: "POL-12345" } });
  fireEvent.click(screen.getByRole("button", { name: /submit/i }));

  expect(onResolve).toHaveBeenCalledWith("POL-12345");
});

test("submit is disabled until a value is entered", () => {
  render(<FormFieldPrompt stepId="step-1" text="What's your policy number?" label="Policy number" onResolve={vi.fn()} />);

  expect(screen.getByRole("button", { name: /submit/i })).toBeDisabled();
});
