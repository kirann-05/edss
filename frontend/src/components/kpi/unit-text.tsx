"use client";

/** "%" sits against the figure, any other unit is smaller text beside it. */
export function UnitText({ unit }: { unit: string }) {
  if (!unit) return null;
  return unit === "%" ? (
    <span className="text-2xl font-medium text-muted-foreground">%</span>
  ) : (
    <span className="text-base text-muted-foreground">{unit}</span>
  );
}
