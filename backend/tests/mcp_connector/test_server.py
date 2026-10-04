"""The connector served over MCP answers exactly what the in-memory connector answers (Lab 5)."""

import asyncio
import importlib.util
from typing import Any

import pytest
from mcp import Client
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
from app.mcp_connector.server import Calendar, build_server

TOOLS = {
    "get_calendar", "list_departments", "get_kpi_definitions", "get_targets",
    "get_domain_metrics", "get_publications", "get_data_health", "get_scope_grants",
    "get_evidence", "get_source",
}  # fmt: skip


@pytest.fixture(scope="module")
def server(connector):
    return build_server(connector)


def call(server, name: str, arguments: dict[str, Any] | None = None, *, wrapped: bool = True):
    """A tool's structured result. Lists and optionals arrive as {"result": ...}, a model as itself."""
    async def go():
        async with Client(server) as client:
            return await client.call_tool(name, arguments or {})

    result = asyncio.run(go())
    assert not result.is_error, result.content
    return result.structured_content["result"] if wrapped else result.structured_content


def as_list(kind, value):
    return TypeAdapter(list[kind]).validate_python(value)


def test_it_offers_every_read_tool_and_nothing_else(server):
    async def go():
        async with Client(server) as client:
            return (await client.list_tools()).tools

    tools = asyncio.run(go())
    assert {t.name for t in tools} == TOOLS
    for tool in tools:
        assert tool.annotations.read_only_hint is True, tool.name
        assert tool.annotations.destructive_hint is False, tool.name
        assert tool.description, tool.name


def test_the_calendar_matches(server, connector):
    calendar = Calendar.model_validate(call(server, "get_calendar", wrapped=False))
    assert calendar.periods == connector.periods()
    assert calendar.current_period == connector.current_period()
    assert calendar.today == connector.today()
    assert calendar.stale_after_days == connector.stale_after_days()


def test_reference_data_matches(server, connector):
    assert as_list(Department, call(server, "list_departments")) == list(
        connector.list_departments()
    )
    assert as_list(KpiDefinition, call(server, "get_kpi_definitions")) == list(
        connector.get_kpi_definitions()
    )
    assert as_list(ScopeGrant, call(server, "get_scope_grants")) == list(
        connector.get_scope_grants()
    )


@pytest.mark.parametrize(
    "domain", [Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE]
)
def test_every_record_arrives_exactly_including_its_decimals(server, connector, domain):
    for period in connector.periods():
        sent = as_list(
            MetricFact,
            call(server, "get_domain_metrics", {"domain": domain.value, "period": period}),
        )
        assert sent == list(connector.get_domain_metrics(domain, period))
        assert all(
            str(a.value) == str(b.value)
            for a, b in zip(sent, connector.get_domain_metrics(domain, period), strict=True)
        )


def test_targets_publications_and_health_match(server, connector):
    for period in connector.periods():
        args = {"period": period}
        assert as_list(KpiTarget, call(server, "get_targets", args)) == list(
            connector.get_targets(period)
        )
        assert as_list(Publication, call(server, "get_publications", args)) == list(
            connector.get_publications(period)
        )
        assert as_list(HealthCellInfo, call(server, "get_data_health", args)) == list(
            connector.get_data_health(period)
        )


def test_evidence_and_sources_by_id(server, connector, store):
    fact = next(iter(store.facts_by_id.values()))
    assert MetricFact.model_validate(call(server, "get_evidence", {"fact_id": fact.id})) == fact
    assert call(server, "get_evidence", {"fact_id": 999_999_999}) is None
    source = connector.get_source(fact.source_system_id)
    assert (
        SourceSystem.model_validate(call(server, "get_source", {"source_system_id": source.id}))
        == source
    )


def test_an_unknown_tool_or_a_bad_argument_is_an_error_not_a_crash(server):
    async def go():
        async with Client(server) as client:
            return (
                await client.call_tool("drop_table", {}),
                await client.call_tool(
                    "get_domain_metrics", {"domain": "hostel", "period": "2025-26"}
                ),
            )

    unknown, bad = asyncio.run(go())
    assert unknown.is_error and bad.is_error


def test_no_opentelemetry_sdk_is_installed_so_the_sdks_spans_go_nowhere():
    # mcp depends on opentelemetry-api only. Without an SDK its spans are no-ops, which keeps
    # rule 7: nothing about a call leaves the machine. Installing an SDK must be a decision.
    assert importlib.util.find_spec("opentelemetry.sdk") is None
