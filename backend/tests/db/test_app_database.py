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
