"""L5d: with EDSS_DATABASE on, people, grants and the data mode live in PostgreSQL."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.dataset_store import save_dataset
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.main import create_app
from app.synthetic.generator import generate
from tests.api.conftest import REF, make_settings

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def database(migrated):
    with migrated.begin() as conn:
        conn.execute(text("truncate app_user, scope_grant, system_config"))
        save_dataset(
            conn,
            generate(reference_date=date(2026, 10, 1)),
            load_seed_definitions(),
            load_seed_targets(),
        )
    return migrated


def start(**overrides):
    app = create_app(
        make_settings(edss_database=True, edss_demo_login=True, **overrides), today=REF
    )
    return TestClient(app), app


def saved(database, run_id, status="awaiting_review"):
    """Wait until the run's own last save has reached the table, so a test edit is not overwritten."""
    import time

    for _ in range(100):
        with database.connect() as conn:
            if (
                conn.execute(
                    text("select status from run where id = :id"), {"id": run_id}
                ).scalar_one()
                == status
            ):
                return
        time.sleep(0.05)
    raise AssertionError(f"{run_id} never reached {status} in the table")


def signed_in(client, email):
    assert client.post("/api/auth/demo-login", json={"email": email}).status_code == 200
    return client


def test_the_app_runs_from_the_database_with_the_same_figures_as_from_memory(database):
    db_client, _ = start()
    memory = TestClient(create_app(make_settings(edss_demo_login=True), today=REF))
    from_db = signed_in(db_client, "registrar@edss.test").get("/api/kpis").json()
    from_memory = signed_in(memory, "registrar@edss.test").get("/api/kpis").json()
    assert from_db == from_memory


def test_flipping_the_data_mode_in_the_database_takes_effect_with_no_restart(database):
    client, app = start()
    signed_in(client, "registrar@edss.test")
    assert client.get("/api/system/status").json()["data_mode"] == "synthetic"
    with database.begin() as conn:
        conn.execute(text("update system_config set value = 'real' where key = 'data_mode'"))
    try:
        assert app.state.edss.system_config.data_mode() == "real"
        assert client.get("/api/system/status").json()["data_mode"] == "real"
    finally:
        with database.begin() as conn:
            conn.execute(
                text("update system_config set value = 'synthetic' where key = 'data_mode'")
            )


def test_a_person_added_and_their_password_survive_a_restart(database):
    client, _ = start()
    signed_in(client, "admin@edss.test")
    made = client.post(
        "/api/admin/users",
        json={"email": "new.dean@edss.test", "name": "A New Dean", "role": "dean",
              "school": "School of Mechanical Engineering", "password": "a-long-test-password"},
    )  # fmt: skip
    assert made.status_code == 201, made.text
    restarted, _ = start()
    signed = restarted.post(
        "/api/auth/login", json={"email": "new.dean@edss.test", "password": "a-long-test-password"}
    )
    assert signed.status_code == 200, signed.text
    with database.connect() as conn:
        row = conn.execute(
            text("select school, password_hash from app_user where email = 'new.dean@edss.test'")
        ).one()
    assert row.school == "School of Mechanical Engineering"
    assert "a-long-test-password" not in row.password_hash


def test_a_password_reset_ends_sessions_even_across_a_restart(database):
    client, app = start()
    signed_in(client, "admin@edss.test")
    dean = app.state.edss.users.by_email("dean.computing@edss.test")
    before = app.state.edss.users.session_version(dean.id)
    reset = client.post(
        f"/api/admin/users/{dean.id}/password", json={"password": "another-long-password"}
    )
    assert reset.status_code == 204, reset.text
    _, restarted = start()
    assert restarted.state.edss.users.session_version(dean.id) == before + 1


def test_a_revoked_grant_stays_revoked_after_a_restart(database):
    client, _ = start()
    signed_in(client, "registrar@edss.test")
    assert client.post("/api/admin/scope-grants/finance/revoke").status_code == 200
    restarted, _ = start()
    grants = signed_in(restarted, "registrar@edss.test").get("/api/admin/scope-grants").json()
    finance = [g for g in grants if g["domain"] == "finance"]
    assert finance and all(g["state"] != "active" for g in finance)


def test_refreshing_from_the_page_is_refused_plainly_in_database_mode(database):
    client, _ = start()
    response = signed_in(client, "registrar@edss.test").post("/api/data/refresh")
    assert response.status_code == 409 and "make seed-db" in response.json()["detail"]


def test_the_apps_audit_rows_are_in_the_table_and_survive_a_restart(database):
    client, _ = start()
    signed_in(client, "council@edss.test")
    with database.connect() as conn:
        found = conn.execute(
            text(
                "select count(*) from audit_log where action = 'auth.demo_login' and actor_id = 'council@edss.test'"
            )
        ).scalar_one()
    assert found >= 1
    _, restarted = start()
    assert restarted.state.edss.audit.verify().ok
    assert any(
        r.actor_id == "council@edss.test"
        for r in restarted.state.edss.audit.rows(action="auth.demo_login")
    )


def test_runs_briefs_versions_and_a_rollback_survive_a_restart(database):
    from app.governance.service import Decision
    from app.services.demo_state import DRAFT_REQUEST, REPORT_REQUEST, _draft

    _, app = start()
    state = app.state.edss
    principal = state.users.by_email("principal@edss.test")
    # an earlier test revoked finance, and that stuck, as it should
    from app.domain.enums import Domain

    state.scopes.grant(Domain.FINANCE, "registrar@edss.test", REF)
    first = _draft(state, REPORT_REQUEST)
    second = _draft(state, DRAFT_REQUEST)
    v1 = state.governance.decide(
        first.brief_id, principal, Decision(kind="approve")
    ).version.version
    v2 = state.governance.decide(
        second.brief_id, principal, Decision(kind="approve")
    ).version.version
    state.governance.rollback(principal, v1, "Restoring the first for the test")

    _, restarted = start()
    again = restarted.state.edss
    assert again.runs.get(first.id).brief_id == first.brief_id
    assert again.governance.get(second.brief_id).status.value == "rolled_back"
    assert [v.version for v in again.governance.versions()][-2:] == [v1, v2]
    assert again.governance.state_of(v1) == "current"
    assert again.governance.state_of(v2) == "rolled_back"
    assert again.audit.verify().ok


def test_a_run_working_when_the_server_stopped_is_shown_as_stopped(database):
    _, app = start()
    for run in app.state.edss.runs.runs():
        saved(database, run.id, run.status.value)
    with database.begin() as conn:
        conn.execute(
            text(
                "update run set status = 'running', detail = jsonb_set(detail, '{status}', '\"running\"') "
                "where id = (select id from run order by created_at desc limit 1)"
            )
        )
    _, restarted = start()
    stopped = [r for r in restarted.state.edss.runs.runs() if r.error and "restarted" in r.error]
    assert stopped and all(r.status.value == "failed" for r in stopped)


def test_a_draft_waiting_for_a_person_is_approved_after_a_restart_and_its_run_finishes(database):
    from app.governance.service import Decision
    from app.services.demo_state import DRAFT_REQUEST, _draft, _finish

    _, app = start()
    waiting = _draft(app.state.edss, DRAFT_REQUEST)
    assert waiting.status.value == "awaiting_review"

    _, restarted = start()  # a new process: nothing in memory, the checkpoint is in the database
    state = restarted.state.edss
    principal = state.users.by_email("principal@edss.test")
    result = state.governance.decide(waiting.brief_id, principal, Decision(kind="approve"))
    state.runs.on_decision(
        waiting.id, result.brief.status.value, result.version.version, principal.email
    )
    done = _finish(state, state.runs.get(waiting.id))
    assert done.status.value == "completed", done.error


def test_a_run_stopped_by_a_restart_resumes_from_its_last_step(database):
    from app.services.demo_state import DRAFT_REQUEST, _draft, _finish

    _, app = start()
    run = _draft(app.state.edss, DRAFT_REQUEST)
    saved(database, run.id)
    with database.begin() as conn:
        conn.execute(
            text(
                "update run set status = 'running', "
                "detail = jsonb_set(detail, '{status}', '\"running\"') where id = :id"
            ),
            {"id": run.id},
        )
    _, restarted = start()
    state = restarted.state.edss
    assert state.runs.get(run.id).status.value == "failed"
    registrar = state.users.by_email("registrar@edss.test")
    state.runs.resume(registrar, run.id)
    back = _finish(state, state.runs.get(run.id))
    assert back.status.value == "awaiting_review", back.error
    # the domain agents had finished before the stop, so the resume did not run them again
    nodes = {e.node for e in state.events.all(run.id)}
    assert not [n for n in nodes if n.startswith("domain:")]


def test_a_published_report_stays_in_the_archive_across_a_restart(database):
    from app.governance.service import Decision
    from app.services.demo_state import DRAFT_REQUEST, _draft

    _, app = start()
    state = app.state.edss
    principal = state.users.by_email("principal@edss.test")
    version = state.governance.decide(
        _draft(state, DRAFT_REQUEST).brief_id, principal, Decision(kind="approve")
    ).version
    _, restarted = start()
    assert f"report-v{version.version}" in [p.id for p in restarted.state.edss.archive.all()]


def test_stopping_the_app_closes_its_database_connections(database):
    app = create_app(make_settings(edss_database=True), today=REF)
    with TestClient(app):  # runs the lifespan: start, then stop
        pool = app.state.edss.on_shutdown[0].__self__
        assert not pool.closed
    assert pool.closed
