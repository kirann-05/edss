"""The API contract. The frontend's TypeScript types are generated from these models.

Two conventions the UI relies on:

  Figures are plain decimal strings, already computed from unrounded values. The UI only
  chooses how many places to show, it never recomputes a figure or a status.

  Department detail a person may not see is not sent. A restricted row carries the
  department's identity and nothing else, so scoping holds even if the UI is bypassed.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.agents.models import ValidationReport
from app.agents.tokens import Segment
from app.core.rbac import Permission
from app.domain.enums import BriefStatus, Domain, FactStatus, KpiFramework, KpiStatus, Role
from app.domain.models import DecimalStr
from app.kpi.results import DeptState
from app.services.runs import RunStatus


class Api(BaseModel):
    model_config = ConfigDict(frozen=True)


# --- auth ---------------------------------------------------------------------------------
class LoginIn(Api):
    email: str
    password: str


class DemoLoginIn(Api):
    email: str


class UserOut(Api):
    id: int
    email: str
    name: str
    role: Role
    dept_code: str | None = None
    school: str | None = None


class ScopeOut(Api):
    everything: bool
    departments: list[str]


class MeOut(Api):
    user: UserOut
    permissions: list[Permission]
    scope: ScopeOut


class DemoUserOut(Api):
    email: str
    name: str
    role: Role
    dept_code: str | None = None
    school: str | None = None


# --- system -------------------------------------------------------------------------------
class SystemStatusOut(Api):
    version: str
    data_mode: Literal["synthetic", "real"]
    llm_provider: str
    # true when drafts come from canned test outputs rather than a model, so nobody mistakes them
    llm_is_fake: bool
    current_period: str
    periods: list[str]
    today: date
    stale_after_days: int
    # a pause added to each domain agent to stand in for a slow source system. 0 means none
    simulated_source_latency_ms: int


# --- kpis ---------------------------------------------------------------------------------
class DeptFlagList(Api):
    departments: list[str]  # only those the viewer may see
    total: int  # all of them, so a HOD still learns that something is off


class KpiFlagsOut(Api):
    stale: DeptFlagList
    missing: DeptFlagList
    excluded: DeptFlagList  # an input is provisional, forecast or pending reconciliation
    undefined: DeptFlagList  # zero denominator for that department
    excluded_fact_count: int
    no_target: bool


class TrendPoint(Api):
    period_year: str
    value: DecimalStr | None
    target: DecimalStr | None
    status: KpiStatus


class KpiOut(Api):
    key: str
    name: str
    domain: Domain
    domain_tags: list[Domain]
    framework: KpiFramework
    placeholder: bool  # true until IQAC supplies the real definition (rule 12)
    note: str | None
    unit: str
    precision: int
    higher_is_better: bool
    version: int
    formula: str
    formula_text: str
    period_year: str
    value: DecimalStr | None
    target: DecimalStr | None
    variance_abs: DecimalStr | None
    variance_pct: DecimalStr | None
    status: KpiStatus
    as_of: date | None  # the oldest input, because a figure is only as fresh as that
    flags: KpiFlagsOut
    input_fact_count: int
    trend: list[TrendPoint]  # every period, oldest first


class StatusSummary(Api):
    met: int
    at_risk: int
    missed: int
    undefined: int


class KpiListOut(Api):
    period_year: str
    is_current: bool
    oldest_as_of: date | None
    newest_as_of: date | None
    summary: StatusSummary
    kpis: list[KpiOut]


class InputTermOut(Api):
    label: str  # the engine's own name, for example sum(plc.registered)
    description: str  # the same in plain language, for example Total students registered
    value: DecimalStr


class DepartmentRowOut(Api):
    dept_code: str
    dept_name: str
    school: str
    access: Literal["visible", "restricted"]
    # everything below is empty for a restricted row
    state: DeptState | None = None
    value: DecimalStr | None = None
    inputs: list[InputTermOut] = []
    stale: bool = False
    as_of: date | None = None
    reason: str | None = None
    fact_ids: list[int] = []


class SpreadOut(Api):
    count: int
    min: DecimalStr
    median: DecimalStr
    max: DecimalStr
    # shown beside the institution value to make rule 11 visible: the two differ (trap T7)
    simple_mean: DecimalStr


class FactOut(Api):
    id: int
    metric_key: str
    metric_label: str
    domain: Domain
    dept_code: str
    period_year: str
    period_sub: str
    value: DecimalStr
    unit: str
    status: FactStatus
    as_of: date
    source_system: str
    source_owner: str
    source_ref: str
    batch_id: int
    used: bool  # false for a figure that was kept out of the KPI, with its status badge


class KpiDrilldownOut(Api):
    kpi: KpiOut
    inputs: list[InputTermOut]
    departments: list[DepartmentRowOut]
    spread: SpreadOut | None  # None when the viewer is scoped to some departments only
    facts: list[FactOut]
    facts_hidden: int  # facts of departments the viewer may not see
    access: Literal["full", "restricted"]


class DomainKpiOut(Api):
    kpi: KpiOut
    departments: list[DepartmentRowOut]


class DomainViewOut(Api):
    domain: Domain
    period_year: str
    kpis: list[DomainKpiOut]


# --- data health --------------------------------------------------------------------------
HealthState = Literal["fresh", "stale", "missing", "closed"]


class NonFinalCounts(Api):
    provisional: int = 0
    forecast: int = 0
    pending_reconciliation: int = 0


class HealthCellOut(Api):
    dept_code: str
    domain: Domain
    restricted: bool = False
    state: HealthState | None = None
    as_of: date | None = None  # the oldest record in the cell
    age_days: int | None = None
    fact_count: int = 0
    non_final: NonFinalCounts = NonFinalCounts()
    batch_ids: list[int] = []


class DepartmentOut(Api):
    code: str
    name: str
    school: str


class BatchOut(Api):
    id: int
    domain: Domain
    source: str
    owner_office: str
    file_ref: str
    row_count: int
    rejected_count: int
    finished_at: date
    checksum: str


class HealthSummary(Api):
    fresh: int
    stale: int
    missing: int
    closed: int


class DataHealthOut(Api):
    period_year: str
    is_current: bool
    today: date
    stale_after_days: int
    domains: list[Domain]
    departments: list[DepartmentOut]
    cells: list[HealthCellOut]
    batches: list[BatchOut]
    summary: HealthSummary


# --- runs ---------------------------------------------------------------------------------
class QuestionOut(Api):
    id: str
    text: str
    why: str
    choices: list[str]


class AnswerIn(Api):
    question_id: str
    answer: str


class AnswersIn(Api):
    answers: list[AnswerIn]


class AnswerOut(Api):
    question_id: str
    question: str  # the words of the question this answers, so a reader needs no id
    answer: str


class CreateRunIn(Api):
    request: str


class PlanStepOut(Api):
    id: str
    title: str
    detail: str


class PlanOut(Api):
    request: str
    period_year: str
    domains: list[Domain]
    kpi_keys: list[str]
    options_for: Literal["off_target", "all"]
    audience: str
    steps: list[PlanStepOut]
    revision: int
    locked_at: datetime | None


class StepPatch(Api):
    title: str | None = None
    detail: str | None = None


class PlanPatchIn(Api):
    period_year: str | None = None
    domains: list[Domain] | None = None
    kpi_keys: list[str] | None = None
    options_for: Literal["off_target", "all"] | None = None
    audience: str | None = None
    steps: dict[str, StepPatch] | None = None


class ReviseIn(Api):
    feedback: str


class LockIn(Api):
    faults: list[str] = []


class PlanHistoryOut(Api):
    revision: int
    changes: list[str]
    at: str


class RunOut(Api):
    id: str
    request: str
    status: RunStatus
    created_by_name: str
    created_at: datetime
    questions: list[QuestionOut]
    answers: list[AnswerOut]
    plan: PlanOut | None
    plan_history: list[PlanHistoryOut]
    faults: list[str]
    brief_id: str | None
    error: str | None


class RunRevisionOut(Api):
    run: RunOut
    changes: list[str]


class KpiChoiceOut(Api):
    key: str
    name: str
    domain: Domain


class FaultOut(Api):
    id: str
    label: str
    description: str


class PlanCatalogueOut(Api):
    periods: list[str]
    current_period: str
    domains: list[Domain]
    kpis: list[KpiChoiceOut]
    audiences: list[str]
    faults: list[FaultOut]  # empty unless the data is synthetic


class RunEventOut(Api):
    id: int
    ts: datetime
    node: str
    label: str
    state: Literal["running", "done", "failed", "waiting"]
    elapsed_ms: int | None
    attempt: int | None
    detail: str | None
    ok: bool | None


# --- briefs -------------------------------------------------------------------------------
class RichTextOut(Api):
    text: str  # with reference tokens, what an editor changes
    segments: list[Segment]  # the same text with every figure resolved


class OptionOut(Api):
    id: str
    title: str
    description: RichTextOut
    assumptions: list[RichTextOut]
    risks: list[RichTextOut]
    trade_offs: list[RichTextOut]


class OptionSetOut(Api):
    kpi_key: str
    kpi_name: str
    status: KpiStatus
    attempt: int
    options: list[OptionOut]


class SummaryOut(Api):
    kpi_key: str
    text: RichTextOut


class AssumptionOut(Api):
    kind: str
    dept_code: str | None
    kpi_keys: list[str]
    text: RichTextOut


class HealthNoteOut(Api):
    dept_code: str
    domain: Domain
    state: str
    as_of: date | None
    non_final: list[FactStatus]


class FigureOut(Api):
    key: str
    name: str
    domain: Domain
    unit: str
    precision: int
    higher_is_better: bool
    placeholder: bool
    value: DecimalStr | None
    target: DecimalStr | None
    variance_abs: DecimalStr | None
    status: KpiStatus
    as_of: date | None
    flags: KpiFlagsOut
    input_fact_count: int
    trend: str


class BriefDocumentOut(Api):
    title: str
    period_year: str
    kpis: list[FigureOut]
    summary: list[SummaryOut]
    option_sets: list[OptionSetOut]
    assumptions: list[AssumptionOut]
    data_health: list[HealthNoteOut]


class ApprovalOut(Api):
    actor_name: str
    role: str
    at: datetime
    ack_escalation: bool


class EditOut(Api):
    option_id: str
    field: str
    before: str | list[str]
    after: str | list[str]
    by: str
    at: datetime


class ApprovalStateOut(Api):
    can_approve: bool
    blocked_reason: str | None
    needs_acknowledgement: bool
    failing_checks: list[str]


class BriefOut(Api):
    id: str
    run_id: str
    status: BriefStatus
    escalated: bool
    diagnosis: str | None
    attempts: int
    created_at: datetime
    created_by: str
    request: str | None
    period_year: str
    document: BriefDocumentOut
    validation: ValidationReport
    history: list[ValidationReport]  # every attempt, so a repair can be followed step by step
    repair_log: list[str]
    approval: ApprovalOut | None
    edits: list[EditOut]
    version: int | None
    decision_reason: str | None
    approval_state: ApprovalStateOut
    can_decide: bool  # whether this person's role may approve, edit or override


class BriefSummaryOut(Api):
    id: str
    run_id: str
    status: BriefStatus
    escalated: bool
    validation_passed: bool
    failing_checks: list[str]
    attempts: int
    created_at: datetime
    request: str | None
    period_year: str
    off_target_count: int


class EditRequestIn(Api):
    option_id: str
    field: Literal["title", "description", "assumptions", "risks", "trade_offs"]
    value: str | list[str]


class DecisionIn(Api):
    kind: Literal["approve", "edit", "override", "send_back"]
    reason: str | None = None
    edits: list[EditRequestIn] = []
    ack_escalation: bool = False


class DecisionOut(Api):
    brief: BriefOut
    version: int | None  # the version number, when the decision published one


class EditCheckIn(Api):
    edits: list[EditRequestIn]


class EditCheckOut(Api):
    report: ValidationReport


class EvidenceRowOut(Api):
    kpi_key: str
    claim: str
    fact_ids: list[int]
    source_systems: list[str]
    scope: str
    tags: list[str]


class PriorMatchOut(Api):
    id: str
    period_year: str
    title: str
    decided_on: date
    decision: str
    matching_kpis: list[str]
    score: float
    reason: str


# --- reports ------------------------------------------------------------------------------
class VersionOut(Api):
    version: int
    brief_id: str
    run_id: str
    title: str
    period_year: str
    approved_by: str
    approved_at: datetime
    state: Literal["current", "previous", "rolled_back"]
    escalation_acknowledged: bool
    edit_count: int
    kpi_count: int


class VersionDetailOut(VersionOut):
    document: BriefDocumentOut
    edits: list[EditOut]


class CurrentReportOut(Api):
    current: VersionOut | None


class ChangeOut(Api):
    section: Literal["figures", "options", "assumptions"]
    kind: Literal["added", "removed", "changed"]
    kpi_key: str | None
    option_id: str | None
    field: str | None
    before: str | None
    after: str | None


class DiffOut(Api):
    from_version: int
    to_version: int
    changes: list[ChangeOut]


class RollbackIn(Api):
    to_version: int
    reason: str


# --- audit --------------------------------------------------------------------------------
class AuditRowOut(Api):
    id: int
    ts: datetime
    run_id: str | None
    actor_type: str
    actor_id: str
    action: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    prev_hash: str
    hash: str


class AuditPageOut(Api):
    rows: list[AuditRowOut]
    total: int
    offset: int
    limit: int


class VerifyOut(Api):
    ok: bool
    checked: int
    broken_at: int | None
    reason: str | None


class TraceOut(Api):
    run_id: str
    events: list[RunEventOut]
    audit: list[AuditRowOut]


# --- admin --------------------------------------------------------------------------------
class AdminUserOut(Api):
    id: int
    email: str
    name: str
    role: Role
    dept_code: str | None
    school: str | None
    active: bool


class CreateUserIn(Api):
    email: str
    name: str
    role: Role
    dept_code: str | None = None
    school: str | None = None
    password: str  # never logged or returned


class UpdateUserIn(Api):
    """Only the fields sent are changed. Sending null clears a department or a school."""

    name: str | None = None
    role: Role | None = None
    dept_code: str | None = None
    school: str | None = None
    active: bool | None = None


class PasswordIn(Api):
    password: str


class DepartmentOptionOut(Api):
    code: str
    name: str
    school: str


class AdminOptionsOut(Api):
    roles: list[Role]
    departments: list[DepartmentOptionOut]
    schools: list[str]
    min_password: int
    areas: list[Domain]


class ScopeGrantOut(Api):
    domain: Domain
    dept_code: str | None
    granted_by: str
    granted_on: date
    expires_on: date | None
    active: bool
    state: Literal["active", "expired", "revoked"]


class GrantIn(Api):
    domain: Domain
    expires_on: date | None = None
