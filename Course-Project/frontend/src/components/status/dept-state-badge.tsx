import { Lock } from "lucide-react";

import type { DepartmentRow } from "@/lib/api/types";
import { HEALTH_STATE, KPI_STATUS, type StatusStyle } from "@/lib/status";

import { StatusChip } from "./status-badge";

const RESTRICTED: StatusStyle = {
  label: "Restricted",
  tone: "neutral",
  icon: Lock,
  hint: "You can see the institution figure, but not this department's detail",
};

const EXCLUDED: StatusStyle = {
  label: "Excluded",
  tone: "serious",
  icon: HEALTH_STATE.missing.icon,
  hint: "An input is provisional, forecast or pending reconciliation, so it is kept out of the figure",
};

/** The one badge that explains a department row, or nothing when the row is simply fine. */
export function DeptStateBadge({ row }: { row: DepartmentRow }) {
  if (row.access === "restricted") return <StatusChip style={RESTRICTED} />;
  switch (row.state) {
    case "missing":
      return <StatusChip style={HEALTH_STATE.missing} />;
    case "excluded":
      return <StatusChip style={EXCLUDED} />;
    case "undefined":
      return <StatusChip style={KPI_STATUS.undefined} />;
    case "ok":
      return row.stale ? <StatusChip style={HEALTH_STATE.stale} /> : null;
    default:
      return null;
  }
}
