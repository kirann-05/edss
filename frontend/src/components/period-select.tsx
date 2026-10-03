"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePeriod } from "@/lib/use-period";

/** The one filter for a page. It sits above everything it scopes and re-scopes all of it at once. */
export function PeriodSelect() {
  const { period, current, periods, setPeriod } = usePeriod();
  const value = period ?? current;
  if (!value || periods.length === 0) return null;
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor="period" className="text-base text-muted-foreground">
        Period
      </Label>
      <Select value={value} onValueChange={setPeriod}>
        <SelectTrigger id="period" className="h-10 min-w-40 text-base">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {[...periods].reverse().map((p) => (
            <SelectItem key={p} value={p} className="text-base">
              {p}
              {p === current ? " (current)" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
