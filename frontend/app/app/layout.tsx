import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Your session — Argus",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return children;
}
