// Friendly names for the generated API types. The source of truth is the backend contract:
// run `make types` after any change to backend/app/api/schemas.py and a mismatch here becomes a
// compile error instead of a runtime bug.
import type { components } from "./schema";

type S = components["schemas"];

export type Me = S["MeOut"];
export type UserOut = S["UserOut"];
export type DemoUser = S["DemoUserOut"];
export type SystemStatus = S["SystemStatusOut"];

export type KpiOut = S["KpiOut"];
export type KpiList = S["KpiListOut"];
export type KpiDrilldown = S["KpiDrilldownOut"];
export type DomainView = S["DomainViewOut"];
export type DomainKpi = S["DomainKpiOut"];
export type DepartmentRow = S["DepartmentRowOut"];
export type FactOut = S["FactOut"];
export type InputTerm = S["InputTermOut"];
export type TrendPoint = S["TrendPoint"];
export type DeptFlagList = S["DeptFlagList"];

export type DataHealth = S["DataHealthOut"];
export type HealthCell = S["HealthCellOut"];
export type HealthState = NonNullable<HealthCell["state"]>;

export type Domain = S["Domain"];
export type KpiStatus = S["KpiStatus"];
export type FactStatus = S["FactStatus"];
export type DeptState = NonNullable<DepartmentRow["state"]>;
export type Role = S["Role"];
export type Permission = S["Permission"];

/** The four domains that have a dashboard tab. Reference counts are denominators only. */
export const DOMAIN_TABS = ["academic", "research", "placement", "finance"] as const;
export type DomainTab = (typeof DOMAIN_TABS)[number];

export const DOMAIN_LABEL: Record<Domain, string> = {
  academic: "Academic",
  research: "Research",
  placement: "Placement",
  finance: "Finance",
  reference: "Reference counts",
};
