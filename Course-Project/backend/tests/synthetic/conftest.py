from datetime import date

import pytest

from app.kpi.engine import PeriodData, compute_all
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.synthetic.generator import generate

REF = date(2026, 10, 1)
STALE_AFTER_DAYS = 90


@pytest.fixture(scope="session")
def ref():
    return REF


@pytest.fixture(scope="session")
def dataset():
    return generate(REF)


def period_data(dataset, period):
    return PeriodData(
        period_year=period,
        departments=dataset.departments,
        facts=tuple(f for f in dataset.facts if f.period_year == period),
        publications=tuple(p for p in dataset.publications if p.period_year == period),
        is_current=period == dataset.current_period,
    )


@pytest.fixture(scope="session")
def results(dataset):
    """KPI results for the current period, keyed by KPI key."""
    period = dataset.current_period
    targets = {t.kpi_key: t for t in load_seed_targets() if t.period_year == period}
    computed = compute_all(
        load_seed_definitions(), targets, period_data(dataset, period), REF, STALE_AFTER_DAYS
    )
    return {r.kpi_key: r for r in computed}


@pytest.fixture(scope="session")
def facts_by_id(dataset):
    return {f.id: f for f in dataset.facts}
