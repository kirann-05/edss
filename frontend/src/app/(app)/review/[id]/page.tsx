"use client";

import { Suspense, use } from "react";

import { BriefReview } from "@/components/brief/brief-review";
import { Skeleton } from "@/components/ui/skeleton";

export default function BriefReviewPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    // the drill-down drawer reads its KPI from the address bar, which needs a Suspense boundary
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <BriefReview id={id} />
    </Suspense>
  );
}
