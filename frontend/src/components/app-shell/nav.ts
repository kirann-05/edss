import {
  Activity,
  ClipboardCheck,
  FilePlus2,
  FileText,
  LayoutDashboard,
  ScrollText,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { Me, Permission } from "@/lib/api/types";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  /** Shown to people with any of these permissions. The API enforces them too, this just tidies the menu. */
  needs: Permission[];
}

// The order is also the landing order: a person starts on the first page they may open
export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, needs: ["view_dashboard"] },
  { href: "/runs", label: "New brief", icon: FilePlus2, needs: ["start_run"] },
  { href: "/review", label: "Review queue", icon: ClipboardCheck, needs: ["review"] },
  { href: "/reports", label: "Reports", icon: FileText, needs: ["view_reports"] },
  { href: "/data-health", label: "Data health", icon: Activity, needs: ["view_data_health"] },
  { href: "/audit", label: "Audit", icon: ScrollText, needs: ["view_audit"] },
  { href: "/admin", label: "Admin", icon: UsersRound, needs: ["manage_users", "manage_scope"] },
];

export function navFor(me: Pick<Me, "permissions">): NavItem[] {
  return NAV_ITEMS.filter((item) => item.needs.some((p) => me.permissions.includes(p)));
}

/** The first page a person may open, or null when they may open none. */
export function landingFor(me: Pick<Me, "permissions">): string | null {
  return navFor(me)[0]?.href ?? null;
}

export function isActive(href: string, pathname: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
