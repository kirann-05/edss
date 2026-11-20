import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.db.dataset_store import save_dataset
from app.kpi.loader import load_seed_definitions, load_seed_targets
from app.main import create_app
from app.synthetic.generator import generate

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
def app(request):
    """With EDSS_API_ON_DATABASE=1 (make test-api-db) the same API tests run against PostgreSQL:
    the shared app keeps its people, runs, briefs, versions and audit log there (L5f)."""
    if os.environ.get("EDSS_API_ON_DATABASE") != "1":
        return create_app(make_settings(), today=REF)
    engine = request.getfixturevalue("migrated")
    with engine.begin() as conn:
        save_dataset(
            conn, generate(reference_date=REF), load_seed_definitions(), load_seed_targets()
        )
    return create_app(make_settings(edss_database=True), today=REF)


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


class Pipeline:
    """A fresh app with runs executed inline, and helpers to drive the real HTTP API."""

    def __init__(self):
        self.app = create_app(make_settings(), today=REF, synchronous_runs=True)
        self._clients: list[TestClient] = []
        self.state = self.app.state.edss

    def login(self, persona: str) -> TestClient:
        client = TestClient(self.app)
        self._clients.append(client)
        response = client.post(
            "/api/auth/login", json={"email": EMAILS[persona], "password": PASSWORD}
        )
        assert response.status_code == 200, response.text
        return client

    def close(self):
        for client in self._clients:
            client.close()

    def start(
        self,
        client: TestClient,
        request="Governing Council brief for 2025-26 on everything",
        faults=None,
    ):
        """Create a run, accept the plan as it is, lock it, and return the finished run."""
        run = client.post("/api/runs", json={"request": request}).json()
        if run["status"] == "clarifying":
            run = client.post(f"/api/runs/{run['id']}/skip-questions").json()
        locked = client.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": faults or []})
        assert locked.status_code == 200, locked.text
        return client.get(f"/api/runs/{run['id']}").json()

    def draft(self, client: TestClient, **kw) -> tuple[str, str]:
        run = self.start(client, **kw)
        assert run["status"] == "awaiting_review", run
        return run["id"], run["brief_id"]


@pytest.fixture
def pipeline():
    pipe = Pipeline()
    yield pipe
    pipe.close()
