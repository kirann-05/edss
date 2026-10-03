from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_ok_and_data_mode():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "edss-backend"
    assert body["data_mode"] in {"synthetic", "real"}


def test_openapi_is_served_under_api_prefix():
    client = TestClient(create_app())
    assert client.get("/api/openapi.json").status_code == 200
