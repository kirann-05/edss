"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

// The control that opened the drawer. Closing it hands focus back there (keyboard users would
// otherwise be dropped at the top of the page).
let opener: HTMLElement | null = null;

export function restoreDrilldownFocus(event: Event) {
  if (opener && document.contains(opener)) {
    event.preventDefault();
    opener.focus();
  }
  opener = null;
}

/**
 * Which KPI's drill-down is open, kept in the URL (?kpi=PL_PCT&dept=CIVIL) so it can be linked
 * and survives a reload. `dept` highlights one department inside the drill-down.
 */
export function useDrilldownParam() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const kpi = params.get("kpi");
  const dept = params.get("dept");

  const go = useCallback(
    (update: (query: URLSearchParams) => void) => {
      const query = new URLSearchParams(params.toString());
      update(query);
      const text = query.toString();
      router.replace(text ? `${pathname}?${text}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );

  const open = useCallback(
    (key: string, department?: string) => {
      if (document.activeElement instanceof HTMLElement) opener = document.activeElement;
      go((query) => {
        query.set("kpi", key);
        if (department) query.set("dept", department);
        else query.delete("dept");
      });
    },
    [go],
  );

  const close = useCallback(
    () =>
      go((query) => {
        query.delete("kpi");
        query.delete("dept");
      }),
    [go],
  );

  return { kpi, dept, open, close };
}
