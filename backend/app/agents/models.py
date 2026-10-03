"""Data models for the agent pipeline: the plan, option drafts, the brief and its validation.

Everything here is frozen. A figure inside a brief is a copy of the engine's result taken at the
time, so a published version never changes underneath its readers.
"""

from datetime import date, datetime
from typing import Literal

from app.domain.enums import Domain, FactStatus, KpiStatus
from app.domain.models import DecimalStr, Frozen
from app.kpi.formulas import InputTerm
from app.kpi.results import KpiFlags


# --- clarify and plan (Lab 1, Lab 3) -------------------------------------------------------
class ClarifyQuestion(Frozen):
    id: str
    text: str
    why: str  # one line on why the agent needs the answer
    choices: tuple[str, ...] = ()  # empty means a free text answer


class Clarification(Frozen):
    question_id: str
    answer: str


class PlanStep(Frozen):
    id: str  # stable, so a revision patches the same step instead of replacing it
    title: str
    detail: str


class Plan(Frozen):
    """What the run will do. Locked before any work begins, and immutable after (FR-1)."""

    request: str
    period_year: str
    domains: tuple[Domain, ...]
    kpi_keys: tuple[str, ...]  # coverage: every KPI here must appear in the brief (check V8)
    options_for: Literal["off_target", "all"] = "off_target"
    audience: str
    steps: tuple[PlanStep, ...]
    revision: int = 1
    locked_at: datetime | None = None

    @property
    def locked(self) -> bool:
        return self.locked_at is not None


# --- figures ---------------------------------------------------------------------------------
class KpiFigure(Frozen):
    """The engine's result for one KPI, frozen inside a brief together with what it rested on."""

    key: str
    name: str
    domain: Domain
    unit: str
    precision: int
    higher_is_better: bool
    placeholder: bool
    definition_active: bool
    definition_approved: bool
    kpi_version: int
    period_year: str
    value: DecimalStr | None
    target: DecimalStr | None
    variance_abs: DecimalStr | None
    variance_pct: DecimalStr | None
    status: KpiStatus
    inputs: tuple[InputTerm, ...]
    input_fact_ids: tuple[int, ...]
    as_of: date | None
    flags: KpiFlags
    band_pct: DecimalStr | None = None  # the at-risk band used, so status can be re-derived
    included_departments: tuple[str, ...] = ()  # whose figures the value rests on (check V9)
    # improving, declining, flat or unknown. Worked out in code from the numbers, so a model
    # is told a direction in words and never sees or computes a figure
    trend: Literal["improving", "declining", "flat", "unknown"] = "unknown"


class FactFigure(Frozen):
    """One source record a token may point at."""

    id: int
    label: str
    dept_code: str
    value: DecimalStr
    unit: str
    status: FactStatus
    source_ref: str


# --- options and risks (FR-5) ----------------------------------------------------------------
class Option(Frozen):
    id: str  # for example PL_PCT-1
    title: str  # words only
    description: str  # figures only as {{kpi:KEY}} or {{fact:ID}} tokens
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    trade_offs: tuple[str, ...]


class OptionSet(Frozen):
    kpi_key: str
    options: tuple[Option, ...]
    attempt: int = 1  # which generation this is, 2 or more means it was repaired


# --- the brief ---------------------------------------------------------------------------------
AssumptionKind = Literal[
    "as_of", "placeholder", "stale", "missing", "excluded", "undefined", "provisional", "forecast"
]


class AssumptionItem(Frozen):
    kind: AssumptionKind
    text: str  # may hold tokens
    dept_code: str | None = None
    kpi_keys: tuple[str, ...] = ()


class SummaryItem(Frozen):
    kpi_key: str
    headline: str  # tokens only, never a literal figure


class HealthNote(Frozen):
    dept_code: str
    domain: Domain
    state: str  # fresh, stale, missing or closed
    as_of: date | None
    non_final: tuple[FactStatus, ...] = ()


class BriefDocument(Frozen):
    title: str
    period_year: str
    plan_kpi_keys: tuple[str, ...]
    kpis: tuple[KpiFigure, ...]
    summary: tuple[SummaryItem, ...]
    option_sets: tuple[OptionSet, ...]
    assumptions: tuple[AssumptionItem, ...]
    data_health: tuple[HealthNote, ...]
    options_for: str = "off_target"  # from the plan, so the document can be checked on its own
    # The approval state lives with the brief record, but check V5 needs to see a claim made in
    # the document itself, so a document that says it is approved can be caught.
    claims_status: str = "draft"


# --- validation (docs/SPEC.md section 7) -----------------------------------------------------
class Locator(Frozen):
    """Where a failure is, so only that part is regenerated (Lab 10)."""

    kpi_key: str | None = None
    option_id: str | None = None
    section: str | None = None


# How a failure is put right, so the repair step does not have to guess from the wording
Fix = Literal["regenerate_options", "rebuild_figure", "rebuild_sections", "reset_status"]


class Violation(Frozen):
    locator: Locator
    message: str
    diagnosis: str
    fix: Fix | None = None


class CheckResult(Frozen):
    id: str  # V1 to V9
    name: str
    passed: bool
    violations: tuple[Violation, ...] = ()


class ValidationReport(Frozen):
    passed: bool
    checks: tuple[CheckResult, ...]
    attempt: int = 1

    @property
    def failing(self) -> tuple[CheckResult, ...]:
        return tuple(c for c in self.checks if not c.passed)
