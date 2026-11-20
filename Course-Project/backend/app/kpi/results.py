"""What the KPI engine returns. Every figure here is computed from unrounded Decimals."""

from datetime import date
from enum import StrEnum

from app.domain.enums import KpiStatus
from app.domain.models import DecimalStr, Frozen
from app.kpi.formulas import InputTerm


class DeptState(StrEnum):
    OK = "ok"
    UNDEFINED = "undefined"  # the formula has a zero denominator for this department (trap T9)
    MISSING = "missing"  # an input has no record at all (trap T2). Never treated as zero
    EXCLUDED = "excluded"  # an input is provisional, forecast or unreconciled (trap T8)


class DepartmentValue(Frozen):
    dept_code: str
    state: DeptState
    value: DecimalStr | None
    inputs: tuple[InputTerm, ...] = ()
    input_fact_ids: tuple[int, ...] = ()
    stale: bool = False
    as_of: date | None = None  # the oldest input, because a figure is only as fresh as that
    reason: str | None = None


class KpiFlags(Frozen):
    stale_departments: tuple[str, ...] = ()
    missing_departments: tuple[str, ...] = ()
    excluded_departments: tuple[str, ...] = ()
    undefined_departments: tuple[str, ...] = ()
    # the provisional, forecast or unreconciled facts that kept a department out
    excluded_fact_ids: tuple[int, ...] = ()
    no_target: bool = False


class KpiResult(Frozen):
    kpi_key: str
    kpi_version: int
    period_year: str
    value: DecimalStr | None
    target: DecimalStr | None
    variance_abs: DecimalStr | None  # value minus target, signed
    variance_pct: DecimalStr | None
    status: KpiStatus
    inputs: tuple[InputTerm, ...]
    input_fact_ids: tuple[int, ...]
    departments: tuple[DepartmentValue, ...]
    flags: KpiFlags
    as_of: date | None
