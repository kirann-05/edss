"use client";

import { AccessPanel } from "@/components/admin/access-panel";
import { PeoplePanel } from "@/components/admin/people-panel";
import { ErrorPanel } from "@/components/error-panel";
import { PageHeader } from "@/components/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminOptions, useMe } from "@/lib/api/queries";

export default function AdminPage() {
  const me = useMe();
  const options = useAdminOptions();
  const manageUsers = me.data?.permissions.includes("manage_users") ?? false;
  const manageScope = me.data?.permissions.includes("manage_scope") ?? false;

  return (
    <>
      <PageHeader
        title="Admin"
        description={
          manageUsers && manageScope
            ? "People and roles, and which areas the agents may read."
            : manageUsers
              ? "People and roles. Data access is authorised by the Registrar."
              : "Which areas the agents may read. People and roles are managed by the Administrator."
        }
      />
      {options.isPending ? (
        <Skeleton className="h-96 w-full" />
      ) : options.isError ? (
        <ErrorPanel error={options.error} onRetry={() => options.refetch()} what="the admin settings" />
      ) : (
        <div className="flex flex-col gap-10">
          {manageScope && <AccessPanel options={options.data} />}
          {manageUsers && <PeoplePanel options={options.data} />}
        </div>
      )}
    </>
  );
}
