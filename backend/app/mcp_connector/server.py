"""The connector as an MCP server (rule 6, docs/ARCHITECTURE.md section 4).

Every tool is read-only and answers exactly what one method of the `Connector` protocol answers, so
an agent sees the same data whether it holds the in-memory connector or an MCP client. The server
reads through a `Connector` too, never the store, so swapping the store for PostgreSQL later does
not touch this file.

Written against mcp 2.3 (`MCPServer`, formerly `FastMCP`). A tool that returns models gets an
output schema. A list or an optional arrives as {"result": ...}, a single model as itself.
"""

from datetime import date

from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from pydantic import BaseModel

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

NAME = "edss-connector"
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)


class Calendar(BaseModel):
    """The four small facts every run needs before it reads anything."""

    periods: tuple[str, ...]
    current_period: str
    today: date
    stale_after_days: int


def build_server(connector: Connector) -> MCPServer:
    server = MCPServer(
        NAME,
        instructions="Read-only university data for the EDSS agents. Every figure carries its "
        "source, as-of date and status. Nothing here can change data.",
    )
    tool = server.tool(annotations=READ_ONLY)

    @tool
    def get_calendar() -> Calendar:
        """The academic periods, the current one, today's date and the freshness window."""
        return Calendar(
            periods=connector.periods(),
            current_period=connector.current_period(),
            today=connector.today(),
            stale_after_days=connector.stale_after_days(),
        )

    @tool
    def list_departments() -> list[Department]:
        """Every department, by code and name."""
        return list(connector.list_departments())

    @tool
    def get_kpi_definitions() -> list[KpiDefinition]:
        """Every KPI definition, with its formula, unit and placeholder marker."""
        return list(connector.get_kpi_definitions())

    @tool
    def get_targets(period: str) -> list[KpiTarget]:
        """The KPI targets for one academic period, such as 2025-26."""
        return list(connector.get_targets(period))

    @tool
    def get_domain_metrics(domain: Domain, period: str) -> list[MetricFact]:
        """Every record for one area and period, each with its source, as-of date and status."""
        return list(connector.get_domain_metrics(domain, period))

    @tool
    def get_publications(period: str) -> list[Publication]:
        """Publications for one period, with the departments each is credited to."""
        return list(connector.get_publications(period))

    @tool
    def get_data_health(period: str) -> list[HealthCellInfo]:
        """How fresh each department's data is in each area, and which records are not final."""
        return list(connector.get_data_health(period))

    @tool
    def get_scope_grants() -> list[ScopeGrant]:
        """Which areas the Registrar has authorised to be read, and until when."""
        return list(connector.get_scope_grants())

    @tool
    def get_evidence(fact_id: int) -> MetricFact | None:
        """One record by its id, or nothing if there is no such record."""
        return connector.get_fact(fact_id)

    @tool
    def get_source(source_system_id: int) -> SourceSystem | None:
        """The source system a record came from, or nothing if there is no such source."""
        return connector.get_source(source_system_id)

    return server
