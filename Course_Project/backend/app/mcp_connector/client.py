"""The `Connector` protocol over MCP, for the agents (rule 6).

The graph's nodes are synchronous and run in threads, while the MCP client is async. So this class
keeps one event loop on a thread of its own, holding one MCP session for its whole life, and each
method sends a tool call to that loop and waits for the answer. The four domain agents can call it
at the same time; their calls share the session.

A read the run's token does not allow comes back as `ConnectorRefused`, never as empty data, so an
agent cannot mistake "not allowed" for "no records".
"""

import asyncio
import contextlib
import threading
from collections.abc import Sequence
from datetime import date
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server import MCPServer
from pydantic import TypeAdapter

from app.agents.connector import HealthCellInfo, ScopeGrant
from app.domain.enums import Domain
from app.domain.models import (
    Department,
    KpiDefinition,
    KpiTarget,
    MetricFact,
    Publication,
    SourceSystem,
)
from app.mcp_connector.server import Calendar

_DEPARTMENTS = TypeAdapter(list[Department])
_DEFINITIONS = TypeAdapter(list[KpiDefinition])
_TARGETS = TypeAdapter(list[KpiTarget])
_FACTS = TypeAdapter(list[MetricFact])
_FACT = TypeAdapter(MetricFact | None)
_PUBLICATIONS = TypeAdapter(list[Publication])
_HEALTH = TypeAdapter(list[HealthCellInfo])
_GRANTS = TypeAdapter(list[ScopeGrant])
_SOURCE = TypeAdapter(SourceSystem | None)


class ConnectorRefused(PermissionError):
    """The connector would not answer: outside the run's areas, or an unknown tool or argument."""


class McpConnector:
    """A `Connector` that reads through an MCP server, by URL with a token, or in-process."""

    def __init__(
        self, server: str | MCPServer, token: str | None = None, timeout: float = 30.0
    ) -> None:
        self._server, self._token, self._timeout = server, token, timeout
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._client: Client | None = None
        self._stop: asyncio.Event | None = None
        self._session: asyncio.Future[None] | None = None
        self._calendar: Calendar | None = None
        ready = threading.Event()
        self._failure: BaseException | None = None
        self._session = asyncio.run_coroutine_threadsafe(self._hold(ready), self._loop)
        if not ready.wait(timeout) or self._failure:
            self.close()
            raise ConnectionError(f"could not open the MCP session: {self._failure}")

    async def _hold(self, ready: threading.Event) -> None:
        """Open the session and keep it open in one task, which is what the client's task groups
        need, until `close` sets the stop event."""
        self._stop = asyncio.Event()
        try:
            if isinstance(self._server, str):
                headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
                http = httpx2.AsyncClient(headers=headers, timeout=self._timeout)
                target: Any = streamable_http_client(self._server, http_client=http)
            else:
                target = self._server
            async with Client(target) as client:
                self._client = client
                ready.set()
                await self._stop.wait()
        except BaseException as error:  # reported by __init__, the thread must not die silently
            self._failure = error
            ready.set()

    def close(self) -> None:
        if self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._session is not None:
            # closing must not raise over whatever error led to it
            with contextlib.suppress(Exception):
                self._session.result(self._timeout)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(self._timeout)

    def __enter__(self) -> "McpConnector":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        if self._client is None:
            raise ConnectionError("the MCP session is not open")
        future = asyncio.run_coroutine_threadsafe(
            self._client.call_tool(name, arguments or {}), self._loop
        )
        result = future.result(self._timeout)
        if result.is_error:
            text = " ".join(getattr(c, "text", "") for c in result.content)
            raise ConnectorRefused(text or f"{name} was refused")
        return result.structured_content

    def _list(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        return self._call(name, arguments)["result"]

    def _calendar_now(self) -> Calendar:
        if self._calendar is None:
            self._calendar = Calendar.model_validate(self._call("get_calendar"))
        return self._calendar

    # --- the Connector protocol -------------------------------------------------------------
    def periods(self) -> tuple[str, ...]:
        return self._calendar_now().periods

    def current_period(self) -> str:
        return self._calendar_now().current_period

    def today(self) -> date:
        return self._calendar_now().today

    def stale_after_days(self) -> int:
        return self._calendar_now().stale_after_days

    def list_departments(self) -> Sequence[Department]:
        return _DEPARTMENTS.validate_python(self._list("list_departments"))

    def get_kpi_definitions(self) -> Sequence[KpiDefinition]:
        return _DEFINITIONS.validate_python(self._list("get_kpi_definitions"))

    def get_targets(self, period: str) -> Sequence[KpiTarget]:
        return _TARGETS.validate_python(self._list("get_targets", {"period": period}))

    def get_domain_metrics(self, domain: Domain, period: str) -> Sequence[MetricFact]:
        arguments = {"domain": domain.value, "period": period}
        return _FACTS.validate_python(self._list("get_domain_metrics", arguments))

    def get_publications(self, period: str) -> Sequence[Publication]:
        return _PUBLICATIONS.validate_python(self._list("get_publications", {"period": period}))

    def get_data_health(self, period: str) -> Sequence[HealthCellInfo]:
        return _HEALTH.validate_python(self._list("get_data_health", {"period": period}))

    def get_scope_grants(self) -> Sequence[ScopeGrant]:
        return _GRANTS.validate_python(self._list("get_scope_grants"))

    def get_fact(self, fact_id: int) -> MetricFact | None:
        return _FACT.validate_python(self._list("get_evidence", {"fact_id": fact_id}))

    def get_source(self, source_system_id: int) -> SourceSystem | None:
        arguments = {"source_system_id": source_system_id}
        return _SOURCE.validate_python(self._list("get_source", arguments))
