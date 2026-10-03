"""Domain records. Frozen Pydantic models so engine inputs and outputs cannot be mutated.

Money and ratios are Decimal, never float. In JSON they travel as plain decimal strings
(no exponent), which the frontend rounds exactly. See frontend/src/lib/format.ts.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, model_validator

from app.domain.enums import Domain, FactStatus, KpiFramework, PeriodAgg, Role


def _plain(value: Decimal) -> str:
    # format(d, "f") never uses exponent notation, unlike str(Decimal("1E+2"))
    return format(value, "f")


DecimalStr = Annotated[Decimal, PlainSerializer(_plain, return_type=str, when_used="json")]


class Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Department(Frozen):
    code: str
    name: str
    school: str
    active: bool = True


class SourceSystem(Frozen):
    id: int
    name: str
    owner_office: str
    kind: str  # csv, sql, api


class IngestBatch(Frozen):
    id: int
    source_system_id: int
    data_mode: str
    domain: Domain
    row_count: int
    rejected_count: int = 0
    file_ref: str
    checksum: str
    ingested_by: str
    finished_at: date


class MetricFact(Frozen):
    id: int
    batch_id: int
    domain: Domain
    metric_key: str
    dept_code: str
    period_year: str  # 2025-26
    period_sub: str  # S1, S2, Q1..Q4, AY, FY
    value: DecimalStr
    numerator: DecimalStr | None = None
    denominator: DecimalStr | None = None
    unit: str
    status: FactStatus
    as_of: date
    source_system_id: int
    source_ref: str


class Publication(Frozen):
    id: int
    batch_id: int
    dedup_key: str  # DOI or internal id. Institution counts one per key (rule, trap T5)
    title: str
    venue: str
    period_year: str
    indexing: str
    status: FactStatus
    dept_codes: tuple[str, ...]  # every department that gets credit


class MetricSpec(Frozen):
    key: str
    domain: Domain
    label: str
    unit: str
    period_agg: PeriodAgg


class KpiDefinition(Frozen):
    key: str
    name: str
    framework: KpiFramework
    domain: Domain  # primary domain, used to group the dashboard
    domain_tags: tuple[Domain, ...]
    formula: str
    unit: str
    higher_is_better: bool = True
    version: int = 1
    approved_by: str | None = None
    approved_on: date | None = None
    active: bool = True
    placeholder: bool = True  # true until IQAC supplies the real definition (rule 12)
    display_precision: int = 1
    at_risk_band_pct: DecimalStr = Decimal("2")
    note: str | None = None


class KpiTarget(Frozen):
    kpi_key: str
    period_year: str
    target_value: DecimalStr
    framework: KpiFramework
    source_doc: str
    placeholder: bool = True


class AppUser(Frozen):
    """A person who signs in. The password hash is kept apart, in services/users.py."""

    id: int
    email: str
    name: str
    role: Role
    dept_code: str | None = None  # a HOD belongs to one department
    school: str | None = None  # a Dean belongs to one school
    active: bool = True

    @model_validator(mode="after")
    def _role_has_its_scope(self) -> "AppUser":
        if self.role is Role.HOD and not self.dept_code:
            raise ValueError("a HOD must have a department")
        if self.role is Role.DEAN and not self.school:
            raise ValueError("a Dean must have a school")
        return self
