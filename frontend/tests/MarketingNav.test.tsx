import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MarketingNav } from "../components/marketing/MarketingNav";
import { AuthProvider } from "../lib/auth/AuthProvider";

vi.mock("../lib/auth/firebase", () => ({
  firebaseAuth: {},
}));

let authCallback: ((user: unknown) => void) | null = null;
const signInWithPopupMock = vi.fn();

vi.mock("firebase/auth", () => ({
  onAuthStateChanged: (_auth: unknown, callback: (user: unknown) => void) => {
    authCallback = callback;
    return () => {};
  },
  signInWithPopup: (...args: unknown[]) => signInWithPopupMock(...args),
  signOut: vi.fn(),
  GoogleAuthProvider: class {},
}));

function renderNav() {
  render(
    <AuthProvider>
      <MarketingNav />
    </AuthProvider>
  );
}

describe("MarketingNav", () => {
  beforeEach(() => {
    authCallback = null;
    signInWithPopupMock.mockReset();
  });

  it("triggers Google sign-in when a logged-out visitor clicks the CTA", async () => {
    renderNav();
    authCallback?.(null);
    const ctas = await waitFor(() => screen.getAllByRole("button", { name: "Sign in" }));

    fireEvent.click(ctas[0]);
    expect(signInWithPopupMock).toHaveBeenCalled();
  });

  it("links a signed-in visitor to /app instead of prompting sign-in", async () => {
    renderNav();
    authCallback?.({ uid: "user-1" });

    const ctas = await screen.findAllByRole("link", { name: "Open Argus" });
    expect(ctas[0]).toHaveAttribute("href", "/app");
  });

  it("opens mobile Sheet menu and triggers sign-in from mobile CTA when logged out", async () => {
    renderNav();
    authCallback?.(null);

    // Click the hamburger menu to open the Sheet
    const menuButton = screen.getByRole("button", { name: "Open menu" });
    fireEvent.click(menuButton);

    // Wait for the Sheet to open and render its content
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toBeInTheDocument();

    // Find and click the mobile CTA within the open Sheet
    const mobileCtasInDialog = within(dialog).getAllByRole("button", { name: "Sign in" });
    expect(mobileCtasInDialog.length).toBeGreaterThan(0);
    fireEvent.click(mobileCtasInDialog[0]);

    expect(signInWithPopupMock).toHaveBeenCalled();
  });

  it("renders mobile nav links in Sheet with correct hrefs and closes on navigation", async () => {
    renderNav();
    authCallback?.(null);

    // Open the Sheet
    const menuButton = screen.getByRole("button", { name: "Open menu" });
    fireEvent.click(menuButton);

    // Wait for the Sheet to open
    const dialog = await screen.findByRole("dialog");

    // Verify mobile nav link exists with correct href
    const mobileNavLink = within(dialog).getByRole("link", { name: "How it works" });
    expect(mobileNavLink).toHaveAttribute("href", "#how-it-works");

    // Verify all other nav links are present
    expect(within(dialog).getByRole("link", { name: "Domains" })).toHaveAttribute("href", "#domains");
    expect(within(dialog).getByRole("link", { name: "Multimodal" })).toHaveAttribute("href", "#multimodal");
    expect(within(dialog).getByRole("link", { name: "Architecture" })).toHaveAttribute("href", "#architecture");
    expect(within(dialog).getByRole("link", { name: "Trust" })).toHaveAttribute("href", "#trust");
  });

  it("displays signed-in mobile CTA link in Sheet", async () => {
    renderNav();
    authCallback?.({ uid: "user-1" });

    // Open the Sheet
    const menuButton = screen.getByRole("button", { name: "Open menu" });
    fireEvent.click(menuButton);

    // Wait for the Sheet to open
    const dialog = await screen.findByRole("dialog");

    // Find the mobile CTA link within the dialog
    const mobileCta = within(dialog).getByRole("link", { name: "Open Argus" });
    expect(mobileCta).toHaveAttribute("href", "/app");
  });
});
