"""The ready-made demo state and its reset (docs/NEXT_STEPS.md D5)."""

import time

from fastapi.testclient import TestClient

from app.main import create_app

from .conftest import EMAILS, PASSWORD, REF, make_settings


def demo_app(**over):
    return create_app(make_settings(edss_demo_login=True, edss_demo_state=True, **over), today=REF)


def sign_in(app, persona="registrar") -> TestClient:
    client = TestClient(app)
    assert (
        client.post(
            "/api/auth/login", json={"email": EMAILS[persona], "password": PASSWORD}
        ).status_code
        == 200
    )
    return client


class TestReadyMadeState:
    def test_it_starts_with_one_approved_report_and_one_draft_waiting(self):
        client = sign_in(demo_app())
        assert client.get("/api/reports/current").json()["current"]["version"] == 1
        waiting = [
            b for b in client.get("/api/briefs").json() if b["status"] in ("draft", "escalated")
        ]
        assert len(waiting) == 1 and waiting[0]["validation_passed"]

    def test_both_went_through_the_real_gate_and_the_audit_log_says_they_were_seeded(self):
        app = demo_app()
        actions = [r.action for r in app.state.edss.audit.rows()]
        assert actions[0] == "demo.seed"
        assert {"plan.lock", "brief.draft", "brief.approve", "report.publish"} <= set(actions)
        assert app.state.edss.audit.verify().ok

    def test_the_seeded_draft_can_be_approved_and_then_rolled_back_to_version_one(self):
        client = sign_in(demo_app(), "principal")
        waiting = next(b for b in client.get("/api/briefs").json() if b["status"] == "draft")
        assert (
            client.post(f"/api/briefs/{waiting['id']}/decision", json={"kind": "approve"}).json()[
                "version"
            ]
            == 2
        )
        back = client.post(
            "/api/reports/rollback", json={"to_version": 1, "reason": "rehearsing the demo"}
        )
        assert back.status_code == 200 and back.json()["state"] == "current"

    def test_nothing_is_seeded_without_demo_mode(self):
        app = create_app(make_settings(edss_demo_login=False, edss_demo_state=True), today=REF)
        assert app.state.edss.governance.briefs() == []

    def test_nothing_is_seeded_unless_asked(self):
        app = create_app(make_settings(edss_demo_login=True), today=REF)
        assert app.state.edss.governance.briefs() == []


class TestReset:
    def test_reset_returns_to_the_ready_made_state_quickly(self):
        app = demo_app()
        client = sign_in(app)
        client.post("/api/runs", json={"request": "Prepare the leadership brief"})
        started = time.monotonic()
        assert client.post("/api/demo/reset").json() == {"reset": True, "seeded": True}
        assert time.monotonic() - started < 10
        client = sign_in(app)  # a reset is a fresh start, so sign in again
        assert (
            client.get("/api/runs").json() and len(client.get("/api/runs").json()) == 2
        )  # the two seeded runs only
        assert client.get("/api/reports/current").json()["current"]["version"] == 1
        actions = [r.action for r in app.state.edss.audit.rows()]
        assert (
            actions[0] == "demo.seed" and "demo.reset" in actions and "run.create" in actions[:-1]
        )

    def test_only_the_registrar_or_administrator_may_reset(self):
        app = demo_app()
        for persona in ("principal", "dean", "hod_cse", "viewer"):
            assert sign_in(app, persona).post("/api/demo/reset").status_code == 403
        assert sign_in(app, "admin").post("/api/demo/reset").status_code == 200

    def test_there_is_no_reset_outside_demo_mode(self):
        app = create_app(make_settings(edss_demo_login=False), today=REF)
        assert sign_in(app).post("/api/demo/reset").status_code == 404
