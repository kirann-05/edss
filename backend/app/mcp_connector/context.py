"""Which connector the current run reads through, when runs read over MCP.

The graph is built once, but every run needs its own MCP session with its own token. So the graph
holds a `RunConnector`, which answers each call with whatever the current run opened. The run's
thread opens it with `reading_through`, and LangGraph runs parallel nodes with a copy of that
thread's context, so all four domain agents see the same run's session.

Outside a run there is nothing to read through, and a call fails loudly rather than falling back
to reading directly.
"""

from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date

from app.agents.connector import Connector, HealthCellInfo, ScopeGrant
from app.domain.enums import Domain
from app.domain.models import (
    Department,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    Publication,
    SourceSystem,
)
from app.mcp_connector.client import McpConnector
from app.mcp_connector.tokens import RunTokens

_current: ContextVar[Connector | None] = ContextVar("edss_run_connector", default=None)


@contextmanager
def reading_through(connector: Connector) -> Iterator[None]:
    token = _current.set(connector)
    try:
        yield
    finally:
        _current.reset(token)


@contextmanager
def mcp_session(
    url: str, tokens: RunTokens, run_id: str, actor: str, domains: Iterable[Domain]
) -> Iterator[McpConnector]:
    """A token for this run's areas, a session that uses it, and both gone when the run stops."""
    token = tokens.mint(run_id, actor, domains)
    try:
        with McpConnector(url, token) as connector:
            yield connector
    finally:
        tokens.revoke(run_id)


class RunConnector:
    """The graph's connector when runs read over MCP: the current run's session."""

    def _now(self) -> Connector:
        connector = _current.get()
        if connector is None:
            raise RuntimeError("no connector is open for this run")
        return connector

    def periods(self) -> tuple[str, ...]:
        return self._now().periods()

    def current_period(self) -> str:
        return self._now().current_period()

    def today(self) -> date:
        return self._now().today()

    def stale_after_days(self) -> int:
        return self._now().stale_after_days()

    def list_departments(self) -> Sequence[Department]:
        return self._now().list_departments()

    def get_kpi_definitions(self) -> Sequence[KpiDefinition]:
        return self._now().get_kpi_definitions()

    def get_targets(self, period: str) -> Sequence[KpiTarget]:
        return self._now().get_targets(period)

    def get_domain_metrics(self, domain: Domain, period: str) -> Sequence[MetricFact]:
        return self._now().get_domain_metrics(domain, period)

    def get_publications(self, period: str) -> Sequence[Publication]:
        return self._now().get_publications(period)

    def get_data_health(self, period: str) -> Sequence[HealthCellInfo]:
        return self._now().get_data_health(period)

    def get_scope_grants(self) -> Sequence[ScopeGrant]:
        return self._now().get_scope_grants()

    def get_fact(self, fact_id: int) -> MetricFact | None:
        return self._now().get_fact(fact_id)

    def get_source(self, source_system_id: int) -> SourceSystem | None:
        return self._now().get_source(source_system_id)
