"""Builds API responses from engine results and applies department scope.

Scope is applied here, once, and not in each route, so there is exactly one place to read when
asking "can a HOD see another department's numbers?". The answer must stay no.
"""

from collections import defaultdict
from statistics import median

from app.api import schemas as s
from app.core.rbac import Scope
from app.domain.enums import Domain, FactStatus, KpiStatus
from app.domain.models import Department, MetricFact
from app.kpi.catalogue import CATALOGUE
from app.kpi.describe import describe_formula, describe_term
from app.kpi.results import DepartmentValue, DeptState
from app.services.store import DataStore

HEALTH_DOMAINS = (
    Domain.ACADEMIC,
    Domain.RESEARCH,
    Domain.PLACEMENT,
    Domain.FINANCE,
    Domain.REFERENCE,
)
_NON_FINAL = (FactStatus.PROVISIONAL, FactStatus.FORECAST, FactStatus.PENDING_RECONCILIATION)


def _flag_list(codes: tuple[str, ...], scope: Scope) -> s.DeptFlagList:
    return s.DeptFlagList(departments=[c for c in codes if scope.allows(c)], total=len(codes))


def _trend(store: DataStore, key: str) -> list[s.TrendPoint]:
    points = []
    for period in store.periods:
        result = store.result(key, period)
        points.append(
            s.TrendPoint(
                period_year=period, value=result.value, target=result.target, status=result.status
            )
        )
    return points


def build_kpi(store: DataStore, scope: Scope, key: str, period: str) -> s.KpiOut:
    definition = store.definition(key)
    result = store.result(key, period)
    flags = result.flags
    return s.KpiOut(
        key=definition.key,
        name=definition.name,
        domain=definition.domain,
        domain_tags=list(definition.domain_tags),
        framework=definition.framework,
        placeholder=definition.placeholder,
        note=definition.note,
        unit=definition.unit,
        precision=definition.display_precision,
        higher_is_better=definition.higher_is_better,
        version=result.kpi_version,
        formula=definition.formula,
        formula_text=describe_formula(definition.formula),
        period_year=period,
        value=result.value,
        target=result.target,
        variance_abs=result.variance_abs,
        variance_pct=result.variance_pct,
        status=result.status,
        as_of=result.as_of,
        flags=s.KpiFlagsOut(
            stale=_flag_list(flags.stale_departments, scope),
            missing=_flag_list(flags.missing_departments, scope),
            excluded=_flag_list(flags.excluded_departments, scope),
            undefined=_flag_list(flags.undefined_departments, scope),
            excluded_fact_count=len(flags.excluded_fact_ids),
            no_target=flags.no_target,
        ),
        input_fact_count=len(result.input_fact_ids),
        trend=_trend(store, key),
    )


def build_kpi_list(store: DataStore, scope: Scope, period: str) -> s.KpiListOut:
    kpis = [build_kpi(store, scope, key, period) for key in store.results(period)]
    counts = {status: sum(1 for k in kpis if k.status is status) for status in KpiStatus}
    as_ofs = [k.as_of for k in kpis if k.as_of is not None]
    facts = store.facts(period)
    return s.KpiListOut(
        period_year=period,
        is_current=period == store.current_period,
        oldest_as_of=min(as_ofs) if as_ofs else None,
        newest_as_of=max((f.as_of for f in facts), default=None),
        summary=s.StatusSummary(
            met=counts[KpiStatus.MET],
            at_risk=counts[KpiStatus.AT_RISK],
            missed=counts[KpiStatus.MISSED],
            undefined=counts[KpiStatus.UNDEFINED],
        ),
        kpis=kpis,
    )


def department_row(scope: Scope, dept: Department, value: DepartmentValue) -> s.DepartmentRowOut:
    if not scope.allows(dept.code):
        return s.DepartmentRowOut(
            dept_code=dept.code, dept_name=dept.name, school=dept.school, access="restricted"
        )
    return s.DepartmentRowOut(
        dept_code=dept.code,
        dept_name=dept.name,
        school=dept.school,
        access="visible",
        state=value.state,
        value=value.value,
        inputs=[
            s.InputTermOut(label=t.label, description=describe_term(t.label), value=t.value)
            for t in value.inputs
        ],
        stale=value.stale,
        as_of=value.as_of,
        reason=value.reason,
        fact_ids=list(value.input_fact_ids),
    )


def fact_out(store: DataStore, fact: MetricFact, used: bool) -> s.FactOut:
    source = store.sources[fact.source_system_id]
    return s.FactOut(
        id=fact.id,
        metric_key=fact.metric_key,
        metric_label=CATALOGUE[fact.metric_key].label,
        domain=fact.domain,
        dept_code=fact.dept_code,
        period_year=fact.period_year,
        period_sub=fact.period_sub,
        value=fact.value,
        unit=fact.unit,
        status=fact.status,
        as_of=fact.as_of,
        source_system=source.name,
        source_owner=source.owner_office,
        source_ref=fact.source_ref,
        batch_id=fact.batch_id,
        used=used,
    )


def _rows(
    store: DataStore, scope: Scope, values: tuple[DepartmentValue, ...]
) -> list[s.DepartmentRowOut]:
    return [department_row(scope, store.departments[v.dept_code], v) for v in values]


def build_drilldown(store: DataStore, scope: Scope, key: str, period: str) -> s.KpiDrilldownOut:
    result = store.result(key, period)
    used_ids = set(result.input_fact_ids)
    wanted_ids = sorted(used_ids | set(result.flags.excluded_fact_ids))

    facts: list[s.FactOut] = []
    hidden = 0
    for fact_id in wanted_ids:
        fact = store.facts_by_id[fact_id]
        if scope.allows(fact.dept_code):
            facts.append(fact_out(store, fact, used=fact_id in used_ids))
        else:
            hidden += 1

    spread = None
    values = [
        v.value for v in result.departments if v.state is DeptState.OK and v.value is not None
    ]
    if scope.everything and values:
        spread = s.SpreadOut(
            count=len(values),
            min=min(values),
            median=median(values),
            max=max(values),
            simple_mean=sum(values) / len(values),
        )

    return s.KpiDrilldownOut(
        kpi=build_kpi(store, scope, key, period),
        inputs=[
            s.InputTermOut(label=t.label, description=describe_term(t.label), value=t.value)
            for t in result.inputs
        ],
        departments=_rows(store, scope, result.departments),
        spread=spread,
        facts=facts,
        facts_hidden=hidden,
        access="full" if scope.everything else "restricted",
    )


def build_domain_view(
    store: DataStore, scope: Scope, domain: Domain, period: str
) -> s.DomainViewOut:
    return s.DomainViewOut(
        domain=domain,
        period_year=period,
        kpis=[
            s.DomainKpiOut(
                kpi=build_kpi(store, scope, d.key, period),
                departments=_rows(store, scope, store.result(d.key, period).departments),
            )
            for d in store.definitions
            if d.domain is domain
        ],
    )


def build_data_health(store: DataStore, scope: Scope, period: str) -> s.DataHealthOut:
    is_current = period == store.current_period
    grouped: dict[tuple[str, Domain], list[MetricFact]] = defaultdict(list)
    for fact in store.facts(period):
        grouped[(fact.dept_code, fact.domain)].append(fact)

    cells: list[s.HealthCellOut] = []
    visible_batches: set[int] = set()
    for dept in store.dataset.departments:
        for domain in HEALTH_DOMAINS:
            if not scope.allows(dept.code):
                cells.append(s.HealthCellOut(dept_code=dept.code, domain=domain, restricted=True))
                continue
            facts = grouped.get((dept.code, domain), [])
            if not facts:
                cells.append(s.HealthCellOut(dept_code=dept.code, domain=domain, state="missing"))
                continue
            oldest = min(f.as_of for f in facts)
            age = (store.today - oldest).days
            if not is_current:
                state: s.HealthState = "closed"
            elif age > store.stale_after_days:
                state = "stale"
            else:
                state = "fresh"
            batch_ids = sorted({f.batch_id for f in facts})
            visible_batches.update(batch_ids)
            counts = {status: sum(1 for f in facts if f.status is status) for status in _NON_FINAL}
            cells.append(
                s.HealthCellOut(
                    dept_code=dept.code,
                    domain=domain,
                    state=state,
                    as_of=oldest,
                    age_days=age,
                    fact_count=len(facts),
                    non_final=s.NonFinalCounts(
                        provisional=counts[FactStatus.PROVISIONAL],
                        forecast=counts[FactStatus.FORECAST],
                        pending_reconciliation=counts[FactStatus.PENDING_RECONCILIATION],
                    ),
                    batch_ids=batch_ids,
                )
            )

    if scope.everything:
        visible_batches = {f.batch_id for f in store.facts(period)}
    batches = [
        s.BatchOut(
            id=b.id,
            domain=b.domain,
            source=store.sources[b.source_system_id].name,
            owner_office=store.sources[b.source_system_id].owner_office,
            file_ref=b.file_ref,
            row_count=b.row_count,
            rejected_count=b.rejected_count,
            finished_at=b.finished_at,
            checksum=b.checksum,
        )
        for b in sorted(store.batches.values(), key=lambda b: b.id)
        if b.id in visible_batches
    ]

    shown = [c for c in cells if not c.restricted]
    return s.DataHealthOut(
        period_year=period,
        is_current=is_current,
        today=store.today,
        stale_after_days=store.stale_after_days,
        domains=list(HEALTH_DOMAINS),
        departments=[
            s.DepartmentOut(code=d.code, name=d.name, school=d.school)
            for d in store.dataset.departments
        ],
        cells=cells,
        batches=batches,
        summary=s.HealthSummary(
            fresh=sum(1 for c in shown if c.state == "fresh"),
            stale=sum(1 for c in shown if c.state == "stale"),
            missing=sum(1 for c in shown if c.state == "missing"),
            closed=sum(1 for c in shown if c.state == "closed"),
        ),
    )
