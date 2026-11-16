"""The KPI engine: deterministic, unrounded, and honest about what it could not compute.

No LLM touches this module (rule 1). Everything is Decimal. For one KPI and one period it:

  1. combines each department's sub-periods per metric (sum or latest, decision D14),
  2. keeps a department OUT of a KPI when a required input is missing (trap T2) or is not
     final or audited (provisional, forecast, pending reconciliation, traps T3 T4 T8). It is
     reported in the flags with the reason. It is never counted as zero,
  3. evaluates the formula over the included departments, so institution percentages come from
     totals and never from averaging department percentages (rule 11, trap T7),
  4. evaluates the same formula over each department alone, and a zero denominator there is
     UNDEFINED, not 0 or 100 (trap T9),
  5. decides status on the unrounded value (rule 5, trap T6).

A stale department (trap T1) is still used but flagged, because old data is better flagged than
silently dropped.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache

from app.domain.enums import ACTUAL_STATUSES, KpiStatus, PeriodAgg
from app.domain.models import Department, KpiDefinition, KpiTarget, MetricFact, Publication
from app.kpi.catalogue import CATALOGUE, SUB_PERIOD_ORDER
from app.kpi.formulas import UNDEFINED, InputTerm, ParsedFormula, evaluate, parse_formula
from app.kpi.results import DepartmentValue, DeptState, KpiFlags, KpiResult


class DuplicateFactError(ValueError):
    """Two facts claim the same department, metric and sub-period, so a sum would double count."""


@dataclass(frozen=True)
class PeriodData:
    """Everything the engine needs for one period, already scoped to that period."""

    period_year: str
    departments: tuple[Department, ...]
    facts: tuple[MetricFact, ...]
    publications: tuple[Publication, ...]
    is_current: bool  # staleness is only judged for the current period


class _Slot(StrEnum):
    OK = "ok"
    MISSING = "missing"
    EXCLUDED = "excluded"


@dataclass(frozen=True)
class _Aggregate:
    slot: _Slot
    value: Decimal | None
    fact_ids: tuple[int, ...]
    non_actual_fact_ids: tuple[int, ...]
    oldest_as_of: date | None


def _aggregate(facts: Sequence[MetricFact], agg: PeriodAgg) -> _Aggregate:
    if not facts:
        return _Aggregate(_Slot.MISSING, None, (), (), None)
    non_actual = tuple(sorted(f.id for f in facts if f.status not in ACTUAL_STATUSES))
    if non_actual:
        return _Aggregate(_Slot.EXCLUDED, None, (), non_actual, None)
    if agg is PeriodAgg.SUM:
        chosen = list(facts)
        value = sum((f.value for f in chosen), Decimal(0))
    else:
        latest = max(facts, key=lambda f: (SUB_PERIOD_ORDER.get(f.period_sub, 0), f.as_of, f.id))
        chosen, value = [latest], latest.value
    return _Aggregate(
        _Slot.OK,
        value,
        tuple(sorted(f.id for f in chosen)),
        (),
        min(f.as_of for f in chosen),
    )


class _Index:
    """Per-period lookup of aggregated figures, built once and shared by every KPI."""

    def __init__(self, data: PeriodData) -> None:
        self.data = data
        self._facts: dict[tuple[str, str], list[MetricFact]] = {}
        seen: set[tuple[str, str, str]] = set()
        for fact in data.facts:
            if fact.period_year != data.period_year:
                continue
            slot = (fact.dept_code, fact.metric_key, fact.period_sub)
            if slot in seen:
                raise DuplicateFactError(
                    f"more than one fact for {fact.dept_code} {fact.metric_key} "
                    f"{fact.period_sub} in {data.period_year}"
                )
            seen.add(slot)
            self._facts.setdefault((fact.dept_code, fact.metric_key), []).append(fact)
        self._cache: dict[tuple[str, str], _Aggregate] = {}
        self._publications = tuple(
            p
            for p in data.publications
            if p.period_year == data.period_year and p.status in ACTUAL_STATUSES
        )

    def aggregate(self, dept: str, key: str) -> _Aggregate:
        cached = self._cache.get((dept, key))
        if cached is None:
            cached = _aggregate(self._facts.get((dept, key), ()), CATALOGUE[key].period_agg)
            self._cache[(dept, key)] = cached
        return cached

    # FormulaInputs protocol
    def metric(self, dept: str, key: str) -> Decimal:
        value = self.aggregate(dept, key).value
        if value is None:  # the engine only evaluates eligible departments
            raise LookupError(f"{dept} has no usable figure for {key}")
        return value

    def publication_count(self, depts: Sequence[str]) -> int:
        wanted = set(depts)
        return len({p.dedup_key for p in self._publications if wanted & set(p.dept_codes)})


@lru_cache(maxsize=256)
def _parsed(formula: str) -> ParsedFormula:
    return parse_formula(formula, CATALOGUE)


def judge(
    value: Decimal, target: Decimal, higher_is_better: bool, band_pct: Decimal
) -> tuple[KpiStatus, Decimal, Decimal | None]:
    """Status and variance from unrounded numbers.

    missed   the target is not reached
    at_risk  reached, but by less than band_pct of the target (decision D15)
    met      reached with at least that margin
    """
    variance_abs = value - target
    variance_pct = None if target == 0 else variance_abs / target * 100
    favourable = variance_abs if higher_is_better else -variance_abs
    margin_needed = abs(target) * band_pct / 100
    if favourable < 0:
        status = KpiStatus.MISSED
    elif favourable < margin_needed:
        status = KpiStatus.AT_RISK
    else:
        status = KpiStatus.MET
    return status, variance_abs, variance_pct


def _is_stale(as_of: date | None, today: date, stale_after_days: int, is_current: bool) -> bool:
    return bool(is_current and as_of is not None and (today - as_of).days > stale_after_days)


def _compute(
    definition: KpiDefinition,
    target: KpiTarget | None,
    index: _Index,
    today: date,
    stale_after_days: int,
) -> KpiResult:
    parsed = _parsed(definition.formula)
    keys = sorted(parsed.required_keys)
    data = index.data

    departments: list[DepartmentValue] = []
    eligible: list[str] = []
    ids_by_dept: dict[str, tuple[int, ...]] = {}
    as_of_by_dept: dict[str, date | None] = {}

    for dept in data.departments:
        aggregates = {key: index.aggregate(dept.code, key) for key in keys}
        missing = [k for k, a in aggregates.items() if a.slot is _Slot.MISSING]
        excluded = [k for k, a in aggregates.items() if a.slot is _Slot.EXCLUDED]
        if missing:
            departments.append(
                DepartmentValue(
                    dept_code=dept.code,
                    state=DeptState.MISSING,
                    value=None,
                    reason="no record for " + ", ".join(missing),
                )
            )
            continue
        if excluded:
            fact_ids = tuple(sorted(i for k in excluded for i in aggregates[k].non_actual_fact_ids))
            departments.append(
                DepartmentValue(
                    dept_code=dept.code,
                    state=DeptState.EXCLUDED,
                    value=None,
                    input_fact_ids=fact_ids,
                    reason="not final or audited: " + ", ".join(excluded),
                )
            )
            continue

        fact_ids = tuple(sorted({i for a in aggregates.values() for i in a.fact_ids}))
        oldest = min((a.oldest_as_of for a in aggregates.values() if a.oldest_as_of), default=None)
        terms: list[InputTerm] = []
        value = evaluate(parsed, (dept.code,), index, terms)
        eligible.append(dept.code)
        ids_by_dept[dept.code] = fact_ids
        as_of_by_dept[dept.code] = oldest
        departments.append(
            DepartmentValue(
                dept_code=dept.code,
                state=DeptState.UNDEFINED if value is UNDEFINED else DeptState.OK,
                value=None if value is UNDEFINED else value,
                inputs=tuple(terms),
                input_fact_ids=fact_ids,
                stale=_is_stale(oldest, today, stale_after_days, data.is_current),
                as_of=oldest,
            )
        )

    institution_terms: list[InputTerm] = []
    if eligible:
        institution = evaluate(parsed, tuple(eligible), index, institution_terms)
    else:
        institution = UNDEFINED
    value = None if institution is UNDEFINED else institution

    target_value = target.target_value if target is not None else None
    if value is not None and target_value is not None:
        status, variance_abs, variance_pct = judge(
            value, target_value, definition.higher_is_better, definition.at_risk_band_pct
        )
    else:
        status, variance_abs, variance_pct = KpiStatus.UNDEFINED, None, None

    def codes(state: DeptState) -> tuple[str, ...]:
        return tuple(d.dept_code for d in departments if d.state is state)

    flags = KpiFlags(
        stale_departments=tuple(d.dept_code for d in departments if d.stale),
        missing_departments=codes(DeptState.MISSING),
        excluded_departments=codes(DeptState.EXCLUDED),
        undefined_departments=codes(DeptState.UNDEFINED),
        excluded_fact_ids=tuple(
            sorted(
                i for d in departments if d.state is DeptState.EXCLUDED for i in d.input_fact_ids
            )
        ),
        no_target=target is None,
    )
    oldest_inputs = [d for d in as_of_by_dept.values() if d is not None]
    return KpiResult(
        kpi_key=definition.key,
        kpi_version=definition.version,
        period_year=data.period_year,
        value=value,
        target=target_value,
        variance_abs=variance_abs,
        variance_pct=variance_pct,
        status=status,
        inputs=tuple(institution_terms),
        input_fact_ids=tuple(sorted({i for code in eligible for i in ids_by_dept[code]})),
        departments=tuple(departments),
        flags=flags,
        as_of=min(oldest_inputs) if oldest_inputs else None,
    )


def compute_kpi(
    definition: KpiDefinition,
    target: KpiTarget | None,
    data: PeriodData,
    today: date,
    stale_after_days: int,
) -> KpiResult:
    return _compute(definition, target, _Index(data), today, stale_after_days)


def compute_all(
    definitions: Sequence[KpiDefinition],
    targets: Mapping[str, KpiTarget],
    data: PeriodData,
    today: date,
    stale_after_days: int,
) -> list[KpiResult]:
    """Every active definition, in the order given, for one period."""
    index = _Index(data)
    return [
        _compute(d, targets.get(d.key), index, today, stale_after_days)
        for d in definitions
        if d.active
    ]
