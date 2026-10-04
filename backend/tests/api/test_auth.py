from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.security import SESSION_COOKIE, issue_token, read_token
from app.main import create_app

from .conftest import EMAILS, PASSWORD, REF, make_settings


class TestLogin:
    def test_a_good_login_returns_the_person_their_permissions_and_a_session_cookie(
        self, anonymous
    ):
        response = anonymous.post(
            "/api/auth/login", json={"email": EMAILS["registrar"], "password": PASSWORD}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user"]["role"] == "registrar"
        assert "approve" in body["permissions"]
        assert body["scope"] == {"everything": True, "departments": []}
        cookie = response.headers["set-cookie"].lower()
        assert SESSION_COOKIE in cookie
        assert "httponly" in cookie  # script on the page can never read the session
        assert "samesite=lax" in cookie

    def test_the_email_is_not_case_sensitive(self, anonymous):
        response = anonymous.post(
            "/api/auth/login", json={"email": EMAILS["registrar"].upper(), "password": PASSWORD}
        )
        assert response.status_code == 200

    def test_a_wrong_password_and_an_unknown_email_look_identical(self, anonymous):
        wrong = anonymous.post(
            "/api/auth/login", json={"email": EMAILS["registrar"], "password": "nope"}
        )
        unknown = anonymous.post(
            "/api/auth/login", json={"email": "nobody@edss.test", "password": "nope"}
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()  # the form cannot reveal which emails have accounts
        assert SESSION_COOKIE not in wrong.headers.get("set-cookie", "")

    def test_a_hod_login_carries_their_department_scope(self, login):
        me = login("hod_cse").get("/api/auth/me").json()
        assert me["user"]["dept_code"] == "CSE"
        assert me["scope"] == {"everything": False, "departments": ["CSE"]}
        assert "approve" not in me["permissions"]

    def test_a_dean_login_carries_their_school_scope(self, login):
        me = login("dean").get("/api/auth/me").json()
        assert me["scope"]["departments"] == ["AIML", "CSE", "MCA"]


class TestSession:
    def test_me_needs_a_session(self, anonymous):
        assert anonymous.get("/api/auth/me").status_code == 401

    def test_logout_ends_the_session(self, login):
        client = login("registrar")
        assert client.get("/api/auth/me").status_code == 200
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/auth/me").status_code == 401

    def test_a_tampered_cookie_is_refused(self, anonymous):
        anonymous.cookies.set(SESSION_COOKIE, "not.a.token")
        assert anonymous.get("/api/auth/me").status_code == 401

    def test_a_token_signed_with_another_secret_is_refused(self, anonymous):
        anonymous.cookies.set(
            SESSION_COOKIE, issue_token(1, "some-other-secret-some-other-secret", 8)
        )
        assert anonymous.get("/api/auth/me").status_code == 401

    def test_an_expired_token_is_refused(self, app, anonymous):
        secret = app.state.edss.jwt_secret
        long_ago = datetime.now(UTC) - timedelta(hours=20)
        anonymous.cookies.set(SESSION_COOKIE, issue_token(1, secret, 8, now=long_ago))
        assert anonymous.get("/api/auth/me").status_code == 401

    def test_a_token_for_a_person_who_does_not_exist_is_refused(self, app, anonymous):
        anonymous.cookies.set(SESSION_COOKIE, issue_token(9999, app.state.edss.jwt_secret, 8))
        assert anonymous.get("/api/auth/me").status_code == 401

    def test_read_token_never_raises_on_garbage(self):
        assert read_token("", "secret") is None
        assert read_token("a.b.c", "secret") is None

    def test_the_cookie_secure_flag_follows_the_setting(self):
        secure = create_app(make_settings(cookie_secure=True), today=REF)
        with TestClient(secure) as client:
            response = client.post(
                "/api/auth/login", json={"email": EMAILS["registrar"], "password": PASSWORD}
            )
        assert "secure" in response.headers["set-cookie"].lower()


class TestDemoLogin:
    @pytest.fixture
    def demo(self):
        app = create_app(make_settings(edss_demo_login=True), today=REF)
        with TestClient(app) as client:
            yield client

    def test_it_does_not_exist_unless_the_flag_is_on(self, anonymous):
        assert anonymous.get("/api/auth/demo-users").status_code == 404
        response = anonymous.post("/api/auth/demo-login", json={"email": EMAILS["registrar"]})
        assert response.status_code == 404
        assert SESSION_COOKIE not in response.headers.get("set-cookie", "")

    def test_it_lists_the_seeded_personas_when_on(self, demo):
        users = demo.get("/api/auth/demo-users").json()
        assert {u["role"] for u in users} == {
            "registrar", "principal", "dean", "hod", "viewer", "admin"
        }  # fmt: skip
        assert all(u["email"].endswith("@edss.test") for u in users)

    def test_it_signs_in_a_seeded_persona_without_a_password(self, demo):
        response = demo.post("/api/auth/demo-login", json={"email": EMAILS["principal"]})
        assert response.status_code == 200
        assert demo.get("/api/auth/me").json()["user"]["role"] == "principal"

    def test_it_refuses_an_email_that_is_not_a_seeded_persona(self, demo):
        assert (
            demo.post("/api/auth/demo-login", json={"email": "ceo@example.com"}).status_code == 404
        )

    def test_it_never_exists_in_real_data_mode_whatever_the_flag_says(self):
        from app.api.deps import demo_login_enabled

        assert demo_login_enabled(make_settings(data_mode="real", edss_demo_login=True)) is False
        assert (
            demo_login_enabled(make_settings(data_mode="synthetic", edss_demo_login=True)) is True
        )
        assert (
            demo_login_enabled(make_settings(data_mode="synthetic", edss_demo_login=False)) is False
        )


class TestStartup:
    def test_real_data_mode_refuses_to_start_on_the_synthetic_services(self):
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            create_app(make_settings(data_mode="real"), today=REF)

    def test_without_a_seed_password_only_demo_sign_in_can_open_an_account(self):
        app = create_app(make_settings(edss_seed_password=None, edss_demo_login=True), today=REF)
        with TestClient(app) as client:
            guess = client.post(
                "/api/auth/login", json={"email": EMAILS["registrar"], "password": PASSWORD}
            )
            assert guess.status_code == 401
            assert (
                client.post("/api/auth/demo-login", json={"email": EMAILS["registrar"]}).status_code
                == 200
            )

    def test_a_missing_jwt_secret_gets_a_throwaway_one_in_synthetic_mode(self):
        app = create_app(make_settings(jwt_secret=None), today=REF)
        assert len(app.state.edss.jwt_secret) >= 32

    def test_the_seed_password_is_a_secret(self):
        assert "test-password" not in repr(make_settings())
        assert isinstance(make_settings().edss_seed_password, SecretStr)


class TestSignInAudit:
    """Each test gets a fresh app (pipeline), so failed sign-ins here cannot lock anyone elsewhere."""

    def _rows(self, pipeline, action):
        return pipeline.state.audit.rows(action=action)

    def test_a_sign_in_is_audited_with_the_role_and_never_the_password(self, pipeline):
        pipeline.login("registrar")
        rows = self._rows(pipeline, "auth.login")
        assert rows and rows[-1].actor_id == "registrar@edss.test"
        assert rows[-1].outputs == {"role": "registrar"}
        everything = " ".join(str(r.inputs) + str(r.outputs) for r in pipeline.state.audit.rows())
        assert PASSWORD not in everything

    def test_a_failed_sign_in_is_audited_under_the_email_tried(self, pipeline):
        client = TestClient(pipeline.app)
        client.post(
            "/api/auth/login", json={"email": "Principal@edss.test", "password": "wrong-password"}
        )
        row = self._rows(pipeline, "auth.login_failed")[-1]
        assert row.actor_id == "principal@edss.test" and row.outputs == {"locked": False}
        assert "wrong-password" not in str(row.inputs) + str(row.outputs)

    def test_signing_out_is_audited(self, pipeline):
        client = pipeline.login("dean")
        assert client.post("/api/auth/logout").status_code == 204
        assert self._rows(pipeline, "auth.logout")[-1].actor_id == "dean.computing@edss.test"


class TestLockout:
    def test_too_many_failures_lock_the_email_even_against_the_right_password(self, pipeline):
        client = TestClient(pipeline.app)
        bad = {"email": "principal@edss.test", "password": "not-it"}
        statuses = [client.post("/api/auth/login", json=bad).status_code for _ in range(5)]
        assert statuses == [401] * 5
        good = {"email": "principal@edss.test", "password": PASSWORD}
        locked = client.post("/api/auth/login", json=good)
        assert locked.status_code == 429
        assert int(locked.headers["retry-after"]) > 0
        assert "Try again" in locked.json()["detail"]
        assert pipeline.state.audit.rows(action="auth.locked")

    def test_another_person_can_still_sign_in_while_one_email_is_locked(self, pipeline):
        client = TestClient(pipeline.app)
        for _ in range(5):
            client.post(
                "/api/auth/login", json={"email": "principal@edss.test", "password": "not-it"}
            )
        assert pipeline.login("registrar").get("/api/auth/me").status_code == 200

    def test_a_success_before_the_limit_resets_the_count(self, pipeline):
        client = TestClient(pipeline.app)
        bad = {"email": "principal@edss.test", "password": "not-it"}
        good = {"email": "principal@edss.test", "password": PASSWORD}
        for _ in range(4):
            client.post("/api/auth/login", json=bad)
        assert client.post("/api/auth/login", json=good).status_code == 200
        for _ in range(4):
            assert client.post("/api/auth/login", json=bad).status_code == 401
        assert client.post("/api/auth/login", json=good).status_code == 200
