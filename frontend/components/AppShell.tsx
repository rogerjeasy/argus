"use client";

import Link from "next/link";
import { LogOut } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/AuthProvider";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { APP_NAV_ITEMS } from "@/lib/app-nav";
import { cn } from "@/lib/utils";

const SIDEBAR_COLLAPSED_KEY = "argus-sidebar-collapsed";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, signOutUser } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/");
    }
  }, [loading, user, router]);

  useEffect(() => {
    setCollapsed(window.localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "true");
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(next));
      return next;
    });
  };

  if (loading || !user) {
    return <main className="flex min-h-screen items-center justify-center text-muted-foreground">Loading…</main>;
  }

  const currentLabel = APP_NAV_ITEMS.find((item) => item.href === pathname)?.label ?? "Argus";

  return (
    <div className="flex min-h-screen bg-background">
      <aside
        className={cn(
          "sticky top-0 hidden h-screen flex-col gap-1 border-e border-border bg-card p-3 md:flex md:w-[72px]",
          !collapsed && "lg:w-64 lg:p-4"
        )}
      >
        <div className="mb-4 flex items-center justify-center px-1 lg:justify-start">
          <span className="text-lg font-semibold tracking-tight text-foreground">{collapsed ? "A" : "Argus"}</span>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {APP_NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                title={item.label}
                className={cn(
                  "flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  active ? "bg-primary/15 text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  collapsed && "justify-center"
                )}
              >
                <Icon className="h-5 w-5 shrink-0" aria-hidden />
                {!collapsed ? <span className="hidden lg:inline">{item.label}</span> : null}
              </Link>
            );
          })}
        </nav>
        <button
          type="button"
          onClick={toggleCollapsed}
          className="hidden min-h-11 items-center justify-center rounded-xl text-sm text-muted-foreground hover:bg-secondary lg:flex"
        >
          {collapsed ? "Expand" : "Collapse"}
        </button>
      </aside>

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-border px-4 sm:px-6">
          <h1 className="text-lg font-semibold tracking-tight text-foreground">{currentLabel}</h1>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            {/* Lives in the top bar, not the sidebar — the sidebar is
                hidden below md, so this is the one element that renders
                identically on every breakpoint. */}
            <Button variant="outline" size="icon" onClick={() => void signOutUser()} aria-label="Sign out">
              <LogOut className="h-5 w-5" aria-hidden />
            </Button>
          </div>
        </header>
        <main className="flex-1 p-4 pb-24 sm:p-6 md:pb-6">{children}</main>
      </div>

      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-40 flex border-t border-border bg-card md:hidden"
        style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      >
        {APP_NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-h-11 flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs font-medium",
                active ? "text-primary" : "text-muted-foreground"
              )}
            >
              <Icon className="h-5 w-5" aria-hidden />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
