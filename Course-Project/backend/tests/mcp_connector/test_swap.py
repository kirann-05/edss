"""The swap test (Lab 5): the agents get the same answers, and the same brief, through MCP."""

from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import GraphDeps, build_graph, initial_state, run_config
from app.agents.llm import FakeLLM
from app.agents.models import ValidationReport
from app.agents.runtime import RunEvents, Runtime
from app.agents.skills.plan_skill import lock_plan
from app.domain.enums import Domain
from app.governance.audit import AuditLog
from app.governance.service import GovernanceService
from app.mcp_connector.client import ConnectorRefused, McpConnector
from app.mcp_connector.server import build_server
from app.mcp_connector.tokens import RunTokens
from tests.mcp_connector.test_scope import serving

AREAS = (Domain.ACADEMIC, Domain.RESEARCH, Domain.PLACEMENT, Domain.FINANCE)


def run_graph(connector, plan, run_id="run-1"):
    audit = AuditLog()
    governance = GovernanceService(audit, lambda doc: ValidationReport(passed=True, checks=()))
    deps = GraphDeps(
        connector=connector,
        model=FakeLLM("drafter"),
        runtime=Runtime(audit, RunEvents()),
        create_draft=lambda **kw: governance.create_draft(**kw).id,
    )
    graph = build_graph(deps, InMemorySaver())
    locked = lock_plan(plan, datetime(2026, 10, 3, tzinfo=UTC))
    return graph.invoke(
        initial_state(run_id, locked, "registrar@edss.test", None), run_config(run_id)
    )


@pytest.fixture(scope="module")
def in_process(connector):
    with McpConnector(build_server(connector)) as mcp:
        yield mcp


def test_every_method_answers_the_same_both_ways(in_process, connector, store):
    assert in_process.periods() == connector.periods()
    assert in_process.current_period() == connector.current_period()
    assert in_process.today() == connector.today()
    assert in_process.stale_after_days() == connector.stale_after_days()
    assert list(in_process.list_departments()) == list(connector.list_departments())
    assert list(in_process.get_kpi_definitions()) == list(connector.get_kpi_definitions())
    assert list(in_process.get_scope_grants()) == list(connector.get_scope_grants())
    for period in connector.periods():
        assert list(in_process.get_targets(period)) == list(connector.get_targets(period))
        assert list(in_process.get_publications(period)) == list(connector.get_publications(period))
        assert list(in_process.get_data_health(period)) == list(connector.get_data_health(period))
        for domain in AREAS:
            assert list(in_process.get_domain_metrics(domain, period)) == list(
                connector.get_domain_metrics(domain, period)
            )
    fact = next(iter(store.facts_by_id.values()))
    assert in_process.get_fact(fact.id) == fact and in_process.get_fact(999_999_999) is None
    assert in_process.get_source(fact.source_system_id) == connector.get_source(
        fact.source_system_id
    )


def test_a_whole_run_gives_identical_kpis_and_brief_through_mcp(in_process, connector, plan):
    direct = run_graph(connector, plan)
    through = run_graph(in_process, plan)
    assert through["figures"] == direct["figures"]
    assert through["brief"] == direct["brief"]
    assert [r["passed"] for r in through["reports"]] == [True]


def test_over_http_with_a_run_token_the_run_is_identical_and_every_read_is_audited(connector, plan):
    audit, tokens = AuditLog(), RunTokens()
    server = build_server(connector, audit=audit, tokens=tokens, public_url="http://127.0.0.1")
    token = tokens.mint("run-http", "registrar@edss.test", plan.domains)
    with serving(server.streamable_http_app()) as url, McpConnector(url, token) as mcp:
        through = run_graph(mcp, plan, run_id="run-http")
    assert through["figures"] == run_graph(connector, plan, run_id="run-http")["figures"]
    calls = [r for r in audit.rows() if r.action == "connector.call" and r.run_id == "run-http"]
    tools = {r.inputs["tool"] for r in calls}
    assert "get_domain_metrics" in tools and len(calls) >= 4
    assert not [r for r in audit.rows() if r.action == "connector.refused"]
    assert audit.verify().ok


def test_a_run_whose_token_lacks_an_area_cannot_read_it(connector, plan):
    tokens = RunTokens()
    server = build_server(connector, audit=AuditLog(), tokens=tokens, public_url="http://127.0.0.1")
    token = tokens.mint("run-narrow", "registrar@edss.test", [Domain.PLACEMENT])
    with serving(server.streamable_http_app()) as url, McpConnector(url, token) as mcp:
        assert mcp.get_domain_metrics(Domain.PLACEMENT, plan.period_year)
        with pytest.raises(ConnectorRefused, match="read:finance"):
            mcp.get_domain_metrics(Domain.FINANCE, plan.period_year)
