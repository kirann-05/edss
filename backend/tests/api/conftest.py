from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.main import create_app

REF = date(2026, 10, 1)
PASSWORD = "test-password-not-a-real-credential"  # only ever used against synthetic seed users

EMAILS = {
    "registrar": "registrar@edss.test",
    "principal": "principal@edss.test",
    "dean": "dean.computing@edss.test",
    "hod_cse": "hod.cse@edss.test",
    "hod_civil": "hod.civil@edss.test",
    "viewer": "council@edss.test",
    "admin": "admin@edss.test",
}


def make_settings(**overrides) -> Settings:
    values = {
        "data_mode": "synthetic",
        "edss_seed_password": SecretStr(PASSWORD),
        "edss_demo_login": False,
        "jwt_secret": SecretStr("test-secret-test-secret-test-secret-0123"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture(scope="session")
def app():
    return create_app(make_settings(), today=REF)


@pytest.fixture
def anonymous(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def login(app):
    """Returns a function: log in as a seeded persona by password and get a signed-in client."""
    clients = []

    def sign_in(persona: str) -> TestClient:
        client = TestClient(app)
        clients.append(client)
        response = client.post(
            "/api/auth/login", json={"email": EMAILS[persona], "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return client

    yield sign_in
    for client in clients:
        client.close()
