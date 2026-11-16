"use client";

import { Suspense } from "react";

import { AuditView } from "@/components/audit/audit-view";
import { Skeleton } from "@/components/ui/skeleton";

export default function AuditPage() {
  return (
    // the filters live in the address bar, which needs a Suspense boundary
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <AuditView />
    </Suspense>
  );
}
