"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

import { useSystemStatus } from "@/lib/api/queries";

/**
 * The period being looked at, kept in the URL (?period=2024-25) so a link shares it and Back
 * behaves. `period` is undefined for the current period, which the API assumes when none is sent.
 * The API checks the value, so an unknown period comes back as a 404 and the page says so.
 */
export function usePeriod() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { data } = useSystemStatus();

  const period = params.get("period") ?? undefined;
  const current = data?.current_period;

  const setPeriod = useCallback(
    (next: string) => {
      const query = new URLSearchParams(params.toString());
      if (next === current) query.delete("period");
      else query.set("period", next);
      const text = query.toString();
      router.replace(text ? `${pathname}?${text}` : pathname, { scroll: false });
    },
    [params, current, pathname, router],
  );

  return { period, current, periods: data?.periods ?? [], setPeriod };
}
