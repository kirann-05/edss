"use client";

import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError } from "@/lib/api/client";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  const [client] = useState(() => {
    // Session expired or missing: send the person to sign in, remembering where they were.
    // The login form itself is exempt, a 401 there just means wrong credentials.
    const onError = (error: unknown) => {
      if (!(error instanceof ApiError) || error.status !== 401) return;
      const { pathname, search } = window.location;
      if (pathname === "/login") return;
      router.replace(`/login?next=${encodeURIComponent(pathname + search)}`);
    };

    return new QueryClient({
      queryCache: new QueryCache({ onError }),
      mutationCache: new MutationCache({ onError }),
      defaultOptions: {
        queries: {
          // Executive data changes on ingest cadence, not by the second
          staleTime: 30_000,
          refetchOnWindowFocus: false,
          retry: (failureCount, error) => {
            // Never retry a refusal. Only retry transient failures.
            if (error instanceof ApiError && error.status < 500) return false;
            return failureCount < 2;
          },
        },
      },
    });
  });

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
