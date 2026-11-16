"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe } from "@/lib/api/queries";

import { ModeBadges } from "./mode-badges";
import { NavList } from "./nav-list";
import { UserMenu } from "./user-menu";

function Brand() {
  return (
    <div className="flex flex-col leading-tight">
      <span className="text-xl font-semibold tracking-tight">EDSS</span>
      <span className="text-sm text-muted-foreground">Executive Decision Support</span>
    </div>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const me = useMe();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const main = useRef<HTMLElement>(null);
  const firstRender = useRef(true);

  // After moving to another page, put focus on the content so a keyboard or screen reader user
  // starts reading the new page instead of being left in the old navigation.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    main.current?.focus();
  }, [pathname]);

  if (me.isPending) {
    return (
      <div className="flex min-h-dvh">
        <div className="hidden w-60 border-r bg-sidebar p-4 lg:block xl:w-64">
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="flex-1 p-8">
          <Skeleton className="h-10 w-64" />
        </div>
      </div>
    );
  }

  if (me.isError || !me.data) {
    // a 401 is already on its way to the sign-in page, anything else is a real fault
    return (
      <main className="grid min-h-dvh place-items-center p-8">
        <div className="flex max-w-md flex-col items-start gap-4">
          <h1 className="text-2xl font-semibold">We could not load your account</h1>
          <p className="text-base text-muted-foreground">
            The server did not answer. Check that the API is running, then try again.
          </p>
          <Button onClick={() => me.refetch()}>Try again</Button>
        </div>
      </main>
    );
  }

  return (
    <div className="flex min-h-dvh">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:text-base focus:ring-2 focus:ring-ring"
      >
        Skip to main content
      </a>

      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 xl:w-64 flex-col gap-6 border-r bg-sidebar p-4 lg:flex print:hidden">
        <Brand />
        <NavList me={me.data} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex min-h-16 flex-wrap items-center justify-between gap-3 border-b bg-background/95 px-4 py-2 backdrop-blur lg:px-8 print:hidden">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              className="lg:hidden"
              onClick={() => setMenuOpen(true)}
              aria-label="Open navigation"
            >
              <Menu aria-hidden />
            </Button>
            <div className="lg:hidden">
              <Brand />
            </div>
            <ModeBadges />
          </div>
          <UserMenu me={me.data} />
        </header>

        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
          <SheetContent side="left" className="w-72 bg-sidebar p-4 sm:max-w-72">
            <SheetHeader className="p-0">
              <SheetTitle>
                <Brand />
              </SheetTitle>
              <SheetDescription className="sr-only">Main navigation</SheetDescription>
            </SheetHeader>
            <NavList me={me.data} onNavigate={() => setMenuOpen(false)} />
          </SheetContent>
        </Sheet>

        <main id="main" ref={main} tabIndex={-1} className="flex-1 px-4 py-6 outline-none lg:px-8 print:p-0">
          <div className="mx-auto flex max-w-[1400px] flex-col gap-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
