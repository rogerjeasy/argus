import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/lib/auth/AuthProvider";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/app",
}));

vi.mock("@/lib/auth/AuthProvider", () => ({ useAuth: vi.fn() }));

beforeEach(() => {
  replace.mockReset();
  window.localStorage.clear();
});

test("shows a loading state while auth resolves", () => {
  vi.mocked(useAuth).mockReturnValue({ user: null, loading: true } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  expect(screen.getByText(/loading/i)).toBeInTheDocument();
  expect(screen.queryByText("child")).not.toBeInTheDocument();
});

test("redirects to / once auth resolves to signed-out", async () => {
  vi.mocked(useAuth).mockReturnValue({ user: null, loading: false } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
});

test("renders the nav and children once signed in", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { uid: "user-1" }, loading: false } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  expect(screen.getByText("child")).toBeInTheDocument();
  expect(replace).not.toHaveBeenCalled();
  // 4 nav items, each rendered as a link twice (desktop sidebar + mobile
  // bottom tabs) — role-scoped so this doesn't also match the top bar's
  // <h1>, which renders the current route's own label as plain text too.
  expect(screen.getAllByRole("link", { name: "Session" })).toHaveLength(2);
  expect(screen.getAllByRole("link", { name: "History" })).toHaveLength(2);
  expect(screen.getAllByRole("link", { name: "Settings" })).toHaveLength(2);
  expect(screen.getAllByRole("link", { name: "Contacts" })).toHaveLength(2);
});

test("marks the current route's nav link with aria-current", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { uid: "user-1" }, loading: false } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  const sessionLinks = screen.getAllByRole("link", { name: /session/i });
  for (const link of sessionLinks) {
    expect(link).toHaveAttribute("aria-current", "page");
  }
});

test("shows the current route's label in the top bar", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { uid: "user-1" }, loading: false } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  expect(screen.getByRole("heading", { name: "Session" })).toBeInTheDocument();
});

test("persists the sidebar collapse state to localStorage", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { uid: "user-1" }, loading: false } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  fireEvent.click(screen.getByRole("button", { name: /collapse/i }));
  expect(window.localStorage.getItem("argus-sidebar-collapsed")).toBe("true");
});

test("shows a sign-out control in the top bar, on every breakpoint", () => {
  vi.mocked(useAuth).mockReturnValue({ user: { uid: "user-1" }, loading: false } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  // Top bar renders identically at every breakpoint (unlike the sidebar,
  // which is hidden below md) — one control here covers desktop, tablet,
  // and mobile without a separate mobile-specific implementation.
  expect(screen.getByRole("button", { name: /sign out/i })).toBeInTheDocument();
});

test("clicking sign out calls signOutUser", () => {
  const signOutUser = vi.fn();
  vi.mocked(useAuth).mockReturnValue({ user: { uid: "user-1" }, loading: false, signOutUser } as never);
  render(
    <AppShell>
      <div>child</div>
    </AppShell>
  );
  fireEvent.click(screen.getByRole("button", { name: /sign out/i }));
  expect(signOutUser).toHaveBeenCalled();
});
