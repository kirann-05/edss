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


def test_every_answer_carries_the_protective_headers_errors_included():
    client = TestClient(create_app())
    for path, status in (("/api/health", 200), ("/api/kpis", 401), ("/api/nothing-here", 404)):
        response = client.get(path)
        assert response.status_code == status, path
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["content-security-policy"] == "frame-ancestors 'none'"
        assert response.headers["referrer-policy"] == "same-origin"
