"""Admin over HTTP: people and roles for the Administrator, data access for the Registrar."""

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import Role
from app.domain.models import AppUser
from app.services.users import UserError

from .conftest import PASSWORD

NEW_PASSWORD = "a-long-new-password"


def new_hod(**overrides):
    body = {
        "email": "hod.ece@edss.test",
        "name": "Dr. Meera Kulkarni",
        "role": "hod",
        "dept_code": "ECE",
        "password": NEW_PASSWORD,
    }
    return {**body, **overrides}


def sign_in(pipeline, email, password):
    client = TestClient(pipeline.app)
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    return client, response


class TestPeople:
    def test_only_the_administrator_manages_people(self, pipeline):
        assert pipeline.login("admin").get("/api/admin/users").status_code == 200
        for persona in ("registrar", "principal", "hod_cse", "viewer"):
            assert pipeline.login(persona).get("/api/admin/users").status_code == 403

    def test_a_new_person_can_sign_in_with_the_password_they_were_given(self, pipeline):
        admin = pipeline.login("admin")
        created = admin.post("/api/admin/users", json=new_hod())
        assert created.status_code == 201
        assert created.json()["dept_code"] == "ECE" and created.json()["active"] is True
        _, response = sign_in(pipeline, "hod.ece@edss.test", NEW_PASSWORD)
        assert response.status_code == 200 and response.json()["scope"]["departments"] == ["ECE"]

    def test_creating_a_person_is_audited_without_the_password(self, pipeline):
        pipeline.login("admin").post("/api/admin/users", json=new_hod())
        row = pipeline.state.audit.rows(action="user.create")[-1]
        assert row.actor_id == "admin@edss.test" and row.outputs["role"] == "hod"
        assert NEW_PASSWORD not in str(row.inputs) + str(row.outputs)

    @pytest.mark.parametrize(
        ("change", "reason"),
        [
            ({"email": "registrar@edss.test"}, "already has that email"),
            ({"email": "not an email"}, "not an email"),
            ({"password": "short"}, "at least 12"),
            ({"dept_code": None}, "a HOD must have a department"),
            ({"dept_code": "ASTRO"}, "no department"),
            ({"role": "dean", "dept_code": None}, "a Dean must have a school"),
        ],
    )
    def test_a_person_that_breaks_the_rules_is_refused_with_the_reason(
        self, pipeline, change, reason
    ):
        response = pipeline.login("admin").post("/api/admin/users", json=new_hod(**change))
        assert response.status_code == 422
        assert reason in response.json()["detail"]

    def test_a_role_change_takes_effect_on_the_next_request(self, pipeline):
        hod = pipeline.login("hod_cse")
        assert hod.get("/api/runs").status_code == 403
        admin = pipeline.login("admin")
        users = {u["email"]: u for u in admin.get("/api/admin/users").json()}
        target = users["hod.cse@edss.test"]
        changed = admin.patch(
            f"/api/admin/users/{target['id']}",
            json={
                "role": "dean",
                "dept_code": None,
                "school": "School of Computer Science and Engineering",
            },
        )
        assert changed.status_code == 200 and changed.json()["role"] == "dean"
        assert hod.get("/api/runs").status_code == 200  # same session, new role
        row = pipeline.state.audit.rows(action="user.update")[-1]
        assert row.outputs["changes"]["role"] == ["hod", "dean"]

    def test_an_administrator_cannot_demote_or_switch_off_themselves(self, pipeline):
        admin = pipeline.login("admin")
        me = admin.get("/api/auth/me").json()["user"]
        for change in ({"role": "viewer"}, {"active": False}):
            response = admin.patch(f"/api/admin/users/{me['id']}", json=change)
            assert response.status_code == 422 and "your own" in response.json()["detail"]

    def test_switching_someone_off_ends_their_session_at_once(self, pipeline):
        dean = pipeline.login("dean")
        assert dean.get("/api/auth/me").status_code == 200
        admin = pipeline.login("admin")
        target = next(u for u in admin.get("/api/admin/users").json() if u["role"] == "dean")
        assert (
            admin.patch(f"/api/admin/users/{target['id']}", json={"active": False}).status_code
            == 200
        )
        assert dean.get("/api/auth/me").status_code == 401
        _, again = sign_in(pipeline, target["email"], PASSWORD)
        assert again.status_code == 401

    def test_a_password_reset_ends_old_sessions_and_the_new_password_works(self, pipeline):
        principal = pipeline.login("principal")
        admin = pipeline.login("admin")
        target = next(u for u in admin.get("/api/admin/users").json() if u["role"] == "principal")
        reset = admin.post(
            f"/api/admin/users/{target['id']}/password", json={"password": NEW_PASSWORD}
        )
        assert reset.status_code == 204
        assert principal.get("/api/auth/me").status_code == 401
        assert sign_in(pipeline, target["email"], PASSWORD)[1].status_code == 401
        assert sign_in(pipeline, target["email"], NEW_PASSWORD)[1].status_code == 200
        row = pipeline.state.audit.rows(action="user.password_reset")[-1]
        assert NEW_PASSWORD not in str(row.inputs) + str(row.outputs)

    def test_a_short_new_password_is_refused(self, pipeline):
        admin = pipeline.login("admin")
        target = admin.get("/api/admin/users").json()[0]
        response = admin.post(
            f"/api/admin/users/{target['id']}/password", json={"password": "short"}
        )
        assert response.status_code == 422


def test_the_last_active_administrator_must_stay_one(pipeline):
    store = pipeline.state.users
    admin = store.by_email("admin@edss.test")
    # someone else with the power to manage people, acting on the only administrator
    other = AppUser(id=999, email="x@edss.test", name="X", role=Role.ADMIN)
    with pytest.raises(UserError, match="last active administrator"):
        store.update(admin.id, {"role": Role.VIEWER}, acting=other)
    with pytest.raises(UserError, match="last active administrator"):
        store.update(admin.id, {"active": False}, acting=other)


class TestDataAccess:
    def test_only_the_registrar_manages_data_access(self, pipeline):
        assert pipeline.login("registrar").get("/api/admin/scope-grants").status_code == 200
        for persona in ("admin", "principal", "dean"):
            assert pipeline.login(persona).get("/api/admin/scope-grants").status_code == 403

    def test_every_area_starts_with_an_active_grant(self, pipeline):
        grants = pipeline.login("registrar").get("/api/admin/scope-grants").json()
        assert {g["domain"] for g in grants} == {"academic", "research", "placement", "finance"}
        assert all(g["state"] == "active" for g in grants)

    def test_a_revoked_area_stops_a_run_before_any_data_is_read(self, pipeline):
        registrar = pipeline.login("registrar")
        revoked = registrar.post("/api/admin/scope-grants/placement/revoke").json()
        assert next(g for g in revoked if g["domain"] == "placement")["state"] == "revoked"
        run = pipeline.start(
            registrar, request="Placement brief for the Governing Council for 2025-26"
        )
        assert run["status"] == "failed" and "Placement" in run["error"]
        assert pipeline.state.audit.rows(action="scope.revoke")

    def test_granting_again_restores_access_with_an_expiry(self, pipeline):
        registrar = pipeline.login("registrar")
        registrar.post("/api/admin/scope-grants/placement/revoke")
        today = pipeline.state.store.today
        granted = registrar.post(
            "/api/admin/scope-grants",
            json={"domain": "placement", "expires_on": str(today.replace(year=today.year + 1))},
        )
        assert granted.status_code == 200 and granted.json()["state"] == "active"
        run = pipeline.start(
            registrar, request="Placement brief for the Governing Council for 2025-26"
        )
        assert run["status"] == "awaiting_review"

    def test_an_expiry_in_the_past_is_refused(self, pipeline):
        response = pipeline.login("registrar").post(
            "/api/admin/scope-grants", json={"domain": "finance", "expires_on": "2020-01-01"}
        )
        assert response.status_code == 422

    def test_both_admin_roles_see_the_choices_and_others_do_not(self, pipeline):
        for persona in ("admin", "registrar"):
            body = pipeline.login(persona).get("/api/admin/options").json()
            assert "hod" in body["roles"] and body["min_password"] == 12
            assert {d["code"] for d in body["departments"]} >= {"CSE", "CIVIL"}
        assert pipeline.login("dean").get("/api/admin/options").status_code == 403
