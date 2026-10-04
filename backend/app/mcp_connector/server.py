"""The connector as an MCP server (rule 6, docs/ARCHITECTURE.md section 4).

Every tool is read-only and answers exactly what one method of the `Connector` protocol answers, so
an agent sees the same data whether it holds the in-memory connector or an MCP client. The server
reads through a `Connector` too, never the store, so swapping the store for PostgreSQL later does
not touch this file.

With run tokens, every call must carry a bearer token minted for a run, and a read outside that
run's areas is refused. Either way, with an audit log every call and every refusal is one row:
who, which tool, the arguments, and a hash of what was returned.

Written against mcp 2.3 (`MCPServer`, formerly `FastMCP`). A tool that returns models gets an
output schema. A list or an optional arrives as {"result": ...}, a single model as itself.
"""

from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from mcp_types import ToolAnnotations
from pydantic import BaseModel, TypeAdapter

from app.agents.connector import Connector, HealthCellInfo, ScopeGrant
from app.agents.runtime import digest
from app.domain.enums import Domain
from app.domain.models import (
    Department,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    Publication,
    SourceSystem,
)
from app.governance.audit import AuditLog
from app.mcp_connector.tokens import REFERENCE, RunTokens, scope_for

NAME = "edss-connector"
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)
T = TypeVar("T")


class Calendar(BaseModel):
    """The four small facts every run needs before it reads anything."""

    periods: tuple[str, ...]
    current_period: str
    today: date
    stale_after_days: int


class OutOfScope(ToolError):
    """A read the run's token does not allow."""


def build_server(
    connector: Connector,
    *,
    audit: AuditLog | None = None,
    tokens: RunTokens | None = None,
    public_url: str = "http://127.0.0.1:8000",
) -> MCPServer:
    server = MCPServer(
        NAME,
        instructions="Read-only university data for the EDSS agents. Every figure carries its "
        "source, as-of date and status. Nothing here can change data.",
        token_verifier=tokens,
        auth=AuthSettings(
            issuer_url=public_url,
            resource_server_url=f"{public_url}/mcp",
            required_scopes=[REFERENCE],
            # the tokens are minted and checked inside this process and never issued for any
            # other server, so there is no audience to confuse
            validate_token_resource=False,
        )
        if tokens
        else None,
    )
    tool = server.tool(annotations=READ_ONLY)

    def serve(name: str, arguments: dict[str, Any], scope: str | None, read: Callable[[], T]) -> T:
        """Check the token's scope, read, and write one audit row either way."""
        access = get_access_token()
        who = access.subject if access and access.subject else "in-process"
        run_id = (access.claims or {}).get("run_id") if access else None
        if tokens is not None and (access is None or (scope and scope not in access.scopes)):
            if audit:
                audit.append(
                    actor_type="agent", actor_id=who, action="connector.refused", run_id=run_id,
                    inputs={"tool": name, "arguments": arguments, "needs": scope},
                    outputs={"reason": "outside this run's scope"},
                )  # fmt: skip
            raise OutOfScope(f"{name} needs {scope}, which this run was not granted")
        result = read()
        if audit:
            plain = TypeAdapter(Any).dump_python(result, mode="json")
            audit.append(
                actor_type="agent", actor_id=who, action="connector.call", run_id=run_id,
                inputs={"tool": name, "arguments": arguments},
                outputs={
                    "result_hash": digest(plain),
                    "items": len(plain) if isinstance(plain, list) else int(plain is not None),
                },
            )  # fmt: skip
        return result

    @tool
    def get_calendar() -> Calendar:
        """The academic periods, the current one, today's date and the freshness window."""
        return serve(
            "get_calendar", {}, REFERENCE,
            lambda: Calendar(
                periods=connector.periods(), current_period=connector.current_period(),
                today=connector.today(), stale_after_days=connector.stale_after_days(),
            ),
        )  # fmt: skip

    @tool
    def list_departments() -> list[Department]:
        """Every department, by code and name."""
        return serve("list_departments", {}, REFERENCE, lambda: list(connector.list_departments()))

    @tool
    def get_kpi_definitions() -> list[KpiDefinition]:
        """Every KPI definition, with its formula, unit and placeholder marker."""
        return serve(
            "get_kpi_definitions", {}, REFERENCE, lambda: list(connector.get_kpi_definitions())
        )

    @tool
    def get_targets(period: str) -> list[KpiTarget]:
        """The KPI targets for one academic period, such as 2025-26."""
        return serve(
            "get_targets", {"period": period}, REFERENCE,
            lambda: list(connector.get_targets(period)),
        )  # fmt: skip

    @tool
    def get_domain_metrics(domain: Domain, period: str) -> list[MetricFact]:
        """Every record for one area and period, each with its source, as-of date and status."""
        return serve(
            "get_domain_metrics", {"domain": domain.value, "period": period}, scope_for(domain),
            lambda: list(connector.get_domain_metrics(domain, period)),
        )  # fmt: skip

    @tool
    def get_publications(period: str) -> list[Publication]:
        """Publications for one period, with the departments each is credited to."""
        # titles and credits only, which validation needs to stop a shared paper being counted
        # twice even in a plan without research
        return serve(
            "get_publications", {"period": period}, REFERENCE,
            lambda: list(connector.get_publications(period)),
        )  # fmt: skip

    @tool
    def get_data_health(period: str) -> list[HealthCellInfo]:
        """How fresh each department's data is in each area, and which records are not final."""
        return serve(
            "get_data_health", {"period": period}, REFERENCE,
            lambda: list(connector.get_data_health(period)),
        )  # fmt: skip

    @tool
    def get_scope_grants() -> list[ScopeGrant]:
        """Which areas the Registrar has authorised to be read, and until when."""
        return serve("get_scope_grants", {}, REFERENCE, lambda: list(connector.get_scope_grants()))

    @tool
    def get_evidence(fact_id: int) -> MetricFact | None:
        """One record by its id, or nothing if there is no such record."""
        fact = connector.get_fact(fact_id)
        # a record is only as visible as its area, so a missing record and a forbidden one
        # are told apart only in the audit log
        scope = scope_for(fact.domain) if fact else REFERENCE
        return serve("get_evidence", {"fact_id": fact_id}, scope, lambda: fact)

    @tool
    def get_source(source_system_id: int) -> SourceSystem | None:
        """The source system a record came from, or nothing if there is no such source."""
        return serve(
            "get_source", {"source_system_id": source_system_id}, REFERENCE,
            lambda: connector.get_source(source_system_id),
        )  # fmt: skip

    return server
