import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SignInForm } from "../components/auth/SignInForm";
import { useAuth } from "../lib/auth/AuthProvider";

vi.mock("../lib/auth/AuthProvider", () => ({
  useAuth: vi.fn(),
}));

function fillAndSubmit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText("Email"), { target: { value: email } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("SignInForm", () => {
  it("shows a validation message and does not submit for an invalid email", async () => {
    const signInWithEmail = vi.fn();
    vi.mocked(useAuth).mockReturnValue({ signInWithEmail } as never);
    const onSuccess = vi.fn();

    render(<SignInForm onSuccess={onSuccess} />);
    fillAndSubmit("not-an-email", "password123");

    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(signInWithEmail).not.toHaveBeenCalled();
  });

  it("calls signInWithEmail and onSuccess for a valid submission", async () => {
    const signInWithEmail = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useAuth).mockReturnValue({ signInWithEmail } as never);
    const onSuccess = vi.fn();

    render(<SignInForm onSuccess={onSuccess} />);
    fillAndSubmit("a@example.com", "password123");

    await waitFor(() => expect(signInWithEmail).toHaveBeenCalledWith("a@example.com", "password123"));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });

  it("renders the mapped error message when sign-in rejects", async () => {
    const signInWithEmail = vi.fn().mockRejectedValue({ code: "auth/wrong-password" });
    vi.mocked(useAuth).mockReturnValue({ signInWithEmail } as never);

    render(<SignInForm onSuccess={vi.fn()} />);
    fillAndSubmit("a@example.com", "wrong-password");

    expect(await screen.findByRole("alert")).toHaveTextContent("doesn't look right");
  });
});
