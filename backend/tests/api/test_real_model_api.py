"""The API when the model is a real server rather than the canned one."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

from ..agents.test_llm_http import Server
from .conftest import EMAILS, PASSWORD, REF, make_settings


@pytest.fixture
def server():
    s = Server()
    yield s
    s.close()


def client_for(**settings) -> TestClient:
    app = create_app(make_settings(**settings), today=REF, synchronous_runs=True)
    client = TestClient(app)
    response = client.post(
        "/api/auth/login", json={"email": EMAILS["registrar"], "password": PASSWORD}
    )
    assert response.status_code == 200
    return client


def real(server_or_url, **over):
    url = server_or_url if isinstance(server_or_url, str) else server_or_url.url
    return {"llm_provider": "ollama", "llm_model": "qwen3.5:4b", "llm_base_url": url, **over}


class TestStatus:
    def test_the_canned_model_is_named_as_such_and_needs_no_server(self):
        body = client_for().get("/api/system/status").json()
        assert body["llm_is_fake"] is True and body["llm_name"] == "fake-drafter"
        assert body["llm_is_local"] is True and body["llm_reachable"] is None

    def test_a_local_model_that_answers_is_reported_reachable(self, server):
        body = client_for(**real(server)).get("/api/system/status").json()
        assert body["llm_is_fake"] is False and body["llm_name"] == "ollama:qwen3.5:4b"
        assert body["llm_is_local"] is True and body["llm_reachable"] is True

    def test_a_model_that_is_not_answering_is_reported_so_before_anyone_starts_a_run(self):
        body = client_for(**real("http://127.0.0.1:9/v1")).get("/api/system/status").json()
        assert body["llm_reachable"] is False

    def test_a_model_on_another_machine_is_reported_as_not_local(self):
        client = client_for(
            **real("http://models.example.com/v1", llm_provider="hosted", allow_hosted_llm=True)
        )
        assert client.get("/api/system/status").json()["llm_is_local"] is False


class TestWhenTheModelFails:
    def test_starting_a_run_with_the_server_down_is_a_503_that_says_what_to_do(self):
        response = client_for(**real("http://127.0.0.1:9/v1")).post(
            "/api/runs", json={"request": "Prepare the leadership brief"}
        )
        assert response.status_code == 503
        assert (
            "not answering" in response.json()["detail"]
            and "LLM_PROVIDER=fake" in response.json()["detail"]
        )

    def test_a_model_that_only_ever_returns_nonsense_does_not_stop_planning(self, server):
        # the planner reads the request with rules first (D30), so an unusable model answer
        # costs three bounded tries and the rules' questions, not a failed request
        for _ in range(6):
            server.answer("not json")
        response = client_for(**real(server)).post(
            "/api/runs", json={"request": "Prepare the leadership brief"}
        )
        assert response.status_code == 201
        assert [q["id"] for q in response.json()["questions"]] == ["period", "scope", "audience"]
        assert len(server.requests) == 3  # the first try and two repairs, then it stopped

    def test_a_run_whose_model_dies_midway_is_marked_stopped_and_can_be_resumed(self, server):
        # the words say everything, so the rules plan it without asking the model (D30), and the
        # run reaches the graph, where the server has nothing to say
        client = client_for(**real(server))
        run = client.post(
            "/api/runs", json={"request": "Placement brief for the Principal for 2025-26"}
        ).json()
        assert run["status"] == "planning" and run["plan"]["domains"] == ["placement"]
        assert server.requests == []
        # the options step now asks the server, which has nothing left to say
        locked = client.post(f"/api/runs/{run['id']}/plan/lock", json={"faults": []})
        assert locked.status_code == 200
        stopped = client.get(f"/api/runs/{run['id']}").json()
        assert stopped["status"] == "failed" and stopped["error"]
        events = client.get(f"/api/runs/{run['id']}/trace").json()["events"]
        assert any(e["state"] == "failed" for e in events)
