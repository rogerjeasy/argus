import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import ContactsPage from "@/app/dashboard/contacts/page";
import { useIdToken } from "@/lib/auth/useIdToken";
import { getTrustedContact, updateTrustedContact } from "@/lib/api/trustedContact";

vi.mock("@/lib/auth/useIdToken", () => ({ useIdToken: vi.fn() }));
vi.mock("@/lib/api/trustedContact", () => ({
  getTrustedContact: vi.fn(),
  updateTrustedContact: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(useIdToken).mockReturnValue("fake-token");
});

test("shows a loading skeleton before the contact resolves", () => {
  vi.mocked(getTrustedContact).mockReturnValue(new Promise(() => {}));
  render(<ContactsPage />);
  expect(screen.queryByLabelText("Trusted contact name")).not.toBeInTheDocument();
});

test("shows a real empty state with no fabricated contact", async () => {
  vi.mocked(getTrustedContact).mockResolvedValue(null);
  render(<ContactsPage />);
  expect(await screen.findByText(/no trusted contact set yet/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /add contact/i })).toBeInTheDocument();
});

test("loads and displays an existing trusted contact", async () => {
  vi.mocked(getTrustedContact).mockResolvedValue({ name: "Jamie", phone_number: "+15559990000" });
  render(<ContactsPage />);
  expect(await screen.findByDisplayValue("Jamie")).toBeInTheDocument();
  expect(screen.getByDisplayValue("+15559990000")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
});

test("shows a calm retry affordance when the contact fails to load", async () => {
  vi.mocked(getTrustedContact).mockRejectedValue(new Error("network down"));
  render(<ContactsPage />);
  expect(await screen.findByRole("button", { name: /try again/i })).toBeInTheDocument();
});

test("saving a new contact calls updateTrustedContact with both fields, not optimistically", async () => {
  vi.mocked(getTrustedContact).mockResolvedValue(null);
  vi.mocked(updateTrustedContact).mockResolvedValue({ name: "Jamie", phone_number: "+15559990000" });

  render(<ContactsPage />);
  fireEvent.change(await screen.findByLabelText("Trusted contact name"), { target: { value: "Jamie" } });
  fireEvent.change(screen.getByLabelText("Trusted contact phone number"), { target: { value: "+15559990000" } });
  fireEvent.click(screen.getByRole("button", { name: /add contact/i }));

  await waitFor(() =>
    expect(vi.mocked(updateTrustedContact)).toHaveBeenCalledWith("fake-token", { name: "Jamie", phone_number: "+15559990000" })
  );
});
