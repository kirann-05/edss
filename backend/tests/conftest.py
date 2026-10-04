from datetime import date

import pytest

from app.agents.compose import fact_figure, figure_from, trend_word
from app.agents.llm import FakeLLM
from app.agents.models import Plan
from app.agents.tokens import RenderContext
from app.domain.enums import Domain
from app.services.connector import InMemoryConnector, ScopeRegistry
from app.services.store import DataStore

pytest_plugins = ["tests.database_fixtures"]  # scratch PostgreSQL, used by tests/db and tests/api

REF = date(2026, 10, 1)
DOMAINS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE)


@pytest.fixture(scope="session")
def store():
    return DataStore.build(REF, 90)


@pytest.fixture(scope="session")
def connector(store):
    return InMemoryConnector(store, ScopeRegistry(REF))


@pytest.fixture(scope="session")
def figures(store):
    period = store.current_period
    previous = store.periods[store.periods.index(period) - 1]
    out = []
    for definition in store.definitions:
        result = store.result(definition.key, period)
        before = store.result(definition.key, previous)
        trend = trend_word(result.value, before.value, result.target, definition.higher_is_better)
        out.append(figure_from(definition, result, trend))
    return out


@pytest.fixture(scope="session")
def plan(store, figures):
    return Plan(
        request="Governing Council brief for the current year",
        period_year=store.current_period,
        domains=DOMAINS,
        kpi_keys=tuple(f.key for f in figures),
        options_for="off_target",
        audience="Governing Council review",
        steps=(),
    )


@pytest.fixture(scope="session")
def health(connector):
    return list(connector.get_data_health(connector.current_period()))


@pytest.fixture(scope="session")
def facts_by_id(store):
    return store.facts_by_id


@pytest.fixture(scope="session")
def render_context(figures, store):
    return RenderContext(
        kpis={f.key: f for f in figures},
        facts={fid: fact_figure(f) for fid, f in store.facts_by_id.items()},
    )


@pytest.fixture
def model():
    return FakeLLM("drafter")
