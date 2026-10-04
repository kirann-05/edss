"""Over real HTTP: a run's token reads its own areas only, and every call is one audit row (Lab 5)."""

import asyncio
import threading
import time
from contextlib import contextmanager

import httpx2
import pytest
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.agents.runtime import digest
from app.domain.enums import Domain
from app.governance.audit import AuditLog
from app.mcp_connector.server import build_server
from app.mcp_connector.tokens import RunTokens


@contextmanager
def serving(app):
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the MCP server did not start"
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        thread.join(5)


class Clock:
    """Real time, which the SDK's own expiry check also uses, but one the test can move forward."""

    def __init__(self):
        self.start = self.now = time.time()

    def __call__(self):
        return self.now


@pytest.fixture(scope="module")
def setup(connector):
    audit, clock = AuditLog(), Clock()
    tokens = RunTokens(ttl_seconds=60, clock=clock)
    server = build_server(connector, audit=audit, tokens=tokens, public_url="http://127.0.0.1")
    with serving(server.streamable_http_app()) as url:
        yield url, tokens, audit, clock


def call(url, token, name, arguments=None):
    async def go():
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        transport = streamable_http_client(
            url, http_client=httpx2.AsyncClient(headers=headers, timeout=30)
        )
        async with Client(transport) as client:
            return await client.call_tool(name, arguments or {})

    return asyncio.run(go())


def rows(audit, action):
    return [r for r in audit.rows() if r.action == action]


def test_a_token_reads_the_areas_its_run_was_granted(setup, connector):
    url, tokens, audit, _ = setup
    token = tokens.mint("run-1", "registrar@edss.test", [Domain.PLACEMENT])
    period = connector.current_period()
    result = call(url, token, "get_domain_metrics", {"domain": "placement", "period": period})
    assert not result.is_error
    assert len(result.structured_content["result"]) == len(
        connector.get_domain_metrics(Domain.PLACEMENT, period)
    )


def test_a_read_outside_the_runs_areas_is_refused_and_audited(setup, connector):
    url, tokens, audit, _ = setup
    token = tokens.mint("run-2", "registrar@edss.test", [Domain.PLACEMENT])
    before = len(rows(audit, "connector.refused"))
    result = call(
        url,
        token,
        "get_domain_metrics",
        {"domain": "finance", "period": connector.current_period()},
    )
    assert result.is_error and "read:finance" in result.content[0].text
    refused = rows(audit, "connector.refused")[before:]
    assert len(refused) == 1
    assert refused[0].run_id == "run-2" and refused[0].actor_id == "registrar@edss.test"
    assert (
        refused[0].inputs["tool"] == "get_domain_metrics"
        and refused[0].inputs["needs"] == "read:finance"
    )


def test_a_record_is_only_as_visible_as_its_area(setup, store):
    url, tokens, _, _ = setup
    token = tokens.mint("run-3", "registrar@edss.test", [Domain.PLACEMENT])
    finance = next(f for f in store.facts_by_id.values() if f.domain is Domain.FINANCE)
    placement = next(f for f in store.facts_by_id.values() if f.domain is Domain.PLACEMENT)
    assert call(url, token, "get_evidence", {"fact_id": finance.id}).is_error
    assert not call(url, token, "get_evidence", {"fact_id": placement.id}).is_error


def test_every_call_is_one_audit_row_with_a_hash_of_what_was_returned(setup):
    url, tokens, audit, _ = setup
    token = tokens.mint("run-4", "principal@edss.test", [])
    before = len(rows(audit, "connector.call"))
    result = call(url, token, "list_departments")
    calls = rows(audit, "connector.call")[before:]
    assert len(calls) == 1
    row = calls[0]
    assert row.run_id == "run-4" and row.actor_id == "principal@edss.test"
    assert row.inputs == {"tool": "list_departments", "arguments": {}}
    assert row.outputs["result_hash"] == digest(result.structured_content["result"])
    assert row.outputs["items"] == len(result.structured_content["result"])
    assert audit.verify().ok


@pytest.mark.parametrize("how", ["none", "unknown", "revoked", "expired"])
def test_no_token_an_unknown_one_a_revoked_one_or_an_expired_one_gets_nothing(setup, how):
    url, tokens, _, clock = setup
    token = tokens.mint(f"run-{how}", "registrar@edss.test", [Domain.PLACEMENT])
    if how == "none":
        token = None
    elif how == "unknown":
        token = "not-a-token"
    elif how == "revoked":
        tokens.revoke(f"run-{how}")
    elif how == "expired":
        clock.now += 61
    try:
        status = initialize(url, token)
    finally:
        clock.now = clock.start
    assert status == 401  # refused before any tool can run


def initialize(url, token):
    """The first message any client sends, made by hand so the HTTP status can be seen."""
    headers = {"Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    hello = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}},
    }  # fmt: skip
    return httpx2.post(url, json=hello, headers=headers, timeout=10).status_code


def test_the_same_request_with_a_good_token_is_let_in(setup):
    url, tokens, _, _ = setup
    assert initialize(url, tokens.mint("run-ok", "registrar@edss.test", [])) == 200
