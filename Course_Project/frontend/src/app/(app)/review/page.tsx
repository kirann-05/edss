"use client";

import { ReviewQueue } from "@/components/brief/review-queue";
import { PageHeader } from "@/components/page-header";

export default function ReviewPage() {
  return (
    <>
      <PageHeader
        title="Review queue"
        description="Drafts that passed validation, or were escalated with a diagnosis, wait here for a named approver."
      />
      <ReviewQueue />
    </>
  );
}
