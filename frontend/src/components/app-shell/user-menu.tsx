"use client";

import { ChevronDown, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLogout } from "@/lib/api/queries";
import type { Me } from "@/lib/api/types";
import { ROLE_LABEL } from "@/lib/roles";

const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter((part) => /^[A-Za-z]/.test(part) && !part.endsWith("."))
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");

export function UserMenu({ me }: { me: Me }) {
  const router = useRouter();
  const logout = useLogout();
  const { user } = me;
  const where = user.dept_code ? ` (${user.dept_code})` : "";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" className="h-11 gap-3 px-3">
          <span
            aria-hidden
            className="grid size-7 place-items-center rounded-full bg-primary text-sm font-medium text-primary-foreground"
          >
            {initials(user.name)}
          </span>
          <span className="hidden flex-col items-start leading-tight sm:flex">
            <span className="text-sm font-medium">{user.name}</span>
            <span className="text-xs text-muted-foreground">
              {ROLE_LABEL[user.role]}
              {where}
            </span>
          </span>
          <ChevronDown aria-hidden className="size-4 text-muted-foreground" />
          <span className="sr-only">Account menu for {user.name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5 font-normal">
          <span className="text-base font-medium">{user.name}</span>
          <span className="text-sm text-muted-foreground">
            {ROLE_LABEL[user.role]}
            {where}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-base"
          onSelect={() => logout.mutate(undefined, { onSuccess: () => router.replace("/login") })}
        >
          <LogOut aria-hidden /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
