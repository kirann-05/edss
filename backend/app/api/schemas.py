"""The API contract. The frontend's TypeScript types are generated from these models.

Two conventions the UI relies on:

  Figures are plain decimal strings, already computed from unrounded values. The UI only
  chooses how many places to show, it never recomputes a figure or a status.

  Department detail a person may not see is not sent. A restricted row carries the
  department's identity and nothing else, so scoping holds even if the UI is bypassed.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.core.rbac import Permission
from app.domain.enums import Domain, FactStatus, KpiFramework, KpiStatus, Role
from app.domain.models import DecimalStr
from app.kpi.results import DeptState


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
