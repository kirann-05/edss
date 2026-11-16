"use client";

import { cn } from "cn";
import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Me } from "@/lib/api/types";

import { isActive, navFor } from "./nav";

export function NavList({ me, onNavigate }: { me: Me; onNavigate?: () => void }) {
  const pathname = usePathname();
  const items = navFor(me);
  return (
    <nav aria-label="Main">
      <ul className="flex flex-col gap-1">
        {items.map(({ href, label, icon: Icon }) => {
          const active = isActive(href, pathname);
          return (
            <li key={href}>
              <Link
                href={href}
                onClick={onNavigate}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex h-11 items-center gap-3 rounded-lg px-3 text-base text-sidebar-foreground transition-colors hover:bg-sidebar-accent",
                  active && "bg-sidebar-accent font-semibold",
                )}
              >
                {active && (
                  <span aria-hidden className="absolute inset-y-2 left-0 w-1 rounded-full bg-sidebar-primary" />
                )}
                <Icon aria-hidden className="size-5 shrink-0" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
