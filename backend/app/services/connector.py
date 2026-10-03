"""The in-memory connector: the store behind the connector protocol.

This module is on the services side of the line, so it may read the store. Agents may not, they
get one of these through the protocol. The Postgres version, and later the MCP server in front
of it, replace this file only.
"""

from collections.abc import Sequence
from datetime import date, timedelta

from app.agents.connector import Connector, HealthCellInfo, ScopeGrant
from app.core.rbac import Scope
from app.domain.enums import Domain, FactStatus
from app.domain.models import (
    Department,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    Publication,
    SourceSystem,
)
from app.services import views
from app.services.store import DataStore

_ALL_DOMAINS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE)


class ScopeRegistry:
    """Who authorised which domain to be read. The Registrar manages it (docs/SPEC.md FR-2)."""

    def __init__(self, today: date, granted_by: str = "registrar@edss.test") -> None:
        self._grants = [
            ScopeGrant(
                domain=domain,
                dept_code=None,
                granted_by=granted_by,
                granted_on=today,
                expires_on=today + timedelta(days=365),
                active=True,
            )
            for domain in _ALL_DOMAINS
        ]

    def all(self) -> list[ScopeGrant]:
        return list(self._grants)

    def revoke(self, domain: Domain) -> None:
        self._grants = [
            ScopeGrant(**{**g.__dict__, "active": False}) if g.domain is domain else g
            for g in self._grants
        ]

    def grant(self, domain: Domain, granted_by: str, today: date) -> None:
        self._grants = [g for g in self._grants if g.domain is not domain]
        self._grants.append(
            ScopeGrant(domain, None, granted_by, today, today + timedelta(days=365), True)
        )


class InMemoryConnector(Connector):
    def __init__(self, store: DataStore, scopes: ScopeRegistry) -> None:
        self._store = store
        self._scopes = scopes

    def periods(self) -> tuple[str, ...]:
        return self._store.periods

    def current_period(self) -> str:
        return self._store.current_period

    def today(self) -> date:
        return self._store.today

    def stale_after_days(self) -> int:
        return self._store.stale_after_days

    def list_departments(self) -> Sequence[Department]:
        return self._store.dataset.departments

    def get_kpi_definitions(self) -> Sequence[KpiDefinition]:
        return self._store.definitions

    def get_targets(self, period: str) -> Sequence[KpiTarget]:
        return self._store.targets(period)

    def get_domain_metrics(self, domain: Domain, period: str) -> Sequence[MetricFact]:
        return self._store.facts(period, domain=domain)

    def get_publications(self, period: str) -> Sequence[Publication]:
        return [p for p in self._store.dataset.publications if p.period_year == period]

    def get_data_health(self, period: str) -> Sequence[HealthCellInfo]:
        health = views.build_data_health(self._store, Scope(everything=True), period)
        return [
            HealthCellInfo(
                dept_code=c.dept_code,
                domain=c.domain,
                state=c.state or "missing",
                as_of=c.as_of,
                age_days=c.age_days,
                non_final=tuple(
                    status
                    for status, count in (
                        (FactStatus.PROVISIONAL, c.non_final.provisional),
                        (FactStatus.FORECAST, c.non_final.forecast),
                        (FactStatus.PENDING_RECONCILIATION, c.non_final.pending_reconciliation),
                    )
                    if count > 0
                ),
            )
            for c in health.cells
        ]

    def get_scope_grants(self) -> Sequence[ScopeGrant]:
        return self._scopes.all()

    def get_fact(self, fact_id: int) -> MetricFact | None:
        return self._store.facts_by_id.get(fact_id)

    def get_source(self, source_system_id: int) -> SourceSystem | None:
        return self._store.sources.get(source_system_id)
