import { History, Mic, Phone, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface AppNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const APP_NAV_ITEMS: AppNavItem[] = [
  { href: "/app", label: "Session", icon: Mic },
  { href: "/app/history", label: "History", icon: History },
  { href: "/app/settings", label: "Settings", icon: Settings },
  { href: "/app/contacts", label: "Contacts", icon: Phone },
];
