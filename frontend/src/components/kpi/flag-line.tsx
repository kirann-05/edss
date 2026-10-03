import { cn } from "cn";

import type { KpiOut } from "@/lib/api/types";
import { flagSummaries } from "@/lib/flags";
import { TONE_CLASS } from "@/lib/status";

/** The data-quality problems behind a figure, said out loud next to it. */
export function FlagLine({ flags, className }: { flags: KpiOut["flags"]; className?: string }) {
  const summaries = flagSummaries(flags);
  if (summaries.length === 0) return null;
  return (
    <ul className={cn("flex flex-wrap gap-1.5", className)}>
      {summaries.map(({ kind, tone, icon: Icon, text, hint }) => (
        <li
          key={kind}
          title={hint}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-sm",
            TONE_CLASS[tone],
          )}
        >
          <Icon aria-hidden className="size-4 shrink-0" />
          {text}
        </li>
      ))}
    </ul>
  );
}
