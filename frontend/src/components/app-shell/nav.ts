import { Activity, LayoutDashboard, type LucideIcon } from "lucide-react";

import type { Me, Permission } from "@/lib/api/types";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Shown only to people with this permission. The API enforces it too, this just tidies the menu. */
  needs: Permission;
}

// Pages are added here as their slice lands (see docs/CHECKLIST.md)
export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, needs: "view_dashboard" },
  { href: "/data-health", label: "Data health", icon: Activity, needs: "view_data_health" },
];

export function navFor(me: Pick<Me, "permissions">): NavItem[] {
  return NAV_ITEMS.filter((item) => me.permissions.includes(item.needs));
}

/** The first page a person may open, or null when they may open none yet. */
export function landingFor(me: Pick<Me, "permissions">): string | null {
  return navFor(me)[0]?.href ?? null;
}

export function isActive(href: string, pathname: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
