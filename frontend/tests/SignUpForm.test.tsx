import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SignUpForm } from "../components/auth/SignUpForm";
import { useAuth } from "../lib/auth/AuthProvider";

vi.mock("../lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

function fillForm({
  name = "Ada Lovelace",
  email = "a@example.com",
  password = "password123",
  confirmPassword = password,
}: Partial<Record<"name" | "email" | "password" | "confirmPassword", string>> = {}) {
  fireEvent.change(screen.getByLabelText("Full name"), { target: { value: name } });
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: confirmPassword } });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
}

describe("SignUpForm", () => {
  it("rejects a password that doesn't meet the strength rule", async () => {
    const signUpWithEmail = vi.fn();
    vi.mocked(useAuth).mockReturnValue({ signUpWithEmail } as never);

    render(<SignUpForm onSuccess={vi.fn()} />);
    fillForm({ password: "onlyletters", confirmPassword: "onlyletters" });

    expect(await screen.findByText("Include at least one number.")).toBeInTheDocument();
    expect(signUpWithEmail).not.toHaveBeenCalled();
  });

  it("rejects a confirm-password mismatch", async () => {
    const signUpWithEmail = vi.fn();
    vi.mocked(useAuth).mockReturnValue({ signUpWithEmail } as never);

    render(<SignUpForm onSuccess={vi.fn()} />);
    fillForm({ confirmPassword: "different123" });

    expect(await screen.findByText("Passwords don't match.")).toBeInTheDocument();
    expect(signUpWithEmail).not.toHaveBeenCalled();
  });

  it("calls signUpWithEmail and onSuccess for a valid submission", async () => {
    const signUpWithEmail = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ signUpWithEmail } as never);
    const onSuccess = vi.fn();

    render(<SignUpForm onSuccess={onSuccess} />);
    fillForm();

    await waitFor(() =>
      expect(signUpWithEmail).toHaveBeenCalledWith("a@example.com", "password123", "Ada Lovelace")
    );
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it("renders the mapped error message when sign-up rejects", async () => {
    const signUpWithEmail = vi.fn().mockRejectedValue({ code: "auth/email-already-in-use" });
    vi.mocked(useAuth).mockReturnValue({ signUpWithEmail } as never);

    render(<SignUpForm onSuccess={vi.fn()} />);
    fillForm();

    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
  });
});
