"use client";

import { Bot, FlaskConical, Lock, TriangleAlert } from "lucide-react";

import { useSystemStatus } from "@/lib/api/queries";

/**
 * Always visible, so nobody mistakes demo data or canned drafts for the real thing.
 * Rule 7: real data stays on this machine, and the badge says which mode this is.
 */
export function ModeBadges() {
  const { data } = useSystemStatus();
  if (!data) return null;
  const synthetic = data.data_mode === "synthetic";
  return (
    <ul className="flex flex-wrap items-center gap-2">
      <li>
        {synthetic ? (
          <span
            title="Every figure comes from the synthetic test dataset, not from university records"
            className="inline-flex items-center gap-1.5 rounded-md border bg-neutral-tint px-2 py-1 text-sm font-medium text-neutral-ink"
          >
            <FlaskConical aria-hidden className="size-4" />
            Synthetic data
          </span>
        ) : (
          <span
            title="Real university data. Processed on this machine and never sent to a hosted model"
            className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-2 py-1 text-sm font-medium text-background"
          >
            <Lock aria-hidden className="size-4" />
            Real data, local only
          </span>
        )}
      </li>
      {data.llm_is_fake ? (
        <li>
          <span
            title="Option and risk text comes from canned test outputs, not from a language model"
            className="inline-flex items-center gap-1.5 rounded-md border border-dashed px-2 py-1 text-sm text-neutral-ink"
          >
            <Bot aria-hidden className="size-4" />
            Drafts are canned
          </span>
        </li>
      ) : (
        <li>
          <span
            title={
              data.llm_is_local
                ? "Option and risk text is written by a language model running on this machine. It is never given a figure and never writes one"
                : "Option and risk text is written by a model reached over the network. Allowed with synthetic data only"
            }
            className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-sm text-neutral-ink"
          >
            <Bot aria-hidden className="size-4" />
            {data.llm_name.replace(/^[a-z_]+:/, "")} ({data.llm_is_local ? "local" : "hosted"})
          </span>
        </li>
      )}
      {data.llm_reachable === false && (
        <li>
          <span
            role="status"
            title="The language model server is not answering. Starting a brief will fail until it is running, or LLM_PROVIDER is set to fake"
            className="inline-flex items-center gap-1.5 rounded-md border border-serious-mark/60 bg-serious-tint px-2 py-1 text-sm font-medium text-serious-ink"
          >
            <TriangleAlert aria-hidden className="size-4" />
            Model not answering
          </span>
        </li>
      )}
    </ul>
  );
}
