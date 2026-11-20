"""The one governed surface agents read data through (rule 6, docs/ARCHITECTURE.md section 4).

Agents depend on this protocol and on nothing else for data. The methods mirror the MCP tools
the connector server will expose (list_departments, get_domain_metrics, get_kpi_definitions,
get_targets, get_data_health, get_evidence), so putting the MCP server in front of the same
surface later changes no agent. A test fails the build if an agent module imports a data reader
(tests/agents/test_architecture.py).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.domain.enums import Domain, FactStatus
from app.domain.models import (
    Department,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    Publication,
    SourceSystem,
)


@dataclass(frozen=True)
class HealthCellInfo:
    dept_code: str
    domain: Domain
    state: str  # fresh, stale, missing or closed
    as_of: date | None
    age_days: int | None
    non_final: tuple[FactStatus, ...]


@dataclass(frozen=True)
class ScopeGrant:
    """A Registrar's authorisation to read one domain, optionally for one department (FR-2)."""

    domain: Domain
    dept_code: str | None
    granted_by: str
    granted_on: date
    expires_on: date | None
    active: bool


class Connector(Protocol):
    def periods(self) -> tuple[str, ...]: ...

    def current_period(self) -> str: ...

    def today(self) -> date: ...

    def stale_after_days(self) -> int: ...

    def list_departments(self) -> Sequence[Department]: ...

    def get_kpi_definitions(self) -> Sequence[KpiDefinition]: ...

    def get_targets(self, period: str) -> Sequence[KpiTarget]: ...

    def get_domain_metrics(self, domain: Domain, period: str) -> Sequence[MetricFact]: ...

    def get_publications(self, period: str) -> Sequence[Publication]: ...

    def get_data_health(self, period: str) -> Sequence[HealthCellInfo]: ...

    def get_scope_grants(self) -> Sequence[ScopeGrant]: ...

    def get_fact(self, fact_id: int) -> MetricFact | None: ...

    def get_source(self, source_system_id: int) -> SourceSystem | None: ...
