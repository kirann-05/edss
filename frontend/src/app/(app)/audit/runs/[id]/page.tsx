"use client";

import { use } from "react";

import { RunTrace } from "@/components/audit/run-trace";

export default function RunTracePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RunTrace id={id} />;
}
