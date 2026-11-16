"use client";

import { use } from "react";

import { RunView } from "@/components/runs/run-view";

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RunView id={id} />;
}
