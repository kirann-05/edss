"use client";

import { Suspense, use } from "react";

import { ErrorPanel } from "@/components/error-panel";
import { VersionView } from "@/components/reports/version-view";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";

export default function VersionPage({ params }: { params: Promise<{ version: string }> }) {
  const { version } = use(params);
  const number = Number(version);
  if (!Number.isInteger(number) || number < 1) {
    return <ErrorPanel error={new ApiError(404, "Not found")} what="this version" />;
  }
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <VersionView number={number} />
    </Suspense>
  );
}
