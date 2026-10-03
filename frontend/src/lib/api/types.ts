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

// runs
export type Run = S["RunOut"];
export type RunStatus = S["RunStatus"];
export type Plan = S["PlanOut"];
export type PlanPatch = S["PlanPatchIn"];
export type PlanCatalogue = S["PlanCatalogueOut"];
export type Question = S["QuestionOut"];
export type AnswerOut = S["AnswerOut"];
export type RunRevision = S["RunRevisionOut"];
export type RunEvent = S["RunEventOut"];
export type RunTrace = S["TraceOut"];

// briefs
export type Brief = S["BriefOut"];
export type BriefSummary = S["BriefSummaryOut"];
export type BriefStatus = S["BriefStatus"];
export type BriefDocument = S["BriefDocumentOut"];
export type Figure = S["FigureOut"];
export type OptionSet = S["OptionSetOut"];
export type BriefOption = S["OptionOut"];
export type RichText = S["RichTextOut"];
export type Segment = S["Segment"];
export type Assumption = S["AssumptionOut"];
export type HealthNote = S["HealthNoteOut"];
export type ApprovalState = S["ApprovalStateOut"];
export type ValidationReport = S["ValidationReport"];
export type CheckResult = S["CheckResult"];
export type Violation = S["Violation"];
export type EditRequest = S["EditRequestIn"];
export type Decision = S["DecisionIn"];
export type DecisionResult = S["DecisionOut"];
export type EvidenceRow = S["EvidenceRowOut"];
export type PriorMatch = S["PriorMatchOut"];

// reports
export type Version = S["VersionOut"];
export type VersionDetail = S["VersionDetailOut"];
export type Diff = S["DiffOut"];
export type Change = S["ChangeOut"];

// audit
export type AuditRow = S["AuditRowOut"];
export type AuditPage = S["AuditPageOut"];
export type AuditVerification = S["VerifyOut"];

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
