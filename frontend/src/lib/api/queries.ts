"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  DataHealth,
  DemoUser,
  Domain,
  DomainView,
  KpiDrilldown,
  KpiList,
  Me,
  SystemStatus,
} from "./types";

const withPeriod = (path: string, period: string | undefined) =>
  period ? `${path}?period=${encodeURIComponent(period)}` : path;

export const keys = {
  me: ["me"] as const,
  status: ["system", "status"] as const,
  demoUsers: ["auth", "demo-users"] as const,
  kpis: (period?: string) => ["kpis", period ?? "current"] as const,
  kpi: (key: string, period?: string) => ["kpi", key, period ?? "current"] as const,
  domain: (domain: Domain, period?: string) => ["domain", domain, period ?? "current"] as const,
  health: (period?: string) => ["data-health", period ?? "current"] as const,
};

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: () => api.get<Me>("/auth/me"), staleTime: 5 * 60_000 });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: keys.status,
    queryFn: () => api.get<SystemStatus>("/system/status"),
    staleTime: 5 * 60_000,
  });
}

/** Demo sign-in exists only in synthetic mode with the flag on. A 404 just means "not offered". */
export function useDemoUsers() {
  return useQuery({
    queryKey: keys.demoUsers,
    queryFn: () => api.get<DemoUser[]>("/auth/demo-users"),
    retry: false,
    staleTime: Infinity,
  });
}

export function useKpis(period?: string, enabled = true) {
  return useQuery({
    queryKey: keys.kpis(period),
    enabled,
    queryFn: () => api.get<KpiList>(withPeriod("/kpis", period)),
    placeholderData: (previous) => previous, // keep the old render while a new period loads
  });
}

export function useKpiDrilldown(key: string | null, period?: string) {
  return useQuery({
    queryKey: keys.kpi(key ?? "", period),
    queryFn: () => api.get<KpiDrilldown>(withPeriod(`/kpis/${encodeURIComponent(key ?? "")}`, period)),
    enabled: key !== null,
  });
}

export function useDomainView(domain: Domain, period?: string) {
  return useQuery({
    queryKey: keys.domain(domain, period),
    queryFn: () => api.get<DomainView>(withPeriod(`/domains/${domain}`, period)),
    placeholderData: (previous) => previous,
  });
}

export function useDataHealth(period?: string, enabled = true) {
  return useQuery({
    queryKey: keys.health(period),
    enabled,
    queryFn: () => api.get<DataHealth>(withPeriod("/data-health", period)),
    placeholderData: (previous) => previous,
  });
}

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { email: string; password: string }) => api.post<Me>("/auth/login", body),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useDemoLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (email: string) => api.post<Me>("/auth/demo-login", { email }),
    onSuccess: (me) => client.setQueryData(keys.me, me),
  });
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<void>("/auth/logout"),
    // a different person may sign in next, so nothing from this session may survive
    onSuccess: () => client.clear(),
  });
}
