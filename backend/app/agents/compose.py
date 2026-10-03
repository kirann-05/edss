"""Builds the decision brief from the engine's results, deterministically (Lab 3 assembly skill).

Nothing in here calls a model. Figures are copied from the engine's results, the summary is
made of tokens, and the assumptions and data health sections are derived from the flags, so the
parts of a brief that carry numbers and caveats never depend on a model behaving.
"""

from collections.abc import Sequence
from decimal import Decimal

from app.agents.connector import HealthCellInfo
from app.agents.models import (
    AssumptionItem,
    BriefDocument,
    FactFigure,
    HealthNote,
    KpiFigure,
    OptionSet,
    Plan,
    SummaryItem,
)
from app.domain.enums import Domain, FactStatus, KpiStatus
from app.domain.models import KpiDefinition, MetricFact
from app.kpi.catalogue import CATALOGUE
from app.kpi.results import DeptState, KpiResult

_NON_FINAL_NOTES = {
    FactStatus.PROVISIONAL: (
        "provisional",
        "Provisional figures are shown apart and are never counted as final.",
    ),
    FactStatus.FORECAST: (
        "forecast",
        "Forecast figures are shown apart and are never added to actuals.",
    ),
}


def figure_from(definition: KpiDefinition, result: KpiResult, trend: str = "unknown") -> KpiFigure:
    """Freeze the engine's result, with the definition facts that checks V6 and V9 re-derive from."""
    return KpiFigure(
        key=definition.key,
        name=definition.name,
        domain=definition.domain,
        unit=definition.unit,
        precision=definition.display_precision,
        higher_is_better=definition.higher_is_better,
        placeholder=definition.placeholder,
        definition_active=definition.active,
        definition_approved=definition.approved_by is not None,
        kpi_version=result.kpi_version,
        period_year=result.period_year,
        value=result.value,
        target=result.target,
        variance_abs=result.variance_abs,
        variance_pct=result.variance_pct,
        status=result.status,
        inputs=result.inputs,
        input_fact_ids=result.input_fact_ids,
        as_of=result.as_of,
        flags=result.flags,
        band_pct=definition.at_risk_band_pct,
        included_departments=tuple(
            d.dept_code
            for d in result.departments
            if d.state in (DeptState.OK, DeptState.UNDEFINED)
        ),
        trend=trend,  # type: ignore[arg-type]
    )


def build_summary(figures: Sequence[KpiFigure]) -> tuple[SummaryItem, ...]:
    return tuple(
        SummaryItem(
            kpi_key=f.key,
            headline=(
                f"{{{{kpi:{f.key}}}}} against a target of {{{{kpi:{f.key}.target}}}}: "
                f"{{{{kpi:{f.key}.status}}}}, {{{{kpi:{f.key}.gap}}}}."
            ),
        )
        for f in figures
    )


def _names(figures: Sequence[KpiFigure], keys: Sequence[str]) -> str:
    wanted = set(keys)
    return ", ".join(f.name for f in figures if f.key in wanted)


def _by_department(figures: Sequence[KpiFigure], pick) -> dict[str, list[str]]:
    affected: dict[str, list[str]] = {}
    for figure in figures:
        for dept in pick(figure.flags):
            affected.setdefault(dept, []).append(figure.key)
    return affected


def build_assumptions(
    figures: Sequence[KpiFigure], health: Sequence[HealthCellInfo], domains: Sequence[Domain]
) -> tuple[AssumptionItem, ...]:
    """What the reader must know to read the figures correctly, stated, never implied."""
    items: list[AssumptionItem] = []
    oldest = min((f.as_of for f in figures if f.as_of is not None), default=None)
    if oldest is not None:
        items.append(
            AssumptionItem(
                kind="as_of",
                text=f"Figures are only as fresh as their oldest input, dated {oldest.isoformat()}.",
            )
        )
    if any(f.placeholder for f in figures):
        items.append(
            AssumptionItem(
                kind="placeholder",
                text=(
                    "KPI definitions and targets are placeholders pending IQAC approval, so statuses "
                    "show how the system works and are not official."
                ),
                kpi_keys=tuple(f.key for f in figures if f.placeholder),
            )
        )

    templates = (
        ("stale", lambda fl: fl.stale_departments,
         "{dept} data is older than the freshness window. It is used, and flagged, in: {names}."),
        ("missing", lambda fl: fl.missing_departments,
         "{dept} has no record for this period. It is left out of {names} and never counted as zero."),
        ("excluded", lambda fl: fl.excluded_departments,
         "{dept} is left out of {names} because an input is provisional, forecast or pending reconciliation."),
        ("undefined", lambda fl: fl.undefined_departments,
         "{dept} has nothing to divide by for {names}, so it has no value there, which is different from zero."),
    )  # fmt: skip
    for kind, pick, template in templates:
        for dept, keys in sorted(_by_department(figures, pick).items()):
            items.append(
                AssumptionItem(
                    kind=kind,  # type: ignore[arg-type]
                    text=template.format(dept=dept, names=_names(figures, keys)),
                    dept_code=dept,
                    kpi_keys=tuple(keys),
                )
            )

    present = {s for c in health if c.domain in domains for s in c.non_final}
    for status, (kind, text) in _NON_FINAL_NOTES.items():
        if status in present:
            items.append(AssumptionItem(kind=kind, text=text))  # type: ignore[arg-type]
    return tuple(items)


def build_health_notes(
    health: Sequence[HealthCellInfo], domains: Sequence[Domain]
) -> tuple[HealthNote, ...]:
    """Every department and domain that is stale, missing or holds a non-final figure."""
    return tuple(
        HealthNote(
            dept_code=c.dept_code,
            domain=c.domain,
            state=c.state,
            as_of=c.as_of,
            non_final=c.non_final,
        )
        for c in health
        if c.domain in domains and (c.state in ("stale", "missing") or c.non_final)
    )


def off_target(figures: Sequence[KpiFigure], options_for: str = "off_target") -> list[KpiFigure]:
    """The KPIs that need options: missed or at risk, or every one that has a status."""
    if options_for == "all":
        return [f for f in figures if f.status is not KpiStatus.UNDEFINED]
    return [f for f in figures if f.status in (KpiStatus.MISSED, KpiStatus.AT_RISK)]


def compose_brief(
    plan: Plan,
    figures: Sequence[KpiFigure],
    option_sets: Sequence[OptionSet],
    health: Sequence[HealthCellInfo],
) -> BriefDocument:
    order = {key: i for i, key in enumerate(plan.kpi_keys)}
    ordered = sorted(figures, key=lambda f: order.get(f.key, len(order)))
    domains = plan.domains
    # the health section covers every domain the plan reads, plus the reference counts it divides by
    health_domains = (*domains, Domain.REFERENCE)
    return BriefDocument(
        title=f"Decision brief, {plan.period_year}",
        period_year=plan.period_year,
        plan_kpi_keys=plan.kpi_keys,
        kpis=tuple(ordered),
        summary=build_summary(ordered),
        option_sets=tuple(sorted(option_sets, key=lambda s: order.get(s.kpi_key, len(order)))),
        assumptions=build_assumptions(ordered, health, health_domains),
        data_health=build_health_notes(health, health_domains),
    )


__all__ = [
    "build_assumptions",
    "build_health_notes",
    "build_summary",
    "compose_brief",
    "fact_figure",
    "figure_from",
    "off_target",
    "trend_word",
]


def trend_word(
    value: Decimal | None,
    previous: Decimal | None,
    target: Decimal | None,
    higher_is_better: bool,
) -> str:
    """improving, declining, flat or unknown, decided here in code and told to a model in words.

    A change smaller than half a percent of the target counts as flat, so noise is not a trend.
    """
    if value is None or previous is None:
        return "unknown"
    margin = abs(target) * Decimal("0.005") if target else Decimal(0)
    change = value - previous
    if abs(change) <= margin:
        return "flat"
    return "improving" if (change > 0) == higher_is_better else "declining"


def fact_figure(fact: MetricFact) -> FactFigure:
    """A source record in the form a {{fact:ID}} token resolves to."""
    return FactFigure(
        id=fact.id,
        label=CATALOGUE[fact.metric_key].label,
        dept_code=fact.dept_code,
        value=fact.value,
        unit=fact.unit,
        status=fact.status,
        source_ref=fact.source_ref,
    )
