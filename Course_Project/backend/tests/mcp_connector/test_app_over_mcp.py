"""L4e: the running app, with runs reading through its own MCP endpoint, one token per run."""

import socket
import time

import httpx2
import pytest

from app.main import create_app
from tests.api.conftest import REF, make_settings

REQUEST = "Placement and research brief for the Governing Council for 2025-26"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live():
    port = free_port()
    app = create_app(
        make_settings(
            edss_demo_login=True,
            edss_demo_state=True,
            connector_url=f"http://127.0.0.1:{port}/mcp/",
        ),
        today=REF,
    )
    import threading  # noqa: PLC0415

    from uvicorn import Config, Server  # noqa: PLC0415  only this test serves the whole app

    server = Server(Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started:
        assert time.monotonic() < deadline, "the app did not start"
        time.sleep(0.02)
    try:
        yield app, f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(5)


def finished(api, run_id):
    for _ in range(200):
        run = api.get(f"/api/runs/{run_id}").json()
        if run["status"] not in ("running",):
            return run
        time.sleep(0.05)
    raise AssertionError("the run did not finish")


def test_a_run_reads_every_area_through_mcp_with_its_own_token(live):
    app, base = live
    with httpx2.Client(base_url=base, timeout=30) as api:
        assert (
            api.post("/api/auth/demo-login", json={"email": "registrar@edss.test"}).status_code
            == 200
        )
        run = api.post("/api/runs", json={"request": REQUEST}).json()
        if run["status"] == "clarifying":
            run = api.post(f"/api/runs/{run['id']}/skip-questions").json()
        assert api.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": []}).status_code == 200
        done = finished(api, run["id"])
    assert done["status"] == "awaiting_review", done.get("error")

    rows = app.state.edss.audit.rows()
    calls = [r for r in rows if r.action == "connector.call" and r.run_id == run["id"]]
    read = {
        r.inputs["arguments"].get("domain")
        for r in calls
        if r.inputs["tool"] == "get_domain_metrics"
    }
    # exactly the plan's areas, plus the reference counts every ratio divides by
    assert read == {"placement", "research", "reference"}
    assert {r.actor_id for r in calls} == {"registrar@edss.test"}
    assert not [r for r in rows if r.action == "connector.refused"]
    assert app.state.edss.audit.verify().ok


def test_the_token_is_gone_when_the_run_stops(live):
    app, base = live
    # every token minted so far belonged to a run that has finished
    with httpx2.Client(base_url=base, timeout=10) as raw:
        hello = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}},
        }  # fmt: skip
        response = raw.post(
            "/mcp/", json=hello, headers={"Accept": "application/json, text/event-stream"}
        )
    assert response.status_code == 401


def test_the_demos_ready_made_runs_read_directly_and_the_rest_of_the_app_is_unchanged(live):
    app, base = live
    seeded = [r for r in app.state.edss.runs.runs() if r.reads_direct]
    assert len(seeded) == 2
    seeded_ids = {r.id for r in seeded}
    assert not [
        r
        for r in app.state.edss.audit.rows()
        if r.action == "connector.call" and r.run_id in seeded_ids
    ]
    with httpx2.Client(base_url=base, timeout=10) as api:
        api.post("/api/auth/demo-login", json={"email": "registrar@edss.test"})
        assert api.get("/api/kpis").status_code == 200
