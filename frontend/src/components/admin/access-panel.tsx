"use client";

import { ShieldCheck, ShieldOff } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/brief/decision-dialogs";
import { ErrorPanel } from "@/components/error-panel";
import { StatusChip } from "@/components/status/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useGrantScope, useRevokeScope, useScopeGrants, useSystemStatus } from "@/lib/api/queries";
import { DOMAIN_LABEL, type AdminOptions, type Domain, type ScopeGrant } from "@/lib/api/types";
import type { StatusStyle } from "@/lib/status";
import { formatDay } from "@/lib/when";

const STATE: Record<ScopeGrant["state"], StatusStyle> = {
  active: { label: "Authorised", tone: "good", icon: ShieldCheck, hint: "Runs may read this area" },
  expired: { label: "Expired", tone: "warning", icon: ShieldOff, hint: "The authorisation ran out. Runs that need it stop at the access check" },
  revoked: { label: "Revoked", tone: "serious", icon: ShieldOff, hint: "Withdrawn by the Registrar. Runs that need it stop at the access check" },
};

function inAYear(today: string): string {
  const date = new Date(`${today}T00:00:00`);
  date.setFullYear(date.getFullYear() + 1);
  return date.toISOString().slice(0, 10);
}

/** FR-2: an area can be read by a run only while the Registrar's authorisation for it stands. */
export function AccessPanel({ options }: { options: AdminOptions }) {
  const grants = useScopeGrants(true);
  const system = useSystemStatus();
  const grant = useGrantScope();
  const revoke = useRevokeScope();
  const [revoking, setRevoking] = useState<Domain | null>(null);
  const [expiry, setExpiry] = useState<Record<string, string>>({});

  if (grants.isPending || !system.data) return <Skeleton className="h-64 w-full" />;
  if (grants.isError) return <ErrorPanel error={grants.error} onRetry={() => grants.refetch()} what="data access" />;

  const today = system.data.today;
  const byArea = new Map(grants.data.map((g) => [g.domain, g]));

  return (
    <section aria-labelledby="access-heading" className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 id="access-heading" className="text-xl font-semibold">
          Data access
        </h2>
        <p className="text-base text-muted-foreground">
          Each area is read only with your authorisation. A run that needs an area without it stops at the access
          check, before any data is read.
        </p>
      </div>
      <ul className="grid gap-3 md:grid-cols-2">
        {options.areas.map((area) => {
          const current = byArea.get(area);
          const state = current?.state ?? "revoked";
          const until = expiry[area] ?? inAYear(today);
          return (
            <li key={area} className="flex flex-col gap-3 rounded-xl border bg-card p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="text-lg font-semibold">{DOMAIN_LABEL[area]}</span>
                <StatusChip style={STATE[state]} />
              </div>
              {current && (
                <p className="text-sm text-muted-foreground">
                  {state === "revoked" ? "Revoked. " : ""}
                  Granted by {current.granted_by} on {formatDay(current.granted_on)}
                  {current.expires_on ? `, ${state === "expired" ? "expired" : "until"} ${formatDay(current.expires_on)}` : ""}.
                </p>
              )}
              {state === "active" ? (
                <Button variant="outline" className="w-fit" onClick={() => setRevoking(area)}>
                  <ShieldOff aria-hidden data-icon="inline-start" />
                  Revoke
                </Button>
              ) : (
                <form
                  className="flex flex-wrap items-end gap-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    grant.mutate({ domain: area, expires_on: until });
                  }}
                >
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor={`until-${area}`} className="text-sm">
                      Authorise until
                    </Label>
                    <Input
                      id={`until-${area}`}
                      type="date"
                      min={today}
                      value={until}
                      onChange={(e) => setExpiry({ ...expiry, [area]: e.target.value })}
                      className="h-10 text-base"
                    />
                  </div>
                  <Button type="submit" disabled={grant.isPending}>
                    <ShieldCheck aria-hidden data-icon="inline-start" />
                    Authorise
                  </Button>
                </form>
              )}
            </li>
          );
        })}
      </ul>
      {grant.isError && <p className="text-base text-critical-ink">{grant.error.message}</p>}
      <ConfirmDialog
        open={revoking !== null}
        onOpenChange={(open) => !open && setRevoking(null)}
        title={revoking ? `Revoke access to ${DOMAIN_LABEL[revoking]}?` : ""}
        description="Runs that need this area stop at the access check until you authorise it again. Briefs already published are not affected."
        confirmLabel="Revoke"
        destructive
        busy={revoke.isPending}
        error={revoke.error?.message ?? null}
        onConfirm={() => revoking && revoke.mutate(revoking, { onSuccess: () => setRevoking(null) })}
      />
    </section>
  );
}
