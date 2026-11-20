"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, retryWhileStarting, startingDelay } from "./client";
import type {
  AdminOptions,
  AdminUser,
  AuditPage,
  AuditVerification,
  Brief,
  BriefStatus,
  BriefSummary,
  CreateUser,
  DataHealth,
  DemoUser,
  Decision,
  DecisionResult,
  Diff,
  Domain,
  DomainView,
  EditRequest,
  EvidenceRow,
  FactOut,
  KpiDrilldown,
  KpiList,
  Me,
  PlanCatalogue,
  PlanPatch,
  PriorMatch,
  RefreshResult,
  Run,
  RunRevision,
  RunTrace,
  ScopeGrant,
  SystemStatus,
  UpdateUser,
  ValidationReport,
  Version,
  VersionDetail,
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
  catalogue: ["plan-catalogue"] as const,
  runs: ["runs"] as const,
  run: (id: string) => ["run", id] as const,
  trace: (id: string) => ["run", id, "trace"] as const,
  briefs: (status?: BriefStatus) => ["briefs", status ?? "all"] as const,
  brief: (id: string) => ["brief", id] as const,
  evidence: (id: string) => ["brief", id, "evidence"] as const,
  fact: (id: number) => ["fact", id] as const,
  prior: (id: string) => ["brief", id, "prior"] as const,
  currentReport: ["reports", "current"] as const,
  versions: ["reports", "versions"] as const,
  version: (n: number) => ["reports", "version", n] as const,
  diff: (from: number, to: number) => ["reports", "diff", from, to] as const,
  audit: (query: string) => ["audit", query] as const,
  auditVerify: ["audit", "verify"] as const,
};

export function useMe() {
  return useQuery({ queryKey: keys.me, queryFn: () => api.get<Me>("/auth/me"), staleTime: 5 * 60_000 });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: keys.status,
    queryFn: () => api.get<SystemStatus>("/system/status"),
    // the model server can stop or start while the page is open, so this is checked now and then
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

/** Demo sign-in exists only in synthetic mode with the flag on. A 404 just means "not offered". */
export function useDemoUsers() {
  return useQuery({
    queryKey: keys.demoUsers,
    queryFn: () => api.get<DemoUser[]>("/auth/demo-users"),
    // a 404 means demo sign-in is off; no answer means the API is still starting, so ask again
    retry: retryWhileStarting,
    retryDelay: startingDelay,
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

// --- runs ------------------------------------------------------------------------------------

export function usePlanCatalogue() {
  return useQuery({
    queryKey: keys.catalogue,
    queryFn: () => api.get<PlanCatalogue>("/plan-catalogue"),
    staleTime: 5 * 60_000,
  });
}

export function useRuns() {
  return useQuery({ queryKey: keys.runs, queryFn: () => api.get<Run[]>("/runs") });
}

/** A run. While the graph is working the record is also polled, so a dropped event stream never strands the page. */
export function useRun(id: string) {
  return useQuery({
    queryKey: keys.run(id),
    queryFn: () => api.get<Run>(`/runs/${encodeURIComponent(id)}`),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2000 : false),
    staleTime: 0,
  });
}

const runPath = (id: string, tail = "") => `/runs/${encodeURIComponent(id)}${tail}`;

/** Every run action returns the whole run, so one handler keeps the cache honest. */
function useRunMutation<V>(call: (variables: V) => Promise<Run>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: call,
    onSuccess: (run) => {
      client.setQueryData(keys.run(run.id), run);
      void client.invalidateQueries({ queryKey: keys.runs });
      void client.invalidateQueries({ queryKey: keys.briefs() });
    },
  });
}

export function useCreateRun() {
  return useRunMutation<string>((request) => api.post<Run>("/runs", { request }));
}

export function useAnswerRun(id: string) {
  return useRunMutation<{ question_id: string; answer: string }[]>((answers) =>
    api.post<Run>(runPath(id, "/answers"), { answers }),
  );
}

export function useSkipQuestions(id: string) {
  return useRunMutation<void>(() => api.post<Run>(runPath(id, "/skip-questions")));
}

export function useEditPlan(id: string) {
  return useRunMutation<PlanPatch>((patch) => api.put<Run>(runPath(id, "/plan"), patch));
}

export function useRevisePlan(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (feedback: string) =>
      api.post<RunRevision>(runPath(id, "/plan/revise"), { feedback }),
    onSuccess: (revision) => client.setQueryData(keys.run(id), revision.run),
  });
}

export function useLockPlan(id: string) {
  return useRunMutation<string[]>((faults) => api.post<Run>(runPath(id, "/plan/lock"), { faults }));
}

export function useResumeRun(id: string) {
  return useRunMutation<void>(() => api.post<Run>(runPath(id, "/resume")));
}

export function useRunTrace(id: string) {
  return useQuery({
    queryKey: keys.trace(id),
    queryFn: () => api.get<RunTrace>(runPath(id, "/trace")),
  });
}

// --- briefs ----------------------------------------------------------------------------------

export function useBriefs(status?: BriefStatus) {
  return useQuery({
    queryKey: keys.briefs(status),
    queryFn: () =>
      api.get<BriefSummary[]>(status ? `/briefs?status_filter=${encodeURIComponent(status)}` : "/briefs"),
    refetchInterval: 15_000, // a draft can arrive while someone has the queue open
  });
}

export function useBrief(id: string) {
  return useQuery({
    queryKey: keys.brief(id),
    queryFn: () => api.get<Brief>(`/briefs/${encodeURIComponent(id)}`),
    staleTime: 0,
  });
}

export function useEvidence(id: string) {
  return useQuery({
    queryKey: keys.evidence(id),
    queryFn: () => api.get<EvidenceRow[]>(`/briefs/${encodeURIComponent(id)}/evidence`),
  });
}

export function usePriorBriefs(id: string) {
  return useQuery({
    queryKey: keys.prior(id),
    queryFn: () => api.get<PriorMatch[]>(`/briefs/${encodeURIComponent(id)}/prior`),
  });
}

/** A dry run: would these edits pass validation? Nothing is saved. */
export function useCheckEdits(id: string) {
  return useMutation({
    mutationFn: (edits: EditRequest[]) =>
      api.post<{ report: ValidationReport }>(`/briefs/${encodeURIComponent(id)}/check-edits`, { edits }),
  });
}

export function useDecide(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (decision: Partial<Decision> & Pick<Decision, "kind">) =>
      api.post<DecisionResult>(`/briefs/${encodeURIComponent(id)}/decision`, decision),
    onSuccess: (result) => {
      client.setQueryData(keys.brief(id), result.brief);
      void client.invalidateQueries({ queryKey: ["briefs"] });
      void client.invalidateQueries({ queryKey: ["reports"] });
      void client.invalidateQueries({ queryKey: keys.runs });
      void client.invalidateQueries({ queryKey: keys.run(result.brief.run_id) });
    },
  });
}

// --- reports ---------------------------------------------------------------------------------

export function useCurrentReport(enabled = true) {
  return useQuery({
    queryKey: keys.currentReport,
    enabled,
    queryFn: () => api.get<{ current: Version | null }>("/reports/current"),
  });
}

export function useVersions() {
  return useQuery({ queryKey: keys.versions, queryFn: () => api.get<Version[]>("/reports/versions") });
}

export function useVersion(number: number) {
  return useQuery({
    queryKey: keys.version(number),
    queryFn: () => api.get<VersionDetail>(`/reports/versions/${number}`),
  });
}

export function useDiff(from: number | null, to: number | null) {
  return useQuery({
    queryKey: keys.diff(from ?? 0, to ?? 0),
    enabled: from !== null && to !== null && from !== to,
    queryFn: () => api.get<Diff>(`/reports/diff?from_version=${from}&to_version=${to}`),
  });
}

export function useRollback() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: { to_version: number; reason: string }) =>
      api.post<Version>("/reports/rollback", body),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["reports"] });
      void client.invalidateQueries({ queryKey: ["briefs"] });
    },
  });
}

// --- audit -----------------------------------------------------------------------------------

export function useAudit(query: string) {
  return useQuery({
    queryKey: keys.audit(query),
    queryFn: () => api.get<AuditPage>(query ? `/audit?${query}` : "/audit"),
    placeholderData: (previous) => previous,
  });
}

export function useAuditVerification() {
  return useQuery({
    queryKey: keys.auditVerify,
    queryFn: () => api.get<AuditVerification>("/audit/verify"),
    staleTime: 0,
  });
}

/** One source record behind a figure. Out-of-scope records come back as 404, like missing ones. */
export function useFact(id: number | null) {
  return useQuery({
    queryKey: keys.fact(id ?? 0),
    enabled: id !== null,
    queryFn: () => api.get<FactOut>(`/facts/${id}`),
  });
}

export function useAuditActions() {
  return useQuery({
    queryKey: ["audit", "actions"],
    queryFn: () => api.get<string[]>("/audit/actions"),
    staleTime: 60_000,
  });
}

// --- admin -----------------------------------------------------------------------------------

export function useAdminOptions() {
  return useQuery({ queryKey: ["admin", "options"], queryFn: () => api.get<AdminOptions>("/admin/options"), staleTime: 5 * 60_000 });
}

export function useAdminUsers(enabled: boolean) {
  return useQuery({ queryKey: ["admin", "users"], enabled, queryFn: () => api.get<AdminUser[]>("/admin/users") });
}

function useAdminMutation<V, R>(call: (variables: V) => Promise<R>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: call,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["admin"] });
      void client.invalidateQueries({ queryKey: ["audit"] });
    },
  });
}

export function useCreateUser() {
  return useAdminMutation((body: CreateUser) => api.post<AdminUser>("/admin/users", body));
}

export function useUpdateUser() {
  return useAdminMutation(({ id, changes }: { id: number; changes: UpdateUser }) =>
    api.patch<AdminUser>(`/admin/users/${id}`, changes),
  );
}

export function useResetPassword() {
  return useAdminMutation(({ id, password }: { id: number; password: string }) =>
    api.post<void>(`/admin/users/${id}/password`, { password }),
  );
}

export function useScopeGrants(enabled: boolean) {
  return useQuery({ queryKey: ["admin", "scope-grants"], enabled, queryFn: () => api.get<ScopeGrant[]>("/admin/scope-grants") });
}

export function useGrantScope() {
  return useAdminMutation((body: { domain: string; expires_on: string | null }) =>
    api.post<ScopeGrant>("/admin/scope-grants", body),
  );
}

export function useRevokeScope() {
  return useAdminMutation((domain: string) => api.post<ScopeGrant[]>(`/admin/scope-grants/${domain}/revoke`));
}

/** Read the sources again. Everything on screen came from the old read, so all of it is refetched. */
export function useRefreshData() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<RefreshResult>("/data/refresh"),
    onSuccess: () => {
      void client.invalidateQueries();
    },
  });
}
